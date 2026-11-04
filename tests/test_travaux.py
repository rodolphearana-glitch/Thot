"""File de travaux : désactivée par défaut, garde-fous, exécution bridée, résultat rangé."""
import json
import subprocess

from thot.ressources import Ressources
from thot.travaux import Travaux


def _experience(depot, nom="expt", commit=True):
    d = depot / "experiences" / nom
    d.mkdir(parents=True)
    (d / "run.py").write_text(
        "import json,sys\np=json.loads(sys.argv[sys.argv.index('--params')+1])\n"
        "print('calcul…')\nprint(json.dumps({'double': p['x']*2}))\n", encoding="utf-8")
    (d / "PREDICTIONS.md").write_text("Le double de x.\n", encoding="utf-8")
    (d / "rapide.json").write_text('{"x": 1}\n', encoding="utf-8")
    if commit:
        subprocess.run(["git", "add", "-A"], cwd=depot, check=True)
        subprocess.run(["git", "commit", "-q", "-m", "exp"], cwd=depot, check=True)


def _deposer(depot, ident, travail):
    f = depot / "travaux" / "a-faire" / f"{ident}.json"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(travail), encoding="utf-8")
    return f


def _file(depot, active=True):
    return Travaux(depot, {"active": active, "duree_max_s": 60}, Ressources({"coeurs_reserves": 0, "intervalle_s": 1}))


def test_desactivee_par_defaut(depot):
    _experience(depot)
    _deposer(depot, "t1", {"experience": "expt", "parametres": {"x": 2}})
    t = Travaux(depot, {}, Ressources())
    assert t.lancer_suivant(False) == "file de travaux désactivée"
    assert (depot / "travaux" / "a-faire" / "t1.json").exists()


def test_travail_execute_et_range(depot):
    _experience(depot)
    _deposer(depot, "t1", {"experience": "expt", "parametres": {"x": 21}, "auteur": "Claude"})
    t = _file(depot)
    assert "terminé" in t.lancer_suivant(False)
    res = json.loads((depot / "travaux" / "faits" / "t1" / "resultat.json").read_text(encoding="utf-8"))
    assert res["reussi"] and res["resultat"] == {"double": 42}
    assert any("bridé" in e for e in res["evenements"])
    assert (depot / "travaux" / "faits" / "t1" / "travail.json").exists()
    assert not (depot / "travaux" / "a-faire" / "t1.json").exists()
    assert t.lancer_suivant(False) == "rien à faire"


def test_predictions_non_commitees_refusees(depot):
    _experience(depot, commit=False)
    _deposer(depot, "t2", {"experience": "expt", "parametres": {"x": 1}})
    _file(depot).lancer_suivant(False)
    res = json.loads((depot / "travaux" / "faits" / "t2" / "resultat.json").read_text(encoding="utf-8"))
    assert not res["reussi"] and "commitées" in res["refus"]


def test_experience_inconnue_ou_chemin_refuse(depot):
    _deposer(depot, "t3", {"experience": "../thot", "parametres": {}})
    _file(depot).lancer_suivant(False)
    res = json.loads((depot / "travaux" / "faits" / "t3" / "resultat.json").read_text(encoding="utf-8"))
    assert "invalide" in res["refus"]


def test_stop_arrete_la_file(depot):
    _experience(depot)
    _deposer(depot, "t4", {"experience": "expt", "parametres": {"x": 1}})
    t = _file(depot)
    t.arreter()
    assert "arrêtée" in t.lancer_suivant(False)
    t.reprendre()
    assert "terminé" in t.lancer_suivant(False)
