# Résultats — Expérience 1, version 0

Premier lancement le 2026-11-02 par Claude, sur processeur (numpy), paramètres par défaut, graines 0, 1 et 2. Environ 30 secondes par graine. Prédictions écrites avant : voir `PREDICTIONS.md`.

## Les chiffres

Précision sur les 31 entités tenues à l'écart (hasard ≈ 0,016). Le réseau gelé connaît parfaitement les 6 relations de base, et l'enchaînement explicite de deux passages retrouve la composition à 100 % sur les trois graines.

| rang k | paramètres de T | structure g0 | g1 | g2 | nulle (3 graines) | témoin (3 graines) |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 256 | 0,000 | 0,000 | 0,000 | 0,000 | 0,000 |
| 2 | 512 | 0,000 | 0,000 | 0,000 | 0,000 | 0,000 |
| 4 | 1 024 | 0,129 | 0,097 | 0,065 | 0,000 | 0,000 |
| 8 | 2 048 | 0,548 | 0,065 | 0,161 | 0,000 | 0,000 |
| 16 | 4 096 | 0,742 | 0,290 | 0,484 | 0,000 | 0,000 |
| 32 | 8 192 | 0,871 | 0,387 | 0,903 | 0,000 | 0,000 |

## Confrontation aux prédictions

- **P1 (structure au-dessus du hasard) : tenue**, sur les trois graines, dès le rang 4. Mais avec une grande variance d'une graine à l'autre (0,39 à 0,90 au rang 32).
- **P2 (nulle au hasard) : tenue.** Zéro partout sur le test, alors que T apprend parfaitement les exemples d'apprentissage : T est capable de tout mémoriser, mais ce qu'elle mémorise ne se généralise que quand la relation est réellement déductible.
- **P3 (témoin en dessous) : tenue.** Le même T sur un réseau jamais entraîné reste à zéro. Ce qui se généralise vient bien du réseau, pas de la transformation.
- **P4 (plateau à petit rang) : non tenue.** La précision monte encore au rang 32. Pas de « petit nombre de paramètres suffisant » visible à cette échelle.

## Ce qu'on peut en dire, et ce qu'on ne peut pas

[FAIT] Dans ce petit monde, une relation jamais apprise mais déductible peut être en partie lue dans l'état interne gelé d'un réseau par une transformation linéaire, sans toucher au réseau, et les deux contrôles excluent les explications les plus évidentes (fuite de mesure, savoir logé dans la transformation).

[INTERPRÉTATION] Le réseau a probablement organisé ses entités de façon en partie régulière (ici cyclique), et c'est cette organisation qui rend la composition « presque visible ». La variance entre graines suggère que cette organisation est plus ou moins propre selon l'entraînement : la même connaissance, plus ou moins accessible selon la manière dont elle a été rangée.

[LIMITES] T est grosse (jusqu'à 8 192 paramètres, soit 45 % du réseau) et n'est entraînée que sur 30 exemples : on est loin du critère « retrouver la conclusion avec moins de paramètres ». Le monde est jouet (décalages cycliques, une seule composition testée). Trois graines seulement.

## Pistes pour la suite (suggestions, non décidées)

1. Mesurer l'organisation du réseau (par exemple : les entités forment-elles un cercle dans l'espace des plongements ?) et voir si elle prédit la variance entre graines.
2. Ajouter une régularisation qui pousse vers une organisation plus régulière pendant l'apprentissage des relations de base, et voir si la composition devient accessible à plus petit rang. Ce serait un premier test du « ranger autrement pour voir plus ».
3. Passer à des relations non cycliques, et à plusieurs compositions, avec la condition `dose` (quantité de structure partagée) proposée dans la lettre 09.
4. Porter l'expérience sur PyTorch pour la carte graphique de Rodolphe, puis sur un petit modèle de langage local.
