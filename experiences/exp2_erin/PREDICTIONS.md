<!-- Écrit par Claude (session cloud), le 5 novembre 2026 vers 00 h 20, AVANT tout lancement sur le PC de Rodolphe. -->

# Expérience 2 : Erin Triples With Bobs — prédictions

## Contexte

Exploration libre du 4 novembre 2026 : Knuth (note d'avril 2026, « Erin Triples With Bobs ») décrit le
problème comme ouvert et écrit « I'm stuck ». Ce soir-là, sur 2 cœurs, CP-SAT (21 min) et CaDiCaL (25 min)
n'ont rien trouvé, et même une simple couverture en boucles séparées n'est pas sortie. Deux hypothèses
restaient : [HYPOTHÈSE] le problème est vraiment dur pour ces solveurs ; [HYPOTHÈSE] le modèle a un défaut.

Vérifications déjà faites [FAIT] : le modèle retrouve les 2 520 têtes et 840 blocs de Knuth pour Erin ; la
course normale fait 84 changements pour Stedman Triples et 42 pour Erin (valeurs connues).
Le 5 novembre, 2 minutes sur 2 cœurs : Stedman reste « UNKNOWN ».

## Protocole

1. **Contrôle nul** (`"methode": "nul"`, Erin sans bob) : doit sortir INFEASIBLE. Contrôle faible : l'impossibilité
   se voit dès le graphe, sans le solveur. Il vérifie la chaîne, pas la puissance du solveur.
2. **Témoin** (`"methode": "stedman"`) : un travail de 3 heures au plus sur le PC de Rodolphe, avec les fils que
   le régulateur laisse (environ 20 sur 32).
3. **Erin** (`"methode": "erin"`) : seulement si le témoin a réussi et que sa solution est vérifiée en sonnant les
   5 040 rangées. Sinon, on ne lance pas Erin : un échec n'y voudrait rien dire.

## Prédictions

- **P0** : le contrôle nul sort INFEASIBLE. Confiance : très haute.
- **P1** : le témoin Stedman est résolu en moins de 3 heures, solution vérifiée. Confiance : **faible à moyenne
  (environ 40 %)**. Des solutions existent (Wyld 1994, Johnson, Saddleton), mais je ne sais pas avec quelle
  puissance ni quel encodage ; mes 2 minutes sur 2 cœurs n'ont rien donné.
- **P2** : si P1 tient, la solution compte entre 400 et 800 bobs (les compositions connues citées par Knuth en ont
  438, 579 et 705). Confiance : moyenne.
- **P3** : si Erin est lancé, aucune solution en 5 heures (statut UNKNOWN). Confiance : haute (environ 90 %), vu
  les jours de calcul de Knuth sans résultat.

## Ce que chaque issue voudra dire

- P1 vraie : le modèle et le solveur savent trouver une étendue de ce type ; un échec sur Erin devient une donnée.
- P1 fausse : le modèle n'est ni validé ni réfuté. Étape suivante : encoder une composition publiée de Stedman
  Triples et vérifier que le modèle l'accepte (témoin positif direct), avant toute nouvelle heure de calcul.
- Une solution d'Erin vérifiée serait un résultat nouveau : à revérifier indépendamment avant d'en parler à quiconque.
