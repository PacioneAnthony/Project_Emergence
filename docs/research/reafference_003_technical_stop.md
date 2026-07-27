# REF-003 — arrêt technique sans résultat scientifique

Date: 2026-07-27. Simulation uniquement sous D-008.

## Décision

REF-003 est close comme **non-résultat technique**. Aucune porte H1/H3/H4/H5 ou
SANITY-EXTERNAL n'est calculée, aucune analyse partielle n'est autorisée et aucune
promotion n'est possible.

## Smoke 14991

La troisième tentative smoke était entièrement verte après deux corrections
d'ingénierie archivées:

- champ analytique `26,72758° ≤ 28,94922°`, marge résiduelle `2,22165°`;
- visibilité minimale `0,15308` en `external_only`, `0,05794` en `mixed`;
- zéro collision et digests concordants;
- équité temporelle `1,10334`;
- projection `39,92741` minutes sous plafond initial `90` minutes, non amendé;
- `247` tests complets verts.

## Campagne réservée

État au moment de l'arrêt:

- 14301..14302: deux triplets / six runs et deux évaluations complets;
- 14303: corpus et sept banques préparés; aucun entraînement ouvert;
- 14304..14316: jamais ouvertes.

Le runner s'est arrêté dans `prepare_seed(14303)` sur:

```text
AssertionError: REF3 per-pair visibility guard failed
```

Les scores de 14301..14302 n'ont pas été lus, agrégés ou interprétés.

## Paires fautives

La contrainte de champ et toutes les paires `mixed` de 14303 passent. Deux paires
`external_only` échouent au seuil contrefactuel individuel `0,01`:

| Index | Bin | Contexte | Effet | Angle tête | Départ objet | Arrivée objet | Δ objet | δ bearing | x image |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 203 | 1 | 1 | `0,00445325` | `37,17773°` | `−0,08304 m` | `0,08584 m` | `0,16887 m` | `−0,27980°` | `46,62067 px` |
| 625 | 4 | 1 | `0,00699966` | `96,50391°` | `0,16970 m` | `0,07513 m` | `−0,09456 m` | `−1,54623°` | `44,14229 px` |

Les moyennes des bins restent élevées (`0,20758` et `0,20958`) et les objets sont
géométriquement dans l'image. La preuve angulaire C1 garantit la présence au champ,
mais pas un effet photométrique minimal: occlusion par la scène, contraste local ou
quasi-annulation de texture restent possibles.

## Interprétation

La garde a correctement empêché une campagne où SANITY-EXTERNAL aurait contenu des
positifs visuellement pathologiques. Modifier le seuil, exclure les deux paires,
resampler ou reprendre 14303 après ouverture de graines réservées serait post hoc.

REF-003 ne confirme ni ne rejette le transport spatial. Elle établit une leçon
d'instrumentation: une enveloppe angulaire est nécessaire mais insuffisante. Une future
tentative doit garantir **par construction** non seulement le champ, mais aussi
l'absence d'occlusion et un contraste/déplacement local minimal, avant tirage des
graines réservées.

## Suite autorisée

Toute nouvelle tentative exige protocole, monde et graines neufs. La manipulation
externe devra être rendue dans une couche ou une zone de scène dédiée dont:

- la visibilité et l'absence d'occlusion sont structurelles;
- le contraste local et la surface déplacée ont une borne analytique;
- la variabilité de position reste indépendante de la commande;
- la même amélioration bénéficie aux cinq méthodes;
- le contrôle exhaustif est effectué sur un ensemble de construction non réservé avant
  la campagne, sans sélection de paires après observation.

