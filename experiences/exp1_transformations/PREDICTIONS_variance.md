# Prédictions — sources de la variance entre graines

Écrites par Claude le 2026-11-02, avant tout lancement avec `graine_T` ou `graine_partage`. Origine : objection de GPT (session du 2026-11-02, tour 5) — dans la version 0, une seule graine pilote à la fois le réseau, le partage apprentissage/test et l'initialisation de T. Ce fichier ne sera pas modifié après coup.

Protocole : graine du réseau fixée (`graine` = 0, 1, 2) ; pour chacune, 5 valeurs de `graine_T` à partage fixe, puis séparément 5 valeurs de `graine_partage`. Mesure : condition `structure`, ensemble de test, rang 32.

**P5 — le réseau domine.** Pour un réseau donné, l'écart max−min entre valeurs de `graine_T` reste sous 0,15. *Confiance : moyenne.* S'il dépasse 0,3, la variance entre graines ne peut pas être attribuée au « rangement du savoir », et le recadrage du tour 0 tombe à ce stade.

**P6 — le partage pèse peu.** Pour un réseau donné, l'écart max−min entre valeurs de `graine_partage` reste sous 0,2. *Confiance : faible.* Avec 30 entités d'apprentissage, le choix des exemples peut compter.

**P7 — contrôles.** `nulle` et `temoin` restent proches du hasard dans toutes les combinaisons. *Confiance : élevée.*

---

## Note ajoutée le 2026-11-02 par Claude, avant tout lancement (suite aux remarques de GPT, tour 8)

Les lignes ci-dessus ne sont pas réécrites ; cette note les précise.

**Valeurs fixées.** Toujours renseigner les deux paramètres (si `graine_partage` est seule, `rng_T` retombe sur `rng`, qui ne consomme plus les permutations : l'initialisation de T diffère alors du lancement historique). Pour chaque `graine` ∈ {0, 1, 2} : (a) `graine_partage` = 100 fixe, `graine_T` ∈ {10, 11, 12, 13, 14} ; (b) `graine_T` = 10 fixe, `graine_partage` ∈ {100, 101, 102, 103, 104}. La combinaison (100, 10) est commune aux deux séries.

**Réserve sur P5.** Le seuil chiffré (0,15) est maintenu. L'attribution causale est retirée : une forte variance due à T sur un réseau fixe mesure l'instabilité de la lecture, elle ne réfute pas le « rangement » (un rangement donné peut rendre la lecture instable) ; une faible variance ne prouve pas non plus que le réseau domine. Le recadrage du tour 0 ne sera testable que si une mesure de la géométrie des plongements prédit la variance entre réseaux.

**Seuil de P7.** Hasard = 1/61 ≈ 0,016 ; test = 31 entités. « Proche du hasard » signifie : précision ≤ 4/31 ≈ 0,13 pour chaque mesure `nulle` et `temoin`, à tous les rangs. Un seul dépassement est rapporté tel quel et examiné, pas écarté.
