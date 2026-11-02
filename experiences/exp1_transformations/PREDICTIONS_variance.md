# Prédictions — sources de la variance entre graines

Écrites par Claude le 2026-11-02, avant tout lancement avec `graine_T` ou `graine_partage`. Origine : objection de GPT (session du 2026-11-02, tour 5) — dans la version 0, une seule graine pilote à la fois le réseau, le partage apprentissage/test et l'initialisation de T. Ce fichier ne sera pas modifié après coup.

Protocole : graine du réseau fixée (`graine` = 0, 1, 2) ; pour chacune, 5 valeurs de `graine_T` à partage fixe, puis séparément 5 valeurs de `graine_partage`. Mesure : condition `structure`, ensemble de test, rang 32.

**P5 — le réseau domine.** Pour un réseau donné, l'écart max−min entre valeurs de `graine_T` reste sous 0,15. *Confiance : moyenne.* S'il dépasse 0,3, la variance entre graines ne peut pas être attribuée au « rangement du savoir », et le recadrage du tour 0 tombe à ce stade.

**P6 — le partage pèse peu.** Pour un réseau donné, l'écart max−min entre valeurs de `graine_partage` reste sous 0,2. *Confiance : faible.* Avec 30 entités d'apprentissage, le choix des exemples peut compter.

**P7 — contrôles.** `nulle` et `temoin` restent proches du hasard dans toutes les combinaisons. *Confiance : élevée.*
