# Pour les IA qui travaillent sur Thot

Ce fichier s'adresse à toute IA (Claude, GPT, autre) qui contribue au dépôt, que ce soit depuis une session du labo ou en travaillant directement sur le code.

## À lire d'abord

1. `contextes/intuitions/formulations-originales-de-rodolphe.md` — ses mots exacts. Ne pas les remplacer par des équivalents.
2. `contextes/correspondance/` — la correspondance GPT ↔ Claude dans l'ordre des numéros. La lettre 08 (transmission technique de GPT) et la 09 (réponse de Claude) fixent le programme de recherche actuel.
3. `contextes/vision/` — la vision de TLS.

## Règles de travail

- **Rodolphe garde la direction.** Les initiatives sont bienvenues quand elles servent son objectif ; une proposition nouvelle est présentée comme telle, jamais comme une décision déjà prise.
- **Niveaux de certitude explicites** : [FAIT] vérifié, [DÉCISION] validée par Rodolphe, [HYPOTHÈSE], [INTERPRÉTATION], [SUGGESTION].
- **Formulations originales conservées** : une reformulation transforme l'information. On ajoute, on ne réécrit pas.
- **Le journal ne se réécrit pas.** `journal/` et `contextes/` sont en ajout seulement. Une correction s'ajoute en note datée, elle n'efface pas.
- **Expériences** : prédictions écrites et commitées avant le premier lancement ; résultats confrontés aux prédictions, limites écrites ; contrôles (condition nulle, témoin) obligatoires ; chaque expérience fournit un `rapide.json` que les tests lancent pour de vrai.
- **Deux IA d'accord ne font pas une preuve.** Le réel (une mesure, une expérience) est le contradicteur indépendant.
- **Pas de secrets dans le dépôt** : il est public. Clés et réglages personnels dans `thot.config.toml`, ignoré par Git.

## Garde-fous de l'auto-mise à jour

Les fichiers listés dans `PROTEGES` de `thot/selfupdate.py` ne se modifient qu'avec l'accord de Rodolphe. Ne cherche pas à contourner ce mécanisme, y compris indirectement (par exemple en déplaçant une logique protégée dans une zone autorisée) : le labo étudie justement les boucles qui se transforment elles-mêmes, il doit pratiquer la prudence qu'il étudie. Si un garde-fou te semble trop strict, dis-le dans une session et propose le changement : Rodolphe tranche.

## Leçons reprises du Studio TLS (ne pas les réapprendre)

Le Studio TLS (`scripts/studio/` du dépôt overmind-TLS, fiche `docs/overmind/reprise/studio-tls.md`) a déjà rencontré la plupart des pièges d'un outil comme Thot sous Windows. Avant de toucher au lancement, aux mises à jour, au codage ou aux processus, relire sa section « Pièges ». Déjà appliqué ici :

- **`lancer.bat` ne se modifie jamais** : Windows relit un `.bat` en cours d'exécution au même endroit, un fichier changé pendant qu'il tourne se lit de travers. Ce qui doit évoluer va dans le Python.
- **UTF-8 forcé** (`PYTHONUTF8=1`) pour les tests, les expériences et les IA lancées : sous Windows, Python lit et écrit sinon en cp1252.
- **Arrêt de l'arbre de processus entier** (`taskkill /T`) quand un délai est dépassé : Claude Code lance d'autres programmes.
- **Les nouvelles versions sont testées avant d'être installées**, dans une copie à part.
- **Le codage se fait dans une copie à part** (`git worktree`), jamais dans le dossier de Rodolphe.

## Ajouter une correspondance

Nommer `NN_auteur_AAAA-MM-JJ_sujet-court.md`, en continuant la numérotation. En tête : un commentaire HTML disant qui l'a écrit, quand, et par quel canal. Puis le texte tel quel.
