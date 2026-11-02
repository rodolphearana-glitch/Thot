"""Interface web locale du labo (http://127.0.0.1:8790).

Fichier protégé : il expose les actions sensibles (approbation des modifications).
"""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
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


class Texte(BaseModel):
    texte: str


class Etat(BaseModel):
    etat: str


class Nombre(BaseModel):
    n: int = 2


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
            "sessions": labo.journal.lister(),
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

    @app.post("/api/sessions")
    def creer(n: NouvelleSession):
        return _protege(labo.creer, n.sujet, n.participants, n.tours_max, n.contextes)

    @app.get("/api/sessions/{ident}")
    def lire(ident: str):
        return _protege(labo.journal.lire, ident)

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

    @app.post("/api/sessions/{ident}/tours")
    def plus_de_tours(ident: str, n: Nombre):
        return _protege(labo.ajouter_tours, ident, n.n)

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
