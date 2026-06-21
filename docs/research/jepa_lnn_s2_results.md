# S2 - JEPA comme perte auxiliaire du LNN

## Objectif

S2 utilise le JEPA pour structurer l'état caché du LNN pendant l'entraînement, sans injecter le latent JEPA dans la politique en boucle fermée.

Le LNN reçoit toujours uniquement:

```text
[distance_ultrason, angle_servo, gyro_z]
```

Une tête auxiliaire prédit depuis l'état LNN suivant le latent cible du prochain contexte JEPA. Cette cible vient de l'encodeur EMA du JEPA. La tête auxiliaire est sauvegardée pour diagnostic, mais elle est retirée à l'inférence.

La perte utilisée est:

```text
L = L_action + lambda_aux * L_latent + L_regularisation_etat
```

## Protocole

- données: `data/raw/sim2d_zoh_scan05_medium_dagger_001.csv`
- JEPA cible: `models/sensor_jepa_zoh_scan05_medium_001_decoder_refined.pth`
- graine d'entraînement commune: `4202`
- architecture LNN: état `64`, MLP caché `128`
- séquences: `64` pas
- entraînement: `2500` epochs, `lr=3e-4`
- évaluation nominale: 5 épisodes de 6000 pas, graines `1001-1005`
- évaluation randomisée: 5 épisodes de 6000 pas, graines `2201-2205`

Un contrôle sans perte auxiliaire a été réentraîné avec exactement la même graine et les mêmes hyperparamètres pour isoler l'effet de S2.

## Résultats

| checkpoint | lambda auxiliaire | RMSE action validation | RMSE latent | collisions nominales | collisions randomisées |
|---|---:|---:|---:|---:|---:|
| `lnn_dagger_seed4202_control_001.pth` | 0 | 0.350261 | n/a | 943 / 30000 (3.14%) | 763 / 30000 (2.54%) |
| `lnn_jepa_aux_w01_001.pth` | 0.1 | 0.352032 | 0.184473 | 1147 / 30000 (3.82%) | 536 / 30000 (1.79%) |
| `lnn_jepa_aux_w03_001.pth` | 0.3 | 0.350351 | 0.162972 | 1567 / 30000 (5.22%) | 178 / 30000 (0.59%) |
| `lnn_jepa_aux_w10_001.pth` | 1.0 | 0.355005 | 0.150957 | 670 / 30000 (2.23%) | 980 / 30000 (3.27%) |
| `lnn_zoh_scan05_medium_dagger_002.pth` | référence active | 0.348901 | n/a | 362 / 30000 (1.21%) | 756 / 30000 (2.52%) |

## Lecture

La perte auxiliaire modifie bien le comportement fermé alors que la RMSE d'action offline reste presque inchangée. L'effet ne se réduit donc pas à une meilleure imitation teacher-forced.

- `lambda=0.3` apporte le meilleur résultat randomisé du projet: `0.59%`, contre `2.54%` pour le contrôle de même graine et `2.52%` pour le contrôleur actif.
- `lambda=1.0` améliore le nominal par rapport au contrôle de même graine (`2.23%` contre `3.14%`), mais reste moins bon que le contrôleur actif (`1.21%`) et régresse sous randomisation.
- la prédictibilité du latent augmente de façon monotone avec `lambda`, mais la performance de contrôle ne suit pas une relation monotone.

S2 valide donc l'idée que le JEPA peut régulariser utilement la dynamique interne du LNN sans créer de distribution shift à l'inférence. En revanche, un poids auxiliaire fixe produit un compromis nominal/robustesse encore instable.

## Décision

Ne promouvoir aucun checkpoint S2 pour le moment. Conserver `models/lnn_zoh_scan05_medium_dagger_002.pth` comme contrôleur actif, car aucun candidat S2 ne le domine sur les deux protocoles.

La variance inter-graines doit être quantifiée avant tout nouveau réglage. Le contrôle de même graine obtient `3.14%` en nominal alors que le checkpoint historique `dagger_002` obtient `1.21%` avec une recette équivalente. Cet écart est du même ordre que les effets attribués à la perte auxiliaire.

E1 est donc bloquant avant le schedule de poids: entraîner le contrôle, `lambda=0.3` et `lambda=1.0` sur au moins trois graines communes, ajouter deux répétitions observation-only de la recette de référence, puis rapporter moyenne, écart-type et min-max. Les évaluations comptent désormais les entrées en collision en plus des ticks autocorrélés.

Le poids auxiliaire programmé reste l'essai E2 rationnel si E1 confirme un effet robuste: perte JEPA forte au début pour former la représentation, puis réduction progressive afin de laisser la politique optimiser le contrôle nominal. La sélection devra utiliser conjointement les rollouts nominaux et randomisés, pas seulement la RMSE offline.
