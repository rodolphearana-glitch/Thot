import subprocess

from thot.selfupdate import AutoMaj, evaluer, extraire_blocs, fichiers_du_patch

AUTORISES = ["prompts/**", "thot/roles/**", "tests/**"]


def patch_nouveau(chemin, contenu="bonjour\n"):
    lignes = contenu.splitlines()
    corps = "\n".join("+" + l for l in lignes)
    return (f"diff --git a/{chemin} b/{chemin}\nnew file mode 100644\n--- /dev/null\n"
            f"+++ b/{chemin}\n@@ -0,0 +1,{len(lignes)} @@\n{corps}\n")


def test_extraire_blocs():
    t = "Avant\n```thot-patch\nA\n```\nentre\n```thot-local\nQ ?\n```\n```thot-patch\nB\n```"
    assert extraire_blocs(t, "thot-patch") == ["A\n", "B\n"]
    assert extraire_blocs(t, "thot-local") == ["Q ?\n"]


def test_fichiers_du_patch():
    touches, supprimes = fichiers_du_patch(patch_nouveau("prompts/x.md"))
    assert touches == {"prompts/x.md"} and not supprimes


def test_zone_autorisee_passe_seule():
    assert evaluer(patch_nouveau("prompts/role.md"), AUTORISES) == ("auto", [])


def test_fichier_protege_demande_accord():
    decision, raisons = evaluer(patch_nouveau("thot/selfupdate.py"), ["thot/**"])
    assert decision == "accord" and any("protégé" in r for r in raisons)


def test_hors_zone_demande_accord():
    decision, _ = evaluer(patch_nouveau("thot/labo.py"), AUTORISES)
    assert decision == "accord"


def test_journal_interdit():
    assert evaluer(patch_nouveau("journal/sessions/x.md"), AUTORISES)[0] == "interdit"
    assert evaluer(patch_nouveau("../hors.md"), AUTORISES)[0] == "interdit"


def test_contenu_sensible_demande_accord():
    for contenu in ("import subprocess\n", "url = 'https://exemple.org'\n", "pip install truc\n"):
        decision, _ = evaluer(patch_nouveau("prompts/x.py", contenu), AUTORISES)
        assert decision == "accord", contenu


def test_application_auto_puis_annulation(depot, config):
    am = AutoMaj(depot, config.auto_maj)
    rec = am.proposer(patch_nouveau("prompts/nouveau.md", "une consigne\n"), "A", "essai")
    assert rec["statut"] == "applique", rec
    assert (depot / "prompts/nouveau.md").read_text() == "une consigne\n"
    log = subprocess.run(["git", "log", "--oneline"], cwd=depot, capture_output=True, text=True)
    assert "auto-maj (A)" in log.stdout
    rec = am.annuler(rec["id"])
    assert rec["statut"] == "annule"
    assert not (depot / "prompts/nouveau.md").exists()


def test_tests_en_echec_rejettent(depot, config):
    am = AutoMaj(depot, config.auto_maj)
    rec = am.proposer(patch_nouveau("tests/test_casse.py", "def test_x():\n    assert False\n"),
                      "B", "casse tout")
    assert rec["statut"] == "rejete_tests"
    assert not (depot / "tests/test_casse.py").exists()


def test_attente_puis_approbation(depot, config):
    am = AutoMaj(depot, config.auto_maj)
    rec = am.proposer(patch_nouveau("thot/roles/../../autre.md"), "A", "x")
    assert rec["statut"] == "interdit"
    rec = am.proposer(patch_nouveau("notes/idee.md", "idée\n"), "A", "hors zone")
    assert rec["statut"] == "en_attente"
    rec = am.approuver(rec["id"])
    assert rec["statut"] == "applique"
    assert (depot / "notes/idee.md").exists()
