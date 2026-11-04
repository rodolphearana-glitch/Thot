"""Régulateur des ressources du PC : les calculs de Thot ne prennent jamais la machine à Rodolphe.

Fichier protégé : il décide de ce que les programmes lancés par Thot ont le droit d'utiliser.

Règles (plan du 4 novembre 2026, réglages par défaut proposés par Claude) :
- des cœurs sont gardés pour Rodolphe (`coeurs_reserves`, 6 par défaut) : les calculs n'ont le droit
  qu'aux autres processeurs logiques (affinité), en priorité basse ;
- adaptatif : toutes les quelques secondes, si Rodolphe utilise plus que ses cœurs gardés, les calculs
  en cours lui rendent des processeurs ; ils les reprennent quand il a fini ;
- carte graphique : elle ne se partage pas finement. Quand un programme de la liste `jeux` tourne,
  les calculs sont mis en pause (suspendus), puis reprennent ;
- un calcul a une durée maximale ; au-delà, tout son arbre de processus est arrêté.

Sans `psutil`, rien ne peut être bridé : le régulateur le dit (etat()["bridage"] = False), il ne fait
jamais semblant.
"""
from __future__ import annotations

import math
import os
import subprocess
import threading
import time
from dataclasses import dataclass, field

try:
    import psutil
except ImportError:  # pragma: no cover - dépend de l'installation
    psutil = None

DEFAUTS = {
    "coeurs_reserves": 6,          # cœurs physiques gardés pour Rodolphe
    "reserver": "debut",           # "debut" : les premiers processeurs logiques ; "fin" : les derniers
    "priorite": "basse",           # "basse" ou "normale"
    "adaptatif": True,
    "jeux": [],                    # noms d'exécutables, ex. ["eldenring.exe"] : pause des calculs
    "pause_si_jeu": True,
    "vram_reservee_go": 10,        # indicatif, pour les modèles locaux
    "intervalle_s": 5,
}


@dataclass
class Rapport:
    """Ce qui s'est passé pendant un calcul bridé."""
    code: int | None = None
    sortie: str = ""
    duree_s: float = 0.0
    pause_s: float = 0.0
    interrompu: str = ""            # raison d'un arrêt forcé, vide sinon
    evenements: list[str] = field(default_factory=list)


class Ressources:
    def __init__(self, config: dict | None = None):
        self.c = {**DEFAUTS, **(config or {})}
        self._arret = threading.Event()

    # -- ce que la machine offre ----------------------------------------------------
    @property
    def bridage(self) -> bool:
        return psutil is not None

    def processeurs(self) -> list[int]:
        n = (psutil.cpu_count(logical=True) if psutil else os.cpu_count()) or 1
        return list(range(n))

    def fils_par_coeur(self) -> int:
        if not psutil:
            return 1
        phys = psutil.cpu_count(logical=False) or 0
        log = psutil.cpu_count(logical=True) or 1
        return max(1, log // phys) if phys else 1

    def reserves(self) -> list[int]:
        """Processeurs logiques gardés pour Rodolphe (jamais tous : au moins un reste aux calculs)."""
        tous = self.processeurs()
        n = min(len(tous) - 1, max(0, int(self.c["coeurs_reserves"])) * self.fils_par_coeur())
        if n <= 0:
            return []
        return tous[:n] if self.c["reserver"] != "fin" else tous[-n:]

    def autorises(self) -> list[int]:
        res = set(self.reserves())
        return [p for p in self.processeurs() if p not in res]

    def jeu_en_cours(self) -> str:
        """Nom du premier jeu de la liste qui tourne, sinon chaîne vide."""
        jeux = {j.lower() for j in self.c.get("jeux", [])}
        if not jeux or not psutil:
            return ""
        for p in psutil.process_iter(["name", "status"]):
            nom = (p.info.get("name") or "").lower()
            if nom in jeux and p.info.get("status") != psutil.STATUS_ZOMBIE:
                return nom
        return ""

    def fils_disponibles(self) -> int:
        """Nombre de fils qu'un calcul peut demander maintenant (pour un solveur : num_workers)."""
        if self.c.get("pause_si_jeu", True) and self.jeu_en_cours():
            return 0
        return len(self.autorises())

    def env(self, base: dict | None = None) -> dict:
        """Variables qui disent aux bibliothèques de calcul combien de fils prendre."""
        e = dict(base if base is not None else os.environ)
        n = str(max(1, len(self.autorises())))
        e.update({"THOT_FILS": n, "OMP_NUM_THREADS": n, "MKL_NUM_THREADS": n, "OPENBLAS_NUM_THREADS": n,
                  "PYTHONUTF8": "1"})
        return e

    def etat(self) -> dict:
        return {
            "bridage": self.bridage,
            "processeurs": len(self.processeurs()),
            "reserves": self.reserves(),
            "autorises": self.autorises(),
            "fils_disponibles": self.fils_disponibles(),
            "jeu": self.jeu_en_cours(),
            "priorite": self.c["priorite"],
            "adaptatif": bool(self.c["adaptatif"]),
            "vram_reservee_go": self.c["vram_reservee_go"],
            "regles": self.c,
        }

    # -- appliquer les règles à un processus -----------------------------------------
    def _arbre(self, proc) -> list:
        try:
            return [proc] + proc.children(recursive=True)
        except psutil.Error:
            return []

    def _appliquer(self, procs: list, cpus: list[int]) -> None:
        for p in procs:
            try:
                if hasattr(p, "cpu_affinity") and cpus:
                    p.cpu_affinity(cpus)
            except (psutil.Error, OSError, ValueError):
                pass
            try:
                if self.c["priorite"] == "basse":
                    p.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS if os.name == "nt" else 10)
            except (psutil.Error, OSError):
                pass

    def _cible(self, arbre: list, actuels: list[int]) -> list[int]:
        """Processeurs à laisser au calcul selon ce que Rodolphe utilise en dehors de Thot."""
        autorises = self.autorises()
        if not self.c["adaptatif"] or not psutil:
            return autorises
        total = psutil.cpu_percent(interval=None) / 100 * len(self.processeurs())   # en processeurs
        notre = 0.0
        for p in arbre:
            try:
                notre += p.cpu_percent(interval=None) / 100
            except psutil.Error:
                pass
        dehors = max(0.0, total - notre)
        marge = len(self.reserves())
        # Rodolphe déborde de ses cœurs gardés (d'au moins un demi-processeur) : on lui en rend.
        manque = math.ceil(dehors - marge) if dehors > marge + 0.5 else 0
        garder = max(1, len(autorises) - manque)
        if garder == len(actuels):
            return actuels
        return autorises[:garder]

    def lancer(self, commande: list[str], cwd, duree_max_s: int, env: dict | None = None,
               sur_evenement=None) -> Rapport:
        """Lance un calcul bridé et attend sa fin. Pause pendant les jeux, affinité adaptative,
        arrêt de tout l'arbre au-delà de la durée (le temps de pause ne compte pas)."""
        from .providers import NO_WINDOW, _tuer
        rap = Rapport()

        def note(t: str) -> None:
            rap.evenements.append(f"{time.strftime('%H:%M:%S')} {t}")
            if sur_evenement:
                sur_evenement(t)

        debut = time.monotonic()
        proc = subprocess.Popen(commande, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, encoding="utf-8", errors="replace",
                                env=env if env is not None else self.env(), creationflags=NO_WINDOW,
                                start_new_session=(os.name != "nt"))
        morceaux: list[str] = []
        lecteur = threading.Thread(target=lambda: morceaux.extend(iter(proc.stdout.readline, "")), daemon=True)
        lecteur.start()
        ps = psutil.Process(proc.pid) if psutil else None
        cpus = self.autorises()
        if ps:
            self._appliquer([ps], cpus)
            note(f"bridé : {len(cpus)} processeurs sur {len(self.processeurs())}, priorité {self.c['priorite']}")
        else:
            note("psutil absent : calcul NON bridé")
        en_pause, pause_debut = False, 0.0
        if psutil:
            psutil.cpu_percent(interval=None)   # première mesure : sert de point de départ
        intervalle = max(1, int(self.c["intervalle_s"]))
        while proc.poll() is None:
            if self._arret.is_set():
                rap.interrompu = "arrêt demandé"
                break
            actif = time.monotonic() - debut - rap.pause_s - ((time.monotonic() - pause_debut) if en_pause else 0)
            if actif > duree_max_s:
                rap.interrompu = f"durée maximale dépassée ({duree_max_s} s)"
                break
            if ps:
                arbre = self._arbre(ps)
                jeu = self.jeu_en_cours() if self.c.get("pause_si_jeu", True) else ""
                if jeu and not en_pause:
                    for p in reversed(arbre):
                        try:
                            p.suspend()
                        except psutil.Error:
                            pass
                    en_pause, pause_debut = True, time.monotonic()
                    note(f"pause : {jeu} tourne")
                elif not jeu and en_pause:
                    for p in arbre:
                        try:
                            p.resume()
                        except psutil.Error:
                            pass
                    rap.pause_s += time.monotonic() - pause_debut
                    en_pause = False
                    note("reprise")
                if not en_pause:
                    nouveaux = self._cible(arbre, cpus)
                    if nouveaux != cpus:
                        note(f"processeurs du calcul : {len(cpus)} → {len(nouveaux)}")
                        cpus = nouveaux
                    self._appliquer(arbre, cpus)
            try:
                proc.wait(timeout=intervalle)
            except subprocess.TimeoutExpired:
                pass
        if rap.interrompu:
            if ps and en_pause:
                for p in self._arbre(ps):
                    try:
                        p.resume()
                    except psutil.Error:
                        pass
            _tuer(proc)
            note(f"arrêté : {rap.interrompu}")
        proc.wait()
        lecteur.join(5)
        rap.code = proc.returncode
        rap.sortie = "".join(morceaux)
        rap.duree_s = round(time.monotonic() - debut, 1)
        rap.pause_s = round(rap.pause_s, 1)
        return rap

    def arreter_tout(self) -> None:
        self._arret.set()

    def reprendre(self) -> None:
        self._arret.clear()
