"""Point d'entrée : `python -m thot` lance le labo sur http://127.0.0.1:8790.

Fichier protégé. Code de sortie 3 = nouvelle version récupérée de GitHub : lancer.bat relance Thot.
"""
from __future__ import annotations

import argparse
import socket
import sys
import threading
import webbrowser


def port_libre(depart: int, essais: int = 20) -> int:
    """Premier port libre à partir de `depart` (Studio TLS ou un autre outil peut occuper le sien)."""
    for port in range(depart, depart + essais):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise SystemExit(f"Aucun port libre entre {depart} et {depart + essais - 1}.")


def main() -> None:
    ap = argparse.ArgumentParser(prog="thot", description="Labo Thot")
    ap.add_argument("--port", type=int, default=8790)
    ap.add_argument("--sans-navigateur", action="store_true")
    args = ap.parse_args()

    import uvicorn

    from .config import charger
    from .labo import Labo
    from .synchro import Synchro
    from .web.app import creer_app

    config = charger()
    labo = Labo(config)
    synchro = Synchro(config.racine, config.github, occupe=labo.occupe)
    labo.synchro = synchro

    port = port_libre(args.port)
    if port != args.port:
        print(f"Le port {args.port} est déjà pris, Thot utilise le {port}.")
    url = f"http://127.0.0.1:{port}"
    print(f"Thot tourne sur {url}  (Ctrl+C pour arrêter)")
    raison = synchro.disponible()
    print("Mise à jour depuis GitHub : " + (raison or "active (au démarrage puis régulièrement)"))
    if not args.sans_navigateur:
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()

    serveur = uvicorn.Server(uvicorn.Config(creer_app(labo), host="127.0.0.1", port=port, log_level="warning"))
    serveur.code_sortie = 0
    synchro.serveur = serveur
    synchro.demarrer()
    serveur.run()
    synchro.arreter()
    if serveur.code_sortie:
        print("Nouvelle version récupérée de GitHub : redémarrage.")
    sys.exit(serveur.code_sortie)


if __name__ == "__main__":
    main()
