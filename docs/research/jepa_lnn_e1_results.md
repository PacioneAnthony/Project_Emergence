# E1 - Variance inter-graines et réplication S2

## Verdict

E1 confirme que la variance d'entraînement est suffisamment grande pour invalider toute promotion mono-graine. Le checkpoint historique `dagger_002` a `1.21%` de ticks de collision nominaux, alors que cinq répétitions observation-only de la même recette donnent `3.30% +/- 0.47%`, avec une plage de `2.79%` à `3.87%`. Son résultat nominal est donc un tirage exceptionnel, pas une référence moyenne reproductible.

La RMSE offline reste stable (`0.348-0.354` pour les contrôles) sans prédire le classement en boucle fermée.

## Résultats moyens

| famille | graines | nominal ticks | nominal événements / 1000 | randomisé ticks | randomisé événements / 1000 |
|---|---:|---:|---:|---:|---:|
| contrôle apparié | 3 | 3.34% +/- 0.47% | 6.99 +/- 1.76 | 2.01% +/- 0.47% | 3.14 +/- 0.08 |
| JEPA auxiliaire `lambda=0.3` | 3 | 3.49% +/- 1.57% | 9.83 +/- 8.06 | 1.10% +/- 0.47% | 2.76 +/- 1.17 |
| JEPA auxiliaire `lambda=1.0` | 3 | 3.62% +/- 2.69% | 7.19 +/- 3.48 | 2.93% +/- 1.74% | 7.01 +/- 4.04 |
| contrôles observation-only combinés | 5 | 3.30% +/- 0.47% | 6.90 +/- 1.61 | 2.01% +/- 0.34% | 3.47 +/- 0.67 |

Les dispersions sont des écarts-types entre graines. Les intervalles complets sont dans `data/processed/experiments/lnn_e1_multiseed/summary.md`.

## Effet de lambda=0.3

Sur les trois graines appariées, `lambda=0.3` réduit le taux de ticks de collision randomisé à chaque fois:

| graine | contrôle | lambda=0.3 | différence absolue |
|---:|---:|---:|---:|
| 4202 | 2.54% | 0.59% | -1.95 point |
| 5202 | 1.67% | 1.51% | -0.16 point |
| 6202 | 1.82% | 1.21% | -0.61 point |

La moyenne passe de `2.01%` à `1.10%`, soit environ `45%` de réduction relative. Cependant, les événements randomisés ne diminuent que pour une graine sur trois. Le nombre moyen d'événements reste proche (`3.14` contre `2.76` par 1000 pas), avec fort chevauchement.

L'interprétation la plus défendable est donc: la régularisation JEPA `lambda=0.3` apprend souvent au LNN à sortir plus vite d'une collision randomisée, mais ne démontre pas encore qu'elle évite davantage les impacts.

En nominal, aucun gain moyen n'est observé. La graine 4202 est même fortement dégradée en nombre d'événements. Le modèle n'est pas promotable.

## Effet de lambda=1.0

`lambda=1.0` est instable sur les deux protocoles. Les plages nominales (`1.90-6.72%`) et randomisées (`1.05-4.48%`) recouvrent à la fois de très bons et de mauvais comportements. Cette branche est abandonnée pour la suite immédiate.

## Décision

E2, le schedule de `lambda`, reste suspendu. L'écart inter-graines et la faiblesse de la sélection par RMSE imposent d'abord E3:

1. entraîner les familles contrôle et `lambda=0.3` sur les trois mêmes graines;
2. évaluer périodiquement chaque entraînement sur des mini-rollouts nominaux et randomisés;
3. sélectionner le checkpoint qui minimise le pire taux de collision des deux protocoles;
4. évaluer le checkpoint retenu sur les graines finales tenues à l'écart;
5. vérifier si E3 réduit la moyenne et surtout la dispersion inter-graines face à E1.

La règle de promotion reste une domination sur les deux protocoles en moyenne sur au moins trois graines, avec vérification des événements de collision et pas seulement des ticks.
