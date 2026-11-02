"""Synchronisation avec GitHub : le PC de Rodolphe se met à jour tout seul.

Fichier protégé (il pousse sur GitHub) : aucune modification automatique sans l'accord de Rodolphe.

Comme le Studio TLS (« tout passe par GitHub », Rodolphe, 2 novembre 2026) :
- au démarrage puis toutes les N minutes, Thot verse dans Git ce que le labo a produit sur le PC
  (journal des sessions, résultats d'expériences) ;
- il récupère ce qui est arrivé sur GitHub (lettres de GPT, corrections de Claude…) ;
- si du code arrive, il lance d'abord les tests sur la nouvelle version : s'ils échouent, il garde
  l'ancienne et le signale ;
- il pousse ce que le PC a produit (journal, modifications automatiques appliquées) ;
- si le code a changé, il redémarre dès qu'aucun tour n'est en cours (lancer.bat le relance).
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

from .journal import maintenant
from .selfupdate import _verrou as verrou_git

CODE_REDEMARRAGE = 3
# Ce qui demande un redémarrage quand ça change : le code et les dépendances.
MOTIFS_CODE = ("thot/", "requirements")


class Synchro:
    def __init__(self, racine: Path, config: dict, occupe=lambda: False):
        self.racine = racine
        self.config = config
        self.occupe = occupe
        self.etat = {"active": bool(config.get("active", True)), "derniere": None, "message": "",
                     "erreur": "", "redemarrage": False, "version": self.version()}
        self._arret = threading.Event()
        self.serveur = None  # uvicorn.Server, pour un arrêt propre

    # -- git ----------------------------------------------------------------------
    def _git(self, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(["git", *args], cwd=cwd or self.racine, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=300)

    def version(self) -> str:
        try:
            r = self._git("rev-parse", "--short", "HEAD")
            return r.stdout.strip() if r.returncode == 0 else ""
        except (OSError, subprocess.SubprocessError):
            return ""

    def disponible(self) -> str:
        """Chaîne vide si la synchro peut tourner, sinon la raison."""
        if not shutil.which("git"):
            return "Git n'est pas installé sur ce PC."
        if self._git("rev-parse", "--git-dir").returncode != 0:
            return "Ce dossier n'est pas relié à GitHub (relance lancer.bat, il s'en occupe)."
        if self._git("remote", "get-url", "origin").returncode != 0:
            return "Pas de dépôt GitHub « origin » configuré."
        return ""

    # -- un passage ------------------------------------------------------------------
    def passage(self) -> dict:
        """Un cycle complet. Renvoie l'état (aussi gardé dans self.etat)."""
        raison = self.disponible()
        if raison:
            self.etat.update(erreur=raison, derniere=maintenant())
            return self.etat
        branche = self.config.get("branche", "main")
        messages, erreur = [], ""
        with verrou_git:
            # 1. Verser ce que le labo a produit sur ce PC.
            chemins = [c for c in ("journal", "experiences") if (self.racine / c).exists()]
            if chemins:
                self._git("add", "-A", "--", *chemins)
            if self._git("diff", "--cached", "--quiet").returncode != 0:
                self._git("commit", "-q", "-m", "journal : sessions et résultats du labo (PC de Rodolphe)")
                messages.append("journal versé")
            # 2. Ce qui est arrivé sur GitHub.
            f = self._git("fetch", "-q", "origin", branche)
            if f.returncode != 0:
                erreur = "GitHub injoignable : " + f.stderr.strip()[-200:]
            else:
                distant = f"origin/{branche}"
                nouveaux = self._git("rev-list", "--count", f"HEAD..{distant}").stdout.strip()
                if nouveaux and nouveaux != "0":
                    touches = self._git("diff", "--name-only", f"HEAD...{distant}").stdout.split()
                    code = any(t.startswith(MOTIFS_CODE) for t in touches)
                    ok, sortie = (True, "") if not code else self._tester(distant)
                    if not ok:
                        erreur = ("Nouvelle version de GitHub refusée : ses tests échouent. Thot garde la "
                                  "version actuelle.\n" + sortie[-1500:])
                    else:
                        r = self._git("rebase", "--autostash", distant)
                        if r.returncode != 0:
                            self._git("rebase", "--abort")
                            erreur = ("Conflit entre le PC et GitHub, rien n'a été changé : "
                                      + (r.stderr or r.stdout).strip()[-400:])
                        else:
                            messages.append(f"{nouveaux} nouveauté(s) récupérée(s) de GitHub")
                            if code:
                                self.etat["redemarrage"] = True
                # 3. Pousser ce que le PC a produit.
                if not erreur and self.config.get("pousser", True):
                    en_avance = self._git("rev-list", "--count", f"{distant}..HEAD").stdout.strip()
                    if en_avance and en_avance != "0":
                        p = self._git("push", "-q", "origin", f"HEAD:{branche}")
                        if p.returncode != 0:
                            erreur = "Envoi vers GitHub impossible : " + p.stderr.strip()[-300:]
                        else:
                            messages.append(f"{en_avance} commit(s) envoyé(s) sur GitHub")
        self.etat.update(derniere=maintenant(), erreur=erreur,
                         message=", ".join(messages) or "à jour", version=self.version())
        return self.etat

    def _tester(self, cible: str) -> tuple[bool, str]:
        """Lance les tests de la nouvelle version dans une copie à part, sans toucher au dossier du PC."""
        copie = self.racine / ".thot" / "verif-maj"
        if copie.exists():
            self._git("worktree", "remove", "--force", str(copie))
            shutil.rmtree(copie, ignore_errors=True)
        copie.parent.mkdir(parents=True, exist_ok=True)
        r = self._git("worktree", "add", "--detach", str(copie), cible)
        if r.returncode != 0:
            return False, r.stderr
        try:
            t = subprocess.run([sys.executable, "-m", "pytest", "-q", "-x"], cwd=copie, capture_output=True,
                               text=True, encoding="utf-8", errors="replace",
                               timeout=int(self.config.get("duree_max_tests_s", 300)))
            return t.returncode == 0, t.stdout + t.stderr
        except subprocess.TimeoutExpired:
            return False, "Tests trop longs."
        finally:
            self._git("worktree", "remove", "--force", str(copie))
            shutil.rmtree(copie, ignore_errors=True)

    # -- en arrière-plan ---------------------------------------------------------------
    def demarrer(self) -> None:
        if not self.etat["active"]:
            self.etat["message"] = "synchronisation désactivée dans thot.config.toml"
            return
        threading.Thread(target=self._boucle, daemon=True).start()

    def arreter(self) -> None:
        self._arret.set()

    def _boucle(self) -> None:
        intervalle = max(60, int(self.config.get("intervalle_minutes", 10)) * 60)
        prochain = 0.0
        while not self._arret.is_set():
            if time.monotonic() >= prochain:
                try:
                    self.passage()
                except Exception as e:  # la synchro ne doit jamais faire tomber le labo
                    self.etat.update(erreur=f"Synchro : {e}", derniere=maintenant())
                prochain = time.monotonic() + intervalle
            if self.etat["redemarrage"] and not self.occupe() and self.serveur is not None:
                self.etat["message"] = "nouvelle version installée, redémarrage…"
                self.serveur.code_sortie = CODE_REDEMARRAGE
                self.serveur.should_exit = True
                return
            self._arret.wait(5)
