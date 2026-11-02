"""Le cœur du labo : faire avancer une session tour par tour."""
from __future__ import annotations

import json
import re
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path

from . import providers
from .budget import Budget, BudgetDepasse
from .codage import Codage
from .config import Config
from .journal import Journal, maintenant
from .selfupdate import AutoMaj, extraire_blocs

DOSSIER_ROLES = Path(__file__).parent / "roles"


class Labo:
    def __init__(self, config: Config):
        self.config = config
        self.racine = config.racine
        self.journal = Journal(self.racine)
        self.budget = Budget(config.budget, self.racine / ".thot")
        self.automaj = AutoMaj(self.racine, config.auto_maj)
        self.codage = Codage(config, self.automaj)
        self._verrous: dict[str, threading.Lock] = {}
        self._actifs = 0
        self._verrou_actifs = threading.Lock()
        self.synchro = None

    def occupe(self) -> bool:
        """Vrai si un tour ou une expérience est en cours (la synchro attend avant de redémarrer)."""
        return self._actifs > 0

    def _debut(self):
        with self._verrou_actifs:
            self._actifs += 1

    def _fin(self):
        with self._verrou_actifs:
            self._actifs -= 1

    def _verrou(self, ident: str) -> threading.Lock:
        return self._verrous.setdefault(ident, threading.Lock())

    # -- contextes ------------------------------------------------------------
    def contextes_disponibles(self) -> list[str]:
        base = self.racine / "contextes"
        if not base.exists():
            return []
        return sorted(str(p.relative_to(self.racine)).replace("\\", "/")
                      for p in base.rglob("*.md"))

    def _lire_contexte(self, chemin: str) -> str:
        p = (self.racine / chemin).resolve()
        if self.racine.resolve() not in p.parents:
            raise ValueError("Contexte hors du dépôt.")
        return p.read_text(encoding="utf-8")

    def charte(self) -> str:
        return (DOSSIER_ROLES / "charte.md").read_text(encoding="utf-8")

    def construire_prompt(self, session: dict, nom: str) -> str:
        maxc = int(self.config.contexte.get("max_caracteres", 120000))
        morceaux_ctx = []
        for c in session.get("contextes", []):
            try:
                morceaux_ctx.append(f"### Contexte : {c}\n\n{self._lire_contexte(c)}")
            except (OSError, ValueError) as e:
                morceaux_ctx.append(f"### Contexte : {c}\n\n(illisible : {e})")
        tours = [
            f"### Tour {t['n']} — {t['auteur']} ({t['type']})\n\n{t['texte']}"
            for t in session["tours"]
        ]
        entete = f"# Sujet de la session\n\n{session['sujet']}\n"
        fin = f"\n\n---\n\nC'est ton tour, {nom}."
        ctx = "\n\n".join(morceaux_ctx)
        # On garde le sujet, les contextes et les tours les plus récents ;
        # les tours anciens sont résumés par leur seul en-tête si la place manque.
        budget = maxc - len(entete) - len(fin) - len(ctx)
        corps, total = [], 0
        for t in reversed(tours):
            if total + len(t) > budget:
                corps.append(t.split("\n", 1)[0] + "\n\n(tour ancien omis faute de place)")
            else:
                corps.append(t)
                total += len(t)
        echange = "\n\n".join(reversed(corps)) or "(aucun tour pour l'instant)"
        return f"{entete}\n# Contextes\n\n{ctx or '(aucun)'}\n\n# Échange\n\n{echange}{fin}"

    # -- sessions ----------------------------------------------------------------
    def creer(self, sujet: str, participants: list[str], tours_max: int,
              contextes: list[str]) -> dict:
        for p in participants:
            self.config.participant(p)  # lève si inconnu
        dispo = set(self.contextes_disponibles())
        contextes = [c for c in contextes if c in dispo]
        return self.journal.creer(sujet, participants, max(1, int(tours_max)), contextes)

    def avancer(self, ident: str) -> dict:
        self._debut()
        try:
            return self._avancer(ident)
        finally:
            self._fin()

    def _avancer(self, ident: str) -> dict:
        with self._verrou(ident):
            s = self.journal.lire(ident)
            if s["etat"] != "en_cours":
                return s
            nb_ia = sum(1 for t in s["tours"] if t["type"] in ("ia", "relais"))
            if nb_ia >= s["tours_max"]:
                s["etat"] = "terminee"
                self.journal.sauver(s)
                return s
            nom = s["participants"][s["prochain"] % len(s["participants"])]
            p = self.config.participant(nom)
            prompt = self.construire_prompt(s, nom)
            systeme = self.charte()
            try:
                self.budget.verifier(p.provider)
                rep = providers.appeler(self.config, p, systeme, prompt)
            except providers.AttenteRelais:
                s["etat"] = "attente_relais"
                s["relais"] = {"participant": nom, "texte": f"{systeme}\n\n---\n\n{prompt}"}
                self.journal.sauver(s)
                return s
            except (BudgetDepasse, providers.ErreurProvider) as e:
                s["etat"] = "pause"
                s["erreurs"].append({"quand": maintenant(), "participant": nom, "erreur": str(e)})
                self.journal.sauver(s)
                return s
            self.budget.enregistrer(p.provider, rep.tokens)
            self.journal.ajouter_tour(ident, nom, rep.texte, "ia", provider=p.provider,
                                      modele=p.modele, tokens=rep.tokens)
            s["prochain"] += 1
            self.journal.sauver(s)
            self._post_traitement(s, nom, rep.texte)
            return self.journal.lire(ident)

    def relayer(self, ident: str, texte: str) -> dict:
        with self._verrou(ident):
            s = self.journal.lire(ident)
            if s["etat"] != "attente_relais" or not s.get("relais"):
                raise ValueError("Cette session n'attend pas de relais.")
            nom = s["relais"]["participant"]
            self.journal.ajouter_tour(ident, nom, texte, "relais")
            s["relais"] = None
            s["etat"] = "en_cours"
            s["prochain"] += 1
            self.journal.sauver(s)
            self._post_traitement(s, nom, texte)
            return self.journal.lire(ident)

    def intervenir(self, ident: str, texte: str, auteur: str = "Rodolphe") -> dict:
        with self._verrou(ident):
            self.journal.ajouter_tour(ident, auteur, texte, "humain")
            return self.journal.lire(ident)

    def changer_etat(self, ident: str, etat: str) -> dict:
        if etat not in ("en_cours", "pause", "terminee"):
            raise ValueError("État inconnu.")
        with self._verrou(ident):
            s = self.journal.lire(ident)
            if s["etat"] == "attente_relais" and etat == "en_cours":
                return s
            s["etat"] = etat
            if etat == "terminee":
                s["relais"] = None
            self.journal.sauver(s)
            return self.journal.lire(ident)

    def changer_contextes(self, ident: str, contextes: list[str]) -> dict:
        """Ajoute ou retire des contextes d'une session ; le changement est noté dans le fil."""
        dispo = set(self.contextes_disponibles())
        nouveaux = sorted(c for c in contextes if c in dispo)
        with self._verrou(ident):
            s = self.journal.lire(ident)
            avant = set(s.get("contextes", []))
            ajoutes, retires = sorted(set(nouveaux) - avant), sorted(avant - set(nouveaux))
            if not ajoutes and not retires:
                return s
            s["contextes"] = nouveaux
            self.journal.sauver(s)
            lignes = [f"+ `{c}`" for c in ajoutes] + [f"− `{c}`" for c in retires]
            self.journal.ajouter_tour(ident, "Labo", "Contextes de la session modifiés par Rodolphe :\n\n"
                                      + "\n".join(lignes), "labo")
            return self.journal.lire(ident)

    def ajouter_tours(self, ident: str, n: int) -> dict:
        with self._verrou(ident):
            s = self.journal.lire(ident)
            s["tours_max"] += max(1, int(n))
            if s["etat"] == "terminee":
                s["etat"] = "en_cours"
            self.journal.sauver(s)
            return self.journal.lire(ident)

    # -- blocs spéciaux ------------------------------------------------------------
    def _post_traitement(self, s: dict, auteur: str, texte: str) -> None:
        ident = s["id"]
        for question in extraire_blocs(texte, "thot-local"):
            self._repondre_local(ident, auteur, question)
        for bloc in extraire_blocs(texte, "thot-experience"):
            self._lancer_experience(ident, auteur, bloc)
        for consigne in extraire_blocs(texte, "thot-codage"):
            self._lancer_codage(s, auteur, consigne)
        for patch in extraire_blocs(texte, "thot-patch"):
            avant = texte.split("```thot-patch", 1)[0].strip().split("\n\n")[-1]
            rec = self.automaj.proposer(patch, auteur, avant, ident)
            etat = {
                "applique": "testée et appliquée automatiquement",
                "en_attente": "en attente de l'accord de Rodolphe",
                "rejete_tests": "rejetée : les tests ne passent pas",
                "invalide": "rejetée : le patch ne s'applique pas",
                "interdit": "refusée : zone interdite",
                "echec": "échec technique",
            }.get(rec["statut"], rec["statut"])
            details = "; ".join(rec.get("raisons", [])) or "aucune réserve"
            msg = (f"Proposition de modification `{rec['id']}` de {auteur} : **{etat}**.\n\n"
                   f"Fichiers : {', '.join(rec['fichiers']) or '-'}\n\nRaisons : {details}")
            if rec.get("erreur"):
                msg += f"\n\nErreur : {rec['erreur']}"
            if rec["statut"] == "rejete_tests" and rec.get("tests"):
                msg += "\n\nSortie des tests (fin) :\n\n```\n" + rec["tests"][-1500:] + "\n```"
            self.journal.ajouter_tour(ident, "Labo", msg, "labo", automaj=rec["id"])

    def _lancer_codage(self, s: dict, auteur: str, consigne: str) -> None:
        ident = s["id"]
        if not self.config.codage.get("active", True):
            self.journal.ajouter_tour(ident, "Labo", f"{auteur} demande un codage, mais le mode codage est "
                                      "désactivé dans thot.config.toml.", "labo")
            return
        try:
            p = self.config.participant(auteur)
        except KeyError:
            self.journal.ajouter_tour(ident, "Labo", f"Codage impossible : participant inconnu ({auteur}).", "labo")
            return
        if p.provider not in ("claude", "codex"):
            self.journal.ajouter_tour(ident, "Labo", f"Codage impossible : {auteur} n'est ni Claude Code ni "
                                      "Codex.", "labo")
            return
        relecteur = None
        for nom in s["participants"]:
            if nom != auteur:
                autre = self.config.participant(nom)
                if autre.provider in ("claude", "codex"):
                    relecteur = autre
                    break
        self.journal.ajouter_tour(
            ident, "Labo", f"Codage lancé pour {auteur} dans une copie à part du dépôt"
            + (f", relecture par {relecteur.nom}" if relecteur else ", sans relecteur") + ". "
            "Le compte rendu arrivera dans le fil ; la session peut continuer en attendant.", "labo")
        self._debut()
        threading.Thread(target=self._executer_codage, args=(ident, s["sujet"], p, consigne, relecteur),
                         daemon=True).start()

    def _executer_codage(self, ident, sujet, p, consigne, relecteur) -> None:
        try:
            cr = self.codage.lancer(p, consigne, relecteur, ident, contexte=f"Sujet de la session : {sujet}")
            lignes = [f"**Codage de {p.nom}** (`{cr['id']}`)"]
            if cr["erreur"]:
                lignes.append(f"Problème : {cr['erreur']}")
            if cr["resume"]:
                lignes += ["", "Compte rendu :", "", cr["resume"]]
            if cr["tests_ok"] is not None:
                lignes += ["", f"Tests relancés par Thot dans la copie : **{'réussis' if cr['tests_ok'] else 'en échec'}**",
                           "", "```", cr["tests"][-1200:], "```"]
            self.journal.ajouter_tour(ident, p.nom, "\n".join(lignes), "codage", codage=cr["id"])
            if cr["relecture"]:
                self.journal.ajouter_tour(ident, relecteur.nom, "**Relecture**\n\n" + cr["relecture"],
                                          "relecture", codage=cr["id"])
            rec = cr["automaj"]
            if rec:
                etat = {"applique": "testé et appliqué automatiquement",
                        "en_attente": "en attente de l'accord de Rodolphe (colonne de droite)",
                        "rejete_tests": "rejeté : les tests ne passent pas",
                        "invalide": "rejeté : le patch ne s'applique pas",
                        "interdit": "refusé : zone interdite", "echec": "échec technique"}.get(rec["statut"], rec["statut"])
                self.journal.ajouter_tour(
                    ident, "Labo", f"Changement `{rec['id']}` issu du codage : **{etat}**.\n\nFichiers : "
                    f"{', '.join(rec['fichiers'])}\n\nRaisons : {'; '.join(rec.get('raisons', [])) or 'aucune réserve'}",
                    "labo", automaj=rec["id"])
        except Exception as e:  # un codage raté ne doit pas faire tomber le labo
            self.journal.ajouter_tour(ident, "Labo", f"Le codage s'est arrêté sur une erreur : {e}", "labo")
        finally:
            self._fin()

    def _repondre_local(self, ident: str, demandeur: str, question: str) -> None:
        locaux = [p for p in self.config.participants if p.provider in ("lmstudio", "ollama")]
        if not locaux:
            self.journal.ajouter_tour(ident, "Labo", "Aucune IA locale configurée.", "labo")
            return
        p = locaux[0]
        systeme = ("Tu es l'IA locale du labo Thot. Réponds précisément à la question posée par "
                   f"{demandeur}. Si tu ne sais pas, dis-le.")
        try:
            rep = providers.appeler(self.config, p, systeme, question)
            self.journal.ajouter_tour(ident, f"{p.nom} ({p.modele})", rep.texte, "local",
                                      question=question, demandeur=demandeur, tokens=rep.tokens)
        except providers.ErreurProvider as e:
            self.journal.ajouter_tour(ident, "Labo", f"IA locale indisponible : {e}", "labo")

    def _lancer_experience(self, ident: str, demandeur: str, bloc: str) -> None:
        try:
            demande = json.loads(bloc)
            nom = demande["nom"]
            params = demande.get("parametres", {})
            if not re.fullmatch(r"[a-z0-9_]+", nom):
                raise ValueError("nom d'expérience invalide")
        except (ValueError, KeyError, TypeError) as e:
            self.journal.ajouter_tour(ident, "Labo", f"Demande d'expérience illisible : {e}", "labo")
            return
        script = self.racine / "experiences" / nom / "run.py"
        if not script.exists():
            self.journal.ajouter_tour(ident, "Labo", f"Expérience inconnue : {nom}", "labo")
            return
        if not self.config.experiences.get("autoriser_lancement_auto", False):
            self.journal.ajouter_tour(
                ident, "Labo",
                f"{demandeur} demande l'expérience `{nom}` avec {json.dumps(params)}. "
                "Le lancement automatique est désactivé : à lancer par Rodolphe.", "labo")
            return
        self.journal.ajouter_tour(
            ident, "Labo", f"Expérience `{nom}` lancée à la demande de {demandeur}, "
            f"paramètres {json.dumps(params)}. Le résultat arrivera dans un tour suivant.", "labo")
        self._debut()
        threading.Thread(target=self._executer_experience,
                         args=(ident, demandeur, nom, params, script), daemon=True).start()

    def _executer_experience(self, ident, demandeur, nom, params, script) -> None:
        try:
            self._executer_experience_(ident, demandeur, nom, params, script)
        finally:
            self._fin()

    def _executer_experience_(self, ident, demandeur, nom, params, script) -> None:
        duree = int(self.config.experiences.get("duree_max_s", 1800))
        dossier_res = script.parent / "resultats"
        dossier_res.mkdir(exist_ok=True)
        try:
            r = subprocess.run([sys.executable, str(script), "--params", json.dumps(params)],
                               cwd=self.racine, capture_output=True, text=True, timeout=duree,
                               encoding="utf-8", errors="replace", env=providers.env_enfant())
            sortie = (r.stdout + r.stderr)[-6000:]
            ok = r.returncode == 0
        except subprocess.TimeoutExpired:
            sortie, ok = f"Interrompue après {duree} s.", False
        horo = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        res = {"nom": nom, "parametres": params, "demandeur": demandeur, "session": ident,
               "quand": maintenant(), "reussi": ok, "sortie": sortie}
        (dossier_res / f"{horo}.json").write_text(json.dumps(res, ensure_ascii=False, indent=2),
                                                  encoding="utf-8")
        self.journal.ajouter_tour(
            ident, "Labo",
            f"Résultat de l'expérience `{nom}` ({'réussie' if ok else 'en échec'}), "
            f"enregistré dans experiences/{nom}/resultats/{horo}.json :\n\n```\n{sortie}\n```",
            "labo")
