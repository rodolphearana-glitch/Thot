"""Chargement de la configuration de Thot.

Fichier protégé : l'auto-mise à jour ne peut pas le modifier sans l'accord de Rodolphe.
"""
from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
FICHIER_CONFIG = RACINE / "thot.config.toml"
FICHIER_EXEMPLE = RACINE / "thot.config.example.toml"


@dataclass
class Participant:
    nom: str
    provider: str
    modele: str = ""
    url: str = ""


@dataclass
class Config:
    cles: dict[str, str]
    participants: list[Participant]
    budget: dict[str, int]
    auto_maj: dict
    experiences: dict
    contexte: dict
    racine: Path = field(default=RACINE)
    source: Path | None = None

    def participant(self, nom: str) -> Participant:
        for p in self.participants:
            if p.nom == nom:
                return p
        raise KeyError(f"Participant inconnu : {nom}")

    def cle(self, provider: str) -> str:
        env = {"anthropic": "ANTHROPIC_API_KEY", "openai": "OPENAI_API_KEY"}.get(provider)
        if env and os.environ.get(env):
            return os.environ[env]
        return self.cles.get(provider, "")


def charger(chemin: Path | None = None, racine: Path | None = None) -> Config:
    racine = racine or RACINE
    if chemin is None:
        chemin = racine / "thot.config.toml"
        if not chemin.exists():
            chemin = racine / "thot.config.example.toml"
    with open(chemin, "rb") as f:
        brut = tomllib.load(f)
    participants = [
        Participant(
            nom=p["nom"],
            provider=p["provider"],
            modele=p.get("modele", ""),
            url=p.get("url", ""),
        )
        for p in brut.get("participants", [])
    ]
    return Config(
        cles=brut.get("cles", {}),
        participants=participants,
        budget=brut.get("budget", {}),
        auto_maj=brut.get("auto_maj", {"active": False, "chemins_autorises": []}),
        experiences=brut.get("experiences", {"autoriser_lancement_auto": False}),
        contexte=brut.get("contexte", {"max_caracteres": 120000}),
        racine=racine,
        source=chemin,
    )
