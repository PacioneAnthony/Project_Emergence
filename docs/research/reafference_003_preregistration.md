# Pré-enregistrement REF-003 — transport spatial sous visibilité contrôlée

Date de gel: 2026-07-27, avant implémentation et tout calcul REF-003. Filiation:
D-017, D-019, D-020 et `reafference_002_technical_stop.md`.

REF-002 n'a produit aucun résultat scientifique. Aucun score 13301..13312 n'a été lu,
agrégé ou utilisé. REF-003 reteste l'hypothèse restée non testée, dans un monde et des
espaces de graines neufs, en corrigeant uniquement la garde d'intégrité qui a arrêté
REF-002.

## Hypothèse

Sous mouvement simultané de la tête et d'un objet dont l'effet visuel est vérifié pour
chaque paire, le transport explicite d'une carte `8×8×128` par la commande relative:

1. prédit mieux le mouvement propre que les contrôles de même capacité;
2. détecte mieux le changement externe en `mixed`;
3. ne se réduit pas à un transport identité;
4. conserve une FPR tenue à part sous mouvements normal et micro.

La revendication reste limitée à ce monde et ne vaut ni segmentation, ni causalité
générale, ni agentivité.

## Nouveauté et interdictions

- Monde `REF3` neuf: dimensions, objets, éclairages, distance, rail et apparence de
  l'objet changés.
- Smoke `14991`.
- Campagne `14301..14316`, n=16, jamais ouverte.
- Graine statistique `2026072701`.
- Aucun artefact, checkpoint, banque, seuil ou score 13301..13316 n'est réutilisé.
- Les poids repartent de l'initialisation pour chaque condition et chaque graine.
- Aucun code, rendu ou calcul REF-003 avant revue contradictoire favorable.

## Protocole hérité sans changement

REF-003 reprend exactement le protocole REF-002 amendé C1–C8 pour:

- `transport_jepa`, `concat_relative_jepa`, `no_command_jepa`, `pixel_change`,
  `yaw_warp`;
- encodeur, adaptateur moteur, résidu, paramètres actifs et identité à commande nulle;
- entrée pré-transition et interdiction d'angle futur;
- corpus `20×600`, 2 400 décisions, 4 500 pas AdamW, batch 256;
- carte `8×8×128`, horizons 1..5 et VICReg sur moyenne spatiale 128;
- sept banques de `128` paires par bin et micro-mouvements `2°`;
- calendriers mobiles et masques warp appariés par multiensemble;
- score normalisé, seuils 5 %, égalités non externes;
- SANITY-EXTERNAL descriptive et H3 comme seule porte de détection;
- H1, H3, H4, H5 et famille Holm commune de huit tests;
- marges `0,03`, `0,10`, TPR mixed `0,70`, FPR globale `0,07` et bin `0,10`;
- learner-validation `≥20 %`, équité, non-fuite motrice, indépendance et H5;
- fermeture de la variante après campagne et revue avant promotion.

Toute différence non explicitement déclarée ci-dessous est interdite.

## Correction unique — intégrité et visibilité

### Disjonction bloquante

La fuite est définie par provenance et par paire, non par l'égalité d'une trame isolée.
Le manifeste exporte pour chaque paire:

- banque, graine, bin, contexte et index;
- graines de pièce, objet, moteur et rendu;
- digest de la paire `(frame_start, frame_end)`;
- digest du tenseur moteur;
- état objet de départ/fin réservé à l'audit.

Gardes bloquantes:

1. espaces de RNG et de pièces disjoints entre corpus et banques, puis entre banques;
2. zéro digest de **paire** commun corpus↔banques ou entre banques;
3. zéro paire dupliquée dans une banque;
4. zéro collision du tuple `(paire, tenseur moteur, provenance)`;
5. entrée motrice toujours recomputable sans champ futur.

Les collisions de trames individuelles sont comptées et exportées avec leurs
provenances. Elles ne sont pas bloquantes si les cinq gardes ci-dessus passent. Elles
ne peuvent pas servir à calibrer, exclure ou pondérer une paire.

### Visibilité contrefactuelle bloquante

Pour chaque paire `external_only` et `mixed`, le générateur produit en audit une trame
de fin contrefactuelle avec:

- même pièce, tête, commande, horizon et rendu;
- objet maintenu à sa position de départ au lieu de sa position finale.

L'effet

```text
mean(abs(frame_end_réelle - frame_end_objet_maintenu)) / 255
```

doit être `≥0,01` pour chaque paire. Minimum, médiane, maximum et distribution par bin
sont exportés. Une paire sous le seuil arrête le smoke ou la campagne; elle n'est ni
resamplée, ni remplacée après observation. L'effet moyen par bin doit aussi rester
`≥0,05`, comme dans REF-002.

Cette garde utilise l'état objet uniquement pour auditer la manipulation. La trame
contrefactuelle, sa valeur et l'état objet restent invisibles aux cinq méthodes.

## Monde REF3

Le banc numérique reste mécaniquement identique, mais la pièce est `3,6×4,1 m`, contient
`8` objets de taille `0,07..0,26 m`, emploie deux palettes lumineuses neuves et place
l'objet externe à `1,05 m` sur un rail de `0,44 m`. Son bearing suit le centre du bin
avec un décalage gelé de `−6°`, afin de rester dans le champ sans livrer sa position aux
modèles.

Les trajectoires objet ont amplitude absolue `0,07..0,18 m`, signes équilibrés et RNG
indépendant. `|corr(commande relative, déplacement objet)| ≤0,05` reste obligatoire
dans le corpus et `mixed`.

## Temps

Le plafond initial est `90` minutes, supérieur à REF-002 uniquement pour couvrir les
1 536 rendus contrefactuels de visibilité par graine. Le smoke chronomètre:

1. préparation, y compris contrefactuels;
2. trois entraînements complets;
3. notation des sept banques;
4. six passes H5;
5. évaluations et gardes.

Projection:

```text
48 × (temps_partagé_smoke / 3 + moyenne_temps_condition_complet)
```

Si elle dépasse 90 minutes, amendement au multiple supérieur de cinq minutes avec
10 % de marge, écrit avec digest avant 14301. Aucun amendement après.

## Décision

La promotion exige conjointement H1, H3, H4, H5, SANITY-EXTERNAL et toutes les gardes
d'intégrité/visibilité. Une baseline égalant ou battant transport sur H3 rend la
complexité non payée.

Échec d'une garde: campagne non interprétable, aucun remplacement ou analyse partielle.
Campagne incomplète: non-résultat technique. Campagne complète: variante close quel que
soit le verdict et seconde revue contradictoire obligatoire avant toute promotion.
