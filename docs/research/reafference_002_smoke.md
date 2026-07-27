# REF-002 — smoke 13991

Date: 2026-07-26. Smoke hors campagne, avant toute graine 13301..13316.

## Première tentative — arrêt d'équité

La première tentative s'est arrêtée avant préparation du corpus ou des banques. Le
benchmark C4 mesurait un ratio temps/pas maximal/minimal de `1,29969`, au-dessus de la
tolérance gelée `1,25`. `transport_jepa` exécutait `grid_sample`, tandis que les deux
contrôles contournaient complètement l'opérateur.

Correction technique pré-campagne: les contrôles exécutent désormais le même
`grid_sample`, avec une grille fixée à l'identité. Leur information, leur tenseur fourni
au résidu et leur prédiction restent bit-identiques au contrôle sans warp. Aucun
paramètre, seuil, score scientifique ou budget n'a été changé.

## Tentative complète — verte

- graine: `13991`;
- spec: `62d36289c7029e24df17c1803a407a4cbcc50d5331c324044d0dfa8abeab0fde`;
- protocole: `cfd8946cceb4ce88bb9d24171b1f5db7561f5b540cb78cf4d3d5f2fdf7bd2210`;
- projection: `48,11896` minutes;
- plafond effectif: `75` minutes, non amendé;
- ratio temps/pas C4: `1,12630`;
- paramètres totaux, entraînables et actifs: `480752` pour chaque condition;
- baisse learner-validation: transport `0,52416`, concat `0,52830`,
  no-command `0,49416`;
- visibilité objet minimale par bin: `0,10005`;
- corrélation mixed: `0,03460`;
- `768/768` paires distinctes dans chacune des sept banques;
- entrée motrice future-free, H5 commun, `MSE(copie)>0` en calibration et
  multiensembles de masques warp: verts.

Le manifeste complet est conservé localement dans
`data/processed/experiments/reafference_002/smoke_13991.json`. Il confirme
`reserved_seeds_opened=false`.
