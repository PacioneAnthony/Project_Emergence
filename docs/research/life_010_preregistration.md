# LIFE-010 — curriculum appris pour une dynamique plastique protégée

Date: 2026-07-27
Statut: close comme non-résultat technique sous D-040
Portée: simulation MuJoCo uniquement

## Origine

LIFE-009 est close sous D-037 avant ses banques réservées. Son smoke a montré:

- une marge oracle de seulement `2,383 % < 10 %`;
- des AUC toutes supérieures à `1`, donc un ajustement qui dégrade le prior;
- une ingénierie correcte et une projection largement sous budget.

LIFE-010 ne retune pas LIFE-009. Il change d'identifiant, de plans, de compétence, de
banques et de graines. Il conserve les gardes d'intégrité qui ont fonctionné.

## Question

Une politique apprise peut-elle choisir entre trois expériences sensorimotrices de coût
identique pour améliorer plus vite un modèle de dynamique du cou, lorsque les
caractéristiques mécaniques dominantes diffèrent entre organismes?

Cette tranche vise toujours la première capacité de l'architecture finale: prédire les
conséquences immédiates de ses mouvements. Elle ajoute deux exigences absentes de
LIFE-009:

1. la mise à jour de compétence ne peut pas dégrader son prior sur une validation
   publique interne;
2. les trois expériences ont exactement le même nombre de pas et le même coût commandé,
   mais des structures temporelles différentes.

## Compétence

Nom: `neck_dynamics_residual_prediction`.

À chaque transition, un prior physique prédit:

```text
prior_next = clip(
    current_angle + clip(next_target - current_angle, -12°, +12°),
    10°,
    170°,
)
```

Le pas de contrôle est `20 ms`; `12°` correspond au servo nominal `600°/s`. Le modèle
apprend uniquement le résidu
`next_as5600 - prior_next`, jamais l'angle complet.

### Base résiduelle gelée

Les features analytiquement normalisées sont:

- constante;
- erreur cible-courant `/160`;
- erreur limitée à `±12°`, divisée par `12`;
- variation AS5600 précédente `/12`;
- variation de commande courante `/160`;
- variation de commande précédente `/160`;
- indicateur de maintien, `abs(command_delta)<1e-9`;
- indicateur de renversement de signe;
- `abs(error)/160`;
- `error × abs(error) / 160²`;
- angle courant centré sur `90°`, divisé par `80`;
- interactions `hold × previous_delta/12` et
  `reversal × previous_delta/12`.

La régression ridge pénalise tous les coefficients sauf la constante avec `alpha=1.0`.
Les normalisations sont les constantes ci-dessus: aucune moyenne ou variance issue des
données n'est ajustée. Les poids initiaux sont nuls, donc le modèle initial est
exactement le prior physique.

### Plasticité protégée

Dans chaque essai de 32 transitions:

- indices de séquence pairs: ajustement;
- indices impairs: validation publique interne, jamais utilisés dans l'ajustement.

Après un nouvel essai, un candidat est ajusté sur l'union de tous les indices pairs
acquis. Le modèle courant et le candidat sont comparés sur l'union de tous les indices
impairs acquis. Le candidat est accepté si:

```text
MAE_publique_candidate <= MAE_publique_courante + 1e-12
```

Sinon les poids courants sont conservés. Données et décision d'acceptation sont
persistées dans les deux cas. Avant le premier essai, la MAE publique est absente; le
premier candidat est accepté seulement si sa MAE sur les 16 indices impairs de ce même
essai est inférieure ou égale à celle du prior.

La banque privée n'intervient jamais dans cette acceptation.

## Expériences candidates

Toutes comportent 32 pas, commencent depuis un reset à `90°`, terminent à `90°` et ont
un coût commandé exactement égal à `560°`.

### `probe_step_hold`

Primitive `probe_step_hold_bounded_servo`:

```text
(160 ×6, 20 ×6, 160 ×6, 20 ×6, 90 ×8)
```

Elle contient cinq changements de cible et de longs maintiens; elle expose vitesse
limite, établissement et amortissement.

### `probe_reversal`

Primitive `probe_reversal_bounded_servo`:

```text
(50,50,90,90,130,130,90,90) ×3
+ (50,50,90,90)
+ (90,90,90,90)
```

Elle contient 14 changements et des maintiens courts; elle expose renversements et
transitoires intermédiaires.

### `probe_micro`

Primitive `probe_micro_bounded_servo`:

```text
(70,90,110,90) ×7
+ (90,90,90,90)
```

Elle contient 28 petits changements; elle expose réponse locale, friction et répétition.

Pour chaque plan:

```text
sum(abs(target_i - target_(i-1))) = 560°
```

avec `target_-1=90°`. La longueur, le coût commandé et le retour à 90 sont des portes
exactes de construction. Déplacement réalisé et durée CPU restent descriptifs. Aucune
cible n'est paramétrable par la politique.

## Familles d'organismes

Chaque organisme appartient à un régime caché constant pendant ses 24 cycles:

1. `speed_dominant`:
   `max_speed_deg_s ~ U[240,720]`, autres paramètres nominaux;
2. `settling_dominant`:
   `position_gain ~ U[7,13]`, `velocity_damping ~ U[0.08,0.24]`, autres nominaux;
3. `friction_dominant`:
   `joint_frictionloss ~ U[0.006,0.030]`,
   `joint_armature ~ U[1e-4,4e-4]`, autres nominaux.

Valeurs nominales:

- vitesse `600°/s`;
- gain `10`;
- amortissement `0.15`;
- friction `0.0147`;
- armature `2e-4`.

Le régime et les paramètres sont dans le manifeste d'intégrité mais interdits au modèle
de compétence, aux features de politique et aux baselines. L'affectation est
déterministe par index de graine modulo trois afin de garantir l'équilibre du test.

Aucun organisme invalide n'est remplacé ou resamplé. NaN, sortie de bornes, instabilité
MuJoCo ou erreur initiale privée nulle arrêtent la tranche concernée.

## Banque privée

Pour chaque organisme, deux flux de bruit réservés exécutent chacun les trois plans
complets, soit `2 × 3 × 32 = 192` transitions.

La banque:

- couvre exactement l'espace d'action;
- utilise les mêmes configurations cachées mais des flux RNG disjoints;
- n'entre jamais dans l'ajustement ou la validation publique de compétence;
- n'entre jamais dans LIFE-002/LIFE-003;
- n'est jamais une feature;
- sert au professeur développement/validation et à l'évaluation différée test.

La métrique est la MAE privée globale. Les trois MAE par motif
`step_hold/reversal/micro` et leur maximum sont secondaires anti-sacrifice.

## Politique apprise

`learned_protected_progress_ridge_v1` prédit le progrès privé relatif d'une candidate.
Son régresseur ridge utilise `alpha=1e-2`, standardisation développement uniquement,
constante non pénalisée et échelle `1.0` pour toute colonne de variance nulle.

Pour chaque candidate, les features autorisées sont:

- one-hot de l'expérience;
- cycle `/24`, nombre total de transitions et nombre de mises à jour acceptées/refusées;
- MAE publique globale courante, ou sentinelle `0.0` avec indicateur d'absence;
- pour chacun des trois motifs: compte d'essais, MAE publique, amélioration publique
  cumulée et incertitude ridge moyenne;
- les mêmes résumés restreints au motif de la candidate;
- dernière expérience et répétitions consécutives;
- six `ExperimentSignals` LIFE-002;
- coût commandé, constant `560/560 = 1`.

Régime, paramètres cachés, banque privée, progrès professeur, futur, politique
concurrente et métriques test sont interdits.

La cible est:

```text
clip((MAE_privée_avant - MAE_privée_après) / max(MAE_privée_avant, 1e-6), -1, 1)
```

La politique est gelée avant le test et ne se réentraîne pas pendant les 24 cycles.

## Professeur contrefactuel

À chaque état, les trois branches copient le modèle de compétence, ses données,
acceptations, mémoire et RNG. Chaque branche utilise des magasins SQLite/J0 temporaires
distincts. Une seule branche, choisie par carré latin, est rejouée dans le magasin
principal.

La copie MuJoCo utilise `mj_copyData` ou une recréation bit-identique vérifiée lorsque
le contrat d'essai repart explicitement d'un reset. Les flux bruit capteur, primitive,
banque privée et uniforme sont nommés et copiés séparément. Le replay sélectionné doit
être bit-identique.

Après 24 cycles principaux: exactement 24 propositions, exécutions, sessions J0 et
assessments de plasticité; aucune branche dans l'histoire.

## Banques et graines

- smoke de conception, non réservé: `18191..18196`, deux organismes par régime;
- développement: `18201..18232`, 32 organismes;
- validation: `18241..18248`, 8 organismes;
- test: `18301..18324`, 24 organismes, huit par régime;
- statistique Monte-Carlo: `2026072703`.

Les espaces RNG `organism`, `private_bank`, `primitive`, `teacher_branch`,
`uniform_policy` et `statistics` sont dérivés par SHA-256 de leur nom, version, graine,
cycle et expérience. Aucun générateur global partagé.

Développement produit exactement `32 × 24 × 3 = 2304` exemples; validation `576`.
Aucun filtrage d'exemple n'est autorisé.

## Politiques test

1. `learned_protected_progress_ridge_v1`;
2. `greedy_public_residual`, baseline principale: motif à MAE publique la plus haute,
   absence traitée comme priorité maximale;
3. `greedy_uncertainty`;
4. `round_robin`;
5. `life006_transparent_score`;
6. `uniform_random`.

ASCII croissant départage toute égalité. Toutes utilisent le même modèle protégé,
catalogue, budget de 24 cycles, bruit indexé par
`(organisme,cycle,expérience)` et coût total commandé structurellement égal à
`24 × 560°`.

L'oracle contrefactuel est obligatoire comme plafond descriptif, jamais comme baseline
de promotion.

## Smoke avant banques

Les six graines smoke exécutent round-robin, baseline principale et oracle. Elles
vérifient:

1. plans 32 pas, coût 560°, retour 90;
2. configurations valides sans remplacement;
3. replay branche→principal bit-identique et comptes 24 exacts;
4. aucune mise à jour acceptée ne dégrade la MAE publique au-delà de `1e-12`;
5. pour chaque graine, MAE privée round-robin finale au moins 20 % sous le prior;
6. amélioration oracle relative face à `greedy_public_residual`:
   médiane des six `>=15 %`, minimum par régime `>=5 %`;
7. projection complète `<=90 minutes`.

Une porte rouge clôt LIFE-010 comme non-résultat de conception avant toute banque. Aucun
plan, seuil, modèle ou domaine n'est modifié sous cet identifiant.

La projection chronomètre banque privée, professeur `24×3`, six politiques test,
oracle, 25 évaluations, analyse et digests. Elle applique les multiplicateurs exacts
32 développement, 8 validation et 24 test.

## P0 — développement et validation

Après smoke vert seulement:

1. ouvrir développement;
2. ajuster une fois poids et standardisation;
3. reproduire bit-identiquement et geler le digest;
4. ouvrir validation seulement;
5. exiger Spearman prédiction-cible `>=0.25`;
6. exiger MAE de politique au moins 15 % sous la constante développement;
7. exiger le même signe de corrélation dans chacun des trois régimes;
8. ouvrir le test seulement si toutes passent.

Tout échec clôt avant test, sans réajustement.

## Résultats et portes test

Métrique primaire: AUC trapézoïdale de MAE privée globale aux instants `0..24`,
normalisée par `24 × MAE_initiale`; plus basse est meilleure.

### P1 — baseline principale

Sur les différences appariées
`AUC_greedy_public_residual - AUC_learned`:

- amélioration moyenne relative `>=5 %`;
- au moins 16/24 graines strictement favorables;
- moyenne favorable dans chacun des trois régimes;
- Monte-Carlo des signes unilatéral `"greater"`, 200 000 tirages, graine
  `2026072703`, `p<=0.05`.

### P2 — baselines secondaires

AUC apprise strictement meilleure en moyenne que chacune des quatre autres baselines.
Quatre tests Monte-Carlo identiques sont corrigés par Holm et doivent tous rester
`<=0.05`. La taille d'effet est portée par P1.

### P3 — plasticité et absence de sacrifice

- aucune mise à jour acceptée ne dégrade la MAE publique au-delà de `1e-12`;
- MAE finale apprise non inférieure à la baseline principale avec marge
  `0.02 × MAE_initiale`;
- pire MAE motif apprise `<=1.10 ×` baseline principale;
- coût commandé exactement égal entre politiques;
- au moins deux expériences choisies dans chaque moitié, agrégées sur le test;
- aucune cible modifiée, exécution incomplète, branche persistée ou cycle actif.

### P4 — reproductibilité

Relecture analytique sans nouvelle exécution J0: poids, acceptations, choix, courbes,
statistiques, comptes et digest logique identiques.

`PROMOUVOIR` exige P0–P4. La promotion autorise uniquement le sélecteur gelé optionnel
en simulation; le sélecteur déclaratif reste le défaut. Une revue Claude des résultats
est obligatoire avant promotion.

## Statistiques

Réutiliser uniquement:

- `learning.paired_stats.monte_carlo_sign_flip_pvalue`;
- `learning.paired_stats.holm_correction`.

Paramètres: alternative `"greater"`, `n_resamples=200000`, graine `2026072703`,
estimateur add-one inchangé. P1 reste hors de la famille Holm P2 parce que la promotion
est conjonctive.

## Arrêts et intégrité

Arrêt immédiat sur fuite, lecture précoce, collision de provenance, configuration
invalide, resampling, compte faux, NaN, replay divergent, garde contournée, duplication,
SQLite/J0 rouge ou plafond dépassé. Les artefacts restent auditables; aucune analyse
partielle.

Échec scientifique après test: résultats publiés, aucune seconde campagne, retuning ou
remplacement. Toute nouvelle tentative exige nouvel identifiant, graines et revue.

## Interprétation limitée

Un succès montrerait qu'une politique apprise alloue mieux des expériences sûres et
équicûteuses pour améliorer un modèle de dynamique protégé sur de nouveaux organismes
simulés. Il ne montrerait pas découverte autonome de plans ou besoins, réafférence
visuelle, transfert physique, curiosité générale ou conscience.

## Amendement pré-calcul après revue Claude Opus 5

Date: 2026-07-27
Verdict source: `AUTORISER AVEC CORRECTIONS BLOQUANTES` dans
`docs/research/life_010_review.md`.

Les clauses B1–B7 suivantes sont additives et prévalent sur toute formulation
antérieure incompatible.

### B1 — ancrage de la taille d'effet

Le smoke rapporte l'AUC de `round_robin` et `greedy_public_residual` pour chaque graine
et régime, avant toute banque:

1. si l'AUC moyenne de greedy est inférieure ou égale à celle de round-robin, greedy
   demeure seule baseline principale;
2. si l'AUC moyenne de greedy est strictement supérieure, round-robin devient
   co-principale.

Dans le second cas, le plancher relatif `>=5 %`, `16/24` graines favorables et le signe
favorable par régime de P1 s'appliquent séparément aux deux baselines et toutes les
conditions doivent passer.

Dans tous les cas, l'amélioration relative moyenne face à round-robin doit aussi être
`>=3 %`, en plus du test P2 corrigé par Holm. Cette décision d'ancrage est écrite dans le
manifeste smoke avec le digest du protocole et ne change plus ensuite.

La marge oracle du smoke reste calculée face à `greedy_public_residual`; si round-robin
devient co-principale, elle est également calculée face à round-robin et doit satisfaire
les mêmes seuils `15 %` médian et `5 %` minimum par régime.

### B2 — sens exact des portes de MAE

Plus bas est toujours meilleur:

```text
MAE_finale_apprise
  <= MAE_finale_baseline_principale + 0.02 × MAE_initiale

pire_MAE_motif_apprise
  <= 1.10 × pire_MAE_motif_baseline_principale
```

Si deux baselines sont principales sous B1, les deux comparaisons doivent passer.

### B3 — portée de la validation publique

Le partage pair/impair est fortement autocorrélé. Il constitue une protection grossière
contre la dégradation, pas une validation de généralisation; seule la banque privée
mesure la compétence.

Le smoke exporte, pour chaque graine et politique:

- candidats acceptés et refusés sur 24 cycles;
- écart médian MAE publique–MAE privée;
- trajectoire des deux MAE.

Si aucun refus n'apparaît sur les six graines, une réussite ultérieure ne peut revendiquer
une « plasticité protégée exercée »; la règle reste inchangée mais cette propriété est
retirée de l'interprétation.

La non-dégradation publique à `1e-12` et l'égalité du coût commandé sont reclassées comme
assertions d'intégrité, hors portes scientifiques. Leur échec reste un arrêt immédiat.

### B4 — assiette complète du smoke

Les six graines smoke exécutent les six politiques test et l'oracle. Sont chronométrés
séparément:

- banque privée;
- professeur `24×3`;
- chacune des six politiques;
- oracle et ses trois branches;
- 25 évaluations de courbe;
- analyse et digests.

La projection applique les multiplicateurs exacts 32 développement, 8 validation et
24 test. Les trois politiques supplémentaires ne contribuent à aucune porte de
conception hors décision d'ancrage B1; elles mesurent l'assiette temporelle.

### B5 — alignement exact du prior

Le smoke asserte:

- `control_dt == 0.02 s`;
- 32 appels `env.step` par plan;
- `600 × 0.02 == 12°` pour la rampe nominale;
- le limiteur porte sur `_limited_deg`, pas sur l'angle AS5600.

Aucune assertion `abs(delta_as5600)<=12°` n'est autorisée. `_limited_deg` est un état
caché non reconstructible exactement depuis les observations publiques; son omission
induit une erreur irréductible commune, empiriquement bornée par la porte de progrès
privé `>=20 %`.

### B6 — limites additionnelles

- Chaque régime ne perturbe qu'un groupe de paramètres, les autres restant nominaux.
  L'inférence est plus facile que sous variation mécanique conjointe; aucun transfert à
  une population réaliste conjointe n'est revendiqué.
- La banque privée rejoue les mêmes plans sous d'autres bruits. Elle mesure l'efficacité
  d'allocation dans le même espace, pas la généralisation à de nouvelles conditions.
  L'alignement public–privé vient de cette identité de distribution, non d'une garde.

### B7 — non-infériorité statistique de P3

Les comparaisons de MAE finale et pire motif sont deux tests appariés de
non-infériorité utilisant
`learning.paired_stats.monte_carlo_noninferiority_pvalue`, `n_resamples=200000`,
graine `2026072703`.

Marges:

- finale: `0.02 × MAE_initiale` par graine;
- pire motif: `0.10 × pire_MAE_motif_baseline` par graine.

Chaque test doit donner `p<=0.05` après correction de Holm dans une famille P3 distincte
de P2. Si B1 crée deux baselines principales, la famille comprend quatre tests et tous
doivent passer.

### Précisions non bloquantes intégrées

- P0 « même signe par régime » reste une garde descriptive à faible puissance;
- greedy commence nécessairement par `probe_micro`, `probe_reversal`,
  `probe_step_hold` sous priorité absence+ASCII;
- allocations sont exportées par moitié, régime, graine et politique;
- l'oracle privilégié est un plafond; l'écart appris/oracle mesure la difficulté
  d'inférence;
- déplacement réalisé est exporté par plan et régime, sans devenir une porte.

## Résultat d'exécution

Le premier smoke `18191` s'est arrêté avant tout résultat scientifique. Après une
exécution de `probe_step_hold`, LIFE-002 a produit `predicted_risk=0.75`, supérieur à la
limite catalogue `0.50`. Le plan est devenu inéligible et le carré latin du professeur
ne pouvait plus être respecté.

LIFE-010 est close sans reprise, relèvement de seuil, calcul de marge ou ouverture de
banque. Voir `docs/research/life_010_technical_stop.md`.
