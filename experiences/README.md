# experiences/

Chaque expérience est un dossier contenant au moins :

- `run.py` — se lance avec `python experiences/<nom>/run.py --params '{"cle": valeur}'` ; imprime un rapport lisible puis une dernière ligne JSON ;
- `PREDICTIONS.md` — écrit **avant** le premier lancement, jamais réécrit ensuite ;
- `RESULTATS.md` — ce qui a été observé, confronté aux prédictions, avec les limites.

Les résultats bruts des lancements faits depuis le labo arrivent dans `resultats/` (un fichier JSON par lancement).

Les IA du labo peuvent demander un lancement dans leur tour avec un bloc `thot-experience` (voir `thot/roles/charte.md`).

## Les expériences

| dossier | question | état |
|---|---|---|
| `exp1_transformations` | Une relation déductible mais jamais apprise peut-elle être lue dans un réseau gelé par une petite transformation ? | v0 lancée, voir RESULTATS.md |

## IA locale sur le PC de Rodolphe (Radeon 7900 XTX, 64 Go, Windows)

**Interroger un modèle local** : installe [Ollama](https://ollama.com) pour Windows (il gère les cartes AMD), puis par exemple `ollama pull qwen3:14b`. Dans `thot.config.toml`, le participant `Local` pointe vers `http://localhost:11434`. Avec 24 Go de mémoire vidéo, les modèles jusqu'à ~30 milliards de paramètres quantifiés tiennent.

**Entraîner ou affiner** : l'expérience 1 v0 tourne en numpy, sans carte graphique. Pour les versions suivantes (PyTorch sur la carte), le support AMD sous Windows évolue vite : à vérifier au moment de l'installer. Les deux pistes habituelles sont PyTorch avec ROCm dans WSL2 (Ubuntu), ou les builds ROCm pour Windows si elles sont disponibles pour la 7900 XTX. Rien n'est installé automatiquement : toute nouvelle dépendance passe par l'accord de Rodolphe.
