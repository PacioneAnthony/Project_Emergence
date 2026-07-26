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
