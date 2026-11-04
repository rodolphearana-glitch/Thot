"""Régulateur de ressources : cœurs gardés pour Rodolphe, pause pendant un jeu, durée maximale."""
import os
import sys
import time

import pytest

from thot.ressources import Ressources

psutil = pytest.importorskip("psutil")


def test_coeurs_reserves_jamais_tous():
    r = Ressources({"coeurs_reserves": 1000})
    assert len(r.autorises()) >= 1
    r = Ressources({"coeurs_reserves": 0})
    assert r.autorises() == r.processeurs() and r.reserves() == []


def test_reserver_debut_ou_fin():
    n = len(Ressources().processeurs())
    if n < 4:
        pytest.skip("trop peu de processeurs pour ce test")
    debut = Ressources({"coeurs_reserves": 1, "reserver": "debut"})
    fin = Ressources({"coeurs_reserves": 1, "reserver": "fin"})
    assert 0 in debut.reserves() and (n - 1) in fin.reserves()
    assert set(debut.reserves()).isdisjoint(debut.autorises())


def test_calcul_bride_et_sortie():
    r = Ressources({"coeurs_reserves": 0, "intervalle_s": 1})
    code = "import os;print('fils', os.environ['THOT_FILS'])"
    rap = r.lancer([sys.executable, "-c", code], cwd=os.getcwd(), duree_max_s=30)
    assert rap.code == 0 and "fils" in rap.sortie and not rap.interrompu
    assert any("bridé" in e for e in rap.evenements)


def test_duree_maximale_arrete_l_arbre():
    r = Ressources({"intervalle_s": 1})
    code = "import subprocess,sys,time;subprocess.Popen([sys.executable,'-c','import time;time.sleep(60)']);time.sleep(60)"
    t = time.time()
    rap = r.lancer([sys.executable, "-c", code], cwd=os.getcwd(), duree_max_s=2)
    assert "durée maximale" in rap.interrompu and time.time() - t < 20


def test_pause_pendant_un_jeu():
    """Un « jeu » (ici un faux programme) qui tourne met le calcul en pause ; le temps de pause ne compte pas."""
    import shutil
    import subprocess
    import tempfile
    if not shutil.which("sleep") or os.name == "nt":
        pytest.skip("faux jeu fabriqué avec la commande sleep d'Unix")
    d = tempfile.mkdtemp()
    faux = os.path.join(d, "fauxjeu")
    shutil.copy(shutil.which("sleep"), faux)
    jeu = subprocess.Popen([faux, "4"])
    try:
        r = Ressources({"jeux": ["fauxjeu"], "intervalle_s": 1, "coeurs_reserves": 0})
        assert r.jeu_en_cours() == "fauxjeu" and r.fils_disponibles() == 0
        rap = r.lancer([sys.executable, "-c", "import time;time.sleep(3);print('fini')"], cwd=d, duree_max_s=30)
        assert rap.code == 0 and "fini" in rap.sortie
        assert any("pause" in e for e in rap.evenements) and any("reprise" in e for e in rap.evenements)
        assert rap.pause_s > 0
    finally:
        jeu.kill()
        shutil.rmtree(d, ignore_errors=True)
