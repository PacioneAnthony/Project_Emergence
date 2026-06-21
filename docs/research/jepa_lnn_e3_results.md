# E3 - Sélection par mini-rollouts

## Correction du protocole

La première exécution E3 a révélé une solution dégénérée: pour la graine `6202`, l'epoch 1 de `lambda=0.3` obtenait zéro collision en restant presque immobile (`v moyen = 0.0036`). Le critère a été corrigé pour exiger une commande avant moyenne d'au moins `0.05` sur les protocoles nominal et randomisé. Le run contaminé a ensuite été recalculé et a sélectionné l'epoch 2000 (`v moyen de sélection = 0.121`).

## Résultats corrigés

| famille | nominal ticks | nominal événements / 1000 | randomisé ticks | randomisé événements / 1000 |
|---|---:|---:|---:|---:|
| contrôle E3 | 3.47% +/- 0.93% | 6.59 +/- 2.26 | 1.85% +/- 0.53% | 3.53 +/- 0.75 |
| `lambda=0.3` E3 | 1.67% +/- 0.16% | 3.61 +/- 0.30 | 1.46% +/- 0.72% | 3.70 +/- 0.96 |

La sélection par rollout choisit des epochs différents du minimum de RMSE dans cinq runs sur six. Cela confirme directement que la RMSE offline n'est pas le bon critère de checkpoint.

## Comparaison à E1

Pour `lambda=0.3`, E3 transforme le compromis observé en E1:

- nominal: `3.49% +/- 1.57%` vers `1.67% +/- 0.16%`;
- randomisé: `1.10% +/- 0.47%` vers `1.46% +/- 0.72%`;
- événements nominaux: `9.83` vers `3.61` par 1000 pas;
- événements randomisés: `2.76` vers `3.70` par 1000 pas.

E3 stabilise donc fortement le nominal et conserve un bon taux de ticks randomisés, mais il ne réduit pas l'incidence des impacts randomisés. Le JEPA auxiliaire semble encore agir davantage sur la récupération que sur l'anticipation.

## Décision

Ne pas remplacer `dagger_002` pour le moment. Le candidat E3 moyen reste au-dessus de son ancre nominale historique (`1.67%` contre `1.21%`) et les intervalles randomisés des familles E3 se recouvrent. La domination en événements randomisés n'est pas acquise.

E2 devient maintenant pertinent: appliquer un schedule cosine de `lambda=1.0` vers `0.1`, tout en conservant la sélection E3 et la contrainte de locomotion. L'objectif est de former une représentation JEPA forte en début d'entraînement, puis de redonner progressivement la priorité au contrôle afin de réduire les impacts randomisés sans perdre la stabilité nominale d'E3.
