# Pré-enregistrement REF-003 — transport spatial sous visibilité contrôlée

Date de gel: 2026-07-27, avant implémentation et tout calcul REF-003. Filiation:
D-017, D-019, D-020 et `reafference_002_technical_stop.md`.

REF-002 n'a produit aucun résultat scientifique. Aucun score 13301..13312 n'a été lu,
agrégé ou utilisé. REF-003 reteste l'hypothèse restée non testée, dans un monde et des
espaces de graines neufs, en corrigeant la garde d'intégrité et la manipulation de
visibilité qui ont arrêté REF-002. Le changement de monde modifie aussi explicitement
la difficulté visuelle de H3, sans modifier aucune porte.

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
- Aucun code, rendu ou calcul REF-003 avant revue contradictoire favorable et
  intégration complète de ses corrections bloquantes.

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

### Digests de l'héritage au gel

| Artefact hérité | SHA-256 |
|---|---|
| `docs/research/reafference_002_preregistration.md` | `cfd8946cceb4ce88bb9d24171b1f5db7561f5b540cb78cf4d3d5f2fdf7bd2210` |
| `learning/reafference_002.py` | `d53ad5044c0be4384e2165422c2f01c27803aac417e22823526e01b2000b72b0` |
| `scripts/research/run_reafference_002.py` | `0ddb0e874a59aa8e6706371a79458f47a7727d5712d1fffd78333a375aa8cb5a` |
| `tests/test_reafference_002.py` | `b54ed41dc9eba42ff3408633e93e82abb331bd5048615e741a1ece18e32219ab` |
| `sim3d/bench_model.py` | `39e44711335deb2ade132be80c2cee79af233e671454a8b3b9cebaa73106ef46` |

Le smoke recalcule ces cinq digests avant tout rendu. Une divergence est bloquante.
Il consigne aussi les digests du présent fichier, des modules REF-003, de la revue et
du manifeste. Les seules divergences autorisées sont les paramètres REF3, les graines,
les gardes de visibilité/intégrité et l'instrumentation temporelle explicitement
déclarés ci-dessous.

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
4. deux entrées partageant `(digest de paire, digest du tenseur moteur)` doivent
   partager la même provenance complète; l'index n'entre pas dans la clé;
5. entrée motrice toujours recomputable sans champ futur.

Les collisions de trames individuelles sont comptées et exportées avec leurs
provenances. Toute collision de trame **corpus↔banque** est bloquante, même si la paire
complète diffère. Les collisions entre banques tenues à part sont descriptives si les
cinq gardes ci-dessus passent. Aucune collision ne peut servir à calibrer, exclure ou
pondérer une paire.

### Contrainte structurelle de champ

Soient `d` la distance de l'objet, `t` la course totale du rail, `w` sa demi-largeur,
`δ` le décalage de bearing par paire, `s_max=4°` le décalage maximal de l'angle de
départ, `a_max=10°` l'amplitude maximale et `φ=15°` le demi-champ horizontal. Toute
configuration atteignable doit satisfaire:

```text
|δ| + atan(t / 2d) + (s_max + a_max)
    ≤ φ + atan(w / d) − 3°
```

La marge `3°` est gelée. REF3 fixe `d=1,05 m`, `t=0,36 m`, `w=0,32 m` et
`δ~U(−3°, +3°)` par paire, avec un RNG disjoint. En degrés:

```text
3 + atan(0,36 / 2,10) + 4 + 10
= 26,7276°
≤ 15 + atan(0,32 / 1,05) − 3
= 28,9492°
```

La marge résiduelle au-delà des `3°` imposés vaut `2,2216°`. Cette preuve est primaire.
Le smoke la recalcule sur l'enveloppe complète — bins, angles de départ, amplitudes,
bearings et extrêmes du rail — avant toute graine réservée. Une violation arrête avant
rendu réservé.

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
Le smoke l'exécute sur les sept banques complètes avant 14301. Il asserte que les
tenseurs consommés par les méthodes ne contiennent aucun champ contrefactuel, état objet
ou mesure de visibilité. Une violation alors que la contrainte structurelle passe est
un défaut d'implémentation, non un aléa à corriger.

Le seuil `0,01` est un détecteur de pathologie, pas le signal attendu. Sur une trame
entière, si le déplacement modifie une fraction `p` des pixels, il exige un changement
local moyen `0,01/p`; à `p=0,04`, cela correspond à `0,25` de contraste normalisé. Le
rendu déterministe a un plancher nul, donc le seuil reste strictement au-dessus du
bruit tout en refusant un objet pratiquement absent.

L'audit exporte aussi, par paire, banque et bin:

- l'effet contrefactuel objet;
- le changement photométrique produit par la tête seule à pose et commande appariées;
- leur rapport;
- la position horizontale de l'objet dans l'image et l'amplitude de mouvement propre.

Ces diagnostics ne participent à aucune porte, sélection, exclusion ou pondération.
Le rapport final met la TPR H3 en regard de leurs distributions.

## Monde REF3

Le banc numérique reste mécaniquement identique, mais la pièce est `3,6×4,1 m`, contient
`8` objets de taille `0,07..0,26 m`, emploie deux palettes lumineuses neuves et place
l'objet externe à `1,05 m` sur un rail de course totale `0,36 m`. Sa demi-largeur vaut
`0,32 m`; sa demi-hauteur `0,24 m`. Son bearing suit le centre du bin avec un décalage
par paire `δ~U(−3°, +3°)`, tiré indépendamment des RNG moteur, objet, pièce et rendu.

Les trajectoires objet ont amplitude absolue `0,07..0,18 m`, signes équilibrés et RNG
indépendant. `|corr(commande relative, déplacement objet)| ≤0,05` reste obligatoire
dans le corpus et `mixed`. Le déplacement signé est tiré avant la position de départ;
conditionnellement à ce déplacement `q`, le départ est uniforme sur tout l'intervalle
qui garantit départ et arrivée dans `[-0,18; +0,18] m`. Il n'existe ni clipping, ni
réduction silencieuse de l'amplitude.

Ce monde augmente la taille angulaire de l'objet et garantit sa présence au champ. À
portes inchangées, la TPR absolue H3 devient plus facile tandis que les marges de
supériorité `≥0,10` deviennent plus difficiles, car toutes les baselines reçoivent le
même gain de signal. Aucun seuil n'est ajusté. Une TPR future ne sera pas comparée à
celle d'un monde où l'objet quittait le champ.

## Temps

Le plafond initial est `90` minutes, supérieur à REF-002 uniquement pour couvrir les
1 536 rendus contrefactuels de visibilité par graine. Le smoke chronomètre séparément
les contrefactuels et refuse qu'une autre croissance de coût leur soit imputée. Il
chronomètre:

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
d'intégrité/visibilité. SANITY-EXTERNAL passe si et seulement si la TPR absolue de
`transport_jepa` sur `external_only`, au seuil issu de `micro_self_calibration`, est
`≥0,70`. Ce seuil reprend a priori le plancher absolu de H3: `external_only` n'a pas
plus de nuisance de mouvement propre que `mixed`, donc une valeur plus faible rendrait
contradictoire la validité du détecteur. Il n'entre dans aucune comparaison de
supériorité ni dans Holm. En dessous, la campagne est non interprétable.

Une baseline égalant ou battant transport sur H3 rend la complexité non payée.

Échec d'une garde: campagne non interprétable, aucun remplacement ou analyse partielle.
Campagne incomplète: non-résultat technique. Campagne complète: variante close quel que
soit le verdict et seconde revue contradictoire obligatoire avant toute promotion.

## Amendements pré-calcul C1–C8

Date d'intégration: 2026-07-27. Source:
`docs/research/reafference_003_review.md`, verdict
`AUTORISER AVEC CORRECTIONS BLOQUANTES`.

Ces amendements sont additifs, prévalent sur toute clause antérieure incompatible et
ont été intégrés avant code, rendu ou calcul REF-003:

- **C1:** géométrie garantie analytiquement sur toute l'enveloppe, avec marge gelée,
  rail `0,36 m`, demi-largeur `0,32 m` et bearing aléatoire par paire;
- **C2:** preuve structurelle primaire, mesure contrefactuelle complète au smoke comme
  contrôle de non-régression, puis contrôle identique en campagne;
- **C3:** collisions de trames corpus↔banques bloquantes; collisions inter-banques
  descriptives;
- **C4:** clé de collision utile `(digest paire, digest moteur)` sans index, dont toute
  répétition exige une provenance identique;
- **C5:** seuil SANITY-EXTERNAL gelé à `0,70`, absolu et hors Holm;
- **C6:** digests de l'héritage consignés et vérifiés avant exécution;
- **C7:** seuil `0,01` justifié comme détecteur de pathologie et diagnostics
  objet/tête/rapport exportés sans effet décisionnel;
- **C8:** augmentation de difficulté/signal du monde déclarée sans ajustement de porte.

Recommandations R1–R6 également intégrées: rectification de la mémoire REF-002,
étanchéité explicite des contrefactuels, temps séparé, diagnostic position×amplitude,
plage de départ conditionnelle et conservation des `236` tests existants plus les tests
REF-003.

Après intégration, l'implémentation puis le smoke 14991 sont autorisés. Les graines
14301..14316 restent fermées jusqu'à un smoke entièrement vert, la preuve analytique
recalculée, les digests concordants, la projection temporelle gelée et un manifeste
complet.

## Correction d'ingénierie smoke I1 — état causal de départ exact

Date: 2026-07-27, après le premier smoke 14991 arrêté sur une garde et avant toute
graine 14301..14316. Aucun score modèle, aucune porte et aucune TPR n'ont été lus.

Le premier smoke a terminé ses trois entraînements puis la garde d'appariement des
masques `yaw_warp` a détecté, dans le bin 0, une différence d'une paire:
`0,76953125` contre `0,78466796875`. Les plans moteurs étaient identiques. La cause
était l'historique servo distinct entre banques avant la trame de départ: vingt pas de
stabilisation ne garantissaient pas un état physique bit-identique au même angle
planifié.

Avant chaque paire des sept banques, le simulateur place désormais la tête à l'angle
pré-transition planifié, avec vitesse nulle et contrôle cohérent, puis appelle
`mj_forward` avant le rendu de départ. Cette opération:

- s'applique identiquement à toutes les banques et méthodes;
- n'utilise aucun champ futur, état objet final ou score;
- rend l'`as5600` de départ et le tenseur moteur exactement recomputables;
- ne modifie ni transition évaluée, ni horizon, ni commande, ni budget d'entraînement;
- rend la garde de multiensemble de masques effectivement déterministe.

Les artefacts du premier smoke restent un échec d'ingénierie archivé. Le protocole et
les digests d'implémentation sont regelés avant la seconde tentative 14991.

## Correction d'ingénierie smoke I2 — benchmark temporel intercalé

Date: 2026-07-27, après la seconde tentative 14991 arrêtée avant génération de données
et avant toute graine 14301..14316. Aucun entraînement smoke, score, TPR ou porte n'a
été produit.

Le benchmark d'équité hérité exécutait les trois conditions en blocs successifs. La
seconde tentative a mesuré un ratio `1,275399 > 1,25`; cette ordonnance ne séparait pas
le coût du modèle d'une dérive temporelle du GPU.

Le seuil `1,25`, les batchs, tailles, optimisateurs, `20` pas d'échauffement et `100`
mesures par condition restent inchangés. Seule l'instrumentation devient:

- ordre tournant intercalé entre les trois conditions à chaque pas;
- synchronisation CUDA immédiatement avant et après chaque mesure;
- médiane des mêmes `100` durées par condition;
- export de l'ordre, du nombre de mesures et des synchronisations.

Cette correction ne répète pas le benchmark jusqu'à succès et ne modifie aucune
opération du modèle. Un ratio intercalé `>1,25` reste bloquant. La seconde tentative et
son manifeste d'échec sont archivés avant tout nouveau smoke.
