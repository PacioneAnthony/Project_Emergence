# REF-002 — arrêt technique sans résultat scientifique

Date: 2026-07-27. Simulation uniquement sous D-008.

## Décision

REF-002 est close comme **non-résultat technique**. Aucune porte H1/H3/H4/H5 n'est
calculée, aucune analyse partielle des graines complètes n'est autorisée et aucune
promotion n'est possible.

## Smoke 13991

Une première tentative s'est arrêtée avant données sur l'équité de calcul:
ratio temps/pas `1,29969 > 1,25`. Les contrôles ont ensuite reçu le même
`grid_sample` fixé à l'identité, sans changement d'information, seuil ou budget.

La tentative complète a passé toutes les gardes:

- projection `48,11896` minutes sous plafond initial `75` minutes;
- plafond non amendé;
- ratio temps/pas `1,12630`;
- paramètres totaux, entraînables et actifs égaux;
- learner-validation, visibilité, indépendance, non-fuite motrice,
  `MSE(copie)>0`, unicité des paires et masques warp verts.

Voir `reafference_002_smoke.md`.

## Campagne réservée

État au moment de l'arrêt:

- 13301..13312: 12 triplets / 36 runs et 12 évaluations complets;
- 13313: corpus, sept banques et manifeste préparés; aucun entraînement ouvert;
- 13314..13316: jamais ouvertes;
- temps consigné par les artefacts: `2109,24128` secondes, soit `35,15402` minutes.

Le runner s'est arrêté dans `data_integrity_checks(13313)` sur:

```text
AssertionError: REF2 inter-bank image collision involving mixed
```

## Collision exacte

SHA-256 de la trame:

```text
102401588fd14d20f67481a9e05a4cbba15b87d9587b4ca4b97fa920e564e861
```

Occurrences:

| Banque | Côté | Index | Bin | Contexte | Angle départ | Horizon | Amplitude | Δ tête | Δ objet |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `moving_self_calibration` | fin | 201 | 1 | 1 | 37,353515625° | 3 | −10° | −10,01953125° | 0 |
| `mixed` | fin | 244 | 1 | 1 | 37,353515625° | 3 | −10° | −10,01953125° | 0,095039383 m |

Les images sont bit-identiques (`moyenne=164,32715`, `écart-type=31,41792`) malgré
des espaces de pièces/RNG et des états objet distincts. L'objet déplacé n'affecte pas
la vue finale dans cette configuration. Il n'existe:

- aucune collision corpus↔banques sur 13313;
- aucune paire `(départ, fin)` dupliquée dans une banque;
- qu'une collision de trame inter-banques.

## Interprétation

La garde C6 interdisait toute collision de **trame**, même lorsque les provenances,
pièces, RNG et états physiques sont distincts. Elle a donc correctement arrêté la
campagne selon le contrat, mais elle confond fuite de données et égalité fortuite
d'observations. Cette égalité ne démontre ni fuite, ni défaut du modèle; elle montre que
le critère d'intégrité était plus fort que la propriété scientifique recherchée.

Modifier la garde ou ignorer cette trame après ouverture de 13301 serait post hoc.
Les résultats 13301..13312 restent conservés uniquement pour audit technique et ne
doivent pas être inspectés ni agrégés.

## Suite autorisée

Toute reprise exige un protocole, un monde et des graines neufs. Le prochain protocole
doit distinguer:

- disjonction de provenance et de paires, réellement nécessaire contre la fuite;
- collisions de trames individuelles, descriptives si les paires et provenances sont
  distinctes;
- visibilité contrefactuelle de l'objet par paire, nécessaire pour que `mixed` mesure
  effectivement un changement externe.
