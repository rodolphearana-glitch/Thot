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

## IA locale sur le PC de Rodolphe (Radeon 7900 XTX, 24 Go de mémoire vidéo, 64 Go de RAM, Windows)

Décidé avec Rodolphe le 2026-11-02 (voir `contextes/decisions/2026-11-02.md`) :

**Pour discuter** : **Qwen3.5 9B** dans **LM Studio** (version compressée GGUF Q4_K_M, ~6,5 Go), servie par le serveur local de LM Studio (`http://localhost:1234`). C'est le participant `Local` des sessions.

**Pour les expériences sur les représentations internes**, la version GGUF ne convient pas : il faut les poids d'origine (Hugging Face, licence Apache 2.0), chargés avec PyTorch. On travaille sur des modèles plus petits de la **même famille**, qui partagent l'architecture du 9B (hybride : 3 couches Gated DeltaNet pour 1 couche d'attention classique, multimodal) :

| modèle | usage | ce qui tient dans 24 Go |
|---|---|---|
| Qwen3.5-0.8B (24 couches) | défricher : roder les méthodes, essais rapides | lecture, modification, réentraînement complet |
| Qwen3.5-4B (32 couches) | confirmer ce qui a tenu sur le 0.8B | lecture complète, affinage léger (LoRA) |
| Qwen3.5-9B (32 couches) | plus tard, si utile | lecture seulement (~18-20 Go en bf16) |

Avoir plusieurs tailles d'une même famille permet aussi de poser la question : un modèle plus gros range-t-il mieux ce qu'il sait, ou en stocke-t-il seulement plus ?

**Rien à télécharger d'avance** : quand une expérience passera sur un vrai modèle, son script récupérera lui-même les poids. À vérifier à ce moment-là : PyTorch sur la carte AMD sous Windows (ROCm pour Windows, ou WSL2). Toute nouvelle dépendance passe par l'accord de Rodolphe.

L'expérience 1 v0 tourne en numpy, sans carte graphique.
