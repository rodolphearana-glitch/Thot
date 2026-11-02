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
- **Expériences** : prédictions écrites et commitées avant le premier lancement ; résultats confrontés aux prédictions, limites écrites ; contrôles (condition nulle, témoin) obligatoires.
- **Deux IA d'accord ne font pas une preuve.** Le réel (une mesure, une expérience) est le contradicteur indépendant.
- **Pas de secrets dans le dépôt** : il est public. Clés et réglages personnels dans `thot.config.toml`, ignoré par Git.

## Garde-fous de l'auto-mise à jour

Les fichiers listés dans `PROTEGES` de `thot/selfupdate.py` ne se modifient qu'avec l'accord de Rodolphe. Ne cherche pas à contourner ce mécanisme, y compris indirectement (par exemple en déplaçant une logique protégée dans une zone autorisée) : le labo étudie justement les boucles qui se transforment elles-mêmes, il doit pratiquer la prudence qu'il étudie. Si un garde-fou te semble trop strict, dis-le dans une session et propose le changement : Rodolphe tranche.

## Ajouter une correspondance

Nommer `NN_auteur_AAAA-MM-JJ_sujet-court.md`, en continuant la numérotation. En tête : un commentaire HTML disant qui l'a écrit, quand, et par quel canal. Puis le texte tel quel.
