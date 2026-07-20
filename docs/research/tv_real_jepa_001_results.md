# Résultats TV-001 — exploration active avec JEPA réel

Date d'exécution: 2026-07-20. Protocole et amendement pré-calibration:
`tv_real_jepa_001_preregistration.md`. Revue pré-campagne:
`tv_real_jepa_001_review.md`. Artefacts locaux complets:
`data/processed/experiments/tv_real_jepa_001/`.

## Verdict exécutif

La campagne est complète et interprétable, mais **TV-H1 et TV-H2 sont rejetées**.
`regional_lp_gain` ne bat pas le babbling avec un JEPA réel et ne résout pas le piège
de la télévision dans ce dispositif. Il dégrade en moyenne l'erreur structurée de
`2,80 %` et alloue davantage de décisions au secteur bruité (`28,28 %` contre
`25,19 %`). Tous les garde-fous passent; le rejet ne vient ni d'un apprenant inerte,
ni d'une perte de couverture, ni d'un budget incorrect.

Décision pré-enregistrée exécutée: **aucune promotion**. L'implémentation et les graines
sont gelées. Aucune retouche de fenêtre, d'epsilon ou de score ne sera faite sur ces
mondes.

## Calibration

La revue Claude a exigé avant calcul le déplacement de la porte `--review-accepted` et
un amendement descriptif sur l'écran et l'alignement des bins. Après intégration et 170
tests verts, la calibration 9201..9203 a passé toutes ses portes:

| mesure | résultat |
|---|---:|
| différences nulles | 3 072 |
| écart-type nul `s` | 0,0002054 |
| erreur médiane `m` | 0,998967 |
| seuil relatif `0,02m` | 0,019979 |
| fenêtre choisie | `B=4` |
| demi-largeur 95 % à B=4 | 0,0002013 |
| faux positifs à B=4 | 0 % |
| corrélation TV absolue maximale | 0,000913 |
| ancres bin visé ≤5 avec angle réel ≥130° | 0 |

Le bruit d'évaluation du modèle aléatoire était donc très inférieur au seuil gelé; la
campagne a démarré automatiquement.

## Résultats appariés

Chaque run contient exactement 8 000 images, 1 600 décisions et le même budget
d'optimisation. Les 24 runs ont duré 20,3 minutes au total.

| graine | erreur babbling | erreur regional | réduction relative | TV babbling | TV regional |
|---|---:|---:|---:|---:|---:|
| 9301 | 0,4150 | 0,4315 | -3,96 % | 25,31 % | 28,62 % |
| 9302 | 0,4221 | 0,4294 | -1,74 % | 25,56 % | 47,19 % |
| 9303 | 0,4005 | 0,3705 | +7,51 % | 25,62 % | 23,06 % |
| 9304 | 0,3685 | 0,3819 | -3,64 % | 25,50 % | 10,56 % |
| 9305 | 0,3821 | 0,4864 | -27,29 % | 24,75 % | 37,06 % |
| 9306 | 0,3662 | 0,3871 | -5,73 % | 25,25 % | 20,88 % |
| 9307 | 0,4158 | 0,3851 | +7,38 % | 25,56 % | 14,88 % |
| 9308 | 0,3691 | 0,3839 | -4,02 % | 23,75 % | 33,62 % |
| 9309 | 0,3589 | 0,4033 | -12,37 % | 25,06 % | 24,12 % |
| 9310 | 0,4174 | 0,3844 | +7,90 % | 23,88 % | 30,19 % |
| 9311 | 0,3966 | 0,3922 | +1,10 % | 26,75 % | 29,44 % |
| 9312 | 0,3800 | 0,3750 | +1,30 % | 25,31 % | 39,75 % |

### TV-H1 — apprentissage structuré

- réduction relative moyenne: `-2,796 %` (sens défavorable);
- IC BCa 95 %: `[-9,922 %, +1,311 %]`;
- signes: 5 favorables, 7 défavorables;
- permutation exacte unilatérale `p=0,8076`, Holm `p=1,0`;
- `dz=-0,285`, rank-bisériale `-0,231`.

Le seuil de +5 % et la significativité sont tous deux manqués. **TV-H1 rejetée.**

### TV-H2 — évitement de la télévision

- allocation moyenne: regional `28,281 %`, babbling `25,193 %`;
- différence babbling − regional: `-3,089 points`;
- IC BCa 95 %: `[-8,599, +2,644] points`;
- signes: 5 favorables, 7 défavorables;
- permutation exacte unilatérale `p=0,8354`, Holm `p=1,0`.

Le seuil absolu regional `<15 %` est largement manqué et la direction moyenne est
opposée. **TV-H2 rejetée.**

### Garde-fous

- apprenant réel: passé; amélioration structurée initiale→finale moyenne `60,87 %`
  pour babbling et `59,88 %` pour regional;
- couverture: passée; entropie minimale `0,8524`, part minimale d'un bin structuré
  `2,6875 %`;
- construction télévision: passée;
- budgets: exacts.

La campagne est donc **interprétable** et la non-promotion est définitive pour TV-001.

## Diagnostic

L'allocation regional par round, moyennée sur les 12 graines, est:

```text
26,0 %, 25,1 %, 41,7 %, 25,7 %, 45,7 %, 34,7 %, 26,6 %, 37,7 %, 8,8 %, 10,9 %
```

contre un babbling stable autour de 25 %. L'ordonnanceur n'est pas simplement attiré
en permanence: il alterne des rounds presque entièrement télévision avec des rounds
d'évitement. Trois mécanismes compatibles avec les traces restent à départager:

1. **Invariance réellement apprise.** Le contenu pixel est i.i.d., mais le JEPA peut
   apprendre à l'ignorer et à encoder le bezel ou la périphérie prédictible. Les gains
   tenus à part des cellules TV sont fortement positifs au début (gain moyen round 1
   `0,498`, contre `0,341` en structuré). La source est pixellement imprévisible sans
   être nécessairement inapprenable au niveau de représentation; apprendre à filtrer
   le bruit est un progrès réel que TV-H2 compte pourtant comme gaspillage.
2. **Retour retardé et exploitation par rounds.** Une cellule ne reçoit qu'une mise à
   jour avant/après par round. Un gain transitoire élevé peut donc provoquer un round
   entier d'exploitation avant que le score ne soit corrigé, ce qui explique les
   oscillations extrêmes.
3. **Saturation vers l'uniforme.** Quand les moyennes signées deviennent toutes
   négatives, le clip après agrégation les ramène toutes à zéro; le bris d'égalité
   redevient uniforme et réintroduit mécaniquement la télévision.

Les gains régionaux agrégés sur toute la campagne sont proches entre structuré et TV
(`0,0780` contre `0,0860`); le signal ne sépare donc pas durablement les deux familles.
Le bruit de mini-batch calibré n'explique pas cet écart: il était environ cent fois plus
petit que la tolérance gelée.

## Limites et suite

TV-001 invalide la promotion de `regional_lp_gain`, mais laisse une ambiguïté
scientifique importante: le mécanisme échoue-t-il à reconnaître l'irréductibilité, ou
récompense-t-il correctement l'acquisition d'une invariance au bruit que la métrique
d'allocation qualifie à tort de gaspillage? Trancher exige une nouvelle manipulation,
pas un réglage de TV-001 — par exemple comparer un encodeur gelé à l'encodeur plastique,
ou définir une cible externe dont l'incertitude irréductible ne peut être supprimée par
la représentation.

Conformément au protocole, une revue contradictoire de résultats est préparée avant de
choisir entre ce diagnostic discriminant et le passage à l'étape 2/J6, indépendante de
la promotion de l'ordonnanceur.
