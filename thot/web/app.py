"""Interface web locale du labo (http://127.0.0.1:8790).

Fichier protégé : il expose les actions sensibles (approbation des modifications).
"""
from __future__ import annotations

import re
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ..config import charger
from ..labo import Labo

STATIQUE = Path(__file__).parent / "static"


class NouvelleSession(BaseModel):
    sujet: str
    participants: list[str]
    tours_max: int = 6
    contextes: list[str] = []
    genre: str = "discussion"
    sources: list[str] = []


class Texte(BaseModel):
    texte: str


class Etat(BaseModel):
    etat: str


class Contextes(BaseModel):
    contextes: list[str]


class Participants(BaseModel):
    participants: list[str]


class Reponse(BaseModel):
    texte: str


class Nombre(BaseModel):
    n: int = 2


class Geste(BaseModel):
    titre: str
    piece: str
    libelle: str = ""
    valeur: str | int | float | bool | None = None


class Oral(BaseModel):
    oral: bool


class Phrase(BaseModel):
    auteur: str = ""
    texte: str


class Correction(BaseModel):
    ligne: str
    remarque: str = ""


class Modele(BaseModel):
    nom: str
    surface: dict


def creer_app(labo: Labo | None = None) -> FastAPI:
    labo = labo or Labo(charger())
    app = FastAPI(title="Thot")
    app.mount("/static", StaticFiles(directory=STATIQUE), name="static")

    def _protege(f, *a):
        try:
            return f(*a)
        except (ValueError, KeyError) as e:
            raise HTTPException(400, str(e))
        except FileNotFoundError:
            raise HTTPException(404, "Introuvable.")
        except RuntimeError as e:
            raise HTTPException(409, str(e))

    @app.get("/")
    def accueil():
        return FileResponse(STATIQUE / "index.html")

    @app.get("/etabli")
    def etabli():
        return FileResponse(STATIQUE / "etabli.html")

    @app.get("/api/etat")
    def etat():
        c = labo.config
        return {
            "participants": [{"nom": p.nom, "provider": p.provider, "modele": p.modele}
                             for p in c.participants],
            "config": str(c.source.name) if c.source else None,
            "contextes": labo.contextes_disponibles(),
            "budget": labo.budget.etat(),
            "synchro": labo.synchro.etat if labo.synchro else None,
            "observations": labo.observatoire.liste_observations(),
            "questions": labo.questions_ouvertes(),
            "sessions": [x | {"tour_en_cours": ({k: v for k, v in labo.en_cours[x["id"]].items()
                                                 if not k.startswith("_")} if x["id"] in labo.en_cours else None)}
                         for x in labo.journal.lister()],
            "automaj": [{k: r.get(k) for k in ("id", "auteur", "statut", "fichiers", "raisons",
                                                "justification", "propose", "commit",
                                                "redemarrage_conseille")}
                        for r in labo.automaj.lister()[:50]],
        }

    @app.post("/api/synchro")
    def synchroniser():
        if not labo.synchro:
            raise HTTPException(409, "Synchronisation indisponible.")
        return labo.synchro.passage()

    @app.get("/api/observations/{fichier}")
    def observation(fichier: str):
        if not re.fullmatch(r"[A-Za-z0-9\-]+\.md", fichier):
            raise HTTPException(400, "Nom invalide.")
        chemin = labo.observatoire.observations / fichier
        if not chemin.exists():
            raise HTTPException(404, "Introuvable.")
        return {"fichier": fichier, "texte": chemin.read_text(encoding="utf-8")}

    @app.post("/api/index")
    def index():
        return {"modifies": [str(c.relative_to(labo.racine)) for c in labo.observatoire.generer_index()]}

    @app.post("/api/sessions")
    def creer(n: NouvelleSession):
        return _protege(labo.creer, n.sujet, n.participants, n.tours_max, n.contextes, n.genre, n.sources)

    @app.get("/api/sessions/{ident}")
    def lire(ident: str):
        return _protege(labo.lire, ident)

    @app.post("/api/sessions/{ident}/avancer")
    def avancer(ident: str):
        return _protege(labo.avancer, ident)

    @app.post("/api/sessions/{ident}/relayer")
    def relayer(ident: str, t: Texte):
        return _protege(labo.relayer, ident, t.texte)

    @app.post("/api/sessions/{ident}/intervenir")
    def intervenir(ident: str, t: Texte):
        return _protege(labo.intervenir, ident, t.texte)

    @app.post("/api/sessions/{ident}/etat")
    def changer_etat(ident: str, e: Etat):
        return _protege(labo.changer_etat, ident, e.etat)

    @app.post("/api/sessions/{ident}/contextes")
    def contextes(ident: str, c: Contextes):
        return _protege(labo.changer_contextes, ident, c.contextes)

    @app.post("/api/sessions/{ident}/participants")
    def participants(ident: str, p: Participants):
        return _protege(labo.changer_participants, ident, p.participants)

    @app.post("/api/sessions/{ident}/interrompre")
    def interrompre(ident: str):
        return _protege(labo.interrompre, ident)

    @app.post("/api/sessions/{ident}/questions/{numero}")
    def repondre(ident: str, numero: int, r: Reponse):
        return _protege(labo.repondre_question, ident, numero, r.texte)

    @app.post("/api/sessions/{ident}/tours")
    def plus_de_tours(ident: str, n: Nombre):
        return _protege(labo.ajouter_tours, ident, n.n)

    @app.post("/api/sessions/{ident}/geste")
    def geste(ident: str, g: Geste):
        return _protege(labo.geste, ident, g.titre, g.piece, g.libelle, g.valeur)

    @app.post("/api/sessions/{ident}/oral")
    def oral(ident: str, o: Oral):
        return _protege(labo.changer_oral, ident, o.oral)

    # -- bibliothèque de surfaces ----------------------------------------------------
    @app.get("/api/modeles")
    def modeles():
        return labo.bibliotheque.lister()

    @app.get("/api/modeles/{nom}")
    def modele(nom: str):
        return _protege(labo.bibliotheque.lire, nom)

    @app.post("/api/modeles")
    def sauver_modele(m: Modele):
        return _protege(labo.bibliotheque.sauver, m.nom, m.surface)

    # -- mémoire de construction ----------------------------------------------------------
    @app.get("/api/memoire")
    def memoire():
        return {"lignes": labo.memoire.lignes(12)}

    @app.post("/api/memoire/corriger")
    def memoire_corriger(c: Correction):
        labo.memoire.corriger(c.ligne, c.remarque)
        return {"lignes": labo.memoire.lignes(12)}

    # -- voix locale ---------------------------------------------------------------------
    @app.get("/api/voix")
    def voix():
        return labo.voix.etat()

    @app.post("/api/voix/ecouter")
    async def ecouter(requete: Request):
        audio = await requete.body()
        if len(audio) > 25_000_000:
            raise HTTPException(413, "Enregistrement trop long.")
        import anyio
        try:
            texte = await anyio.to_thread.run_sync(labo.voix.ecouter, audio, requete.headers.get("content-type", ""))
        except ValueError as e:
            raise HTTPException(400, str(e))
        except RuntimeError as e:
            raise HTTPException(409, str(e))
        return {"texte": texte}

    @app.post("/api/voix/dire")
    def dire(p: Phrase):
        return Response(_protege(labo.voix.dire, p.auteur, p.texte), media_type="audio/wav")

    # -- ressources du PC et file de travaux ------------------------------------------
    @app.get("/api/ressources")
    def ressources():
        return labo.ressources.etat()

    @app.get("/api/travaux")
    def travaux():
        return labo.travaux.etat()

    @app.post("/api/travaux/arreter")
    def travaux_arreter():
        labo.travaux.arreter()
        return labo.travaux.etat()

    @app.post("/api/travaux/reprendre")
    def travaux_reprendre():
        labo.travaux.reprendre()
        return labo.travaux.etat()

    @app.get("/api/automaj/{ident}")
    def automaj_lire(ident: str):
        return _protege(labo.automaj.lire, ident)

    @app.post("/api/automaj/{ident}/{action}")
    def automaj_action(ident: str, action: str):
        f = {"approuver": labo.automaj.approuver, "refuser": labo.automaj.refuser,
             "annuler": labo.automaj.annuler}.get(action)
        if not f:
            raise HTTPException(404, "Action inconnue.")
        return _protege(f, ident)

    return app
