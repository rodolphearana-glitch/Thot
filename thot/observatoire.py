"""Observer Thot : index des sessions, vue des recadrages, rapports d'observation.

Demande de Rodolphe et GPT-6 (2026-11-02, contextes/correspondance : mission « Observabilité,
introspection expérimentale et mémoire de fonctionnement »).

Deux parties strictement séparées :
- l'indexation (journal/INDEX.md, INDEX.json, RECADRAGES.md) : purement mécanique, sans appel à
  une IA, déterministe (même journal → mêmes fichiers, octet pour octet), régénérée à chaque synchro ;
- l'auto-observation (journal/observations/) : une analyse par une IA, lancée à la main, une fois,
  comptée dans le budget, écrite dans un nouveau fichier daté (jamais d'écrasement).

Tout ce qui est écrit ici passe par `masquer` : le dépôt est public.

Ce module lit les journaux et n'y écrit jamais (seulement les fichiers dérivés listés ci-dessus).
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime
from pathlib import Path

from .journal import RE_RECADRAGE

from .confidentialite import masquer  # noqa: E402


# --------------------------------------------------------------------------- lecture des journaux
def _lire_json(chemin: Path, defaut):
    try:
        return json.loads(chemin.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return defaut


def _tours(dossier: Path) -> list[dict]:
    f = dossier / "tours.jsonl"
    res = []
    if f.exists():
        for ligne in f.read_text(encoding="utf-8").splitlines():
            try:
                res.append(json.loads(ligne))
            except ValueError:
                continue  # ligne abîmée : ignorée ici, jamais réécrite
    return res


RE_BLOC = re.compile(r"```(thot-[a-z]+)[ \t]*\n(.*?)```", re.DOTALL)
RE_EXP_LANCEE = re.compile(r"Expérience `([a-z0-9_]+)` lancée à la demande de ([^,]+), paramètres (\{.*?\})")
RE_EXP_RESULTAT = re.compile(r"Résultat de l'expérience `([a-z0-9_]+)` \((réussie|en échec)\)"
                             r"(?:, enregistré dans ([^\s:]+))?")
RE_AUTOMAJ = re.compile(r"(?:Proposition de modification|Changement) `([0-9\-]+)`[^:]*: \*\*(.+?)\*\*")


def evenements(tour: dict) -> list[dict]:
    """Ce qui s'est passé dans un tour, en distinguant ce qui est demandé de ce qui est exécuté.

    Les tours récents portent leurs événements (`evenement`) ; pour les plus anciens, ils sont déduits
    du texte, et marqués comme tels."""
    evs = []
    texte = tour.get("texte", "")
    if tour.get("type") in ("ia", "relais"):
        for langage, contenu in RE_BLOC.findall(texte):
            genre = {"thot-experience": "experience_demandee", "thot-patch": "modification_proposee",
                     "thot-codage": "codage_demande", "thot-local": "question_locale"}.get(langage)
            if genre:
                ev = {"genre": genre, "source": "bloc"}
                if genre == "experience_demandee":
                    try:
                        d = json.loads(contenu)
                        ev.update(nom=d.get("nom"), parametres=d.get("parametres", {}))
                    except ValueError:
                        ev["illisible"] = True
                evs.append(ev)
    if tour.get("type") == "labo" or tour.get("auteur") == "Labo":
        if tour.get("evenement"):
            evs.append({"source": "journal", **tour["evenement"]})
        else:
            for nom, demandeur, params in RE_EXP_LANCEE.findall(texte):
                evs.append({"genre": "experience_lancee", "nom": nom, "demandeur": demandeur.strip(),
                            "source": "déduit du texte"})
            for nom, issue, fichier in RE_EXP_RESULTAT.findall(texte):
                evs.append({"genre": "experience_resultat", "nom": nom, "reussie": issue == "réussie",
                            "fichier": fichier or None, "source": "déduit du texte"})
            for ident, statut in RE_AUTOMAJ.findall(texte):
                evs.append({"genre": "modification_traitee", "id": ident, "statut": statut,
                            "source": "déduit du texte"})
    return evs


def resume_session(dossier: Path) -> dict | None:
    s = _lire_json(dossier / "session.json", None)
    if not isinstance(s, dict) or "id" not in s:
        return None
    tours = _tours(dossier)
    recadrages = sum(len(t.get("recadrages") or RE_RECADRAGE.findall(t.get("texte", ""))) for t in tours)
    evs = [e for t in tours for e in evenements(t)]
    compte = lambda g: sum(1 for e in evs if e.get("genre") == g)  # noqa: E731
    return {
        "id": s["id"],
        "sujet": masquer(s.get("sujet", "")),
        "participants": s.get("participants", []),
        "etat": s.get("etat", "inconnu"),
        "genre": s.get("genre", "discussion"),
        "sources": s.get("sources", []),
        "relances": s.get("relances", 0),
        "cree": s.get("cree"),
        "dernier_evenement": tours[-1].get("horodatage") if tours else s.get("cree"),
        "tours": len(tours),
        "tours_ia": sum(1 for t in tours if t.get("type") in ("ia", "relais")),
        "recadrages": recadrages,
        "experiences_demandees": compte("experience_demandee"),
        "experiences_executees": compte("experience_resultat"),
        "modifications_proposees": compte("modification_proposee") + compte("codage_demande"),
        "contextes": s.get("contextes", []),
        "fichiers": {
            "lisible": f"sessions/{s['id']}/session.md",
            "tours": f"sessions/{s['id']}/tours.jsonl",
            "etat": f"sessions/{s['id']}/session.json",
        },
    }


# --------------------------------------------------------------------------- index
class Observatoire:
    def __init__(self, racine: Path):
        self.racine = racine
        self.journal = racine / "journal"
        self.sessions = self.journal / "sessions"
        self.observations = self.journal / "observations"

    def resumes(self) -> list[dict]:
        if not self.sessions.exists():
            return []
        res = [resume_session(d) for d in sorted(self.sessions.iterdir()) if d.is_dir()]
        return [r for r in res if r]

    def recadrages(self) -> list[dict]:
        res = []
        for r in self.resumes():
            for t in _tours(self.sessions / r["id"]):
                for texte in t.get("recadrages") or RE_RECADRAGE.findall(t.get("texte", "")):
                    res.append({"session": r["id"], "tour": t.get("n"), "auteur": t.get("auteur"),
                                "date": t.get("horodatage"), "texte": masquer(texte.strip()),
                                "statut": "déclaré"})
        return res

    def generer_index(self) -> list[Path]:
        """Régénère INDEX.json, INDEX.md, RECADRAGES.md et observations/INDEX.md.

        Déterministe : aucun horodatage de génération ; ne réécrit un fichier que s'il change.
        Renvoie la liste des fichiers effectivement modifiés."""
        self.journal.mkdir(parents=True, exist_ok=True)
        resumes = self.resumes()
        recs = self.recadrages()
        obs = self.liste_observations()
        sorties = {
            self.journal / "INDEX.json": json.dumps(
                {"format": 1, "sessions": resumes, "recadrages": len(recs), "observations": obs},
                ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            self.journal / "INDEX.md": self._index_md(resumes, len(recs), obs),
            self.journal / "RECADRAGES.md": self._recadrages_md(recs),
            self.observations / "INDEX.md": self._observations_md(obs),
        }
        changes = []
        for chemin, contenu in sorties.items():
            chemin.parent.mkdir(parents=True, exist_ok=True)
            if not chemin.exists() or chemin.read_text(encoding="utf-8") != contenu:
                chemin.write_text(contenu, encoding="utf-8")
                changes.append(chemin)
        return changes

    @staticmethod
    def _index_md(resumes: list[dict], nb_recadrages: int, obs: list[dict]) -> str:
        L = ["# Index des sessions de Thot", "",
             "Généré automatiquement à partir des journaux (sans IA). Ne pas modifier à la main.", "",
             "- Format programme : [INDEX.json](INDEX.json)",
             f"- Recadrages déclarés : [RECADRAGES.md](RECADRAGES.md) ({nb_recadrages})",
             f"- Rapports d'observation : [observations/INDEX.md](observations/INDEX.md) ({len(obs)})",
             "- Modifications du labo : [auto-maj/](auto-maj/)", ""]
        if not resumes:
            return "\n".join(L + ["Aucune session pour l'instant.", ""])
        L += ["| session | genre | sujet | participants | état | tours (IA) | relances | recadrages | expériences demandées / exécutées | dernier événement |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        for r in sorted(resumes, key=lambda r: r["id"], reverse=True):
            sujet = r["sujet"].replace("|", "\\|").replace("\n", " ")
            sujet = sujet[:90] + ("…" if len(sujet) > 90 else "")
            L.append(f"| [{r['id']}]({r['fichiers']['lisible']}) | {r['genre']} | {sujet} | {', '.join(r['participants'])} | "
                     f"{r['etat']} | {r['tours']} ({r['tours_ia']}) | {r['relances']} | {r['recadrages']} | "
                     f"{r['experiences_demandees']} / {r['experiences_executees']} | "
                     f"{(r['dernier_evenement'] or '?')[:16].replace('T', ' ')} |")
        return "\n".join(L + [""])

    @staticmethod
    def _recadrages_md(recs: list[dict]) -> str:
        L = ["# Recadrages déclarés", "",
             "Lignes `[RECADRAGE]` écrites par les participants, recopiées mot pour mot.", "",
             "**Déclaré** n'est pas **observé** ni **validé** : ici, un participant *dit* avoir changé de "
             "perspective. Qu'un changement ait effectivement eu lieu relève d'un rapport d'observation "
             "([observations/](observations/INDEX.md)) ; qu'il ait été utile, d'une expérience.", ""]
        if not recs:
            return "\n".join(L + ["Aucun recadrage déclaré pour l'instant.", ""])
        for r in recs:
            L += [f"## {r['session']} — tour {r['tour']} — {r['auteur']}",
                  f"*{(r['date'] or 'date inconnue')[:16].replace('T', ' ')}* · statut : {r['statut']} · "
                  f"[contexte](sessions/{r['session']}/session.md)", "", f"> {r['texte']}", ""]
        return "\n".join(L)

    # ----------------------------------------------------------------------- observations
    def liste_observations(self) -> list[dict]:
        if not self.observations.exists():
            return []
        res = []
        for f in sorted(self.observations.glob("*.md")):
            if f.name == "INDEX.md":
                continue
            entete = f.read_text(encoding="utf-8").split("\n", 12)
            titre = next((l[2:].strip() for l in entete if l.startswith("# ")), f.stem)
            res.append({"fichier": f.name, "titre": titre})
        return res

    @staticmethod
    def _observations_md(obs: list[dict]) -> str:
        L = ["# Rapports d'observation", "",
             "Analyses de Thot sur ses propres sessions, lancées à la main. Ce sont des analyses, pas des "
             "vérités établies : chacune donne ses sources, sa méthode et ses limites. Un rapport n'est "
             "jamais réécrit ; un nouveau rapport s'ajoute.", "",
             "[← Index des sessions](../INDEX.md)", ""]
        if not obs:
            return "\n".join(L + ["Aucun rapport pour l'instant.", ""])
        return "\n".join(L + [f"- [{o['titre']}]({o['fichier']})" for o in reversed(obs)] + [""])

    def export_session(self, ident: str, limite: int = 60000) -> str:
        """Le fil d'une session, masqué, avec ses événements, pour l'analyse."""
        d = self.sessions / ident
        s = _lire_json(d / "session.json", {})
        L = [f"## Session {ident}", f"Sujet : {s.get('sujet', '?')}",
             f"Participants : {', '.join(s.get('participants', []))} · état : {s.get('etat', '?')}", ""]
        for t in _tours(d):
            evs = evenements(t)
            L += [f"### Tour {t.get('n')} — {t.get('auteur')} ({t.get('type')}) — {t.get('horodatage', '?')}",
                  t.get("texte", "")]
            if evs:
                L.append("Événements : " + json.dumps(evs, ensure_ascii=False))
            L.append("")
        texte = masquer("\n".join(L))
        return texte if len(texte) <= limite else texte[:limite] + "\n\n(… session tronquée pour l'analyse)"

    def ecrire_observation(self, participant: str, modele: str, sessions: list[str], consigne: str,
                           analyse: str) -> Path:
        """Écrit un nouveau rapport daté. N'écrase jamais un rapport existant."""
        self.observations.mkdir(parents=True, exist_ok=True)
        base = datetime.now().strftime("%Y%m%d-%H%M%S") + f"-{re.sub(r'[^a-z0-9]+', '-', participant.lower())}"
        chemin, n = self.observations / f"{base}.md", 2
        while chemin.exists():
            chemin, n = self.observations / f"{base}-{n}.md", n + 1
        empreinte = hashlib.sha256(consigne.encode("utf-8")).hexdigest()[:12]
        dates = [r.get("cree") for r in self.resumes() if r["id"] in sessions]
        L = [f"# Observation du {datetime.now().strftime('%Y-%m-%d %H:%M')} par {participant}", "",
             "*Rapport d'auto-observation de Thot : une analyse, pas une vérité établie. "
             "Ce fichier ne sera pas réécrit.*", "",
             "## Cadre", "",
             f"- Période analysée : {min(dates)[:16] if dates else '?'} → {max(dates)[:16] if dates else '?'}",
             "- Sessions incluses : " + ", ".join(f"[{s}](../sessions/{s}/session.md)" for s in sessions),
             "- Sources : les journaux de ces sessions (`tours.jsonl`), lus sans modification ; "
             "aucun autre fichier n'a été fourni à l'analyste.",
             f"- Méthode : analyse par {participant}" + (f" ({modele})" if modele else "") +
             f", en lecture seule, avec la consigne d'observation de `thot/observatoire.py` "
             f"(empreinte {empreinte}). Un seul passage, sans reprise.", "",
             "## Analyse", "", masquer(analyse.strip()), ""]
        chemin.write_text("\n".join(L), encoding="utf-8")
        return chemin


CONSIGNE_OBSERVATION = """Tu analyses, en lecture seule, des sessions passées de Thot, le labo de recherche de
Rodolphe. Le but n'est pas de juger les participants ni de féliciter qui que ce soit : c'est de produire
une analyse TRAÇABLE du fonctionnement du labo, que Rodolphe et les autres IA pourront vérifier.

Règles :
- Chaque observation cite sa source : session, numéro de tour, auteur. Une citation se fait mot pour mot.
- Marque chaque affirmation : [FAIT] (constatable dans le journal), [INTERPRÉTATION], [HYPOTHÈSE],
  [SUGGESTION]. Rien d'autre n'est un fait.
- Un recadrage DÉCLARÉ (ligne [RECADRAGE]) n'est pas un recadrage OBSERVÉ : dis si tu observes un
  changement réel dans la manière de poser le problème dans les tours suivants, ou seulement une
  reformulation. Aucun recadrage n'est VALIDÉ sans résultat d'expérience à l'appui.
- Distingue une expérience demandée d'une expérience exécutée, et une prédiction d'un résultat.
- Ne déduis jamais un progrès du fait qu'une IA dit avoir progressé. Deux IA d'accord ne font pas une
  confirmation indépendante.
- Tu ne connais pas le fonctionnement interne des modèles : n'affirme rien sur leurs paramètres.

Structure attendue (titres de niveau 3) :
### Répétitions
### Contradictions
### Convergences (et pourquoi elles pourraient ne pas être indépendantes)
### Transformations de cadre
Pour au moins un recadrage, donne : 1. le cadre initial, avec sa source ; 2. le recadrage exact ;
3. le cadre utilisé ensuite ; 4. les changements observables dans les messages suivants ; 5. une
hypothèse sur son effet ; 6. les raisons pour lesquelles cette interprétation pourrait être fausse.
### Conséquences différées
### Prédictions et résultats
### Hypothèses nouvelles
### Incertitudes et limites de cette analyse
### Expériences proposées pour vérifier ces conclusions

Sois aussi court que le contenu le permet. Écris « rien d'observable » plutôt que d'inventer.
"""
