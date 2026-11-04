"""Surfaces de l'établi : des interfaces que les IA composent pour une tâche, avec des pièces fixées.

Une IA écrit un bloc `thot-surface` (JSON) ; l'établi l'affiche. Pas de HTML ni de script venant des IA :
seulement des pièces connues, dont chaque champ est vérifié ici. Le vocabulaire s'enrichit en ajoutant
une pièce dans PIECES et son rendu dans `thot/web/static/etabli.html`.

Une surface utile se sauve comme modèle (`modeles/surfaces/<nom>.json`) et se réutilise :
`{"modele": "nom"}` reprend le modèle, les autres clés le complètent ou le remplacent.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

# type de pièce → champs permis (et leur nature)
PIECES: dict[str, dict[str, str]] = {
    "texte": {"texte": "str"},
    "curseur": {"id": "id", "libelle": "str", "min": "num", "max": "num", "pas": "num", "valeur": "num",
                "outil": "str"},
    "choix": {"id": "id", "libelle": "str", "options": "strs", "valeur": "str", "outil": "str"},
    "interrupteur": {"id": "id", "libelle": "str", "valeur": "bool", "outil": "str"},
    "jauge": {"libelle": "str", "valeur": "num", "max": "num"},
    "comparaison": {"colonnes": "colonnes"},
    "decision": {"id": "id", "libelle": "str", "options": "strs"},
    "champ": {"id": "id", "libelle": "str", "indice": "str"},
    "lien": {"libelle": "str", "url": "url"},
}
RE_ID = re.compile(r"[A-Za-z0-9_\-]{1,40}")
RE_NOM = re.compile(r"[a-z0-9][a-z0-9_\-]{0,60}")
MAX_PIECES = 30
MAX_TEXTE = 2000


def _str(v, n=MAX_TEXTE) -> str:
    if not isinstance(v, (str, int, float)):
        raise ValueError("texte attendu")
    return str(v)[:n]


def _champ(nature: str, v):
    if nature == "str":
        return _str(v)
    if nature == "id":
        if not isinstance(v, str) or not RE_ID.fullmatch(v):
            raise ValueError(f"identifiant invalide : {v!r}")
        return v
    if nature == "num":
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            raise ValueError(f"nombre attendu : {v!r}")
        return v
    if nature == "bool":
        return bool(v)
    if nature == "strs":
        if not isinstance(v, list) or not v or len(v) > 12:
            raise ValueError("liste d'options attendue (1 à 12)")
        return [_str(x, 200) for x in v]
    if nature == "url":
        u = _str(v, 500)
        if not (u.startswith("https://") or u.startswith("http://") or u.startswith("/")):
            raise ValueError("lien : http(s):// ou chemin local seulement")
        return u
    if nature == "colonnes":
        if not isinstance(v, list) or not 1 <= len(v) <= 4:
            raise ValueError("comparaison : 1 à 4 colonnes")
        return [{"titre": _str(c.get("titre", ""), 200), "texte": _str(c.get("texte", ""))}
                for c in v if isinstance(c, dict)]
    raise ValueError(nature)


def valider(brut: dict) -> dict:
    """Surface nettoyée ; ValueError si elle ne tient pas."""
    if not isinstance(brut, dict):
        raise ValueError("une surface est un objet JSON")
    pieces = brut.get("pieces", [])
    if not isinstance(pieces, list) or not pieces:
        raise ValueError("une surface a au moins une pièce")
    if len(pieces) > MAX_PIECES:
        raise ValueError(f"au plus {MAX_PIECES} pièces")
    propres, ids = [], set()
    for i, p in enumerate(pieces):
        if not isinstance(p, dict) or p.get("type") not in PIECES:
            raise ValueError(f"pièce {i} : type inconnu ({p.get('type') if isinstance(p, dict) else p!r}) ; "
                             f"types : {', '.join(PIECES)}")
        champs = PIECES[p["type"]]
        q = {"type": p["type"]}
        for k, v in p.items():
            if k in champs:
                try:
                    q[k] = _champ(champs[k], v)
                except ValueError as e:
                    raise ValueError(f"pièce {i} ({p['type']}), champ {k} : {e}") from None
        if "id" in champs:
            q.setdefault("id", f"{p['type']}{i}")
            if q["id"] in ids:
                raise ValueError(f"identifiant en double : {q['id']}")
            ids.add(q["id"])
        propres.append(q)
    return {"titre": _str(brut.get("titre", "Surface"), 120), "outil": _str(brut.get("outil", ""), 120),
            "pieces": propres}


class Bibliotheque:
    """Modèles de surfaces sauvés dans le dépôt."""

    def __init__(self, racine: Path):
        self.dossier = racine / "modeles" / "surfaces"

    def lister(self) -> list[dict]:
        out = []
        for f in sorted(self.dossier.glob("*.json")):
            try:
                s = json.loads(f.read_text(encoding="utf-8"))
                out.append({"nom": f.stem, "titre": s.get("titre", f.stem),
                            "pieces": [p["type"] for p in s.get("pieces", [])]})
            except (OSError, ValueError, KeyError, TypeError):
                continue
        return out

    def lire(self, nom: str) -> dict:
        if not RE_NOM.fullmatch(nom):
            raise ValueError("nom de modèle invalide")
        f = self.dossier / f"{nom}.json"
        if not f.exists():
            raise KeyError(f"Modèle inconnu : {nom}")
        return json.loads(f.read_text(encoding="utf-8"))

    def sauver(self, nom: str, surface: dict) -> dict:
        if not RE_NOM.fullmatch(nom):
            raise ValueError("nom de modèle : minuscules, chiffres, - et _")
        s = valider(surface)
        self.dossier.mkdir(parents=True, exist_ok=True)
        (self.dossier / f"{nom}.json").write_text(json.dumps(s, ensure_ascii=False, indent=2) + "\n",
                                                  encoding="utf-8")
        return {"nom": nom, **s}

    def composer(self, brut: dict) -> dict:
        """Bloc d'une IA → surface : reprend un modèle si `modele` est donné, puis valide."""
        if isinstance(brut, dict) and brut.get("modele"):
            base = self.lire(str(brut["modele"]))
            brut = {**base, **{k: v for k, v in brut.items() if k != "modele"}}
        return valider(brut)
