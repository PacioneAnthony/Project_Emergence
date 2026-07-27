# Pré-enregistrement REF-002 — transport sensorimoteur spatial explicite

Date de gel: 2026-07-26, avant implémentation et tout calcul. Filiation: étape 3 de
`CODEX_TASK_BRIEF.md`, D-015, D-016 et D-017. REF-001 est close; aucune graine, image,
banque, seuil ou valeur décisionnelle 12301..12316 n'est réutilisée pour régler REF-002.

## Hypothèse mécaniste

REF-001 a établi proprement que concaténer une commande absolue à un latent global ne
produit pas une copie d'efférence exploitable. REF-002 teste une hypothèse différente:
la rotation de caméra possède une structure spatiale qui doit être imposée au
prédicteur. Un modèle qui transporte explicitement une carte de caractéristiques selon
le déplacement moteur relatif attendu doit:

1. mieux prédire les changements dus à la tête;
2. laisser dans son résidu les changements indépendants de ce transport;
3. détecter l'externe sous mouvement simultané mieux qu'un modèle recevant la même
   information sans biais de transport et qu'un warp géométrique simple.

La revendication reste opérationnelle et limitée à ce monde. Elle ne vaut ni
segmentation, ni causalité générale, ni agentivité.

## Nouveauté obligatoire

- Monde `REF2` neuf, textures, géométries, éclairages et espaces de graines neufs.
- Smoke `13991`; campagne `13301..13316`, n=16, jamais ouverts auparavant.
- Entrée motrice relative neuve: angle courant de tête et séquence des erreurs signées
  `commande_cible − angle_courant`, normalisées par 160°, connues avant chaque
  transition. Aucun angle futur ni état objet n'entre dans le modèle.
- Prédiction spatiale avant pooling, et non prédicteur MLP sur latent global.
- Calibration des baselines par strate de mouvement, afin d'éviter le décalage de
  domaine tête mobile/tête tenue identifié par la revue REF-001.

## Conditions et baselines

Trois conditions apprenantes partagent encodeur, largeur, nombre de paramètres,
initialisation, corpus, ordre de batchs et budget:

1. `transport_jepa`: un petit réseau moteur produit un déplacement horizontal continu
   et une modulation à partir de l'entrée relative; `grid_sample` transporte la carte
   spatiale, puis un résidu convolutionnel prédit la carte cible;
2. `concat_relative_jepa`: reçoit exactement la même entrée relative et le même budget
   paramétrique, mais la diffuse comme canaux constants avant le même résidu
   convolutionnel, sans déplacement spatial imposé;
3. `no_command_jepa`: architecture et capacité identiques, mais séquence de commandes
   mise à zéro; angle courant et horizon conservés.

Les branches inutilisées sont conservées de façon à rendre les nombres de paramètres
strictement identiques. Le smoke exige une sortie bit-identique entre
`concat_relative_jepa` alimenté par commandes nulles et `no_command_jepa` à
l'initialisation.

Deux baselines analytiques reçoivent les mêmes trames et la même information motrice:

- `pixel_change`: différence absolue brute, conservée comme contrôle minimal;
- `yaw_warp`: warp projectif horizontal déterministe de la trame courante, utilisant
  les intrinsics gelés et le déplacement prédit par le modèle servo connu, puis erreur
  photométrique moyenne sur le masque de pixels valides.

`yaw_warp` n'est ajusté sur aucune banque et ne reçoit aucun état objet. Si cette
baseline égale ou bat `transport_jepa`, la complexité apprise n'est pas payée.

## Monde, corpus et budgets

Le monde REF2 conserve un vrai corps objet sur joint coulissant, mais change la pièce,
le rail, l'apparence de l'objet et les distributions de trajectoires. Le RNG objet est
distinct des RNG moteur, pièce, lot et modèle.

- 20 épisodes × 600 images à 10 Hz = 12 000 images par graine.
- 2 400 décisions motrices; moitié des épisodes avec objet immobile, moitié avec objet
  mobile indépendamment.
- 4 500 pas AdamW par condition, batch 256 = 1 152 000 exemples-gradient.
- Images 64×64; carte spatiale 8×8, largeur de base 32, latent agrégé 128; horizons
  1..5; AdamW `3e-4`, weight decay `1e-4`; variance/covariance inchangées.
- 48 runs apprenants maximum.
- Plafond initial: 75 minutes murales cumulées de préparation, entraînement **et
  évaluation**. Chaque phase est chronométrée et exportée.

Le smoke exécute une répétition complète de chaque condition. Projection:

```text
48 × (temps_partagé_smoke / 3 + moyenne_des_temps_condition_complets)
```

Si la projection dépasse 75 minutes, le plafond est amendé avant toute graine réservée
au multiple supérieur de cinq minutes avec 10 % de marge. Aucun amendement n'est permis
après ouverture de 13301.

## Banques tenues à part et appariement de domaine

Chaque graine possède sept banques de 128 paires par angle-bin, équilibrées 64/64 par
contexte et disjointes du corpus:

1. `moving_self_calibration`: tête mobile, objet immobile;
2. `moving_self_test`: même distribution motrice tenue à part;
3. `static_calibration`: tête et objet immobiles, bruit de rendu identique;
4. `static_test`: second contrôle statique tenu à part;
5. `external_only`: tête immobile, objet mobile;
6. `mixed`: tête et objet mobiles indépendamment;
7. `learner_validation`: mélange sans rôle dans les seuils.

`moving_self_calibration`, `moving_self_test` et `mixed` réutilisent des calendriers
moteurs appariés bit à bit, redistribués sur des pièces et RNG objet disjoints: départ,
amplitude, signe et horizon ont ainsi exactement le même multiensemble par bin.
`static_calibration`, `static_test` et `external_only` partagent la strate zéro. Les
seuils de `external_only` viennent uniquement de `static_calibration`; ceux de `mixed`
et de `moving_self_test` viennent uniquement de `moving_self_calibration`. Une
baseline n'est donc jamais évaluée hors de sa strate de calibration.

Les six bins de centre 20°, 40°, 60°, 80°, 100° et 120° sont conservés comme instrument
de mesure, mais les pièces et trajectoires sont neuves. Les labels et états objet ne
servent qu'à l'audit et aux métriques finales.

## Scores et seuils

Score JEPA spatial:

```text
mean_MSE(pred_map, target_map) /
max(mean_MSE(pred_map, target_map) + mean_MSE(current_map, target_map), 1e-8)
```

`pixel_change` et `yaw_warp` sont des erreurs photométriques `[0,1]`. Chaque méthode,
graine, bin et strate possède son seuil: plus petit score laissant au plus 5 % des 128
contrôles strictement au-dessus. Les égalités sont non externes.

Les distributions de score, de MSE copie, les masques valides du warp et la relation
score–amplitude motrice sont exportés. Aucun diagnostic descriptif ne pèse sur une
porte.

## Hypothèses et portes

Toutes les différences sont calculées par graine après moyenne des six bins. Les bins
favorables sont les différences moyennes inter-graines strictement positives.
`learning/paired_stats.py` est utilisé avec tests exacts à n=16, IC BCa 95 % à 10 000
rééchantillonnages, graine `2026072601`, signes, `dz` et rank-bisériale.

### REF2-H1 — transport du mouvement propre

Sur `moving_self_test`, l'erreur de `transport_jepa` est inférieure séparément à
`concat_relative_jepa` et `no_command_jepa` d'au moins `0,03`; borne BCa basse
positive sur les différences contrôle−transport, p exacte corrigée et `≥5/6` bins.

### REF2-H2 — externe pur dans une strate calibrée

Avec seuil `static_calibration`, `transport_jepa` atteint TPR `≥0,85` sur
`external_only` et dépasse chaque contrôle (`concat_relative_jepa`,
`no_command_jepa`, `pixel_change`, `yaw_warp`) d'au moins `0,10`, avec borne BCa basse
positive, p corrigée et `≥5/6` bins.

### REF2-H3 — externe sous mouvement simultané

Avec seuil `moving_self_calibration`, `transport_jepa` atteint TPR `≥0,70` sur `mixed`
et dépasse séparément les quatre contrôles d'au moins `0,10`, avec borne BCa basse
positive, p corrigée et `≥5/6` bins.

### REF2-H4 — spécificité transférée

Pour `transport_jepa`:

- FPR `moving_self_test` globale `≤0,07`, aucune moyenne de bin `>0,10`;
- FPR `static_test` globale `≤0,07`, aucune
  moyenne de bin `>0,10`.

### REF2-H5 — utilisation causale de la commande

À modèle `transport_jepa` gelé, permuter les séquences de commandes entre paires du
même bin et de même amplitude augmente l'erreur `moving_self_test` d'au moins `0,03`.
Le signe de commande inversé produit le même effet. Les deux comparaisons exigent borne
BCa basse positive, p corrigée et `≥5/6` bins.

Les douze tests de supériorité H1/H2/H3/H5 partagent une correction Holm commune.
Toutes les portes sont conjonctives.

## Gardes obligatoires

- **Apprenant:** baisse d'erreur `learner_validation ≥20 %` pour les trois conditions.
- **Action utile exportée:** variance intra-bin de la commande relative strictement
  positive dans toutes les banques mobiles; minimum, moyenne et maximum exportés.
- **Indépendance:** `|corr(commande relative, déplacement objet)| ≤0,05` dans corpus et
  `mixed`; RNG disjoints et tête constante dans `external_only`.
- **Visibilité:** effet contrefactuel objet `≥0,05` par bin au smoke.
- **Domaine:** digests des calendriers et égalité exacte des multiensembles moteur par
  bin confirment l'appariement calibration/test/mixed; toute divergence est un arrêt
  d'intégrité, pas une covariable post hoc.
- **Fuite:** zéro collision corpus↔banques et zéro collision entre banques sur le smoke
  **et les graines réservées**; la vérification SHA-256 est exportée pour chaque graine.
- **Équité:** digests d'initialisation et d'ordre de batchs, capacité, corpus, banques,
  budgets et temps exportés pour les trois conditions.
- **Warp:** intrinsics, masque valide et transformation recomputables hors ligne.
- **Budget:** préparation, entraînement et évaluation inclus dans le plafond.

Toute garde échouée rend la campagne non interprétable. Aucune correction sur les
graines réservées n'est permise.

## Règles de décision et portée

- H1–H5 et toutes les gardes passent: proposer le transport spatial comme mécanisme
  minimal de réafférence, sous réserve d'une revue contradictoire des résultats.
- H1 ou H5 échoue: le mécanisme n'utilise pas causalement la commande; aucune
  revendication de copie d'efférence.
- H2 ou H3 échoue: aucune détection externe opérationnelle.
- H4 échoue: seuil non transférable; rejet.
- `yaw_warp` ou une autre baseline égale/bat transport sur H2/H3: complexité non payée.
- Quel que soit le verdict, REF-002 clôt cette variante. Toute suite exige hypothèse,
  fichier, monde et graines neufs.

## Séquence

1. Revue contradictoire pré-calcul du présent fichier.
2. Intégration additive des corrections bloquantes éventuelles.
3. Implémentation et 193+ tests, sans graine réservée.
4. Smoke complet 13991, incluant projection temporelle et toutes les gardes.
5. Campagne 13301..13316 uniquement après smoke vert.
6. Analyse complète et seconde revue contradictoire avant toute promotion.

Simulation uniquement sous D-008; aucune action physique, aucun flash et aucun achat.

## Amendements pré-calcul C1–C8

Date d'intégration: 2026-07-26. Source:
`docs/research/reafference_002_review.md`, verdict
`AUTORISER AVEC CORRECTIONS BLOQUANTES`.

Les amendements suivants sont additifs, gelés avant code et prévalent sur toute clause
antérieure incompatible. Aucun smoke, rendu, entraînement, calcul scientifique ni graine
`13301..13316` n'a été ouvert pour les choisir.

### C1 — suppression du contrôle strictement statique

`static_calibration` et `static_test` sont remplacées par
`micro_self_calibration` et `micro_self_test`. Dans ces deux banques:

- l'objet reste immobile;
- chaque paire applique une commande relative non nulle de valeur absolue `2°`;
- les signes sont équilibrés `64/64` dans chaque bin;
- horizons `1..5`, angles de départ et contextes sont équilibrés et consignés;
- les espaces de pièces et RNG sont disjoints entre calibration et test.

Le score spatial normalisé reste unique dans toutes les banques. Toute banque de
calibration doit avoir `MSE(copie) > 0` pour chaque paire; minimum, médiane et maximum
sont exportés. Une valeur nulle ou non finie est un arrêt d'intégrité.

`external_only` conserve une tête strictement immobile. Son seuil descriptif provient
de `micro_self_calibration`, mais cette comparaison est explicitement hors domaine
moteur et ne porte aucune revendication ni porte de promotion.

### C2 — H2 devient un contrôle descriptif

`REF2-H2` est retirée des portes et renommée **SANITY-EXTERNAL**:

- la TPR absolue de chaque méthode sur `external_only`, avec les seuils descriptifs
  ci-dessus, est exportée;
- l'effet contrefactuel pixel objet doit rester `≥0,05` par bin au smoke;
- aucun test de supériorité H2 n'entre dans Holm;
- aucune valeur `external_only` ne peut être citée comme soutien partiel à une
  revendication de réafférence.

`REF2-H3` sur `mixed` devient l'unique porte de détection externe. Un échec descriptif
de SANITY-EXTERNAL signale une manipulation ou un détecteur défaillant et rend la
campagne non interprétable, mais aucune supériorité n'y est attendue.

H4 porte désormais sur `moving_self_test` et `micro_self_test`, avec les mêmes plafonds
globaux `0,07` et par bin `0,10`. Les FPR par graine et graine×bin sont toujours
exportées, même si H4 passe.

La famille Holm commune contient huit tests: H1 contre deux contrôles, H3 contre quatre
contrôles et les deux perturbations H5 du seul `transport_jepa`.

### C3 — prédicteur analytique gelé de `yaw_warp`

`yaw_warp` ne reçoit jamais `as5600_fin`, le déplacement réalisé ni aucune mesure
postérieure à la transition. Son déplacement est produit uniquement par l'angle courant
et la séquence de commandes, avec le modèle cinématique gelé:

```text
angle_prédit_0 = angle_courant
pour chaque commande cible c_k:
    angle_prédit_{k+1} =
        angle_prédit_k + clip(c_k - angle_prédit_k, -12°, +12°)
delta_prédit = angle_prédit_h - angle_courant
```

`12° = BenchServoConfig.max_speed_deg_s × BenchConfig.control_dt = 600 × 0,02`.
Aucun coefficient n'est ajusté sur un corpus ou une banque.

Pour une image carrée `64×64`, `fx=fy=32/tan(15°)` à partir du FOV vertical gelé de
`30°`, et `cx=cy=31,5`. Le warp inverse fait tourner chaque rayon autour de l'axe
vertical par `delta_prédit`, utilise une interpolation bilinéaire, zéros hors champ et
un masque de validité recomputable. La convention de signe est figée par trois tests:
déplacement nul = identité bit à bit; yaw positif décale un repère fixe dans le sens
opposé du mouvement caméra; inversion du yaw inverse le déplacement.

Le smoke exige que l'entrée du warp soit bit-indépendante des mesures futures et
recalcule hors ligne déplacement, grille, masque et erreur. `yaw_warp` possède des
intrinsics exacts et un modèle direct gelé, asymétrie conservatrice en sa faveur. S'il
gagne, la conclusion autorisée est qu'un modèle analytique direct bat l'apprenant à ce
budget, non que tout transport spatial serait sans valeur.

### C4 — équité effective des trois apprenants

Les trois conditions utilisent un encodeur, un adaptateur moteur et un résidu
convolutionnel de mêmes formes. Aucun paramètre mort ou branche de remplissage n'est
autorisé pour égaliser artificiellement les comptes.

Le smoke exporte et exige, par graine:

1. digest bit-identique des poids initiaux de l'encodeur;
2. corpus, banques, ordre de batchs, pas, exemples-gradient et graine d'optimiseur
   identiques;
3. nombres identiques de paramètres totaux, entraînables et recevant un gradient non
   nul après un pas représentatif;
4. temps mural médian par pas sur `100` pas après `20` pas d'échauffement. Le ratio
   maximum/minimum doit être `≤1,25`; sinon l'asymétrie est bloquante et le budget doit
   être révisé avant toute graine réservée;
5. à commande relative nulle, grille de transport identité et tenseur fourni au résidu
   bit-identique à celui de `concat_relative_jepa` à canaux moteurs nuls. Tout écart est
   un arrêt d'intégrité.

L'initialisation nulle requise pour l'identité ne doit pas rendre l'adaptateur moteur
inactif: ses paramètres doivent recevoir un gradient non nul au pas représentatif.

### C5 — construction non fuitée de l'entrée motrice

Dans chacune des sept banques amendées, le tenseur moteur effectivement fourni aux
modèles est recalculé uniquement depuis:

- `as5600` de la trame de départ;
- la séquence des commandes cibles connue avant transition;
- l'horizon.

L'égalité bit à bit entre tenseur recalculé et tenseur consommé est obligatoire au
smoke et sur chaque graine. `as5600_fin`, delta réalisé et état objet restent dans
l'audit mais ne sont accessibles ni au constructeur d'entrée, ni aux apprenants, ni à
`yaw_warp`.

### C6 — diversité et disjonction des banques

Dans `micro_self_calibration` et `micro_self_test`, les paires varient par angle précis
de départ dans le bin, signe, horizon, pièce et RNG capteur/rendu. Les deux banques ont
des espaces de pièces et RNG disjoints. Les sept banques utilisent des espaces de
pièces/RNG disjoints conformément à leur rôle.

La garde SHA-256 couvre désormais:

- zéro collision corpus↔banques;
- zéro collision entre banques;
- zéro paire dupliquée à l'intérieur d'une banque;
- compte exporté de trames de départ, trames d'arrivée et paires distinctes par banque.

### C7 — H5 devient une garde de non-dégénérescence

H5 est renommée **garde de non-dégénérescence du transport**. Elle ne prouve pas un
modèle direct causal appris et ne peut pas être citée ainsi.

Pour la permutation, « même amplitude » signifie **même valeur absolue**. Dans chaque
strate `(bin, horizon, |amplitude|)`, un dérangement cyclique déterministe échange les
séquences entre contextes distincts et, lorsque les deux signes existent, avec le signe
opposé. Aucune séquence ne reste sur sa paire; le digest du mapping est exporté. Le test
d'inversion applique séparément l'opposé de la séquence propre à chaque paire.

Les deux passes sont exécutées sur les trois conditions gelées. Pour
`transport_jepa`, permutation et inversion doivent chacune augmenter l'erreur
`moving_self_test` d'au moins `0,03`, avec IC, p Holm et `≥5/6` bins: ce sont les deux
tests H5 de la famille commune. Les mêmes résultats pour `concat_relative_jepa` et
`no_command_jepa` sont descriptifs et indiquent si ces contrôles utilisent la commande.

### C8 — projection temporelle exhaustive

Le temps complet de chaque condition smoke inclut exactement quatre phases exportées
séparément:

1. préparation du monde, corpus et sept banques;
2. entraînement des `4 500` pas;
3. notation des sept banques;
4. six passes H5 contrefactuelles, deux pour chacune des trois conditions.

La projection conserve la formule gelée:

```text
48 × (temps_préparation_partagée_smoke / 3
      + moyenne_des_temps_complets_des_trois_conditions)
```

Si elle dépasse `75` minutes, le nouveau plafond, le digest du présent protocole et la
projection sont écrits dans le manifeste smoke avant toute ouverture de `13301`.
Aucun amendement n'est permis ensuite.

### Recommandations R1–R6 intégrées

- Les marges `0,03` (erreur/H5) et `0,10` (TPR) sont des choix a priori sur une
  nouvelle échelle inconnue avant calcul; aucune valeur REF-001 ne les détermine et
  aucun ajustement post hoc n'est permis.
- Les dispersions FPR par graine et graine×bin sont obligatoires.
- L'asymétrie conservatrice de `yaw_warp` et sa limite d'interprétation sont explicites
  sous C3.
- Les termes VICReg variance/covariance portent sur le vecteur `128` obtenu par moyenne
  spatiale de la carte `8×8×128`, avec la même réduction et les mêmes coefficients dans
  les trois conditions.
- L'implémentation doit conserver les `215` tests existants et ajouter ses tests REF-002
  avant smoke.
- La garde Domaine exige aussi l'égalité des multiensembles de fractions de pixels
  valides du warp entre `moving_self_calibration`, `moving_self_test` et `mixed`, par
  bin. Toute divergence est un arrêt d'intégrité.

## Décision amendée

La promotion exige conjointement H1, H3, H4, H5, SANITY-EXTERNAL et toutes les gardes.
H3 est l'unique preuve de détection externe sous mouvement propre. H1 ou H5 échoué
interdit toute revendication de copie d'efférence; H3 échoué interdit la détection
réafférente; H4 échoué invalide le transfert des seuils. Une baseline égalant ou battant
`transport_jepa` sur H3 rend la complexité non payée.

Après ces amendements, l'implémentation et le smoke `13991` sont autorisés. Les graines
`13301..13316` restent interdites jusqu'à un smoke entièrement vert, une projection
concordante et un manifeste portant le digest du protocole amendé. Toute promotion
reste interdite avant revue contradictoire des résultats.
