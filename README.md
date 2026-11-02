# Thot

*Un petit labo de recherche où des intelligences différentes, humaines et artificielles, font avancer une idée par itérations.*

> « préciser sans épuiser » — Rodolphe

Thot est né le 2 novembre 2026 d'une correspondance entre Rodolphe, GPT-6 et Claude sur une question : **une part du coût du raisonnement vient-elle de la façon dont les connaissances sont organisées, plutôt que de leur quantité ?** Autrement dit : une relation déjà présente dans ce qu'on sait peut-elle devenir visible en changeant de clé de lecture, et un système peut-il apprendre à trouver ces clés de mieux en mieux ?

Le nom vient du dieu égyptien de l'écriture et du savoir. Dans le *Phèdre*, Socrate raconte que Thot offrit l'écriture au roi Thamous comme remède pour la mémoire, et que le roi répondit qu'elle servirait à se rappeler, pas à se souvenir. Le labo tient les deux : une mémoire écrite de tout ce qui se dit (le journal), et un dialogue vivant qui peut la remettre en question.

Le dépôt est public : on ne brevette pas le soleil.

## Ce que contient le dépôt

| dossier | contenu |
|---|---|
| `contextes/` | La mémoire du labo : formulations originales de Rodolphe (mot pour mot), correspondance complète entre GPT et Claude, documents de vision. À lire avant de contribuer. |
| `thot/` | Le logiciel : sessions d'itération, appels aux modèles, journal, budget, auto-mise à jour. |
| `experiences/` | Les expériences, avec leurs prédictions écrites avant de les lancer. |
| `journal/` | Toutes les sessions du labo, tour par tour, et l'historique des modifications automatiques. Rien n'y est jamais réécrit. |
| `prompts/` | Zone libre où les IA peuvent faire évoluer leurs consignes. |

## Lancer le labo (Windows)

Thot parle à Claude et à GPT **comme le Studio TLS** : par Claude Code et Codex installés sur le PC, connectés à tes comptes Claude et ChatGPT. Aucune clé d'API.

1. Il faut Python 3.11 ou plus récent ([python.org](https://www.python.org/downloads/), case « Add Python to PATH » cochée), et Claude Code et Codex connectés (s'ils marchent pour le Studio TLS, c'est bon).
2. Récupère le dépôt (bouton vert **Code → Download ZIP**, ou `git clone`).
3. Double-clique sur **`lancer.bat`**. La première fois, il installe ce qu'il faut et crée `thot.config.toml` (ignoré par Git).
4. Le labo s'ouvre dans ton navigateur, sur http://127.0.0.1:8790 (ou le port libre suivant si celui-ci est pris).

**Mise à jour automatique** (comme le Studio TLS) : au premier lancement, `lancer.bat` relie le dossier à GitHub, même s'il vient d'un ZIP. Ensuite, au démarrage puis toutes les 10 minutes, Thot récupère les nouveautés de GitHub, **teste le nouveau code avant de l'installer** (il garde l'ancienne version si les tests échouent), envoie sur GitHub le journal du labo, et redémarre tout seul si le code a changé, quand aucun tour n'est en cours. Bouton « Synchroniser maintenant » dans la colonne de gauche. Il faut Git pour Windows (déjà là si le Studio TLS tourne).

**IA locale** : Thot parle au modèle chargé dans **LM Studio** par son serveur local (onglet Developer → Start Server, port 1234). Ollama marche aussi (`provider = "ollama"`).

Dans une session, Claude et GPT lisent le dépôt en **lecture seule** : ils peuvent ouvrir les contextes et les expériences eux-mêmes, mais ne modifient rien directement. Leurs propositions de modification passent par l'auto-mise à jour.

Sous Linux ou macOS : `pip install -r requirements.txt`, `cp thot.config.example.toml thot.config.toml`, puis `python -m thot`.

## Comment marche une session

Tu poses un sujet, tu choisis les participants dans l'ordre (par exemple Claude puis GPT) et les contextes à leur donner. À chaque tour, le participant reçoit la charte du labo (`thot/roles/charte.md`), le sujet, les contextes et tout l'échange. Tu peux intervenir quand tu veux, mettre en pause, ajouter des tours.

Dans leur tour, les IA peuvent :

- marquer un **recadrage** (`[RECADRAGE] …`) : ces lignes sont collectées, elles forment le corpus des changements de perspective du labo ;
- **interroger l'IA locale** (bloc `thot-local`) ;
- **lancer une expérience** du dépôt (bloc `thot-experience`) ;
- **faire coder un changement** (bloc `thot-codage`) : l'IA code dans une copie à part du dépôt et lance les tests, l'autre IA relit, puis le changement passe par l'auto-mise à jour ;
- **proposer une petite modification directement** (bloc `thot-patch`).

## Auto-mise à jour : de l'autonomie, avec un lit de rivière

Règles validées par Rodolphe le 2026-11-02 :

- Une modification qui ne touche que les zones autorisées (`prompts/`, `thot/roles/`, `thot/web/static/`, `experiences/`, `tests/`) est appliquée sur une branche à part, **testée**, puis fusionnée seule si les tests passent.
- Tout le reste attend l'accord de Rodolphe : nouvelle dépendance, accès réseau, commandes système, accès aux clés, suppression de fichiers, et les fichiers protégés (le mécanisme d'auto-mise à jour lui-même, le budget, la configuration, les appels aux modèles).
- Le journal et les contextes ne peuvent jamais être modifiés par un patch.
- Chaque modification est journalisée dans `journal/auto-maj/` avec sa raison, et peut être **annulée en un clic** (git revert).
- Un **plafond quotidien** de tokens et d'appels, fixé par Rodolphe, arrête les sessions quand il est atteint.

## Observer Thot

Tout ce que fait le labo est lisible directement sur GitHub, sans accès au PC de Rodolphe. Points d'entrée stables :

- [`journal/INDEX.md`](journal/INDEX.md) — toutes les sessions : sujet, participants, état, tours, recadrages, expériences demandées / exécutées, avec un lien vers chaque fil.
- [`journal/INDEX.json`](journal/INDEX.json) — le même index pour un programme (format stable, `"format": 1`).
- [`journal/RECADRAGES.md`](journal/RECADRAGES.md) — toutes les lignes `[RECADRAGE]`, mot pour mot, avec leur auteur, leur session, leur tour et un lien vers le contexte. Ce sont des recadrages **déclarés**.
- [`journal/observations/INDEX.md`](journal/observations/INDEX.md) — les rapports d'auto-observation : une IA analyse des sessions passées, en lecture seule (menu « Observer Thot »). Ce sont des analyses, jamais des vérités établies.
- [`journal/auto-maj/`](journal/auto-maj/) — chaque modification du labo, avec sa raison, ses tests et son statut.

Les index sont refaits sans IA à chaque synchronisation, de façon déterministe. Tout ce qui est publié passe par un filtre qui retire chemins personnels, clés et adresses électroniques (`thot/confidentialite.py`).

Lien direct pour une IA extérieure : `https://github.com/rodolphearana-glitch/Thot/blob/main/journal/INDEX.md`

## Pour les IA qui contribuent

Lire `AGENTS.md`.
