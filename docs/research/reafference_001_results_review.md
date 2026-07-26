# Revue contradictoire des résultats REF-001 — réafférence visuelle

Date: 2026-07-26. Revue demandée après la campagne réservée complète et avant toute
promotion ou nouvelle direction. Fichiers audités intégralement:
`docs/research/reafference_001_preregistration.md`,
`docs/research/reafference_001_review.md`,
`docs/research/reafference_001_results.md`,
`docs/research/reafference_001_analysis.json`,
`docs/research/reafference_001_evaluations.json`,
`docs/research/reafference_001_integrity.json`; en complément `learning/reafference.py`,
`scripts/research/run_reafference.py`, `learning/paired_stats.py`,
`tests/test_reafference.py`, les diffs de `sim3d/bench_model.py`, `sim3d/bench_env.py`,
`DECISIONS.md` et `PILOTAGE.md`, ainsi que les artefacts bruts de
`data/processed/experiments/reafference_001/` (corpora, banques, runs, smoke).

Aucun entraînement n'a été lancé. Aucun fichier autre que la présente revue n'a été
modifié. Aucun retuning n'est proposé sur `12301..12316`.

Méthode de recalcul: les statistiques gelées ont été **réimplémentées depuis zéro**
(énumération exhaustive des 2^16 assignations de signes, BCa 10 000 rééchantillonnages
graine `2026072002`, Holm pas-à-pas) sans importer `learning/paired_stats.py`, afin que
l'audit n'hérite pas d'un éventuel défaut du code analysé. Les seuils, TPR, FPR, bins
favorables et budgets ont été recalculés depuis les 16 évaluations par graine; les
gardes structurelles ont été revérifiées directement sur les banques et corpus stockés.

## Verdict

**AUTORISER AVEC CORRECTIONS.** La campagne est intègre, le recalcul indépendant est
identique aux exports au chiffre près, les portes ont été appliquées exactement comme
gelées, et le verdict mécanique négatif est correct et non ambigu. Les corrections
demandées sont **exclusivement documentaires**: elles portent sur la manière dont deux
résultats sont formulés dans le dossier de clôture, sur trois faits d'audit à consigner,
et sur aucune donnée, aucun seuil et aucune graine.

**REF-001 ne peut pas être promu comme détecteur minimal de réafférence.** La
revendication exige conjointement l'explication de l'ego-motion et la détection externe;
aucune des deux n'est établie, et l'écart aux portes n'est pas marginal.

## 1. Reproductibilité du recalcul — identique au chiffre près

Recalcul indépendant depuis `reafference_001_evaluations.json`, comparé aux exports:

| Quantité | Recalcul | Export | Écart |
|---|---|---|---|
| H1 moyenne, IC BCa, p exacte, différences de bin, 16 valeurs | identiques | identiques | `0` |
| 6 comparaisons: moyennes, IC BCa, p exactes, p Holm, bins favorables, verdicts | identiques | identiques | `0` |
| TPR absolues `external_only` / `mixed` | identiques | identiques | `0` |
| H4: 6 FPR de bin, FPR globale, max de bin | identiques | identiques | `0` |
| 384 seuils (4 méthodes × 6 bins × 16 graines) | identiques | identiques | `0` |
| Temps mural cumulé `1908,041 s` | identique | identique | `0` |

La famille Holm compte bien **six** membres, conformément à C1, et non quatre. La graine
BCa `2026072002` est effectivement celle qui reproduit les intervalles publiés. Les p
exactes sont bien exactes à n=16: la plus petite valeur observée, `1,5259e-05`, vaut
exactement `2^-16`, ce qui confirme l'énumération complète et non un Monte-Carlo.

`193 tests` passent, revérifiés dans le venv du projet.

## 2. Gel du protocole — vérifié cryptographiquement

- Le SHA-256 du pré-enregistrement consigné par le smoke,
  `d4b864c8…0dc7c5b`, est **identique octet pour octet** au fichier actuel. Le protocole
  n'a donc pas bougé entre le smoke, l'ouverture des graines et aujourd'hui.
- Le diff du pré-enregistrement est strictement **additif**: en-tête daté + amendements
  C1–C5. Aucune hypothèse, aucun seuil, aucune graine, aucun budget d'origine n'a été
  retouché.
- `spec_digest = 4813a377…7137a14` est identique dans le smoke, les 32 runs, l'export
  d'intégrité, et recalculé depuis `RefSpec()` dans le code actuel. Le code n'a pas été
  modifié après les runs.
- Les modifications de monde (`bench_model.py`, `bench_env.py`) sont additives et
  conditionnées par `reafference_object=False` par défaut: aucune campagne antérieure
  n'est perturbée.

## 3. H1 — explication de l'ego-motion: échec net, direction inversée

| Critère | Exigé | Obtenu |
|---|---|---|
| moyenne `no_action − action` | `≥0,05` | **`−0,001825`** |
| borne BCa basse | `>0` | `−0,006658` (IC `[−0,006658; +0,002865]`) |
| p exacte unilatérale | `≤0,05` | `0,757141` |
| bins favorables | `≥5/6` | **`2/6`** |
| signes | — | `6+ / 10−` |

Les quatre critères échouent, et la direction est **nominalement en faveur du JEPA sans
action**. Comme les deux conditions partagent par graine l'initialisation, le corpus,
les banques, l'ordre de batchs, la capacité (`1 219 171` paramètres) et le budget
(`4 500` pas, batch `256`), et ne diffèrent que par la mise à zéro du vecteur d'action,
c'est une nulle propre: **dans ce monde et à ce budget, le vecteur d'action n'apporte
aucune information exploitable sur le changement visuel auto-produit.** L'ampleur
(`dz = −0,18`) est celle d'un bruit, pas d'un effet inversé réel.

## 4. H2 / H3 — détection externe: échec sur toutes les portes qui pèsent

### TPR absolues — l'écart n'est pas marginal

| Banque | Exigé | Obtenu | Graines atteignant la porte |
|---|---|---|---|
| `external_only` | `≥0,75` | `0,370768` (étendue `0,165`–`0,615`) | **`0/16`** |
| `mixed` | `≥0,70` | `0,142660` (étendue `0,095`–`0,286`) | **`0/16`** |

En externe pur le détecteur atteint la moitié du plancher exigé; en mixte, le cinquième.
Aucune graine n'approche la porte. Il n'y a ici aucune décision limite à arbitrer.

### Six comparaisons de supériorité sous Holm commun

| Comparaison | moyenne | IC BCa 95 % | p Holm | bins | verdict |
|---|---|---|---|---|---|
| externe vs `no_action_jepa` | `+0,029622` | `[−0,021647; +0,081062]` | `0,586182` | `5/6` | échec |
| externe vs `pixel_change` | `+0,370768` | `[+0,310744; +0,428885]` | `9,1553e-05` | `6/6` | passe |
| externe vs `pixel_change_action` | `+0,363607` | `[+0,305548; +0,418063]` | `9,1553e-05` | `6/6` | passe |
| mixte vs `no_action_jepa` | `−0,001139` | `[−0,028971; +0,019531]` | `0,878937` | `4/6` | échec |
| mixte vs `pixel_change` | `+0,003418` | `[−0,029378; +0,051270]` | `0,878937` | `4/6` | échec |
| mixte vs `pixel_change_action` | `+0,022135` | `[−0,011393; +0,067220]` | `0,586182` | `4/6` | échec |

H2 et H3 sont donc faux, chacun pour deux raisons indépendantes (TPR absolue et
supériorité face au contrôle de même capacité).

### Correction 1 — les deux comparaisons qui « passent » sont vides par construction

C'est le point d'audit le plus important de cette revue, et il va **contre** la lecture
la plus favorable au candidat.

Sur `external_only`, `pixel_change` obtient une TPR de **exactement `0,0000` dans les six
bins et les seize graines** — zéro détection sur `12 288` paires — et
`pixel_change_action` obtient `0,00716`. La cause est structurelle: les seuils sont
calibrés sur `self_calibration`, où la tête bouge de 3 à 10° et où le seuil pixel moyen
vaut `0,267`–`0,318`; ils sont ensuite appliqués à `external_only`, où la tête est tenue
constante par construction et où l'amplitude pixel brute ne peut mécaniquement pas
atteindre ce niveau. L'AUC descriptive de `pixel_change` en externe pur vaut `0,063`,
c'est-à-dire massivement **sous** le hasard: le score pixel y est systématiquement plus
bas que sur `self_test`, ce qui est la signature d'un décalage de domaine, pas d'une
comparaison de compétence.

Le score JEPA `pred/(pred+copie)` est borné et normalisé, donc insensible à ce
changement d'échelle; ses seuils (`0,465`–`0,513`) transfèrent. L'asymétrie joue en
faveur d'`action_jepa` et ne peut donc pas fabriquer un faux échec — mais elle rend les
deux comparaisons pixel en externe pur **non informatives**. Elles mesurent la fragilité
hors domaine d'une baseline non bornée, pas une compétence du résidu d'action.

Conséquence documentaire: la phrase « L'action bat les deux baselines pixel en externe
pur » (D-015, `PILOTAGE.md`, et implicitement le tableau de `reafference_001_results.md`)
est littéralement vraie au sens des portes gelées, mais ne doit jamais être citée comme
soutien partiel à la réafférence. Elle doit être accompagnée du fait que la TPR pixel y
vaut zéro par décalage de domaine.

À l'inverse, sur `mixed` — la seule banque où la tête et l'objet bougent tous deux et où
la baseline pixel est **dans son domaine de calibration** — `pixel_change` atteint
`0,139242` contre `0,142660` pour `action_jepa`: statistiquement indiscernables
(`p Holm = 0,878937`, IC contenant zéro). La règle gelée « pixel égale ou bat action: la
complexité JEPA n'est pas payée; aucune promotion » est donc déclenchée de manière
autonome, indépendamment de l'échec des TPR absolues.

## 5. H4 — spécificité: échec par le plafond de bin, et instabilité inter-graines

| Critère | Exigé | Obtenu |
|---|---|---|
| FPR globale `self_test` | `≤0,07` | `0,063721` — **passe** |
| max des FPR moyennes de bin | `≤0,10` | **`0,118652`** (bin 4, centre 100°) — échec |

FPR moyennes par bin: `[0,062988; 0,076172; 0,035156; 0,061523; 0,118652; 0,027832]`.

### Correction 2 — l'échec H4 est partiel et son instabilité doit être consignée

`reafference_001_results.md` réduit H4 à `False`, et D-015 mentionne correctement le
bin fautif. Il manque toutefois deux faits que la clôture doit porter, sous peine de
laisser croire que la spécificité était « presque bonne »:

- **`5/16` graines dépassent la FPR globale de `0,07`**, dont une à `0,1797`
  (graine 12313).
- **`16/96` cellules graine×bin dépassent `0,10`**, avec un maximum à `0,5234`.

Le seuil est pourtant parfaitement calibré: la FPR de calibration vaut exactement
`6/128 = 0,046875` pour chaque méthode, chaque bin et chaque graine, conforme au `≤0,05`
par construction. L'excès sur `self_test` est donc un authentique **défaut de
généralisation du seuil d'une banque propre à l'autre**, pas un défaut d'implémentation.
Le détecteur n'est pas seulement faible: sa spécificité ne transfère pas de façon stable.

## 6. Diagnostics petit-changement (C3) — la crainte pré-calcul est levée

La revue pré-calcul redoutait que `MSE(copie) → 0` sur les banques propres pousse les
seuils vers 1 et écrase mécaniquement les TPR, rendant un échec H2/H3/H4 inattribuable.
Les diagnostics gelés réfutent ce scénario:

| Banque | médiane des médianes `MSE(copie)` (action / no_action) | minimum sur 96 bins |
|---|---|---|
| `self_calibration` | `1,631` / `1,708` | `0,075` / `0,090` |
| `self_test` | `1,686` / `1,728` | `0,102` / `0,160` |
| `mixed` | `1,705` / `1,747` | `0,043` / `0,033` |
| `external_only` | `1,101` / `1,159` | `0,000` / `0,000` |

Les banques propres ne s'approchent jamais du régime dégénéré, et les seuils se situent
autour de `0,47`–`0,51`, c'est-à-dire au voisinage de la valeur « prédiction ≈ copie »
(`0,5`), et non près de `1`. **Les échecs H2/H3/H4 sont donc attribuables à une absence
réelle de séparation, pas à la saturation du score borné.** C'est exactement ce que C3
devait garantir, et il le garantit: l'échec est non ambigu.

Seule `external_only` présente des minima de `MSE(copie)` exactement nuls dans `4` bins
sur `96`. Ces paires obtiennent un score de `1` et sont comptées comme détections, ce qui
gonfle très légèrement la TPR d'`action_jepa` — biais orienté **en faveur** du candidat,
et sans portée face à un déficit de `0,38` sur la porte.

L'AUC descriptive confirme la lecture sans se substituer aux portes: `action_jepa`
`0,7655` en externe pur et `0,5217` en mixte; `no_action_jepa` `0,7396` et `0,5030`. Il
existe un signal faible mais réel sur le changement externe pur, essentiellement
indépendant de la fourniture de l'action (`+0,026` d'AUC), et rien d'exploitable sous
mouvement simultané.

## 7. Gardes — toutes tenues, avec une exception quantifiée et non décisionnelle

- **Apprenant.** `32/32` runs, réduction relative `0,5321`–`0,6056`, très au-dessus du
  `0,20` exigé. Recalculée depuis `initial`/`final`, cohérente à `1e-12`. Les deux
  conditions apprennent réellement; l'échec n'est pas un échec d'entraînement.
- **Indépendance.** Corpus: `|r| ≤ 0,031751`; `mixed`: `|r| ≤ 0,044807`; toutes `≤0,05`.
  Tête constante sur `external_only` revérifiée directement sur les banques des 16
  graines: `0` delta de tête non nul sur `24 576` paires. Domaine conforme à C2.
- **Visibilité.** Contrefactuel objet figé au smoke: `0,2110`–`0,2235` selon les bins,
  soit plus de quatre fois le plancher `0,05`. L'objet est incontestablement visible;
  l'échec de détection n'est pas un échec de manipulation.
- **Équité.** Sur les 16 graines: digest d'initialisation, digest d'ordre de batchs,
  SHA-256 du corpus et des cinq banques **identiques entre conditions**; capacité
  `1 219 171` sur les 32 runs; `4 500` pas, batch `256`, `1 152 000` exemples-gradient
  partout; passe avant à actions nulles bit-identique au smoke. Les 16 digests
  d'initialisation et les 16 corpus sont bien distincts entre graines. L'ablation est
  propre.
- **Budgets.** `12 000` images, `2 400` décisions, `768` paires par banque
  (`128 × 6`), équilibre `64/64` par contexte: exact sur toutes les banques des 16
  graines, revérifié depuis les fichiers.
- **Seuils recomputables.** Les `384` seuils sont exactement reproduits depuis les scores
  bruts `self_calibration` exportés. C4-iii est satisfait sur la campagne, pas seulement
  au smoke.

### Correction 3 — une collision d'image à consigner

La vérification de non-fuite au niveau image, que le runner n'exécutait qu'au smoke
`12991`, a été refaite ici sur les 16 graines réservées par hachage SHA-256 de chaque
trame:

- **Le corpus est disjoint des cinq banques sur les 16 graines**, sans exception. C'est
  la disjonction qui pourrait biaiser une porte, et elle tient parfaitement.
- **Une seule collision existe, entre deux banques tenues à part**: graine `12312`, trame
  de départ n° 34 de `external_only` (bin 0, contexte 0) identique à une trame de
  `learner_validation`. Une paire sur `24 576`, sur une graine sur seize.

Portée: nulle sur les portes. `learner_validation` ne sert qu'à la garde apprenant et ne
partage aucune métrique avec `external_only`; aucune donnée d'entraînement n'est
concernée. Ce fait doit néanmoins figurer au dossier comme exception connue et chiffrée
à la formulation « banques/corpus disjoints », et **ne justifie ni reprise, ni
correction, ni réouverture de graine.**

### Correction 4 — la garde « action utile » n'a pas de trace numérique

Le pré-enregistrement exige une variance d'action non nulle dans chaque bin de
`self_calibration`, `self_test` et `mixed`. Cette garde est bien satisfaite — je l'ai
vérifiée a posteriori sur les banques: variance intra-bin minimale de l'angle cible
appliqué `10,13` / `10,25` / `10,12` deg² respectivement, jamais nulle — mais elle est
seulement **structurelle** dans le code et n'apparaît dans aucun export, contrairement
aux gardes apprenant et indépendance. À consigner comme dette de traçabilité pour les
protocoles suivants de cette famille, sans effet rétroactif.

## 8. Plafond au smoke — C5 n'a pas été déclenché

| Grandeur | Valeur |
|---|---|
| temps partagé du smoke | `48,145 s` |
| temps moyen par condition | `34,948 s` |
| projection `32 × (48,145/2 + 34,948)` | `1 888,646 s` = **`31,48 min`** |
| plafond initial | `3 600 s` = `60 min` |
| plafond effectif | `3 600 s`, **non amendé** |
| campagne consignée | `1 908,041 s` = **`31,80 min`** |

### Correction 5 — vocabulaire et périmètre de la comptabilité

La demande de revue parle du « plafond amendé au smoke ». Il faut consigner que **la
clause d'amendement C5 n'a pas été déclenchée**: la projection tenant sous 60 minutes, le
plafond effectif est resté le plafond initial. `amended = false`. La formule a été
revérifiée et la projection est fidèle à `0,3 %` près du temps réel — la leçon de D-012
a été correctement convertie en porte et la porte a fonctionné.

Point mineur à mentionner: `completed_campaign_seconds()` additionne la préparation par
graine et les deux runs d'entraînement, mais **pas** le temps d'`evaluate_seed`. Les
`31,80 min` consignées sous-estiment donc légèrement le mur réel. Avec `28 min` de marge
sous le plafond, cela ne peut rien changer; l'assiette doit simplement être énoncée.

## 9. Explication de l'ego-motion contre détection externe

Le pré-enregistrement (R5, et la clause « Portée ») exige que les deux soient distinguées.
Elles le sont, et elles échouent séparément:

- **Explication de l'ego-motion (H1): non démontrée.** Avantage `−0,001825`, direction
  nominalement inverse, `p = 0,757`. Conditionner par l'action ne réduit pas l'erreur de
  prédiction sur le mouvement propre face à un jumeau de capacité identique.
- **Détection externe (H2–H4): non démontrée.** TPR `0,371` contre `0,75` en externe pur,
  `0,143` contre `0,70` en mixte, avantage non significatif (`+0,030`) puis nul
  (`−0,001`) face au contrôle, spécificité en échec sur le plafond de bin.
- **Réafférence: non démontrée**, puisqu'elle exige conjointement les deux, et
  qu'aucune n'est acquise. Aucune revendication partielle n'est disponible non plus.

Ce qui peut être affirmé sans excès: à `n=16`, `4 500` pas et dans ce monde, le résidu
borné d'un JEPA porte un signal faible mais supérieur au hasard sur le changement externe
**pur** (AUC `≈ 0,77`, TPR `≈ 0,37` à un seuil auto-calibré à 5 %), que l'action soit
fournie ou non; et il ne porte pratiquement rien lorsque mouvement propre et mouvement
externe coexistent (AUC `≈ 0,52`). Le résultat négatif porte sur **le conditionnement par
l'action**, pas sur les résidus JEPA en général — et il est informatif précisément parce
que le dispositif apparié est irréprochable.

## 10. Réponse aux questions posées

- **Verdict:** AUTORISER AVEC CORRECTIONS (documentaires uniquement).
- **REF-001 peut-il être promu comme détecteur minimal de réafférence?** **Non.** H1, H2,
  H3 et H4 échouent tous; deux règles de décision indépendantes interdisent la promotion
  (« H1 échoue » et « pixel égale ou bat action » sur `mixed`); l'écart aux portes n'est
  ni marginal ni attribuable à un artefact de mesure.
- **Retuning sur `12301..12316`:** aucun n'est proposé et aucun n'est autorisé. La
  variante est close conformément à la clause de clôture. Toute reprise exige une
  hypothèse, un fichier et des graines neufs.

## Corrections demandées

Toutes portent sur le dossier de clôture. Aucune ne touche une donnée, un seuil ou une
graine; aucune ne requiert le moindre calcul.

1. **Vacuité des comparaisons pixel en externe pur.** Consigner dans D-015,
   `PILOTAGE.md` et `reafference_001_results.md` que `pixel_change` obtient une TPR de
   `0,0000` sur `external_only` par décalage de domaine (seuil calibré tête mobile,
   banque tête tenue, AUC `0,063`), que les deux comparaisons « passées » sont donc non
   informatives, et qu'en `mixed` — seul régime où la baseline est dans son domaine —
   `pixel_change` (`0,1392`) égale `action_jepa` (`0,1427`).
2. **Nature de l'échec H4.** Consigner que la FPR globale `0,063721` respecte le plafond
   et que seul le plafond par bin échoue, en y ajoutant l'instabilité: `5/16` graines
   au-dessus de `0,07` (max `0,1797`) et `16/96` cellules au-dessus de `0,10`
   (max `0,5234`).
3. **Collision d'image.** Consigner l'unique collision `external_only` /
   `learner_validation` sur la graine `12312` (1 paire sur `24 576`), et le fait que la
   disjonction corpus↔banques — la seule susceptible de biaiser une porte — tient sur les
   16 graines.
4. **Traçabilité de la garde « action utile ».** Consigner qu'elle est structurelle et
   sans export chiffré, et l'exporter comme les autres gardes dans les protocoles
   suivants.
5. **Plafond et assiette temporelle.** Écrire que C5 n'a pas été déclenché
   (`amended = false`, plafond effectif = plafond initial de 60 min) et que les
   `31,80 min` consignées excluent le temps d'évaluation.

## Ce que la clôture établit

REF-001 est un résultat négatif **propre**, ce qui est rare et a de la valeur. Le
protocole a été gelé puis vérifié cryptographiquement, la porte de faisabilité issue de
D-012 a fonctionné du premier coup, l'ablation apparié est bit-à-bit équitable, les
diagnostics C3 ont permis d'attribuer l'échec à une absence réelle de séparation plutôt
qu'à une métrique dégénérée, et la baseline C1 a empêché une conclusion « complexité
payée » qui aurait été invalide. Les cinq corrections pré-calcul ont toutes servi.

La conclusion à retenir pour la suite: dans ce contraste, la copie d'efférence ne
s'obtient pas gratuitement en branchant le vecteur d'action sur un prédicteur latent. Ce
constat oriente une éventuelle hypothèse future — qui devra être neuve, pré-enregistrée
et sur graines vierges — sans rien devoir aux graines `12301..12316`.
