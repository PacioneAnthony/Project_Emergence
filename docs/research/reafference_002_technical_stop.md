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
pièces, RNG et états physiques sont distincts. Elle a correctement arrêté la campagne
selon le contrat. La collision ne démontre pas une fuite de données, mais elle démontre
qu'une manipulation `mixed` pouvait devenir visuellement nulle.

Modifier la garde ou ignorer cette trame après ouverture de 13301 serait post hoc.
Les résultats 13301..13312 restent conservés uniquement pour audit technique et ne
doivent pas être inspectés ni agrégés.

## Rectification après revue REF-003

La revue pré-calcul REF-003 a reconstitué l'enveloppe géométrique depuis le code et les
distributions gelées, sans lire aucun score réservé. Avec bearing objet `centre+8°`,
angle de départ `centre+U(−4°,+4°)`, amplitude tête jusqu'à `10°` et demi-champ `15°`:

- le centre de l'objet sortait du champ dans environ `24,9 %` des paires `mixed`;
- l'objet entier sortait du champ dans environ `3,06 %` des paires;
- la garde de visibilité REF-002, mesurée uniquement tête pointée vers le centre du bin,
  était structurellement incapable de détecter ces cas.

Le diagnostic initial « égalité fortuite d'observations » était donc incomplet. La
cause scientifique sous-jacente est une manipulation externe défaillante à certaines
poses. La garde de collision a tiré sous une formulation mal ciblée, mais a empêché une
campagne dont H3 aurait été inattribuable. Cette rectification ne change ni la clôture
technique, ni l'interdiction d'analyse partielle.

## Suite autorisée

Toute reprise exige un protocole, un monde et des graines neufs. Le prochain protocole
doit distinguer:

- disjonction de provenance et de paires, réellement nécessaire contre la fuite;
- collisions de trames inter-banques descriptives si paires et provenances sont
  distinctes, mais collisions corpus↔banques toujours bloquantes;
- visibilité garantie analytiquement sur toute l'enveloppe puis vérifiée
  contrefactuellement par paire, nécessaire pour que `mixed` mesure effectivement un
  changement externe.
