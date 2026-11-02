"""Journal des sessions : chaque tour est conservé tel quel, rien n'est réécrit.

Structure sur disque (dans le dépôt, pour être partagé) :
    journal/sessions/<id>/session.json   état et réglages de la session
    journal/sessions/<id>/tours.jsonl    un tour par ligne, en ajout seulement
    journal/sessions/<id>/session.md     rendu lisible (régénéré)
"""
from __future__ import annotations

import json
import re
import threading
import unicodedata
from datetime import datetime
from pathlib import Path

from .confidentialite import masquer

_verrou = threading.Lock()

RE_RECADRAGE = re.compile(r"^\s*\[RECADRAGE\]\s*(.+)$", re.MULTILINE)


def _slug(texte: str, n: int = 40) -> str:
    t = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode()
    t = re.sub(r"[^a-zA-Z0-9]+", "-", t).strip("-").lower()
    return t[:n].strip("-") or "session"


def maintenant() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


class Journal:
    def __init__(self, racine: Path):
        self.dossier = racine / "journal" / "sessions"
        self.dossier.mkdir(parents=True, exist_ok=True)

    # -- sessions -----------------------------------------------------------
    def creer(self, sujet: str, participants: list[str], tours_max: int,
              contextes: list[str]) -> dict:
        sujet = masquer(sujet)  # le sujet donne aussi son nom au dossier, publié sur GitHub
        base = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + _slug(sujet)
        ident, n = base, 2
        while (self.dossier / ident).exists():
            ident, n = f"{base}-{n}", n + 1
        d = self.dossier / ident
        d.mkdir(parents=True)
        session = {
            "id": ident,
            "sujet": sujet,
            "participants": participants,
            "tours_max": tours_max,
            "contextes": contextes,
            "etat": "en_cours",
            "prochain": 0,
            "relais": None,
            "cree": maintenant(),
            "erreurs": [],
        }
        (d / "tours.jsonl").touch()
        self.sauver(session)
        return session

    def lire(self, ident: str) -> dict:
        d = self._dossier(ident)
        session = json.loads((d / "session.json").read_text(encoding="utf-8"))
        session["tours"] = self.tours(ident)
        return session

    def sauver(self, session: dict) -> None:
        s = {k: v for k, v in session.items() if k != "tours"}
        with _verrou:
            d = self._dossier(s["id"])
            (d / "session.json").write_text(
                json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        self.rendre(s["id"])

    def lister(self) -> list[dict]:
        res = []
        for d in sorted(self.dossier.iterdir(), reverse=True):
            f = d / "session.json"
            if f.exists():
                s = json.loads(f.read_text(encoding="utf-8"))
                res.append({k: s[k] for k in ("id", "sujet", "etat", "cree")})
        return res

    # -- tours --------------------------------------------------------------
    def tours(self, ident: str) -> list[dict]:
        f = self._dossier(ident) / "tours.jsonl"
        lignes = f.read_text(encoding="utf-8").splitlines() if f.exists() else []
        return [json.loads(l) for l in lignes if l.strip()]

    def ajouter_tour(self, ident: str, auteur: str, texte: str, type_: str,
                     **extra) -> dict:
        texte = masquer(texte)  # le dépôt est public
        with _verrou:
            n = len(self.tours(ident))
            tour = {
                "n": n,
                "auteur": auteur,
                "type": type_,
                "horodatage": maintenant(),
                "texte": texte,
                "recadrages": RE_RECADRAGE.findall(texte),
                **extra,
            }
            with open(self._dossier(ident) / "tours.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps(tour, ensure_ascii=False) + "\n")
        self.rendre(ident)
        return tour

    # -- rendu ----------------------------------------------------------------
    def rendre(self, ident: str) -> None:
        d = self._dossier(ident)
        s = json.loads((d / "session.json").read_text(encoding="utf-8"))
        lignes = [
            f"# {s['sujet']}",
            "",
            f"Session `{s['id']}` · créée {s['cree']} · état : {s['etat']}",
            f"Participants : {', '.join(s['participants'])}",
            "",
        ]
        if s.get("contextes"):
            lignes += ["Contextes fournis :", *[f"- `{c}`" for c in s["contextes"]], ""]
        for t in self.tours(ident):
            lignes += ["---", "", f"## Tour {t['n']} — {t['auteur']} ({t['type']})",
                       f"*{t['horodatage']}*", "", t["texte"], ""]
        (d / "session.md").write_text(masquer("\n".join(lignes)), encoding="utf-8")

    def _dossier(self, ident: str) -> Path:
        if not re.fullmatch(r"[A-Za-z0-9\-]+", ident):
            raise ValueError("Identifiant de session invalide.")
        return self.dossier / ident
