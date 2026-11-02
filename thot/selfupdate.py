"""Auto-mise à jour encadrée du labo.

Fichier protégé : aucune modification automatique ne peut le toucher sans l'accord de Rodolphe
(sinon le labo pourrait desserrer ses propres garde-fous).

Principe (validé par Rodolphe le 2026-11-02) :
- une IA propose un patch (diff unifié) ;
- s'il ne touche que des chemins autorisés et ne contient rien de sensible, il est appliqué
  sur une branche à part, les tests sont lancés, et il est fusionné seul s'ils passent ;
- sinon il attend l'accord de Rodolphe (dépendance, réseau, commandes système, suppression,
  fichiers protégés, clés) ;
- tout est journalisé dans journal/auto-maj/ et chaque modification reste annulable.
"""
from __future__ import annotations

import fnmatch
import os
import json
import re
import shutil
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path

from .confidentialite import masquer
from .journal import maintenant

_verrou = threading.Lock()

# Toujours soumis à l'accord de Rodolphe, quelle que soit la configuration.
PROTEGES = [
    "thot/selfupdate.py",
    "thot/synchro.py",
    "thot/codage.py",
    "thot/confidentialite.py",
    "thot/__main__.py",
    "thot/budget.py",
    "thot/config.py",
    "thot/providers/**",
    "thot/web/app.py",
    ".gitignore",
    "pyproject.toml",
    "requirements*.txt",
    "thot.config*.toml",
    "lancer.bat",
    ".github/**",
]
# Jamais modifiable par patch : la mémoire du labo ne se réécrit pas.
INTERDITS = ["journal/**", "contextes/**", ".git/**", ".thot/**"]

MOTIFS_SENSIBLES = {
    "accès réseau": re.compile(r"https?://|\bhttpx\b|\brequests\b|\burllib\b|\bsocket\b"),
    "exécution de commandes système": re.compile(r"\bsubprocess\b|\bos\.system\b|\bos\.popen\b"),
    "installation de paquets": re.compile(r"\bpip\b|\bconda\b|\bnpm\b"),
    "accès aux clés": re.compile(r"API_KEY|\bcles\b|thot\.config\.toml"),
}


def extraire_blocs(texte: str, langage: str) -> list[str]:
    motif = re.compile(r"```" + re.escape(langage) + r"[ \t]*\n(.*?)```", re.DOTALL)
    return [m.strip("\n") + "\n" for m in motif.findall(texte)]


def fichiers_du_patch(patch: str) -> tuple[set[str], set[str]]:
    """Renvoie (fichiers touchés, fichiers supprimés)."""
    touches, supprimes = set(), set()
    lignes = patch.splitlines()
    for i, l in enumerate(lignes):
        if l.startswith("--- ") and i + 1 < len(lignes) and lignes[i + 1].startswith("+++ "):
            avant = l[4:].strip()
            apres = lignes[i + 1][4:].strip()
            avant = re.sub(r"^a/", "", avant)
            apres = re.sub(r"^b/", "", apres)
            if apres == "/dev/null":
                supprimes.add(avant)
                touches.add(avant)
            else:
                touches.add(apres)
                if avant != "/dev/null" and avant != apres:
                    touches.add(avant)
    return touches, supprimes


def _correspond(chemin: str, motifs: list[str]) -> bool:
    return any(fnmatch.fnmatch(chemin, m) for m in motifs)


def evaluer(patch: str, chemins_autorises: list[str]) -> tuple[str, list[str]]:
    """Décide si un patch peut être appliqué seul.

    Renvoie ("auto" | "accord" | "interdit", raisons).
    """
    touches, supprimes = fichiers_du_patch(patch)
    raisons: list[str] = []
    if not touches:
        return "interdit", ["aucun fichier reconnu dans le patch"]
    for f in sorted(touches):
        if ".." in Path(f).parts or Path(f).is_absolute():
            return "interdit", [f"chemin hors du dépôt : {f}"]
        if _correspond(f, INTERDITS):
            return "interdit", [f"zone non modifiable par patch : {f}"]
    for f in sorted(touches):
        if _correspond(f, PROTEGES):
            raisons.append(f"fichier protégé : {f}")
        elif not _correspond(f, chemins_autorises):
            raisons.append(f"hors des chemins autorisés : {f}")
    for f in sorted(supprimes):
        raisons.append(f"suppression de fichier : {f}")
    ajouts = "\n".join(l for l in patch.splitlines() if l.startswith("+") and not l.startswith("+++"))
    for nom, motif in MOTIFS_SENSIBLES.items():
        if motif.search(ajouts):
            raisons.append(nom)
    return ("accord" if raisons else "auto"), raisons


class AutoMaj:
    def __init__(self, racine: Path, config: dict):
        self.racine = racine
        self.config = config
        self.dossier = racine / "journal" / "auto-maj"
        self.dossier.mkdir(parents=True, exist_ok=True)
        self.travail = racine / ".thot" / "worktrees"

    # -- registre -------------------------------------------------------------
    def lister(self) -> list[dict]:
        res = []
        for f in sorted(self.dossier.glob("*.json"), reverse=True):
            res.append(json.loads(f.read_text(encoding="utf-8")))
        return res

    def lire(self, ident: str) -> dict:
        if not re.fullmatch(r"[A-Za-z0-9\-]+", ident):
            raise ValueError("Identifiant invalide.")
        return json.loads((self.dossier / f"{ident}.json").read_text(encoding="utf-8"))

    def _sauver(self, rec: dict) -> None:
        for champ in ("tests", "erreur", "justification"):
            if rec.get(champ):
                rec[champ] = masquer(rec[champ])
        (self.dossier / f"{rec['id']}.json").write_text(
            json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    # -- cycle de vie -----------------------------------------------------------
    def proposer(self, patch: str, auteur: str, justification: str, session: str = "") -> dict:
        with _verrou:
            ident = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            decision, raisons = evaluer(patch, self.config.get("chemins_autorises", []))
            rec = {
                "id": ident,
                "auteur": auteur,
                "session": session,
                "justification": justification.strip()[:2000],
                "propose": maintenant(),
                "fichiers": sorted(fichiers_du_patch(patch)[0]),
                "raisons": raisons,
                "patch": patch,
                "statut": "en_attente",
                "historique": [],
            }
            if decision == "interdit":
                rec["statut"] = "interdit"
            elif not self.config.get("active", False):
                rec["raisons"].append("auto-mise à jour désactivée dans la configuration")
            elif decision == "auto":
                self._appliquer(rec)
            self._sauver(rec)
            return rec

    def approuver(self, ident: str) -> dict:
        with _verrou:
            rec = self.lire(ident)
            if rec["statut"] != "en_attente":
                raise ValueError(f"Statut actuel : {rec['statut']}")
            rec["historique"].append({"quand": maintenant(), "quoi": "approuvé par Rodolphe"})
            self._appliquer(rec)
            self._sauver(rec)
            return rec

    def refuser(self, ident: str) -> dict:
        with _verrou:
            rec = self.lire(ident)
            if rec["statut"] != "en_attente":
                raise ValueError(f"Statut actuel : {rec['statut']}")
            rec["statut"] = "refuse"
            rec["historique"].append({"quand": maintenant(), "quoi": "refusé par Rodolphe"})
            self._sauver(rec)
            return rec

    def annuler(self, ident: str) -> dict:
        with _verrou:
            rec = self.lire(ident)
            if rec["statut"] != "applique" or not rec.get("commit"):
                raise ValueError("Seule une modification appliquée peut être annulée.")
            r = self._git("revert", "--no-edit", rec["commit"])
            if r.returncode != 0:
                self._git("revert", "--abort")
                raise RuntimeError("Annulation impossible : " + (r.stderr or r.stdout)[-800:])
            rec["statut"] = "annule"
            rec["commit_annulation"] = self._git("rev-parse", "HEAD").stdout.strip()
            rec["historique"].append({"quand": maintenant(), "quoi": "annulé (git revert)"})
            self._sauver(rec)
            return rec

    # -- mécanique --------------------------------------------------------------
    def _git(self, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", *args], cwd=cwd or self.racine, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
        )

    def _appliquer(self, rec: dict) -> None:
        if self._git("rev-parse", "HEAD").returncode != 0:
            rec["raisons"].append("le dossier n'est pas un dépôt Git avec au moins un commit")
            rec["statut"] = "en_attente"
            return
        branche = f"auto/{rec['id']}"
        wt = self.travail / rec["id"]
        wt.parent.mkdir(parents=True, exist_ok=True)
        r = self._git("worktree", "add", str(wt), "-b", branche, "HEAD")
        if r.returncode != 0:
            rec["statut"] = "echec"
            rec["erreur"] = r.stderr[-800:]
            return
        try:
            fichier_patch = wt.parent / f"{rec['id']}.patch"
            fichier_patch.write_text(rec["patch"], encoding="utf-8")
            r = self._git("apply", "--whitespace=nowarn", str(fichier_patch), cwd=wt)
            if r.returncode != 0:
                rec["statut"] = "invalide"
                rec["erreur"] = "Le patch ne s'applique pas : " + r.stderr[-800:]
                return
            ok, sortie = self._tests(wt)
            rec["tests"] = sortie[-3000:]
            if not ok:
                rec["statut"] = "rejete_tests"
                return
            self._git("add", "-A", cwd=wt)
            message = (
                f"auto-maj ({rec['auteur']}) : {rec['justification'][:72] or 'modification du labo'}\n\n"
                f"{rec['justification']}\n\nProposé dans la session {rec['session'] or '-'}, "
                f"enregistrement journal/auto-maj/{rec['id']}.json"
            )
            r = self._git("commit", "-m", message, cwd=wt)
            if r.returncode != 0:
                rec["statut"] = "echec"
                rec["erreur"] = (r.stderr or r.stdout)[-800:]
                return
            sha = self._git("rev-parse", "HEAD", cwd=wt).stdout.strip()
            r = self._git("merge", "--ff-only", branche)
            if r.returncode != 0:
                r = self._git("cherry-pick", sha)
                if r.returncode != 0:
                    self._git("cherry-pick", "--abort")
                    rec["statut"] = "en_attente"
                    rec["raisons"].append("conflit avec l'état actuel du dépôt")
                    return
                sha = self._git("rev-parse", "HEAD").stdout.strip()
            rec["statut"] = "applique"
            rec["commit"] = sha
            rec["applique"] = maintenant()
            rec["redemarrage_conseille"] = any(f.startswith("thot/") and f.endswith(".py") for f in rec["fichiers"])
        finally:
            self._git("worktree", "remove", "--force", str(wt))
            self._git("branch", "-D", branche)
            shutil.rmtree(wt, ignore_errors=True)

    def _tests(self, wt: Path) -> tuple[bool, str]:
        duree = int(self.config.get("duree_max_tests_s", 300))
        try:
            r = subprocess.run(
                [sys.executable, "-m", "pytest", "-q", "-x"], cwd=wt, capture_output=True,
                text=True, timeout=duree, encoding="utf-8", errors="replace",
                env={**os.environ, "PYTHONUTF8": "1"},
            )
        except subprocess.TimeoutExpired:
            return False, f"Tests interrompus après {duree} s."
        return r.returncode == 0, (r.stdout + r.stderr)
