# Pré-enregistrement REF-001 — réafférence visuelle et changement externe

Date de gel: 2026-07-20, avant implémentation et tout calcul. Filiation: étape 3 de
`CODEX_TASK_BRIEF.md`, D-012 et D-013. Aucun monde, artefact ou graine décisionnelle de
TV-001, J6-R001 ou J6-AR001 n'est réutilisé pour régler ce protocole.

## Question

Après apprentissage sur un objet parfois mobile indépendamment de la tête, le résidu de
prédiction d'un JEPA conditionné par l'action peut-il:

1. expliquer les changements visuels auto-produits par le mouvement de tête;
2. rester élevé lorsqu'un objet change indépendamment;
3. détecter ce changement externe mieux qu'un JEPA de même capacité sans action et
   qu'un score pixel brut?

La revendication est opérationnelle: **réafférence = résidu faible sur mouvement propre
seul et résidu discriminant sur mouvement externe**, sans fournir au modèle l'état ou
le label de l'objet. Elle ne revendique ni segmentation d'objet ni causalité générale.

## Hypothèses gelées

- **REF-H1 — explication du mouvement propre:** sur la banque tenue à part `self_test`,
  `action_jepa` réduit l'erreur bornée moyenne d'au moins `0,05` face à
  `no_action_jepa`, avec borne BCa basse positive, test exact significatif et `5/6`
  bins favorables.
- **REF-H2 — détection externe pure:** au seuil calibré à FPR `≤0,05` sur une banque
  `self_calibration` séparée, `action_jepa` atteint TPR `≥0,75` sur `external_only` et
  dépasse séparément `no_action_jepa` et `pixel_change` d'au moins `0,10` de TPR.
- **REF-H3 — détection sous mouvement mixte:** au même seuil, `action_jepa` atteint TPR
  `≥0,70` sur `mixed` et dépasse les deux baselines d'au moins `0,10`.
- **REF-H4 — spécificité tenue à part:** sur `self_test`, distincte de la calibration,
  FPR globale `≤0,07` et aucune FPR de bin `>0,10` pour `action_jepa`.

La promotion exige H1–H4 et toutes les gardes. Une AUC descriptive élevée ne remplace
jamais les portes TPR/FPR au seuil tenu à part.

## Graines, conditions et budget

- Smoke hors protocole: `12991`, sans rôle décisionnel.
- Campagne: graines vierges `12301..12316`, 16 paires apprenantes.
- Deux conditions apprenantes: `no_action_jepa`, `action_jepa`.
- Baseline analytique obligatoire: `pixel_change`, calculée sur les mêmes paires; elle
  reçoit les mêmes images et actions mais n'utilise volontairement pas l'action.
- Corpus partagé bit à bit: 20 épisodes de 600 images à 10 Hz, soit 12 000 images et
  2 400 décisions par condition apprenante.
- Entraînement égal: exactement 4 500 pas AdamW, batch 256, soit 1 152 000
  exemples-gradient par condition. Même architecture et nombre de paramètres; dans
  `no_action_jepa`, l'entrée action est remplacée par zéro sans retirer de capacité.
- Plafond: 32 runs apprenants et 60 minutes GPU murales cumulées. Runner résumable au
  niveau run, keep-awake et arrêt technique sur divergence ou plafond.

Le score pixel n'utilise aucun entraînement et ne reçoit donc pas un budget qui pourrait
le défavoriser; c'est une baseline simple stricte. Les conclusions architecturales
primaires opposent les deux JEPA à calcul et capacité identiques.

## Monde et objet externe

Le jumeau de tête observe une pièce neuve REF, sans ceinture D/E/F. Un objet physique
MJCF très visible se déplace sur un rail horizontal indépendamment de la commande servo.
Sa trajectoire est générée par un RNG distinct de celui du babbling et n'est jamais une
fonction de l'action de tête.

Le corpus d'entraînement contient, par épisodes tirés avant collecte:

- 50 % d'épisodes où l'objet reste immobile;
- 50 % où sa vitesse et ses changements de direction sont aléatoires et indépendants.

Ce drapeau, la position, la vitesse et le RNG de l'objet ne sont enregistrés que dans
le manifeste d'audit physique. Ils ne sont jamais des entrées du JEPA, d'une sonde ou
d'une règle d'entraînement. Les deux conditions voient exactement les mêmes pixels,
actions et ordre de batchs par graine.

## Banques tenues à part

Chaque graine possède cinq banques issues de pièces, trajectoires et espaces de graines
disjoints du corpus et entre eux. Chaque banque contient 128 paires par bin structuré,
équilibrées 64/64 par contexte visuel:

1. `self_calibration`: objet immobile, tête mobile; fixe le seuil de chaque méthode/bin;
2. `self_test`: objet immobile, tête mobile; mesure la spécificité sans réutiliser la
   calibration;
3. `external_only`: tête tenue à l'angle du bin, objet mobile;
4. `mixed`: tête et objet mobiles indépendamment;
5. `learner_validation`: mélange sans labels utilisé uniquement par la garde apprenant.

Les labels `self_only`, `external_only` et `mixed` viennent du simulateur et servent
uniquement au calcul final des métriques. Ils ne pilotent ni l'entraînement, ni une
sélection de checkpoint, ni un hyperparamètre. Les banques ne sont jamais entraînées.

Le smoke asserte: objet vrai geom/joint MJCF; mouvement objet bit-identique entre
conditions et indépendant des actions; déplacement visible normalisé `≥0,05` face au
contre-factuel objet figé dans chacun des six bins; espaces de graines et images
disjoints; 128 paires/bin; corpus et budgets exacts; aucune colonne objet/label transmise
aux modèles.

## Modèles et scores

Les deux JEPA reprennent v3: images 64×64, largeur 32, latent 128, prédicteur 512,
horizons 1..5, stop-gradient, variance/covariance et AdamW `3e-4`/`1e-4`.

Initialisation encodeur/prédicteur/sondes et ordre de batchs identiques par graine. La
seule différence est `use_action=True` ou `False`; la branche sans action remplace le
vecteur par zéro dans un prédicteur de capacité identique.

Score JEPA par paire:

```text
score = MSE(prediction, cible) / max(MSE(prediction, cible) + MSE(copie, cible), 1e-8)
```

Score analytique:

```text
pixel_change = mean(abs(frame_next - frame_current)) / 255
```

Pour chaque graine, méthode et bin, le seuil est le plus petit score tel qu'au plus 5 %
des 128 observations `self_calibration` le dépassent. Les égalités sont classées
non-externes (`score > seuil` détecte). Le seuil est figé puis appliqué sans changement
à `self_test`, `external_only` et `mixed`.

## Métriques

- erreur bornée moyenne `self_test` par méthode JEPA, graine et bin;
- TPR `external_only` et `mixed` par méthode, graine et bin;
- FPR `self_test` par méthode, graine et bin;
- AUC ROC descriptive sur `self_test` contre chaque banque externe;
- différences appariées de TPR `action − no_action` et `action − pixel`;
- erreurs initiales/finales sur `learner_validation`, pertes, probes, budgets, digests et
  temps mural;
- corrélation descriptive entre amplitude d'action et score sur `self_test`, afin de
  vérifier que le résidu action ne croît pas simplement avec l'ego-motion.

## Statistiques et portes

`learning/paired_stats.py` est utilisé exclusivement. Tests exacts par retournement de
signes, IC BCa 95 % à 10 000 rééchantillonnages avec graine `2026072002`, signes, `dz`,
rank-bisériale; n=16.

### REF-H1

Par graine, moyenne des six différences d'erreur
`no_action_jepa − action_jepa`. Porte: moyenne `≥0,05`, borne BCa basse `>0`, p exacte
`≤0,05`, au moins `5/6` différences moyennes de bin positives.

### REF-H2 et REF-H3

Par graine, TPR agrégée par moyenne des six bins. Quatre comparaisons de supériorité:
action−no_action et action−pixel sur `external_only`, puis sur `mixed`. Chacune exige
moyenne `≥0,10`, borne BCa basse `>0`, et p exacte après une correction Holm commune
aux quatre p `≤0,05`. En plus, la TPR absolue action moyenne doit atteindre `0,75` en
external et `0,70` en mixed; `≥5/6` bins sont favorables face à chaque baseline.

### REF-H4

FPR action sur `self_test`, moyenne sur graines et bins, `≤0,07`; maximum des six FPR
moyennes de bin `≤0,10`. La FPR de calibration est rapportée et doit être `≤0,05` par
construction, sans être réutilisée comme test.

## Gardes

- **Apprenant:** l'erreur bornée moyenne de `learner_validation` baisse d'au moins 20 %
  entre initialisation et fin pour les deux JEPA.
- **Action utile:** la variance des actions est non nulle dans chaque bin de
  `self_calibration`, `self_test` et `mixed`; sinon H1/H3/H4 sont non interprétables.
- **Objet visible:** l'amplitude pixel externe tenue à part passe la construction smoke
  dans les six bins; jamais calibrée sur les graines réservées.
- **Indépendance:** corrélation absolue action–déplacement objet `≤0,05` dans le corpus et
  les banques externes; échec = campagne non interprétable.
- **Aucune fuite:** labels et état objet absents des tenseurs modèle; banques/corpus
  disjoints; seuils issus exclusivement de `self_calibration`.
- **Équité:** corpus, initialisation, ordre de batchs, paramètres, gradients et banques
  identiques hors mise à zéro de l'action; digests consignés.
- **Budget/plafond:** divergence = arrêt technique, aucune analyse partielle.

## Règles de décision

- **H1–H4 et toutes les gardes passent:** proposer le résidu `action_jepa` comme
  détecteur minimal de changement externe/réafférence, sous réserve de la revue Claude
  des résultats.
- **H1 échoue:** l'action n'explique pas mieux l'ego-motion; aucune revendication de
  réafférence, même si la détection externe est élevée.
- **H2 ou H3 échoue:** le résidu ne sépare pas assez l'externe des baselines; aucune
  promotion.
- **H4 échoue:** le détecteur confond encore mouvement propre et externe; rejet.
- **Pixel égale ou bat action:** la complexité JEPA n'est pas payée; aucune promotion.
- **Garde apprenant, indépendance, visibilité, fuite, équité ou budget échoue:** résultat
  non interprétable ou arrêt technique; aucune correction sur ces graines.
- Toute reprise exige nouvelle hypothèse, nouveau fichier et graines vierges.

## Séquence

1. Revue contradictoire du présent pré-enregistrement avant code.
2. Après corrections autorisées: implémentation, 181+ tests et smoke 12991.
3. Ouverture de 12301..12316 uniquement après smoke vert et manifeste concordant.
4. Analyse complète, export auditable et seconde revue Claude avant promotion.

Simulation uniquement sous D-008; aucune action physique, aucun achat, aucun flash.
