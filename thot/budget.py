"""Plafonds quotidiens d'utilisation des API.

Fichier protégé : l'auto-mise à jour ne peut pas le modifier sans l'accord de Rodolphe.
L'état est stocké localement dans .thot/usage.json (ignoré par Git).
"""
from __future__ import annotations

import json
import threading
from datetime import date
from pathlib import Path

_verrou = threading.Lock()

PROVIDERS_PAYANTS = ("anthropic", "openai")      # plafond de tokens (API payantes)
PROVIDERS_COMPTES = ("anthropic", "openai", "claude", "codex")  # plafond d'appels (API et abonnements)


class BudgetDepasse(Exception):
    pass


class Budget:
    def __init__(self, config: dict, dossier_etat: Path):
        self.config = config
        self.fichier = dossier_etat / "usage.json"
        self.fichier.parent.mkdir(parents=True, exist_ok=True)

    def _lire(self) -> dict:
        aujourd_hui = date.today().isoformat()
        if self.fichier.exists():
            try:
                etat = json.loads(self.fichier.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                etat = {}
            if etat.get("jour") == aujourd_hui:
                return etat
        return {"jour": aujourd_hui, "tokens": {}, "appels": 0}

    def _ecrire(self, etat: dict) -> None:
        self.fichier.write_text(json.dumps(etat, indent=2), encoding="utf-8")

    def verifier(self, provider: str) -> None:
        """Lève BudgetDepasse si un appel à ce provider dépasserait un plafond."""
        with _verrou:
            etat = self._lire()
            max_appels = int(self.config.get("appels_par_jour", 0))
            if provider in PROVIDERS_COMPTES and etat["appels"] >= max_appels:
                raise BudgetDepasse(f"Plafond d'appels du jour atteint ({max_appels}).")
            if provider in PROVIDERS_PAYANTS:
                plafond = int(self.config.get(f"{provider}_tokens_par_jour", 0))
                if etat["tokens"].get(provider, 0) >= plafond:
                    raise BudgetDepasse(
                        f"Plafond de tokens du jour atteint pour {provider} ({plafond})."
                    )

    def enregistrer(self, provider: str, tokens: int) -> None:
        with _verrou:
            etat = self._lire()
            if provider in PROVIDERS_COMPTES:
                etat["appels"] += 1
            if provider in PROVIDERS_PAYANTS:
                etat["tokens"][provider] = etat["tokens"].get(provider, 0) + int(tokens)
            self._ecrire(etat)

    def etat(self) -> dict:
        with _verrou:
            etat = self._lire()
        etat["plafonds"] = {
            "appels_par_jour": self.config.get("appels_par_jour", 0),
            **{
                f"{p}_tokens_par_jour": self.config.get(f"{p}_tokens_par_jour", 0)
                for p in PROVIDERS_PAYANTS
            },
        }
        return etat
