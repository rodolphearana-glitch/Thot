"""Point d'entrée : `python -m thot` lance le labo sur http://127.0.0.1:8790."""
from __future__ import annotations

import argparse
import socket
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

    from .web.app import creer_app

    port = port_libre(args.port)
    if port != args.port:
        print(f"Le port {args.port} est déjà pris, Thot utilise le {port}.")
    args.port = port
    url = f"http://127.0.0.1:{args.port}"
    print(f"Thot tourne sur {url}  (Ctrl+C pour arrêter)")
    if not args.sans_navigateur:
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    uvicorn.run(creer_app(), host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
