# Prédictions écrites avant le premier lancement

Écrites par Claude le 2026-11-02, **avant** d'avoir lancé l'expérience une seule fois. Honnêteté sur la trace : le dépôt n'avait pas encore de commit, ces prédictions ont donc été commitées en même temps que les premiers résultats. Pour les expériences suivantes, le commit des prédictions précédera le lancement. Elles ne seront pas modifiées après coup : si les résultats les contredisent, on le note dans `RESULTATS.md`, on ne réécrit pas ce fichier.

**P1 — structure.** Sur les entités tenues à l'écart, la condition `structure` dépasse nettement le hasard (1/61 ≈ 0,016) pour au moins un rang k. *Confiance : moyenne.* Rien ne garantit que le réseau ait organisé ses entités de façon cyclique : il a pu apprendre chaque relation par cœur. Si P1 échoue alors que la référence à deux sauts réussit, ce sera en soi un résultat intéressant : une relation **déductible** (le réseau sait faire les deux sauts) mais **pas accessible** par une simple lecture linéaire.

**P2 — nulle.** La condition `nulle` reste proche du hasard sur le test, quel que soit k. *Confiance : élevée.* Si elle monte nettement, c'est une fuite de mesure et aucun autre chiffre n'est interprétable.

**P3 — témoin.** La condition `temoin` (réseau jamais entraîné) reste nettement sous `structure`. *Confiance : moyenne à élevée.* Si le témoin fait aussi bien, alors le savoir était dans T et pas dans le réseau : c'est l'avertissement de GPT sur les décodeurs.

**P4 — rang.** Si P1 tient, la précision de `structure` cesse de progresser au-delà d'un petit rang. Ce rang minimal donne une première mesure, très grossière, du « nombre de paramètres nécessaires pour retrouver la conclusion » (critère de Rodolphe).
