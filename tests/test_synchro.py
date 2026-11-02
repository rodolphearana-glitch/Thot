"""La synchro avec un « GitHub » simulé par un dépôt nu local."""
import subprocess

from thot.synchro import Synchro


def effacer(dossier):
    """rmtree qui marche aussi sous Windows, où Git met ses fichiers en lecture seule."""
    import os
    import shutil
    import stat

    def deverrouiller(fonction, chemin, _info):
        os.chmod(chemin, stat.S_IWRITE)
        fonction(chemin)

    shutil.rmtree(dossier, onerror=deverrouiller)


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


def preparer(depot, tmp_path):
    distant = tmp_path / "github.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(distant)], check=True)
    git(depot, "remote", "add", "origin", str(distant))
    git(depot, "push", "-q", "origin", "main")
    git(depot, "branch", "-q", "-u", "origin/main")
    autre = tmp_path / "autre"
    subprocess.run(["git", "clone", "-q", str(distant), str(autre)], check=True)
    git(autre, "config", "user.email", "gpt@example.com")
    git(autre, "config", "user.name", "GPT")
    return distant, autre


def test_recupere_et_pousse(depot, tmp_path):
    distant, autre = preparer(depot, tmp_path)
    # GPT ajoute une lettre sur GitHub.
    (autre / "contextes" / "lettre.md").write_text("bonjour\n")
    git(autre, "add", "-A"); git(autre, "commit", "-q", "-m", "lettre"); git(autre, "push", "-q")
    # Le labo a produit une session sur le PC.
    s = depot / "journal" / "sessions" / "x"
    s.mkdir(parents=True)
    (s / "session.md").write_text("une session\n")
    sy = Synchro(depot, {"active": True})
    etat = sy.passage()
    assert etat["erreur"] == "", etat
    assert (depot / "contextes" / "lettre.md").exists()
    assert etat["redemarrage"] is False  # pas de code touché
    git(autre, "pull", "-q")
    assert (autre / "journal" / "sessions" / "x" / "session.md").exists()


def test_nouveau_code_teste_puis_redemarrage(depot, tmp_path):
    _, autre = preparer(depot, tmp_path)
    (autre / "thot" / "nouveau.py").write_text("X = 1\n")
    git(autre, "add", "-A"); git(autre, "commit", "-q", "-m", "code"); git(autre, "push", "-q")
    sy = Synchro(depot, {"active": True})
    etat = sy.passage()
    assert etat["erreur"] == "" and etat["redemarrage"] is True
    assert (depot / "thot" / "nouveau.py").exists()


def test_code_casse_refuse(depot, tmp_path):
    _, autre = preparer(depot, tmp_path)
    (autre / "tests" / "test_casse.py").write_text("def test_x():\n    assert False\n")
    (autre / "thot" / "casse.py").write_text("X = 2\n")
    git(autre, "add", "-A"); git(autre, "commit", "-q", "-m", "casse"); git(autre, "push", "-q")
    avant = git(depot, "rev-parse", "HEAD")
    etat = Synchro(depot, {"active": True}).passage()
    assert "refusée" in etat["erreur"]
    assert git(depot, "rev-parse", "HEAD") == avant
    assert not (depot / "thot" / "casse.py").exists()


def test_sans_github(depot):
    git(depot, "remote", "remove", "origin") if "origin" in git(depot, "remote") else None
    etat = Synchro(depot, {"active": True}).passage()
    assert "origin" in etat["erreur"]


def test_dossier_venu_d_un_zip(depot, tmp_path):
    """Un dossier sans historique commun avec GitHub (ZIP, liaison ratée) se relie seul."""
    distant, autre = preparer(depot, tmp_path)
    (autre / "contextes" / "nouvelle.md").write_text("de GitHub\n")
    git(autre, "add", "-A"); git(autre, "commit", "-q", "-m", "nouvelle"); git(autre, "push", "-q")
    zip_ = tmp_path / "zip"
    subprocess.run(["git", "clone", "-q", str(distant), str(zip_)], check=True)
    effacer(zip_ / ".git")
    (zip_ / "contextes" / "nouvelle.md").unlink()          # ZIP un peu plus ancien
    (zip_ / "journal" / "sessions" / "s1").mkdir(parents=True)
    (zip_ / "journal" / "sessions" / "s1" / "session.md").write_text("session locale\n")
    git(zip_, "init", "-q", "-b", "main")
    git(zip_, "config", "user.email", "pc@example.com"); git(zip_, "config", "user.name", "PC")
    git(zip_, "remote", "add", "origin", str(distant))
    # Ce qui s'est passé chez Rodolphe : un premier commit local sans lien avec GitHub.
    git(zip_, "add", "-A", "--", "journal"); git(zip_, "commit", "-q", "-m", "journal")
    etat = Synchro(zip_, {"active": True}).passage()
    assert etat["erreur"] == "", etat
    assert "relié" in etat["message"]
    assert (zip_ / "contextes" / "nouvelle.md").read_text() == "de GitHub\n"
    assert (zip_ / "journal" / "sessions" / "s1" / "session.md").exists()
    git(autre, "pull", "-q")
    assert (autre / "journal" / "sessions" / "s1" / "session.md").exists()
