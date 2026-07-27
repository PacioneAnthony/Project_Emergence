# LIFE-012 — curriculum résiduel avec plateaux d'établissement réalisés

Date: 2026-07-27
Statut: close à la plaque; portes 4, 5 et 6 rouges; aucune banque réservée ouverte
Portée: simulation MuJoCo uniquement

## Origine et séparation

LIFE-011 est close sous D-043. Sa plaque de marge a validé la médiane oracle (`16,8853 %`)
mais échoué sur le minimum `settling_dominant`: `4,4039 % < 5 %` sur 18496. Aucun
professeur et aucune banque réservée n'ont été ouverts.

Les exports prévus par B2 montrent une hétérogénéité utile:

- sur 18493, l'oracle choisit micro 23/24 fois et atteint `19,8871 %`;
- sur 18496, il choisit step-hold 20/24 fois mais n'atteint que `4,4039 %`;
- greedy choisit micro 22/24 fois sur les deux organismes.

LIFE-012 ne relâche ni le minimum de 5 %, ni la médiane de 15 %, ni les autres portes.
Elle introduit un nouvel identifiant, de nouveaux plans et de nouvelles graines. Son
changement scientifique unique est de réduire le coût commandé commun de 480° à 240°
pour transformer une partie de la rampe saturée en plateaux réellement atteints.

## Hypothèse

Des plans équicûteux qui séparent réellement rampe, renversement et établissement
créent une opportunité oracle d'au moins 5 % sur chaque organisme mono-facteur, y compris
dans le régime settling, puis permettent à une politique apprise d'inférer quelle
expérience améliore le plus une compétence résiduelle protégée.

## Compétence et organismes

La compétence `neck_dynamics_residual_prediction_v2`, le prior à `12°/pas`, la ridge
résiduelle à treize features (`alpha=1,0`), le partage pair/impair, la règle de protection
`+1e-12`, les trois régimes mono-facteur et leurs distributions sont identiques à
LIFE-011 amendée.

Les limites restent déclarées: le régime settling varie conjointement gain et
amortissement malgré le terme mono-facteur au niveau des familles; la banque privée
évalue la même distribution et ne mesure pas un transfert.

## Plans v4 gelés

Chaque plan fait 32 pas, démarre et finit à 90°, reste dans `[30°,150°]` et coûte
exactement 240° commandés.

### `probe_step_settle_v4`

Primitive `probe_step_settle_v4_bounded_servo`:

```text
(150 ×8, 90 ×8, 30 ×8, 90 ×8)
```

Quatre changements de 60°. Au nominal, la rampe atteint chaque cible en cinq pas puis
dispose de trois pas de maintien: 20 pas mobiles, 6 maintiens hors neutre et 240° de
déplacement réalisé.

### `probe_reversal_v4`

Primitive `probe_reversal_v4_bounded_servo`:

```text
(60 ×4, 90 ×4, 120 ×4, 90 ×4) ×2
```

Huit changements de 30°. Au nominal: 24 pas mobiles, 4 maintiens hors neutre, 240°
réalisés.

### `probe_micro_v4`

Primitive `probe_micro_v4_bounded_servo`:

```text
(75 ×2, 90 ×2, 105 ×2, 90 ×2) ×4
```

Seize changements de 15°. Au nominal: 32 pas mobiles, aucun maintien, 240° réalisés.

### Porte analytique avant code

La rampe `_limited_deg` est reconstruite aux cadences `4,8`, `12,0` et `14,4°/pas`.
Pour chaque paire et chaque cadence, au moins un des quatre indicateurs
`n_mobiles`, `n_renversements`, `n_maintiens_hors_neutre`,
`déplacement_réalisé` diffère sans inversion d'ordre entre cadences.

Au nominal, les ordres gelés sont:

```text
n_mobiles                 : step_settle 20 < reversal 24 < micro 32
n_renversements           : step_settle  2 < reversal  4 < micro  8
n_maintiens_hors_neutre   : step_settle  6 > reversal  4 > micro  0
```

L'échec de cette arithmétique clôt LIFE-012 avant simulation.

## Sécurité et intégrité

Chaque `ExperimentSpec` conserve:

```text
max_predicted_risk = 0.50
max_motor_cost = 0.80
max_proposals_per_session = 100
```

Les cibles évitent la zone de marge; le coût structurel observé vaut
`240/(160×32)=0,046875`. `predicted_risk=0,0` et `motor_cost=0,046875` sont déclarés
constants, mis à l'échelle 1,0 et ne portent aucune revendication scientifique.

L'invariant par essai B4 et le préflight complet de profondeur deux B5 sont conservés
sans modification dans tout magasin. Une violation clôt LIFE-012 sans reprise.

## Banque, politiques et professeur

La banque privée reste uniforme: deux flux par plan, soit `2×3×32=192` transitions.
Elle exporte les vues complète, mobile et inerte. Le coefficient final de la feature
angle est rapporté.

Le professeur contrefactuel, la politique ridge de progrès protégé, les six politiques,
l'oracle, les branches SQLite/J0, les comptes exacts et les digests sont identiques à
LIFE-011, avec substitution mécanique des identifiants v4. Greedy effectue son
tourniquet ASCII initial `micro`, `reversal`, `step_settle`.

## Graines

- smoke: `18791..18796`;
- développement: `18801..18832`;
- validation: `18841..18848`;
- test: `18901..18924`;
- statistique: `2026072705`.

Espaces RNG SHA-256: `organism`, `private_bank`, `primitive`,
`eligibility_preflight`, `teacher_branch`, `uniform_policy`, `statistics`, tous sous
namespace LIFE-012 et disjoints des campagnes antérieures.

## Smoke en deux plaques

La plaque de marge exécute d'abord préflight, banque, round-robin, greedy et oracle sur
les six graines. Elle tranche:

1. plans et complémentarité analytique exacts;
2. assertions d'éligibilité et invariant par essai;
3. organismes valides, deux par régime, sans remplacement;
4. MAE finale round-robin `<=80 %` du prior sur chaque graine;
5. marge oracle face à greedy: médiane `>=15 %` et minimum de chaque régime `>=5 %`;
6. ancrage numérique
   `AUC_moyenne(greedy) > AUC_moyenne(round_robin)`; si vrai, round-robin devient
   co-principale et l'oracle doit franchir les mêmes marges face à elle.

Une porte rouge clôt avant professeur. Les marges par graine/régime, préférences oracle
et décompositions mobile/inerte sont alors exportées.

Si et seulement si la plaque est verte, la plaque de chronométrage exécute professeur,
politique apprise, trois politiques restantes, replay, analyses et digests. Les dix
portes finales sont celles de LIFE-011 B1–B6, notamment projection complète incluant
préflight `<=90 minutes`, poids bit-identiques, branches/comptes exacts et protection
verte.

## P0–P4

P0–P4, les familles Holm, l'ancrage dynamique, le plancher P1 de 3 % face à round-robin,
les effets principaux de 5 %, `16/24`, signes par régime, Monte-Carlo 200 000, P3 de
non-infériorité appariée et P4 analytique sont repris mot pour mot de LIFE-011 amendée.
Aucun seuil n'est modifié.

## Arrêts et portée

Toute porte rouge, fuite, lecture précoce, collision, resampling, NaN, compte faux,
replay divergent, garde contournée ou plafond dépassé clôt LIFE-012 sans analyse
partielle ou seconde campagne.

Un succès démontrerait seulement une meilleure allocation entre trois plans
ingénieurisés dans un banc simulé mono-facteur. Il ne démontrerait ni découverte
autonome d'expériences, causalité générale, transfert physique, conscience ou
compatibilité curriculum–garde; cette dernière reste satisfaite par construction.

## Amendements pré-calcul issus de la revue LIFE-012

Date d'intégration: 2026-07-27. B1–B5 sont additifs et priment sur toute formulation
antérieure incompatible. Aucune graine LIFE-012 n'a été ouverte avant ce gel.

### B1 — voie B: cadence critique et dégénérescence déclarée

La voie B est choisie et gelée. Le coût 240° et le triplet v4 restent inchangés. Leur
cadence critique commune est `240/32 = 7,5°/pas`, soit `375°/s`.

`settling_dominant` et `friction_dominant` restent à `12°/pas`: le mécanisme de plateau
y est disponible. Dans `speed_dominant ~ U[240,720]°/s`, `28,125 %` des organismes sont
sous 375°/s. La probabilité d'en rencontrer au moins un vaut `48,34 %` parmi les deux
organismes speed du smoke et `92,88 %` parmi les huit du test.

Sous ce seuil, les trois plans ont 32 pas mobiles, aucun plateau et `153,6°` réalisés;
ils ne diffèrent plus que par 2/4/8 renversements. Un échec sur un tel organisme sera
attribué au dessin, jamais à la politique. Il n'autorise aucun filtrage, remplacement,
resampling, restriction de `U[240,720]`, changement de seuil ou reprise.

La voie B et le digest du protocole sont écrits au manifeste avant métrique et ne peuvent
être révisés.

### B2 — classes de diagnostic vides

Une classe vide est valide et exportée avec:

```text
count = 0
prior_mae = null
final_mae = null
error_mass_fraction = null
margin = null
```

Aucune exception n'est levée. Seule la vue complète, toujours forte de 192 transitions,
porte les portes scientifiques. Le rapport exporte la cadence propre de chaque organisme
et `plateau_disponible = (cadence > 7,5°/pas)`. Ce statut n'est ni une porte ni un motif
d'exclusion.

### B3 — taxonomie rampe/plateau/temps_mort

Chaque transition est classée exclusivement depuis `_limited_deg`:

- `rampe`: déplacement non nul;
- `plateau`: déplacement nul dans les trois pas suivant une arrivée (`k=3`);
- `temps_mort`: déplacement nul au-delà.

Pour le triplet v4 à cadence nominale, par flux de 96 transitions:

```text
rampe = 76
plateau = 20
temps_mort = 0
```

Le banc de deux flux vaut donc `152/40/0`. À cadence sous-critique, il vaut `192/0/0`.
`temps_mort=0` est une assertion obligatoire pour chaque organisme.

Par organisme, plan et classe, la plaque exporte: compte, MAE du prior, MAE finale
round-robin, part de masse d'erreur totale et marge oracle restreinte. Elle exporte aussi
la suite des résidus de plateau afin d'évaluer leur décroissance face au pas AS5600 de
`0,0879°`.

L'indicateur `hold` de la base gelée signifie seulement « cible inchangée ». Il reste
actif pendant une partie des rampes et aucune feature n'isole explicitement le plateau.
Un échec peut donc relever de la représentation, pas seulement de l'allocation.

### B4 — statut et historique de la porte de marge

Le minimum oracle `>=5 %` par organisme et régime est plus strict que P1, qui exige une
moyenne favorable par régime. C'est une garantie d'attribution et d'uniformité du dessin.

Historique:

- v2: jamais mesurée, arrêt D-040;
- v3: médiane `16,8853 %`, minimum settling `4,4039 %`, arrêt D-043;
- v4: LIFE-012.

Le minimum repose sur deux organismes par régime et possède une forte variance
d'échantillonnage. Un passage au troisième dessin ne prouvera pas à lui seul l'uniformité.
Forme, seuil et effectif restent néanmoins inchangés sous LIFE-012.

### B5 — portée et conservations

Le lien « absence de plateau v3 → marge 4,4039 % » est une hypothèse de conception non
mesurée. Aucune comparaison v3/v4 contrefactuelle n'est effectuée sur les mêmes
organismes. Un succès montrerait seulement que v4 franchit les portes, pas que les
plateaux en sont la cause.

`predicted_risk=0,0` et `motor_cost=0,046875` sont constants, échelle 1,0.
`life006_transparent_score` est donc réduite à
`epistemic_gain + learning_progress + 0,25·novelty + 0,5·controllability`; cette faiblesse
est rappelée dans P2.

L'invariant par essai s'applique à tout magasin et toute profondeur. Le préflight de
profondeur deux est une vérification de bout en bout supplémentaire, jamais un substitut.
