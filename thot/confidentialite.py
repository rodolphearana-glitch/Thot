"""Ce qui ne doit jamais partir sur GitHub (le dépôt est public).

Appliqué à tout ce que Thot écrit dans le journal à partir du 2026-11-02 au soir, et à tout ce qu'il en
exporte (index, recadrages, rapports d'observation).
"""
from __future__ import annotations

import re

_MOTIFS_PRIVES = [
    # Chemins personnels (Windows, avec simples ou doubles barres ; Linux ; macOS).
    (re.compile(r"[A-Za-z]:(\\\\|\\|/)+Users(\\\\|\\|/)+[^\\/\s\"'`]+", re.IGNORECASE), "~"),
    (re.compile(r"/home/[^/\s\"'`]+"), "~"),
    (re.compile(r"/Users/[^/\s\"'`]+"), "~"),
    # Clés d'API et jetons.
    (re.compile(r"sk-ant-[A-Za-z0-9_\-]{10,}"), "[CLÉ MASQUÉE]"),
    (re.compile(r"sk-[A-Za-z0-9_\-]{20,}"), "[CLÉ MASQUÉE]"),
    (re.compile(r"gh[pousr]_[A-Za-z0-9]{20,}"), "[JETON MASQUÉ]"),
    (re.compile(r"(?i)(api[_-]?key|token|secret)(\s*[=:]\s*)[\"']?[A-Za-z0-9_\-]{16,}"), r"\1\2[MASQUÉ]"),
    # Adresses électroniques (sauf les adresses techniques de signature).
    (re.compile(r"\b(?!noreply@|thot@)[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"), "[COURRIEL MASQUÉ]"),
]


def masquer(texte: str) -> str:
    """Retire d'un texte ce qui ne doit pas être publié (chemins personnels, clés, courriels)."""
    if not texte:
        return texte
    for motif, remplacement in _MOTIFS_PRIVES:
        texte = motif.sub(remplacement, texte)
    return texte


