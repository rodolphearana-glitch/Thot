"""Chaque expérience tourne vraiment, en version très courte.

Constat du premier rapport d'observation (2026-11-02) : une modification de run.py avait été
« testée et appliquée » alors qu'aucun test ne lançait l'expérience. Désormais, toute expérience
doit fournir un `rapide.json` (paramètres d'un lancement de quelques secondes) ; ce test la lance
comme le labo le ferait et vérifie qu'elle se termine et rend sa ligne JSON finale.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent
EXPERIENCES = sorted(p.parent for p in (RACINE / "experiences").glob("*/run.py"))


@pytest.mark.parametrize("dossier", EXPERIENCES, ids=[d.name for d in EXPERIENCES])
def test_experience_tourne_en_version_courte(dossier):
    rapide = dossier / "rapide.json"
    assert rapide.exists(), f"{dossier.name} doit fournir rapide.json (lancement de quelques secondes)"
    params = {k: v for k, v in json.loads(rapide.read_text(encoding="utf-8")).items() if not k.startswith("_")}
    r = subprocess.run([sys.executable, str(dossier / "run.py"), "--params", json.dumps(params)],
                       cwd=RACINE, capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=120, env={**os.environ, "PYTHONUTF8": "1"})
    assert r.returncode == 0, (r.stdout + r.stderr)[-2000:]
    derniere = r.stdout.strip().splitlines()[-1]
    resultat = json.loads(derniere)
    assert isinstance(resultat, dict) and resultat
