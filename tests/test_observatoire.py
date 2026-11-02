"""Observer Thot : index, recadrages, confidentialité, auto-observation (mission GPT-6 / Rodolphe)."""
import hashlib
import json
import time

import pytest

from thot.confidentialite import masquer
from thot.config import Participant
from thot.labo import Labo
from thot.observatoire import Observatoire, evenements


def empreintes(dossier):
    return {str(f.relative_to(dossier)): hashlib.sha256(f.read_bytes()).hexdigest()
            for f in sorted(dossier.rglob("*")) if f.is_file()}


@pytest.fixture
def labo(config):
    return Labo(config)


def test_1_session_vide(labo, config):
    s = labo.creer("Rien encore", ["A"], 2, [])
    Observatoire(config.racine).generer_index()
    index = json.loads((config.racine / "journal" / "INDEX.json").read_text(encoding="utf-8"))
    r = next(x for x in index["sessions"] if x["id"] == s["id"])
    assert r["tours"] == 0 and r["recadrages"] == 0 and r["experiences_demandees"] == 0
    assert f"]({r['fichiers']['lisible']})" in (config.racine / "journal" / "INDEX.md").read_text(encoding="utf-8")
    assert (config.racine / "journal" / r["fichiers"]["lisible"]).exists()


def test_2_plusieurs_participants(labo, config):
    s = labo.creer("Discussion", ["A", "B"], 3, [])
    for _ in range(3):
        labo.avancer(s["id"])
    r = next(x for x in Observatoire(config.racine).resumes() if x["id"] == s["id"])
    assert r["participants"] == ["A", "B"] and r["tours_ia"] == 3 and r["etat"] == "en_cours"


def test_3_plusieurs_recadrages(labo, config):
    s = labo.creer("Cadres", ["Relais"], 3, [])
    labo.avancer(s["id"])
    labo.relayer(s["id"], "Texte.\n[RECADRAGE] premier changement de cadre\nsuite\n[RECADRAGE] second, mot pour mot")
    o = Observatoire(config.racine)
    o.generer_index()
    recs = [r for r in o.recadrages() if r["session"] == s["id"]]
    assert [r["texte"] for r in recs] == ["premier changement de cadre", "second, mot pour mot"]
    assert all(r["statut"] == "déclaré" and r["auteur"] == "Relais" for r in recs)
    md = (config.racine / "journal" / "RECADRAGES.md").read_text(encoding="utf-8")
    assert "> second, mot pour mot" in md and f"sessions/{s['id']}/session.md" in md


def test_4_experience_demandee_non_executee(labo, config):
    s = labo.creer("Exp", ["Relais"], 3, [])
    labo.avancer(s["id"])
    labo.relayer(s["id"], '```thot-experience\n{"nom": "exp_absente", "parametres": {"graine": 3}}\n```\n')
    r = next(x for x in Observatoire(config.racine).resumes() if x["id"] == s["id"])
    assert r["experiences_demandees"] == 1 and r["experiences_executees"] == 0


def test_5_experience_executee(labo, config):
    exp = config.racine / "experiences" / "exp_test"
    exp.mkdir(parents=True)
    (exp / "run.py").write_text("print('mesure : 0.42')\n")
    config.experiences["autoriser_lancement_auto"] = True
    s = labo.creer("Exp", ["Relais"], 3, [])
    labo.avancer(s["id"])
    labo.relayer(s["id"], '```thot-experience\n{"nom": "exp_test", "parametres": {}}\n```\n')
    fin = time.time() + 30
    while time.time() < fin and labo.occupe():
        time.sleep(0.2)
    tours = labo.journal.lire(s["id"])["tours"]
    evs = [e for t in tours for e in evenements(t)]
    genres = [e["genre"] for e in evs]
    assert genres.count("experience_demandee") == 1 and "experience_lancee" in genres
    res = next(e for e in evs if e["genre"] == "experience_resultat")
    assert res["reussie"] is True and res["source"] == "journal" and res["fichier"].endswith(".json")


def test_6_session_interrompue(labo, config):
    s = labo.creer("Coupée", ["A"], 5, [])
    labo.avancer(s["id"])
    labo.changer_etat(s["id"], "terminee")
    r = next(x for x in Observatoire(config.racine).resumes() if x["id"] == s["id"])
    assert r["etat"] == "terminee" and r["tours"] == 1


def test_7_donnees_anciennes_incompletes(config):
    d = config.racine / "journal" / "sessions" / "20260101-000000-ancienne"
    d.mkdir(parents=True)
    (d / "session.json").write_text(json.dumps({"id": "20260101-000000-ancienne"}), encoding="utf-8")
    (d / "tours.jsonl").write_text(
        json.dumps({"n": 0, "auteur": "Labo", "type": "labo",
                    "texte": "Résultat de l'expérience `vieille` (en échec), enregistré dans x.json :"}) + "\n"
        + "{ligne abîmée\n"
        + json.dumps({"n": 1, "auteur": "Claude", "texte": "[RECADRAGE] sans champ recadrages"}) + "\n",
        encoding="utf-8")
    (config.racine / "journal" / "sessions" / "pas-une-session").mkdir()
    o = Observatoire(config.racine)
    o.generer_index()
    r = next(x for x in o.resumes() if x["id"] == "20260101-000000-ancienne")
    assert r["sujet"] == "" and r["etat"] == "inconnu" and r["tours"] == 2 and r["recadrages"] == 1
    assert r["experiences_executees"] == 1
    assert evenements(json.loads((d / "tours.jsonl").read_text().splitlines()[0]))[0]["source"] == "déduit du texte"


def test_8_regeneration_stable(labo, config):
    s = labo.creer("Stable", ["A"], 2, [])
    labo.avancer(s["id"])
    o = Observatoire(config.racine)
    o.generer_index()
    avant = empreintes(config.racine / "journal")
    assert o.generer_index() == []                      # rien ne change, rien n'est réécrit
    assert empreintes(config.racine / "journal") == avant


def test_9_aucun_secret_dans_les_exports(labo, config):
    s = labo.creer("Chemin C:\\Users\\roudo\\Bureau et mail rodolphe.x@gmail.com", ["Relais"], 3, [])
    labo.avancer(s["id"])
    labo.relayer(s["id"], "Erreur dans C:\\\\Users\\\\roudo\\\\x.py ; clé sk-ant-api03-ABCDEFGHIJKLMNOPQRSTUV ; "
                          "/home/quelquun/projet ; token = abcdefghijklmnopqrstuvwx")
    o = Observatoire(config.racine)
    o.generer_index()
    publies = [config.racine / "journal" / n for n in ("INDEX.md", "INDEX.json", "RECADRAGES.md")]
    publies += list((config.racine / "journal" / "sessions" / s["id"]).glob("*"))
    tout = "".join(f.read_text(encoding="utf-8") for f in publies) + o.export_session(s["id"])
    for secret in ("roudo", "rodolphe.x@gmail.com", "sk-ant-api03", "quelquun", "abcdefghijklmnopqrstuvwx"):
        assert secret not in tout, secret
    assert masquer("noreply@anthropic.com") == "noreply@anthropic.com"


def test_10_journaux_historiques_preserves_et_observation(labo, config, monkeypatch):
    s = labo.creer("Source", ["Relais"], 3, [])
    labo.avancer(s["id"])
    labo.relayer(s["id"], "Un tour.\n[RECADRAGE] le cadre change")
    sources = empreintes(config.racine / "journal" / "sessions")
    vu = {}

    def faux_appel(cfg, p, systeme, prompt):
        vu["prompt"] = prompt
        from thot.providers import Reponse
        return Reponse("### Transformations de cadre\n[FAIT] tour 1, Relais : « le cadre change ».\n"
                       "### Incertitudes et limites de cette analyse\nUne seule session.", 10)

    monkeypatch.setattr("thot.labo.providers.appeler", faux_appel)
    labo.config.participants.append(Participant("Analyste", "echo"))
    labo.observer("Analyste", [s["id"]])
    fin = time.time() + 20
    while time.time() < fin and labo.occupe():
        time.sleep(0.1)
    assert empreintes(config.racine / "journal" / "sessions") == sources   # l'analyse n'a pas touché ses sources
    rapports = [f for f in (config.racine / "journal" / "observations").glob("*.md") if f.name != "INDEX.md"]
    assert len(rapports) == 1
    texte = rapports[0].read_text(encoding="utf-8")
    for rubrique in ("Période analysée", "Sessions incluses", "Sources", "Méthode", "[FAIT]"):
        assert rubrique in texte
    assert "le cadre change" in vu["prompt"]
    # Une deuxième observation ne remplace pas la première.
    labo.observer("Analyste", [s["id"]])
    while labo.occupe():
        time.sleep(0.1)
    rapports2 = [f for f in (config.racine / "journal" / "observations").glob("*.md") if f.name != "INDEX.md"]
    assert len(rapports2) == 2 and rapports[0].read_text(encoding="utf-8") == texte
    assert rapports[0].name in (config.racine / "journal" / "observations" / "INDEX.md").read_text(encoding="utf-8")
