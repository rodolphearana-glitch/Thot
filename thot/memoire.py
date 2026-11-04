"""Mémoire de construction : Thot garde la trace de sa propre construction, tenue par les IA.

Demande de Rodolphe (5 novembre 2026) : « il gère la mémoire pour garder la trace de sa propre
construction comme il veux », « en restant dans les limite de l'utilisation bien sur ».

- Une IA ajoute des lignes avec un bloc `thot-memoire` (une ligne par fait, décision ou leçon).
- En ajout seulement : une correction s'ajoute, rien ne s'efface (règle du journal).
- Limites d'utilisation : lignes courtes, quelques lignes par tour, seule la fin du fichier est relue à
  chaque tour, et le fichier part dans `memoire/archives/` quand il dépasse sa taille.
"""
from __future__ import annotations

import threading
from datetime import datetime
from pathlib import Path

from .confidentialite import masquer

MAX_LIGNE = 300
MAX_LIGNES_PAR_TOUR = 5
MAX_FICHIER = 40000
RELU = 6000
ENTETE = ("# Mémoire de construction de Thot\n\n"
          "Tenue par les IA du labo (bloc thot-memoire), en ajout seulement. Rodolphe y signale les lignes fausses.\n\n")
_verrou = threading.Lock()


class Memoire:
    def __init__(self, racine: Path):
        self.dossier = racine / "memoire"
        self.fichier = self.dossier / "construction.md"

    def _archiver_si_besoin(self) -> None:
        if self.fichier.exists() and self.fichier.stat().st_size > MAX_FICHIER:
            arch = self.dossier / "archives"
            arch.mkdir(parents=True, exist_ok=True)
            nom = f"construction-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
            self.fichier.rename(arch / nom)
            self.fichier.write_text(ENTETE + f"(Lignes précédentes : memoire/archives/{nom})\n\n", encoding="utf-8")

    def ajouter(self, auteur: str, bloc: str) -> list[str]:
        lignes = [l.strip().lstrip("-• ").strip() for l in bloc.splitlines() if l.strip()]
        lignes = [masquer(l)[:MAX_LIGNE] for l in lignes][:MAX_LIGNES_PAR_TOUR]
        if not lignes:
            return []
        jour = datetime.now().strftime("%Y-%m-%d")
        with _verrou:
            self.dossier.mkdir(parents=True, exist_ok=True)
            if not self.fichier.exists():
                self.fichier.write_text(ENTETE, encoding="utf-8")
            self._archiver_si_besoin()
            with open(self.fichier, "a", encoding="utf-8") as f:
                for l in lignes:
                    f.write(f"- {jour} ({auteur}) {l}\n")
        return lignes

    def corriger(self, ligne: str, remarque: str = "") -> None:
        texte = f"CORRECTION : la ligne « {ligne.strip()[:MAX_LIGNE]} » est fausse."
        if remarque.strip():
            texte += " " + remarque.strip()[:MAX_LIGNE]
        jour = datetime.now().strftime("%Y-%m-%d")
        with _verrou:
            self.dossier.mkdir(parents=True, exist_ok=True)
            if not self.fichier.exists():
                self.fichier.write_text(ENTETE, encoding="utf-8")
            with open(self.fichier, "a", encoding="utf-8") as f:
                f.write(f"- {jour} (Rodolphe) {masquer(texte)}\n")

    def lignes(self, n: int = 12) -> list[str]:
        if not self.fichier.exists():
            return []
        return [l[2:] for l in self.fichier.read_text(encoding="utf-8").splitlines() if l.startswith("- ")][-n:]

    def pour_prompt(self) -> str:
        if not self.fichier.exists():
            return ""
        t = self.fichier.read_text(encoding="utf-8")
        return t if len(t) <= RELU else "(début omis)\n" + t[-RELU:]
