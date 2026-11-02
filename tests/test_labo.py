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
