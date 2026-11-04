"""File de travaux : des calculs déposés sur GitHub que le PC de Rodolphe lance seul, puis renvoie.

Fichier protégé : il fait tourner du code sur le PC sans clic.

Désactivée par défaut (`[travaux] active = false`). Rodolphe l'allume lui-même.

Un travail est un fichier `travaux/a-faire/<id>.json` :

    {"experience": "exp2_erin", "parametres": {...}, "duree_max_s": 28800,
     "auteur": "Claude", "pourquoi": "une phrase"}

Garde-fous, vérifiés avant chaque lancement :
- seulement `experiences/<nom>/run.py`, jamais une autre commande ;
- l'expérience a ses prédictions (`PREDICTIONS.md`) déjà commitées, et un `rapide.json` (que les tests
  lancent pour de vrai) ; le code est arrivé par la synchro, qui teste toute nouvelle version avant
  de l'installer ;
- bridé par le régulateur (cœurs gardés, priorité basse, pause pendant un jeu, durée maximale) ;
- un travail à la fois ; le fichier `travaux/STOP` (ou le bouton de l'établi) arrête tout.

Limite connue, écrite plutôt que cachée : rien n'empêche techniquement un script d'expérience d'utiliser
le réseau. La relecture, les tests et l'historique Git restent la protection.

Résultat : `travaux/faits/<id>/` (le travail, la sortie, le rapport du régulateur), versé sur GitHub.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import threading
from pathlib import Path

from .journal import maintenant
from .ressources import Ressources

RE_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_\-]{0,80}")


class Travaux:
    def __init__(self, racine: Path, config: dict, ressources: Ressources):
        self.racine = racine
        self.config = {"active": False, "duree_max_s": 28800, **(config or {})}
        self.ressources = ressources
        self.dossier = racine / "travaux"
        self.en_cours: dict | None = None
        self._verrou = threading.Lock()

    # -- état -------------------------------------------------------------------------
    @property
    def active(self) -> bool:
        return bool(self.config.get("active"))

    @property
    def arrete(self) -> bool:
        return (self.dossier / "STOP").exists()

    def a_faire(self) -> list[Path]:
        return sorted((self.dossier / "a-faire").glob("*.json"))

    def faits(self, n: int = 20) -> list[dict]:
        out = []
        for d in sorted((self.dossier / "faits").glob("*/"), reverse=True)[:n]:
            try:
                out.append(json.loads((d / "resultat.json").read_text(encoding="utf-8")))
            except (OSError, ValueError):
                continue
        return out

    def etat(self) -> dict:
        return {"active": self.active, "arrete": self.arrete,
                "en_cours": {k: v for k, v in (self.en_cours or {}).items() if not k.startswith("_")} or None,
                "a_faire": [p.stem for p in self.a_faire()], "faits": self.faits()}

    def arreter(self) -> None:
        (self.dossier).mkdir(exist_ok=True)
        (self.dossier / "STOP").write_text(f"Arrêt demandé le {maintenant()}.\n", encoding="utf-8")
        self.ressources.arreter_tout()

    def reprendre(self) -> None:
        (self.dossier / "STOP").unlink(missing_ok=True)
        self.ressources.reprendre()

    # -- vérifications ------------------------------------------------------------------
    def _git(self, *args) -> subprocess.CompletedProcess:
        return subprocess.run(["git", *args], cwd=self.racine, capture_output=True, text=True,
                              encoding="utf-8", errors="replace")

    def verifier(self, fichier: Path) -> tuple[dict, str]:
        """Le travail lu, et une raison de refus (vide si tout va bien)."""
        if not RE_ID.fullmatch(fichier.stem):
            return {}, "identifiant de travail invalide"
        try:
            t = json.loads(fichier.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            return {}, f"travail illisible : {e}"
        nom = str(t.get("experience", ""))
        if not re.fullmatch(r"[a-z0-9_]+", nom):
            return t, "nom d'expérience invalide"
        d = self.racine / "experiences" / nom
        if not (d / "run.py").exists():
            return t, f"expérience inconnue : {nom}"
        for requis in ("PREDICTIONS.md", "rapide.json"):
            if not (d / requis).exists():
                return t, f"{nom} n'a pas de {requis}"
        if not self._git("log", "-1", "--format=%H", "--", f"experiences/{nom}/PREDICTIONS.md").stdout.strip():
            return t, f"les prédictions de {nom} ne sont pas commitées : elles doivent l'être avant tout lancement"
        if not isinstance(t.get("parametres", {}), dict):
            return t, "parametres doit être un objet JSON"
        return t, ""

    # -- exécution ------------------------------------------------------------------------
    def lancer_suivant(self, en_arriere_plan: bool = True) -> str:
        """Lance le prochain travail s'il y en a un et que tout le permet. Renvoie ce qui s'est passé."""
        if not self.active:
            return "file de travaux désactivée"
        if self.arrete:
            return "file arrêtée (travaux/STOP)"
        if not self._verrou.acquire(blocking=False):
            return "un travail tourne déjà"
        liste = self.a_faire()
        if not liste:
            self._verrou.release()
            return "rien à faire"
        fichier = liste[0]
        if en_arriere_plan:
            threading.Thread(target=self._executer_et_liberer, args=(fichier,), daemon=True).start()
            return f"travail {fichier.stem} lancé"
        self._executer_et_liberer(fichier)
        return f"travail {fichier.stem} terminé"

    def _executer_et_liberer(self, fichier: Path) -> None:
        try:
            self._executer(fichier)
        finally:
            self.en_cours = None
            self._verrou.release()

    def _executer(self, fichier: Path) -> None:
        ident = fichier.stem
        sortie_dir = self.dossier / "faits" / ident
        if sortie_dir.exists():
            ident = f"{ident}-{maintenant().replace(':', '').replace('-', '')[:15]}"
            sortie_dir = self.dossier / "faits" / ident
        sortie_dir.mkdir(parents=True)
        travail, refus = self.verifier(fichier)
        res = {"id": ident, "travail": travail, "debut": maintenant(), "fin": None, "reussi": False}
        if refus:
            res.update(fin=maintenant(), refus=refus)
        else:
            nom = travail["experience"]
            duree = min(int(travail.get("duree_max_s", self.config["duree_max_s"])), int(self.config["duree_max_s"]))
            self.en_cours = {"id": ident, "experience": nom, "debut": res["debut"], "evenements": []}
            evts = self.en_cours["evenements"]
            rap = self.ressources.lancer(
                [sys.executable, str(self.racine / "experiences" / nom / "run.py"),
                 "--params", json.dumps(travail.get("parametres", {}))],
                cwd=self.racine, duree_max_s=duree, sur_evenement=evts.append)
            (sortie_dir / "sortie.txt").write_text(rap.sortie, encoding="utf-8")
            derniere = rap.sortie.strip().splitlines()[-1] if rap.sortie.strip() else ""
            try:
                res["resultat"] = json.loads(derniere)
            except ValueError:
                res["resultat"] = None
            res.update(fin=maintenant(), reussi=rap.code == 0 and not rap.interrompu, code=rap.code,
                       duree_s=rap.duree_s, pause_s=rap.pause_s, interrompu=rap.interrompu,
                       evenements=rap.evenements)
        (sortie_dir / "resultat.json").write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
        shutil.move(str(fichier), str(sortie_dir / "travail.json"))
