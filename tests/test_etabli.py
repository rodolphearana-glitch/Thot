"""L'établi : mémoire de construction, voix sans dépendances, routes de la page."""
from fastapi.testclient import TestClient

from thot.labo import Labo
from thot.memoire import MAX_LIGNES_PAR_TOUR, Memoire
from thot.web.app import creer_app


def test_memoire_tenue_par_les_ia(config):
    labo = Labo(config)
    s = labo.creer("Sujet", ["Relais"], 4, [])
    labo.avancer(s["id"])
    bloc = "\n".join(f"- leçon {i}" for i in range(9))
    s = labo.relayer(s["id"], f"Je note.\n\n```thot-memoire\n{bloc}\n```\n")
    assert "a noté" in s["tours"][-1]["texte"]
    lignes = labo.memoire.lignes()
    assert len(lignes) == MAX_LIGNES_PAR_TOUR and "(Relais) leçon 0" in lignes[0]
    assert "leçon 0" in labo.construire_prompt(labo.journal.lire(s["id"]), "Relais")
    labo.memoire.corriger(lignes[0])
    assert "CORRECTION" in labo.memoire.lignes()[-1]


def test_memoire_archivee_quand_elle_grossit(tmp_path, monkeypatch):
    import thot.memoire as m
    monkeypatch.setattr(m, "MAX_FICHIER", 500)
    mem = Memoire(tmp_path)
    for i in range(20):
        mem.ajouter("A", f"ligne numéro {i} " + "x" * 40)
    assert list((tmp_path / "memoire" / "archives").glob("*.md"))
    assert mem.fichier.stat().st_size < 1500


def test_page_et_api_de_l_etabli(config):
    c = TestClient(creer_app(Labo(config)))
    assert c.get("/etabli").status_code == 200
    v = c.get("/api/voix").json()
    assert v["parole"] in ("piper", "navigateur") and "A" in v["participants"]
    assert "processeurs" in c.get("/api/ressources").json()
    assert c.get("/api/travaux").json()["active"] is False
    assert c.get("/api/modeles").json() == []
    assert c.post("/api/memoire/corriger", json={"ligne": "x"}).status_code == 200
    r = c.post("/api/voix/dire", json={"auteur": "A", "texte": "bonjour"})
    assert r.status_code == 409          # pas de voix Piper ici : la page prend la voix de Windows
