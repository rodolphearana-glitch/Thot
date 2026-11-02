"""Point d'entrée : `python -m thot` lance le labo sur http://127.0.0.1:8765."""
from __future__ import annotations

import argparse
import threading
import webbrowser


def main() -> None:
    ap = argparse.ArgumentParser(prog="thot", description="Labo Thot")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--sans-navigateur", action="store_true")
    args = ap.parse_args()

    import uvicorn

    from .web.app import creer_app

    url = f"http://127.0.0.1:{args.port}"
    print(f"Thot tourne sur {url}  (Ctrl+C pour arrêter)")
    if not args.sans_navigateur:
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    uvicorn.run(creer_app(), host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
