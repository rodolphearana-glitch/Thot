import shutil
import subprocess
import sys
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

from thot.config import Config, Participant  # noqa: E402


def _git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def depot(tmp_path):
    """Une copie minimale du labo dans un dépôt Git temporaire."""
    for nom in ("thot", "tests", "contextes", "prompts"):
        src = RACINE / nom
        if src.exists():
            shutil.copytree(src, tmp_path / nom, ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy(RACINE / ".gitignore", tmp_path / ".gitignore")
    # Les tests du dépôt temporaire se limitent à un test trivial (évite la récursion).
    for f in (tmp_path / "tests").glob("test_*.py"):
        f.unlink()
    (tmp_path / "tests" / "test_trivial.py").write_text("def test_ok():\n    assert True\n")
    _git(tmp_path, "init", "-q", "-b", "main")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "Test")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "init")
    return tmp_path


@pytest.fixture
def config(depot):
    return Config(
        cles={},
        participants=[
            Participant("A", "echo"),
            Participant("B", "echo"),
            Participant("Relais", "manuel"),
        ],
        budget={"appels_par_jour": 10, "anthropic_tokens_par_jour": 1000,
                "openai_tokens_par_jour": 1000},
        auto_maj={"active": True, "chemins_autorises": ["prompts/**", "thot/roles/**", "tests/**"],
                  "duree_max_tests_s": 120},
        experiences={"autoriser_lancement_auto": False},
        contexte={"max_caracteres": 50000},
        racine=depot,
    )
