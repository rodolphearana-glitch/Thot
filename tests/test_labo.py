from fastapi.testclient import TestClient

from thot.labo import Labo
from thot.web.app import creer_app


def test_session_alternee_et_fin(config):
    labo = Labo(config)
    s = labo.creer("Une question de départ", ["A", "B"], 3, [])
    for _ in range(5):
        s = labo.avancer(s["id"])
    auteurs = [t["auteur"] for t in s["tours"]]
    assert auteurs == ["A", "B", "A"]
    assert s["etat"] == "terminee"
    md = (config.racine / "journal/sessions" / s["id"] / "session.md").read_text(encoding="utf-8")
    assert "Une question de départ" in md and "Tour 2 — A" in md


def test_relais_manuel(config):
    labo = Labo(config)
    s = labo.creer("Sujet", ["A", "Relais"], 4, [])
    s = labo.avancer(s["id"])
    s = labo.avancer(s["id"])
    assert s["etat"] == "attente_relais"
    assert "Sujet" in s["relais"]["texte"]
    s = labo.relayer(s["id"], "Réponse collée\n[RECADRAGE] et si la question était mal posée ?")
    assert s["etat"] == "en_cours"
    dernier = s["tours"][-1]
    assert dernier["type"] == "relais" and dernier["recadrages"] == ["et si la question était mal posée ?"]


def test_intervention_et_patch_dans_un_tour(config):
    labo = Labo(config)
    s = labo.creer("Sujet", ["Relais"], 4, [])
    labo.intervenir(s["id"], "Une remarque de Rodolphe")
    s = labo.avancer(s["id"])
    patch = ("diff --git a/prompts/r.md b/prompts/r.md\nnew file mode 100644\n--- /dev/null\n"
             "+++ b/prompts/r.md\n@@ -0,0 +1 @@\n+rôle de contradicteur\n")
    s = labo.relayer(s["id"], f"Je propose un rôle.\n\n```thot-patch\n{patch}```\n")
    labo_tour = s["tours"][-1]
    assert labo_tour["auteur"] == "Labo" and "appliquée automatiquement" in labo_tour["texte"]
    assert (config.racine / "prompts/r.md").exists()


def test_contexte_hors_depot_ignore(config):
    labo = Labo(config)
    s = labo.creer("Sujet", ["A"], 1, ["../secret.md", "contextes/inexistant.md"])
    assert s["contextes"] == []


def test_api(config):
    client = TestClient(creer_app(Labo(config)))
    e = client.get("/api/etat").json()
    assert {p["nom"] for p in e["participants"]} == {"A", "B", "Relais"}
    s = client.post("/api/sessions", json={"sujet": "Test", "participants": ["A"],
                                           "tours_max": 1}).json()
    s = client.post(f"/api/sessions/{s['id']}/avancer").json()
    assert len(s["tours"]) == 1
    assert client.post("/api/sessions", json={"sujet": "x", "participants": ["Inconnu"]}).status_code == 400
    assert client.get("/").status_code == 200


def test_changer_contextes(config):
    labo = Labo(config)
    (config.racine / "contextes" / "a.md").write_text("A\n")
    (config.racine / "contextes" / "b.md").write_text("B\n")
    s = labo.creer("Sujet", ["A"], 2, ["contextes/a.md"])
    s = labo.changer_contextes(s["id"], ["contextes/b.md", "../hors.md"])
    assert s["contextes"] == ["contextes/b.md"]
    assert "+ `contextes/b.md`" in s["tours"][-1]["texte"] and "− `contextes/a.md`" in s["tours"][-1]["texte"]
    assert "B" in labo.construire_prompt(labo.journal.lire(s["id"]), "A")


def test_changer_participants_en_cours(config):
    labo = Labo(config)
    s = labo.creer("Sujet", ["A"], 6, [])
    labo.avancer(s["id"])                                  # A parle
    s = labo.changer_participants(s["id"], ["A", "B"])     # on ajoute B
    assert "+ B" in s["tours"][-1]["texte"]
    s = labo.avancer(s["id"])
    assert s["tours"][-1]["auteur"] == "B"                 # B parle juste après A
    s = labo.avancer(s["id"])
    assert s["tours"][-1]["auteur"] == "A"
    s = labo.changer_participants(s["id"], ["B"])          # on retire A
    s = labo.avancer(s["id"])
    assert s["tours"][-1]["auteur"] == "B" and "− A" in s["tours"][-2]["texte"]
    import pytest
    with pytest.raises(ValueError):
        labo.changer_participants(s["id"], [])
    with pytest.raises(KeyError):
        labo.changer_participants(s["id"], ["Inconnu"])


def test_tour_deja_en_cours_pas_relance(config):
    labo = Labo(config)
    s = labo.creer("Sujet", ["A"], 3, [])
    labo.en_cours[s["id"]] = {"participant": "A", "provider": "echo", "debut": "2026-11-02T17:00:00+01:00"}
    lu = labo.avancer(s["id"])
    assert lu["tours"] == [] and lu["tour_en_cours"]["participant"] == "A"
    labo.en_cours.clear()
    assert len(labo.avancer(s["id"])["tours"]) == 1
    assert labo.lire(s["id"])["tour_en_cours"] is None


def test_question_pour_rodolphe(config):
    labo = Labo(config)
    s = labo.creer("Sujet", ["Relais"], 3, [])
    labo.avancer(s["id"])
    labo.relayer(s["id"], "Il faut installer numpy.\n\n```thot-question\nPeux-tu lancer pip install numpy ?\n```\n")
    ouvertes = labo.questions_ouvertes()
    assert len(ouvertes) == 1 and ouvertes[0]["auteur"] == "Relais" and "numpy" in ouvertes[0]["texte"]
    s = labo.repondre_question(s["id"], 1, "C'est fait.")
    assert labo.questions_ouvertes() == []
    assert s["tours"][-1]["auteur"] == "Rodolphe" and "C'est fait." in s["tours"][-1]["texte"]
    import pytest
    with pytest.raises(ValueError):
        labo.repondre_question(s["id"], 1, "encore")


def test_interrompre_un_tour(config, tmp_path, monkeypatch):
    """Un tour trop long s'interrompt : le programme est arrêté, la session passe en pause."""
    import os
    import stat
    import sys
    import threading
    import time
    if os.name == "nt":
        import pytest
        pytest.skip("faux exécutable en script Unix")
    from thot.config import Participant
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    lent = bin_ / "claude"
    lent.write_text(f"#!{sys.executable}\nimport time\ntime.sleep(60)\n")
    lent.chmod(lent.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", str(bin_) + os.pathsep + os.environ["PATH"])
    config.participants.append(Participant("Lent", "claude"))
    labo = Labo(config)
    s = labo.creer("Sujet", ["Lent"], 2, [])
    fil = threading.Thread(target=labo.avancer, args=(s["id"],))
    fil.start()
    for _ in range(50):
        if s["id"] in labo.en_cours and labo.en_cours[s["id"]]["_fil"] in __import__("thot.providers", fromlist=["x"]).PROCESSUS:
            break
        time.sleep(0.1)
    debut = time.time()
    labo.interrompre(s["id"])
    fil.join(10)
    assert not fil.is_alive() and time.time() - debut < 10
    lu = labo.lire(s["id"])
    assert lu["etat"] == "pause" and "interrompu" in lu["erreurs"][-1]["erreur"].lower()
    assert lu["tours"] == [] and lu["tour_en_cours"] is None
