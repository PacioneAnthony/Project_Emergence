# LIFE-011 — curriculum résiduel avec éligibilité persistante

Date: 2026-07-27
Statut: pré-enregistrement proposé; aucun code, smoke ou calcul LIFE-011 autorisé
Portée: simulation MuJoCo uniquement

## Origine et séparation

LIFE-010 est close sous D-040. Son premier smoke s'est arrêté avant métrique parce que
`probe_step_hold`, après sa propre observation, portait `predicted_risk=0.75` contre une
limite catalogue `0.50`.

LIFE-011 est un nouvel identifiant avec:

- plans et coût nouveaux;
- graines nouvelles;
- manifests et digests nouveaux;
- nouvelle revue pré-calcul.

Elle conserve sans modification la compétence résiduelle, la plasticité pair/impair,
les régimes mécaniques, les politiques, les statistiques et les corrections B1–B7 de
LIFE-010. Les seules modifications scientifiques sont les plans recentrés et une porte
explicite d'éligibilité après historique propre.

## Question

Une politique apprise peut-elle allouer des expériences temporellement complémentaires,
équicûteuses et durablement éligibles pour améliorer un prédicteur résiduel de la
dynamique du cou sur de nouveaux organismes simulés?

## Compétence héritée

Nom: `neck_dynamics_residual_prediction_v2`.

Le prior reste:

```text
prior_next = clip(
    current_angle + clip(next_target - current_angle, -12°, +12°),
    10°,
    170°
)
```

Le modèle ridge apprend uniquement `next_as5600 - prior_next`, avec les treize features
analytiquement normalisées et `alpha=1.0` de LIFE-010.

Chaque essai de 32 transitions réserve:

- séquences paires à l'ajustement;
- séquences impaires à la protection publique autocorrélée.

Le candidat est accepté si sa MAE publique cumulée est
`<= MAE_courante + 1e-12`; sinon les poids courants restent actifs. Acceptations,
refus, données et digests sont persistés. Cette protection est une assertion grossière,
pas une preuve de généralisation; seule la banque privée mesure la compétence.

## Nouveaux plans

Tous les plans:

- comportent exactement 32 pas;
- démarrent depuis un reset à `90°`;
- terminent à `90°`;
- restent dans `[30°,150°]`;
- coûtent exactement `480°` commandés;
- utilisent le registre fermé LIFE-004;
- ne sont jamais paramétrables par la politique.

### `probe_step_hold_v2`

Primitive `probe_step_hold_v2_bounded_servo`:

```text
(150 ×6, 30 ×6, 150 ×6, 30 ×6, 90 ×8)
```

5 changements; coût `60+120+120+120+60=480°`.

### `probe_reversal_v2`

Primitive `probe_reversal_v2_bounded_servo`:

```text
(50,50,90,90,130,130,90,90) ×3
+ (90,90,90,90,90,90,90,90)
```

12 changements de `40°`; coût `480°`.

### `probe_micro_v2`

Primitive `probe_micro_v2_bounded_servo`:

```text
(70,90,110,90) ×6
+ (90,90,90,90,90,90,90,90)
```

24 changements de `20°`; coût `480°`.

La différence temporelle 5/12/24 remplace 5/14/28; aucune autre sémantique n'est
modifiée.

## Contrat de sécurité gelé

Chaque `ExperimentSpec` utilise:

```text
max_predicted_risk = 0.50
max_motor_cost = 0.80
max_proposals_per_session = 100
```

Les signaux observés ne sont jamais écrasés par le curriculum. Une candidate bloquée ne
peut pas être forcée, même par le professeur ou l'oracle.

### Porte d'éligibilité propre

Avant tout professeur ou trajectoire de politique, chaque graine smoke exécute dans un
magasin temporaire distinct:

1. une première exécution de chaque plan;
2. reconstruction LIFE-002 de son historique;
3. nouvelle activation des trois candidates;
4. proposition explicite du même plan sous les gardes fraîches.

Pour chaque plan, la seconde proposition doit:

- rester éligible;
- ne contenir aucune raison de blocage;
- avoir `predicted_risk<=0.50`;
- avoir `motor_cost<=0.80`;
- conserver exactement primitive, cibles, digest et coût.

Un échec arrête LIFE-011 comme non-résultat de conception. Aucun seuil ou plan n'est
modifié sous cet identifiant.

## Organismes et banque privée

Les trois régimes mono-facteur sont inchangés:

- `speed_dominant`: vitesse `U[240,720]`;
- `settling_dominant`: gain `U[7,13]`, amortissement `U[0.08,0.24]`;
- `friction_dominant`: friction `U[0.006,0.030]`, armature `U[1e-4,4e-4]`.

Les autres paramètres restent nominaux. Cette séparation facilite artificiellement
l'inférence; aucun transfert à variation jointe n'est revendiqué.

La banque privée exécute deux flux réservés pour chacun des trois nouveaux plans:
`2×3×32=192` transitions. Elle mesure l'allocation dans le même espace, pas la
généralisation à de nouvelles conditions.

## Politique et professeur

`learned_protected_progress_ridge_v2` conserve:

- ridge politique `alpha=1e-2`;
- liste blanche de features LIFE-010;
- cible de progrès privé relatif bornée `[-1,1]`;
- standardisation développement uniquement;
- poids gelés avant test.

Les identifiants v2 remplacent les identifiants précédents dans le one-hot et les
départages ASCII. Les branches contrefactuelles restent isolées dans SQLite/J0
temporaires; une seule branche carrée-latine est rejouée dans le magasin principal.
Après 24 cycles: 24 propositions, exécutions, sessions J0 et assessments, aucune branche
dans l'histoire.

## Graines

- smoke: `18491..18496`, deux organismes par régime;
- développement: `18501..18532`;
- validation: `18541..18548`;
- test: `18601..18624`, huit par régime;
- statistique: `2026072704`.

Espaces RNG disjoints et dérivés SHA-256:
`organism`, `private_bank`, `primitive`, `eligibility_preflight`, `teacher_branch`,
`uniform_policy`, `statistics`.

Développement: 2304 exemples; validation: 576; aucun filtre ou remplacement.

## Politiques

1. `learned_protected_progress_ridge_v2`;
2. `greedy_public_residual`, principale initiale;
3. `greedy_uncertainty`;
4. `round_robin`;
5. `life006_transparent_score`;
6. `uniform_random`;
7. oracle privilégié descriptif.

Toutes reçoivent 24 cycles et coûtent structurellement `24×480°`.

## Smoke avant banques

Les six graines exécutent:

- préflight d'éligibilité des trois plans;
- banque privée;
- professeur `24×3`;
- six politiques;
- oracle;
- 25 évaluations par trajectoire;
- analyse et digests.

Portes obligatoires:

1. plans exacts 32 pas, 480°, retour 90°, cibles `[30°,150°]`;
2. éligibilité initiale et après historique propre sous risque 0.50/coût 0.80;
3. organismes valides, équilibrés, sans remplacement;
4. branches bit-identiques et comptes principaux 24 exacts;
5. chaque round-robin termine avec MAE privée au moins 20 % sous le prior;
6. oracle face à greedy: marge médiane `>=15 %`, minimum de chaque régime `>=5 %`;
7. si greedy a une AUC moyenne pire que round-robin, round-robin devient co-principale
   et l'oracle doit franchir les mêmes marges face à elle;
8. projection complète `<=90 minutes`;
9. poids smoke bit-identiques au second ajustement;
10. assertions du prior et de protection vertes.

Acceptations/refus et écart public–privé sont exportés. Si aucun refus n'apparaît, une
réussite ne revendique pas une protection exercée.

Une porte rouge ferme avant banques, sans retuning.

## P0 développement–validation

Après smoke entièrement vert:

- ouvrir 18501..18532, ajuster une fois et geler poids/standardisation;
- reproduction bit-identique;
- ouvrir 18541..18548 seulement;
- Spearman prédiction–cible `>=0.25`;
- MAE de politique `>=15 %` sous constante développement;
- signe de corrélation favorable dans chaque régime, garde descriptive;
- ouvrir 18601..18624 seulement si tout passe.

## P1–P4 test

Métrique primaire: AUC normalisée de MAE privée globale aux instants 0..24.

P1, pour chaque baseline principale décidée au smoke:

- amélioration relative moyenne `>=5 %`;
- 16/24 graines favorables;
- moyenne favorable dans chaque régime;
- Monte-Carlo des signes unilatéral, 200 000, graine 2026072704, `p<=0.05`.

Face à round-robin, amélioration moyenne `>=3 %` dans tous les cas.

P2: quatre baselines secondaires, AUC moyenne strictement meilleure et tests
Monte-Carlo corrigés Holm, tous `<=0.05`.

P3 scientifique:

- MAE finale non inférieure selon
  `learned <= baseline + 0.02×initial`;
- pire motif selon `learned <= 1.10×baseline`;
- deux tests appariés `monte_carlo_noninferiority_pvalue`, 200 000, graine
  2026072704, famille Holm distincte; quatre tests si deux baselines principales;
- tous `p<=0.05`.

P3 intégrité:

- aucune mise à jour acceptée ne viole `+1e-12`;
- coût exactement égal;
- au moins deux expériences par moitié agrégée;
- aucun résidu actif, branche persistée ou garde contournée.

P4: replay analytique sans nouvelle exécution J0, tous poids, choix, courbes,
statistiques, comptes et digest identiques.

Promotion exige P0–P4 et revue Claude des résultats. Elle autorise seulement un sélecteur
optionnel gelé en simulation.

## Arrêts

Arrêt immédiat sur plan inéligible, fuite, lecture précoce, collision, resampling, NaN,
compte faux, replay divergent, garde contournée, SQLite/J0 rouge ou plafond dépassé.
Aucune analyse partielle, reprise ou seconde campagne.

## Limites

Un succès démontrerait uniquement une meilleure allocation entre trois plans conçus par
l'ingénieur, sous régimes mono-facteur et évaluation de même distribution. Il ne
démontrerait ni découverte de plans/besoins, variation mécanique réaliste, réafférence
visuelle, transfert physique, curiosité générale ou conscience.

