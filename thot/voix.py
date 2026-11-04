"""Voix locale : Thot écoute Rodolphe et lit les tours à voix haute, avec les calculs de son PC.

Fichier protégé (il fait tourner des modèles sur le PC).

- Écouter : `faster-whisper` sur le processeur (dépendance optionnelle, `requirements-voix.txt`).
  Le modèle est téléchargé une fois par la bibliothèque au premier usage, puis tout reste sur le PC.
- Parler : `piper` si une voix est installée et indiquée dans `[voix]` ; sinon la page utilise les voix
  françaises de Windows, locales elles aussi, par le navigateur.
- Une voix par participant (`[voix.participants]`), pour que Claude, GPT et la locale ne se confondent pas.

La pensée, elle, ne devient pas locale : Claude et GPT réfléchissent chez Anthropic et OpenAI. Seul le
participant « Local » (LM Studio) est entièrement sur le PC.
"""
from __future__ import annotations

import io
import os
import tempfile
import threading
import wave
from pathlib import Path

DEFAUTS = {
    "modele_ecoute": "small",      # tiny, base, small, medium, large-v3, large-v3-turbo…
    "langue": "fr",
    "participants": {},            # {"Claude": "fr_FR-siwis-medium.onnx" ou un nom de voix Windows, …}
    "dossier_voix": "modeles/voix",
}


def _importable(nom: str) -> bool:
    try:
        __import__(nom)
        return True
    except ImportError:
        return False


class Voix:
    def __init__(self, racine: Path, config: dict | None, participants: list[str], fils: int = 4):
        self.racine = racine
        self.c = {**DEFAUTS, **(config or {})}
        self.participants = participants
        self.fils = max(1, fils)
        self._whisper = None
        self._piper: dict[str, object] = {}
        self._verrou = threading.Lock()

    # -- ce qui est disponible -------------------------------------------------------------
    def _fichier_voix(self, auteur: str) -> Path | None:
        nom = self.c["participants"].get(auteur) or self.c["participants"].get("*")
        if not nom or not str(nom).endswith(".onnx"):
            return None
        f = Path(nom)
        if not f.is_absolute():
            f = self.racine / self.c["dossier_voix"] / f
        return f if f.exists() else None

    def parole(self) -> str:
        if _importable("piper") and any(self._fichier_voix(p) for p in self.participants + ["*"]):
            return "piper"
        return "navigateur"

    def etat(self) -> dict:
        return {"ecoute": _importable("faster_whisper"), "modele_ecoute": self.c["modele_ecoute"],
                "parole": self.parole(), "participants": self.participants,
                "voix": {k: str(v) for k, v in self.c["participants"].items()}}

    # -- écouter -----------------------------------------------------------------------------
    def ecouter(self, audio: bytes, type_mime: str = "audio/webm") -> str:
        if not audio:
            raise ValueError("enregistrement vide")
        if not _importable("faster_whisper"):
            raise RuntimeError("Écoute indisponible : installe les dépendances de la voix "
                               "(pip install -r requirements-voix.txt).")
        from faster_whisper import WhisperModel
        with self._verrou:
            if self._whisper is None:
                self._whisper = WhisperModel(self.c["modele_ecoute"], device="cpu", compute_type="int8",
                                             cpu_threads=self.fils)
            ext = ".ogg" if "ogg" in type_mime else ".wav" if "wav" in type_mime else ".webm"
            f = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
            try:
                f.write(audio)
                f.close()
                segments, _ = self._whisper.transcribe(f.name, language=self.c["langue"], vad_filter=True)
                return " ".join(s.text.strip() for s in segments).strip()
            finally:
                os.unlink(f.name)

    # -- dire --------------------------------------------------------------------------------
    def dire(self, auteur: str, texte: str) -> bytes:
        """WAV de la phrase, avec la voix Piper du participant."""
        fichier = self._fichier_voix(auteur)
        if not fichier or not _importable("piper"):
            raise RuntimeError("Pas de voix Piper pour ce participant : la page utilise les voix de Windows.")
        from piper import PiperVoice
        with self._verrou:
            v = self._piper.get(str(fichier))
            if v is None:
                v = self._piper[str(fichier)] = PiperVoice.load(str(fichier))
            tampon = io.BytesIO()
            with wave.open(tampon, "wb") as w:
                if hasattr(v, "synthesize_wav"):      # piper-tts ≥ 1.3
                    v.synthesize_wav(texte[:2000], w)
                else:                                 # piper-tts 1.2
                    v.synthesize(texte[:2000], w)
            return tampon.getvalue()
