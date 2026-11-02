"""Claude Code et Codex simulés par de faux exécutables : on vérifie la façon de les appeler."""
import json
import os
import stat
import sys

import pytest

from thot import providers
from thot.config import Participant


def faux(dossier, nom, script):
    chemin = dossier / nom
    chemin.write_text(f"#!{sys.executable}\n{script}", encoding="utf-8")
    chemin.chmod(chemin.stat().st_mode | stat.S_IEXEC)
    return chemin


@pytest.mark.skipif(os.name == "nt", reason="faux exécutables en script Unix")
def test_claude_code_sans_cle(tmp_path, config, monkeypatch):
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    faux(bin_, "claude", """
import json, os, sys
prompt = sys.stdin.read()
print(json.dumps({"result": "vu:" + str("ANTHROPIC_API_KEY" in os.environ) + ":" + " ".join(sys.argv[1:6]),
                  "usage": {"input_tokens": 3, "output_tokens": 4}}))
""")
    monkeypatch.setenv("PATH", str(bin_) + os.pathsep + os.environ["PATH"])
    monkeypatch.setenv("ANTHROPIC_API_KEY", "ne-doit-pas-passer")
    r = providers.appeler(config, Participant("Claude", "claude"), "charte", "bonjour")
    assert r.texte.startswith("vu:False:-p --output-format json --allowedTools Read,Glob,Grep")
    assert r.tokens == 7


@pytest.mark.skipif(os.name == "nt", reason="faux exécutables en script Unix")
def test_codex_lecture_seule(tmp_path, config, monkeypatch):
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    faux(bin_, "codex", """
import sys
args = sys.argv[1:]
assert args[args.index("--sandbox") + 1] == "read-only"
entree = sys.stdin.read()
open(args[args.index("-o") + 1], "w", encoding="utf-8").write("réponse à : " + entree.splitlines()[-1])
""")
    monkeypatch.setenv("PATH", str(bin_) + os.pathsep + os.environ["PATH"])
    r = providers.appeler(config, Participant("GPT", "codex"), "charte", "la question")
    assert r.texte == "réponse à : la question"


@pytest.mark.skipif(os.name == "nt", reason="faux exécutables en script Unix")
def test_claude_non_connecte(tmp_path, config, monkeypatch):
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    faux(bin_, "claude", 'import json; print(json.dumps({"result": "Not logged in · Please run /login", "is_error": True}))')
    monkeypatch.setenv("PATH", str(bin_) + os.pathsep + os.environ["PATH"])
    with pytest.raises(providers.ErreurProvider, match="pas connecté"):
        providers.appeler(config, Participant("Claude", "claude"), "c", "p")


def test_budget_compte_les_appels_abonnement(config):
    from thot.budget import Budget, BudgetDepasse
    b = Budget({"appels_par_jour": 2}, config.racine / ".thot")
    for _ in range(2):
        b.verifier("claude")
        b.enregistrer("claude", 0)
    with pytest.raises(BudgetDepasse):
        b.verifier("codex")
    b.verifier("ollama")  # l'IA locale ne compte pas
