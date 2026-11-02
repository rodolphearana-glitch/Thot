"""Mode codage, avec de faux Claude Code et Codex (scripts Unix)."""
import json
import os
import stat
import sys
import time

import pytest

from thot.labo import Labo
from thot.config import Participant

pytestmark = pytest.mark.skipif(os.name == "nt", reason="faux exécutables en script Unix")

FAUX_CLAUDE = """
import json, os, sys
args = sys.argv[1:]
consigne = sys.stdin.read()
if "--permission-mode" in args:            # mode codage : on écrit dans le dossier courant
    assert "Bash" in args[args.index("--allowedTools") + 1]
    assert os.path.realpath(os.getcwd()) != os.path.realpath(os.environ["THOT_RACINE"])
    os.makedirs("prompts", exist_ok=True)
    open("prompts/role-codage.md", "w", encoding="utf-8").write("rôle écrit en codage\\n")
    print(json.dumps({"result": "Fait : prompts/role-codage.md. Tests : non lancés ici."}))
else:
    print(json.dumps({"result": "AVIS : favorable"}))
"""

FAUX_CODEX = """
import sys
args = sys.argv[1:]
assert args[args.index("--sandbox") + 1] == "read-only"
sys.stdin.read()
open(args[args.index("-o") + 1], "w", encoding="utf-8").write("Rien à redire.\\nAVIS : favorable")
"""


def installer(dossier, nom, script):
    chemin = dossier / nom
    chemin.write_text(f"#!{sys.executable}\n{script}", encoding="utf-8")
    chemin.chmod(chemin.stat().st_mode | stat.S_IEXEC)


@pytest.fixture
def labo_codage(config, tmp_path, monkeypatch):
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    installer(bin_, "claude", FAUX_CLAUDE)
    installer(bin_, "codex", FAUX_CODEX)
    monkeypatch.setenv("PATH", str(bin_) + os.pathsep + os.environ["PATH"])
    monkeypatch.setenv("THOT_RACINE", str(config.racine))
    config.participants = [Participant("Claude", "claude"), Participant("GPT", "codex"),
                           Participant("Relais", "manuel")]
    return Labo(config)


def attendre(labo, ident, condition, delai=60):
    fin = time.time() + delai
    while time.time() < fin:
        s = labo.journal.lire(ident)
        if condition(s):
            return s
        time.sleep(0.3)
    raise AssertionError("délai dépassé : " + json.dumps([t["texte"][:80] for t in s["tours"]]))


def test_codage_complet(labo_codage, config):
    s = labo_codage.creer("Améliorations", ["Relais", "GPT"], 4, [])
    # Le tour de « Claude » arrive par le relais pour simplifier : on le rebaptise ici.
    labo_codage.config.participants[2] = Participant("Relais", "manuel")
    s = labo_codage.avancer(s["id"])
    s = labo_codage.relayer(s["id"], "Je code ça.\n\n```thot-codage\nAjoute un rôle dans prompts/.\n```\n")
    assert "Codage impossible" in s["tours"][-1]["texte"]  # le relais n'est ni Claude Code ni Codex

    s = labo_codage.creer("Améliorations", ["Claude", "GPT"], 4, [])
    labo_codage._post_traitement(s, "Claude", "```thot-codage\nAjoute un rôle dans prompts/.\n```\n")
    s = attendre(labo_codage, s["id"], lambda s: any(t.get("automaj") and t["auteur"] == "Labo" for t in s["tours"]))
    types = [t["type"] for t in s["tours"]]
    assert "codage" in types and "relecture" in types
    assert (config.racine / "prompts" / "role-codage.md").exists()      # appliqué par l'auto-maj
    assert "appliqué automatiquement" in s["tours"][-1]["texte"]
    assert not any((config.racine / ".thot" / "codage").iterdir())       # copie retirée
    assert labo_codage.occupe() is False
