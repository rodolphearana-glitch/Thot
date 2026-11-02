"""Mode codage : une IA du labo code pour de vrai, dans une copie à part du dépôt.

Fichier protégé : aucune modification automatique sans l'accord de Rodolphe.

Inspiré du codage du Studio TLS (établi à part, relecture par l'autre IA), mais branché sur les
garde-fous de Thot : le résultat devient un patch qui passe par l'auto-mise à jour (zones libres →
testé et appliqué seul ; le reste → accord de Rodolphe ; tout reste annulable).

Déroulé d'un codage demandé par un bloc ```thot-codage``` :
1. copie à part du dépôt (`git worktree`, détachée, partie du HEAD courant), dans .thot/codage/<id> ;
2. l'IA qui a demandé le codage (Claude Code ou Codex) y modifie les fichiers et lance les tests ;
3. Thot relance lui-même les tests dans la copie (UTF-8 forcé, leçon du Studio) ;
4. l'autre IA de la session relit le changement, en lecture seule ;
5. le changement devient un patch proposé à l'auto-mise à jour, avec le résumé, les tests et la relecture ;
6. la copie est retirée (le patch, lui, est gardé dans journal/auto-maj/).
"""
from __future__ import annotations

import os
import shutil
import stat
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from . import providers
from .config import Config, Participant

CHARTE_CODAGE = """Tu es en mode codage dans Thot, le labo de recherche de Rodolphe.

Tu travailles dans une COPIE À PART du dépôt (le dossier courant), jamais dans le dossier de Rodolphe.
Ce que tu modifies ici devient une proposition : Thot relance les tests, l'autre IA relit, puis les
garde-fous de l'auto-mise à jour décident (zones libres : appliqué seul si les tests passent ; le reste :
accord de Rodolphe). Tout reste annulable.

Règles :
- Lis AGENTS.md avant de commencer, et respecte-le (journal/ et contextes/ ne se réécrivent pas ;
  aucun secret dans le dépôt, il est public ; les fichiers protégés de thot/selfupdate.py ne se
  contournent pas).
- Fais exactement ce qui est demandé, sans élargir le périmètre. Une idée en plus se propose, elle ne
  s'ajoute pas en douce.
- Ajoute ou adapte un test quand tu changes un comportement.
- Lance les tests avec : {python} -m pytest -q
- Ne fais ni commit ni push : Thot s'en charge.
- Termine par un court compte rendu : ce qui est fait, les tests lancés et leur résultat, ce qui n'est
  pas vérifié (par exemple un rendu visuel que tu n'as pas pu voir).
"""

CHARTE_RELECTURE = """Tu relis, en lecture seule, un changement codé par une autre IA dans Thot, le labo de
recherche de Rodolphe. Dis en quelques lignes : s'il fait ce qui était demandé, les erreurs ou risques
que tu vois (avec le fichier et la ligne), et ce qui n'est pas vérifié. Pas de reformulation du
changement, pas de complaisance. Termine par une ligne seule : AVIS : favorable, ou AVIS : réservé."""


def _effacer(dossier: Path) -> None:
    def deverrouiller(fonction, chemin, _info):
        try:
            os.chmod(chemin, stat.S_IWRITE)
            fonction(chemin)
        except OSError:
            pass
    shutil.rmtree(dossier, onerror=deverrouiller)


class Codage:
    def __init__(self, config: Config, automaj):
        self.config = config
        self.racine = config.racine
        self.automaj = automaj
        self.reglages = getattr(config, "codage", None) or {}

    def _git(self, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(["git", *args], cwd=cwd or self.racine, capture_output=True, text=True,
                              encoding="utf-8", errors="replace")

    def lancer(self, auteur: Participant, consigne: str, relecteur: Participant | None,
               session: str, contexte: str = "") -> dict:
        """Exécute un codage complet. Renvoie un compte rendu (dict) ; ne lève pas sur un échec de l'IA."""
        ident = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        copie = self.racine / ".thot" / "codage" / ident
        copie.parent.mkdir(parents=True, exist_ok=True)
        cr = {"id": ident, "auteur": auteur.nom, "consigne": consigne, "resume": "", "tests": "",
              "tests_ok": None, "relecture": "", "patch": "", "automaj": None, "erreur": ""}
        r = self._git("worktree", "add", "--detach", str(copie), "HEAD")
        if r.returncode != 0:
            cr["erreur"] = "Copie à part impossible : " + r.stderr.strip()[-400:]
            return cr
        try:
            delai = int(self.reglages.get("duree_max_s", 3600))
            systeme = CHARTE_CODAGE.format(python=f'"{sys.executable}"')
            prompt = (f"# Ce qui est demandé (par {auteur.nom}, dans la session {session})\n\n{consigne}\n\n"
                      + (f"# Contexte de la session\n\n{contexte}\n" if contexte else ""))
            try:
                rep = providers.coder(self.config, auteur, systeme, prompt, copie, delai)
                cr["resume"] = rep.texte
            except providers.ErreurProvider as e:
                cr["erreur"] = str(e)
            # Ce qui a changé, même si l'IA s'est arrêtée en route (rien n'est perdu : c'est dans le patch).
            self._git("add", "-A", cwd=copie)
            cr["patch"] = self._git("diff", "--cached", "--binary", "HEAD", cwd=copie).stdout
            if not cr["patch"].strip():
                cr["erreur"] = cr["erreur"] or "Aucun fichier modifié."
                return cr
            cr["tests_ok"], cr["tests"] = self._tests(copie)
            if relecteur is not None:
                cr["relecture"] = self._relire(relecteur, consigne, cr, copie)
            justification = self._justification(cr)
            rec = self.automaj.proposer(cr["patch"], auteur.nom, justification, session)
            cr["automaj"] = rec
            return cr
        finally:
            self._git("worktree", "remove", "--force", str(copie))
            if copie.exists():
                _effacer(copie)
            self._git("worktree", "prune")

    def _tests(self, copie: Path) -> tuple[bool, str]:
        try:
            t = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=copie, capture_output=True,
                               text=True, encoding="utf-8", errors="replace", env=providers.env_enfant(),
                               timeout=int(self.reglages.get("duree_max_tests_s", 600)))
            return t.returncode == 0, (t.stdout + t.stderr)[-3000:]
        except subprocess.TimeoutExpired:
            return False, "Tests trop longs."

    def _relire(self, relecteur: Participant, consigne: str, cr: dict, copie: Path) -> str:
        prompt = (f"# Ce qui était demandé\n\n{consigne}\n\n# Compte rendu de {cr['auteur']}\n\n"
                  f"{cr['resume'] or '(aucun)'}\n\n# Tests relancés par Thot : "
                  f"{'réussis' if cr['tests_ok'] else 'en échec'}\n\n```\n{cr['tests'][-1500:]}\n```\n\n"
                  f"# Le changement\n\n```diff\n{cr['patch'][:60000]}\n```")
        try:
            # Le relecteur lit la copie (lecture seule) : il voit le code tel qu'il sera.
            if relecteur.provider == "claude":
                rep = providers._claude_code(relecteur, CHARTE_RELECTURE, prompt, self.racine, copie)
            elif relecteur.provider == "codex":
                rep = providers._codex(relecteur, CHARTE_RELECTURE, prompt, self.racine, copie)
            else:
                rep = providers.appeler(self.config, relecteur, CHARTE_RELECTURE, prompt)
            return rep.texte
        except providers.ErreurProvider as e:
            return f"(relecture impossible : {e})"

    @staticmethod
    def _justification(cr: dict) -> str:
        morceaux = [f"Codage par {cr['auteur']} : {cr['consigne'].strip()[:300]}"]
        if cr["tests_ok"] is not None:
            morceaux.append("Tests dans la copie : " + ("réussis." if cr["tests_ok"] else "EN ÉCHEC."))
        if cr["relecture"]:
            avis = [l for l in cr["relecture"].splitlines() if l.strip().upper().startswith("AVIS")]
            morceaux.append("Relecture : " + (avis[-1].strip() if avis else "voir le fil."))
        return "\n".join(morceaux)
