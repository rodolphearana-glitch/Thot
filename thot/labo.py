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
from .confidentialite import masquer
from .observatoire import CONSIGNE_OBSERVATION, Observatoire
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
        self.observatoire = Observatoire(self.racine)
        self._verrous: dict[str, threading.Lock] = {}
        self._actifs = 0
        self.en_cours: dict[str, dict] = {}   # session -> tour en cours (qui parle, depuis quand)
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
        if session.get("genre") == "observation":
            par_source = max(6000, (maxc // 2) // max(1, len(session.get("sources", []))))
            exports = "\n\n".join(self.observatoire.export_session(x, par_source) for x in session.get("sources", []))
            morceaux_ctx.insert(0, "### Sessions observées (journaux, en lecture seule)\n\n" + exports)
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
              contextes: list[str], genre: str = "discussion", sources: list[str] | None = None) -> dict:
        if not participants:
            raise ValueError("Il faut au moins un participant.")
        for p in participants:
            self.config.participant(p)  # lève si inconnu
        dispo = set(self.contextes_disponibles())
        contextes = [c for c in contextes if c in dispo]
        if genre not in ("discussion", "observation"):
            raise ValueError("Genre de session inconnu.")
        if genre == "observation":
            # Une observation ne porte que sur des discussions : jamais sur une autre observation
            # (pas d'auto-analyse récursive).
            discussions = {r["id"] for r in self.journal.lister() if r["genre"] == "discussion"}
            sources = [x for x in (sources or []) if x in discussions] or sorted(discussions)
            if not sources:
                raise ValueError("Aucune discussion à observer.")
        else:
            sources = []
        return self.journal.creer(sujet, participants, max(1, int(tours_max)), contextes, genre, sources)

    def _terminer(self, s: dict) -> None:
        """Clôt une session ; une observation publie alors son rapport (un nouveau à chaque clôture)."""
        s["etat"] = "terminee"
        s["relais"] = None
        if s.get("genre") == "observation":
            tours = [t for t in self.journal.tours(s["id"]) if t.get("type") in ("ia", "relais", "humain")]
            if tours:
                corps = "\n\n".join(f"### Tour {t['n']} — {t['auteur']}\n\n{t['texte']}" for t in tours)
                modeles = ", ".join(sorted({f"{p.nom} : {p.provider}" + (f" {p.modele}" if p.modele else "")
                                            for p in self.config.participants if p.nom in s["participants"]}))
                chemin = self.observatoire.ecrire_observation(
                    " et ".join(s["participants"]), modeles, s.get("sources", []), CONSIGNE_OBSERVATION,
                    f"Discussion d'observation `{s['id']}` ({len(tours)} tours). Question : {s['sujet']}\n\n{corps}")
                s.setdefault("rapports", []).append(chemin.name)
                self.journal.sauver(s)
                self.journal.ajouter_tour(s["id"], "Labo", f"Rapport publié : `journal/observations/{chemin.name}` "
                                          "(un nouveau rapport s'ajoute à chaque clôture, aucun n'est réécrit).",
                                          "labo", evenement={"genre": "rapport_publie", "fichier": chemin.name})
                self.observatoire.generer_index()
                return
        self.journal.sauver(s)

    def avancer(self, ident: str) -> dict:
        if ident in self.en_cours:
            # Un tour tourne déjà pour cette session : on ne le relance pas, on renvoie l'état.
            return self.lire(ident)
        self._debut()
        try:
            return self._avancer(ident)
        finally:
            self.en_cours.pop(ident, None)
            self._fin()

    def lire(self, ident: str) -> dict:
        """La session, avec le tour en cours s'il y en a un (qui parle, depuis quand)."""
        s = self.journal.lire(ident)
        tec = self.en_cours.get(ident)
        s["tour_en_cours"] = {k: v for k, v in tec.items() if not k.startswith("_")} if tec else None
        return s

    def interrompre(self, ident: str) -> dict:
        """Arrête le tour en cours de cette session ; la session passe en pause, rien n'est écrit au fil
        à part la mention de l'interruption."""
        tec = self.en_cours.get(ident)
        if not tec:
            raise ValueError("Aucun tour en cours dans cette session.")
        providers.interrompre(tec["_fil"])
        return self.lire(ident)

    def _avancer(self, ident: str) -> dict:
        with self._verrou(ident):
            s = self.journal.lire(ident)
            if s["etat"] != "en_cours":
                return s
            nb_ia = sum(1 for t in s["tours"] if t["type"] in ("ia", "relais"))
            if nb_ia >= s["tours_max"]:
                self._terminer(s)
                return self.journal.lire(ident)
            nom = s["participants"][s["prochain"] % len(s["participants"])]
            p = self.config.participant(nom)
            self.en_cours[ident] = {"participant": nom, "provider": p.provider, "debut": maintenant(),
                                    "_fil": threading.get_ident()}
            prompt = self.construire_prompt(s, nom)
            systeme = self.charte()
            if s.get("genre") == "observation":
                systeme += "\n\n# Cette session est une OBSERVATION\n\n" + CONSIGNE_OBSERVATION + (
                    "\nVous êtes plusieurs analystes : répondez-vous, contestez les observations des autres "
                    "quand elles ne tiennent pas, et ne répétez pas ce qui a déjà été dit. À la clôture, "
                    "toute la discussion devient un rapport dans journal/observations/.\n\n"
                    "IMPORTANT : les journaux à analyser sont DÉJÀ dans ce message. N'ouvre aucun fichier du "
                    "dépôt (ni code, ni journal, ni contexte) : ton analyse porte sur ce qui t'est fourni, "
                    "et tes sources sont les numéros de tours cités ici. Réponds directement.")
            try:
                self.budget.verifier(p.provider)
                rep = providers.appeler(self.config, p, systeme, prompt,
                                        int(self.config.contexte.get("duree_max_tour_s", 900)))
                if threading.get_ident() in providers.INTERROMPUS:   # modèle local : réponse arrivée trop tard
                    providers.INTERROMPUS.discard(threading.get_ident())
                    raise providers.ErreurProvider("Tour interrompu par Rodolphe.")
            except providers.AttenteRelais:
                s["etat"] = "attente_relais"
                s["relais"] = {"participant": nom, "texte": f"{systeme}\n\n---\n\n{prompt}"}
                self.journal.sauver(s)
                return s
            except (BudgetDepasse, providers.ErreurProvider) as e:
                s["etat"] = "pause"
                s["erreurs"].append({"quand": maintenant(), "participant": nom, "erreur": masquer(str(e))})
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

    # -- questions pour Rodolphe ----------------------------------------------------------
    def _poser_question(self, ident: str, auteur: str, texte: str) -> None:
        """Une IA pose une question à Rodolphe : elle s'affiche en haut de la page au lieu de se perdre
        dans un long message (constat du premier rapport d'observation)."""
        s = self.journal.lire(ident)
        qs = s.setdefault("questions", [])
        q = {"id": len(qs) + 1, "auteur": auteur, "texte": masquer(texte.strip()), "posee": maintenant(),
             "statut": "ouverte"}
        qs.append(q)
        self.journal.sauver(s)
        self.journal.ajouter_tour(ident, "Labo", f"Question n° {q['id']} de {auteur} pour Rodolphe, affichée en haut "
                                  f"de la page :\n\n> {q['texte']}", "labo",
                                  evenement={"genre": "question_posee", "question": q["id"], "auteur": auteur})

    def repondre_question(self, ident: str, numero: int, texte: str) -> dict:
        with self._verrou(ident):
            s = self.journal.lire(ident)
            q = next((x for x in s.get("questions", []) if x["id"] == int(numero)), None)
            if q is None:
                raise ValueError("Question inconnue.")
            if q["statut"] != "ouverte":
                raise ValueError("Cette question a déjà une réponse.")
            q["statut"], q["reponse"], q["repondue"] = "repondue", masquer(texte.strip()), maintenant()
            self.journal.sauver(s)
            self.journal.ajouter_tour(ident, "Rodolphe", f"Réponse à la question n° {q['id']} de {q['auteur']} "
                                      f"(« {q['texte'][:200]} ») :\n\n{texte.strip()}", "humain",
                                      evenement={"genre": "question_repondue", "question": q["id"]})
            return self.lire(ident)

    def questions_ouvertes(self) -> list[dict]:
        res = []
        for x in self.journal.lister():
            for q in x.get("questions", []):
                if q["statut"] == "ouverte":
                    res.append({"session": x["id"], "sujet": x["sujet"], **q})
        return res

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
            if etat == "terminee":
                if s["etat"] != "terminee":
                    self._terminer(s)
                return self.journal.lire(ident)
            s["etat"] = etat
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

    def changer_participants(self, ident: str, participants: list[str]) -> dict:
        """Ajoute, retire ou réordonne les participants d'une session en cours (discussion ou observation)."""
        if not participants:
            raise ValueError("Il faut au moins un participant.")
        for p in participants:
            self.config.participant(p)  # lève si inconnu
        if len(set(participants)) != len(participants):
            raise ValueError("Un participant figure deux fois.")
        with self._verrou(ident):
            s = self.journal.lire(ident)
            avant = s["participants"]
            if participants == avant:
                return s
            # Le tour de parole reprend après le dernier qui a parlé, s'il est toujours là.
            derniers = [t["auteur"] for t in s["tours"] if t.get("type") in ("ia", "relais")]
            if derniers and derniers[-1] in participants:
                s["prochain"] = participants.index(derniers[-1]) + 1
            else:
                s["prochain"] = s.get("prochain", 0) % len(participants)
            s["participants"] = list(participants)
            if s.get("etat") == "attente_relais" and s.get("relais", {}).get("participant") not in participants:
                s["relais"], s["etat"] = None, "en_cours"
            self.journal.sauver(s)
            lignes = ([f"+ {n}" for n in participants if n not in avant] + [f"− {n}" for n in avant if n not in participants])
            self.journal.ajouter_tour(ident, "Labo", "Participants modifiés par Rodolphe :\n\n" + "\n".join(lignes)
                                      + f"\n\nOrdre de parole : {', '.join(participants)}.", "labo",
                                      evenement={"genre": "participants_modifies", "avant": avant, "apres": participants})
            return self.journal.lire(ident)

    def ajouter_tours(self, ident: str, n: int) -> dict:
        with self._verrou(ident):
            s = self.journal.lire(ident)
            s["tours_max"] += max(1, int(n))
            s["relances"] = s.get("relances", 0) + 1
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
        for question in extraire_blocs(texte, "thot-question"):
            self._poser_question(ident, auteur, question)
        if s.get("genre", "discussion") == "discussion":   # une observation ne peut pas en demander une autre
            for question in extraire_blocs(texte, "thot-observer"):
                self._demander_observation(s, auteur, question)
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
            self.journal.ajouter_tour(ident, "Labo", msg, "labo", automaj=rec["id"],
                                      evenement={"genre": "modification_traitee", "id": rec["id"],
                                                 "statut": rec["statut"], "par": "thot-patch"})

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
                    "labo", automaj=rec["id"], evenement={"genre": "modification_traitee", "id": rec["id"],
                                                          "statut": rec["statut"], "par": "thot-codage"})
        except Exception as e:  # un codage raté ne doit pas faire tomber le labo
            self.journal.ajouter_tour(ident, "Labo", f"Le codage s'est arrêté sur une erreur : {e}", "labo")
        finally:
            self._fin()

    # -- observation demandée depuis une session ---------------------------------------
    def _demander_observation(self, s: dict, auteur: str, question: str) -> None:
        """Un participant demande à Observer Thot d'analyser SA session ; le rapport revient dans le fil.

        Garde-fous : une seule observation en cours par session, un plafond par session, des tours
        bornés, le budget du jour ; une observation ne peut pas en demander une autre."""
        ident = s["id"]
        reglages = self.config.observation
        en_cours = [x for x in self.journal.lister()
                    if x["genre"] == "observation" and x["etat"] != "terminee" and ident in x["sources"]]
        faites = sum(1 for x in self.journal.lister() if x["genre"] == "observation" and ident in x["sources"])
        if en_cours:
            self.journal.ajouter_tour(ident, "Labo", f"{auteur} demande une observation, mais une autre est déjà "
                                      "en cours sur cette session.", "labo")
            return
        if faites >= int(reglages.get("max_par_session", 3)):
            self.journal.ajouter_tour(ident, "Labo", f"{auteur} demande une observation, mais le plafond de "
                                      f"{reglages.get('max_par_session', 3)} observations pour cette session est atteint.", "labo")
            return
        analystes = [n for n in reglages.get("analystes", []) if n in {p.nom for p in self.config.participants}]
        if not analystes:
            analystes = [n for n in s["participants"]
                         if self.config.participant(n).provider not in ("manuel",)] or s["participants"]
        tours = max(1, int(reglages.get("tours", 2)))
        obs = self.creer(f"Demandé par {auteur} dans la session {ident} : {question.strip()}", analystes, tours,
                         [], genre="observation", sources=[ident])
        obs = self.journal.lire(obs["id"])
        obs["parent"] = ident
        self.journal.sauver(obs)
        self.journal.ajouter_tour(ident, "Labo", f"Observation `{obs['id']}` lancée à la demande de {auteur} "
                                  f"({', '.join(analystes)}, {tours} tours). Le rapport arrivera dans ce fil.",
                                  "labo", evenement={"genre": "observation_demandee", "observation": obs["id"],
                                                     "demandeur": auteur})
        self._debut()
        threading.Thread(target=self._derouler_observation, args=(ident, obs["id"]), daemon=True).start()

    def _derouler_observation(self, parent: str, obs_id: str) -> None:
        try:
            limite = self.journal.lire(obs_id)["tours_max"] + 2
            for _ in range(limite):
                o = self.avancer(obs_id)
                if o["etat"] != "en_cours":
                    break
            o = self.journal.lire(obs_id)
            if o["etat"] != "terminee":
                self.journal.ajouter_tour(parent, "Labo", f"L'observation `{obs_id}` s'est arrêtée avant la fin "
                                          f"(état : {o['etat']}"
                                          + (f", {o['erreurs'][-1]['erreur']}" if o.get("erreurs") else "")
                                          + "). Elle peut être reprise dans « Observer Thot ».", "labo")
                return
            rapport = (o.get("rapports") or [None])[-1]
            texte = (self.observatoire.observations / rapport).read_text(encoding="utf-8") if rapport else ""
            limite_c = int(self.config.observation.get("max_caracteres_rapport", 20000))
            if len(texte) > limite_c:
                texte = texte[:limite_c] + f"\n\n(… rapport tronqué ici ; texte complet : journal/observations/{rapport})"
            self.journal.ajouter_tour(
                parent, "Observer Thot",
                f"Rapport de l'observation `{obs_id}` (`journal/observations/{rapport}`). C'est une analyse, "
                f"pas une vérité établie : à vous de voir ce qui vous sert.\n\n{texte}",
                "observation", evenement={"genre": "observation_rendue", "observation": obs_id, "fichier": rapport})
        except Exception as e:
            self.journal.ajouter_tour(parent, "Labo", f"L'observation `{obs_id}` a échoué : {masquer(str(e))[:300]}",
                                      "labo")
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
            f"paramètres {json.dumps(params)}. Le résultat arrivera dans un tour suivant.", "labo",
            evenement={"genre": "experience_lancee", "nom": nom, "demandeur": demandeur, "parametres": params})
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
            "labo", evenement={"genre": "experience_resultat", "nom": nom, "reussie": ok, "parametres": params,
                               "fichier": f"experiences/{nom}/resultats/{horo}.json"})
