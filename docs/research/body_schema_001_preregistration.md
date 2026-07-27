# BODY-SCHEMA-001 — schéma corporel probabiliste avant reprise de J5

Date: 2026-07-27
Statut: pré-enregistrement proposé; aucun code, test scientifique ou calcul autorisé
Portée: jalon J1, simulation MuJoCo uniquement

## Motivation et rupture avec LIFE

LIFE-009..012 ont tenté de qualifier un sélecteur d'expériences. D-046 arrête cette
famille: sur 18793, prior, greedy, round-robin et oracle restent identiques parce que la
protection refuse 24/24 mises à jour. Un ordonnanceur ne peut créer du progrès si la
compétence sous-jacente n'est pas plastique.

BODY-SCHEMA-001 revient à l'ordre de succès de `DEVELOPMENTAL_ARCHITECTURE.md`:

1. prédire robustement les conséquences immédiates du cou;
2. exprimer une incertitude calibrée;
3. détecter une commande sans effet;
4. seulement ensuite reprendre J5 et le choix d'expérience.

Il ne choisit aucun plan et n'emploie aucun oracle de curriculum.

## Question

À budget d'observation identique, un modèle résiduel probabiliste à bootstrap de trials
entiers peut-il:

- battre le prior physique et la ridge déterministe LIFE sur de nouveaux organismes;
- apprendre sur chaque organisme sans séquence 24/24 refusée;
- produire des intervalles calibrés;
- signaler un actionneur sans effet à partir de son innovation prédictive?

## Organismes

Les trois familles restent:

- `speed_dominant`: `max_speed_deg_s ~ U[240,720]`;
- `settling_dominant`: gain `U[7,13]`, amortissement `U[0,08,0,24]`;
- `friction_dominant`: friction `U[0,006,0,030]`, armature `U[1e-4,4e-4]`.

Les paramètres restent cachés aux modèles. La variation conjointe gain/amortissement et
le caractère artificiellement mono-facteur sont déclarés.

## Excitation fixe, commune à tous les modèles

Il n'existe aucune politique d'allocation. Chaque organisme reçoit la même séquence
causale de 30 trials de 32 pas:

- 6 trials publics de protection/calibration, deux par motif;
- 24 trials d'apprentissage en round-robin fixe, huit par motif.

Les motifs couvrent impulsions bornées, renversements et micro-mouvements dans
`[30°,150°]`. Leurs cibles exactes, coûts, digests et ordre latin sont gelés avant code.
Ils doivent rester éligibles sous `predicted_risk<=0,50`, `motor_cost<=0,80`.

Les six trials publics ne sont jamais utilisés pour ajuster les coefficients. Ils servent
uniquement à la protection et à la calibration conformelle. Les 24 trials
d'apprentissage sont identiques, bit à bit, pour tous les modèles d'un organisme.

Une banque privée distincte de six trials — deux par motif, graines RNG séparées — est
construite avant l'apprentissage et lue seulement aux instants `0,3,6,...,24`. Elle
mesure la compétence, jamais la décision de mise à jour.

## Transitions et information autorisée

Chaque modèle reçoit uniquement:

- angle AS5600 courant;
- variation d'angle précédente;
- cible précédente et cible suivante;
- variations de commande courante et précédente;
- indicateurs de cible inchangée et renversement;
- interactions et termes quadratiques gelés.

Il ne reçoit ni paramètres MuJoCo, régime, `_limited_deg`, banque privée, graine
d'organisme ou état vrai non observé.

La cible principale est l'angle AS5600 au pas suivant. La variation d'angle suivante est
une métrique dérivée obligatoire.

## Modèles comparés

### B0 — persistance

```text
next_angle = current_angle
```

### B1 — prior physique

Prior borné LIFE à `12°/pas`, sans adaptation.

### B2 — ridge résiduelle LIFE

Treize features, `alpha=1,0`, protection pair/impair et règle `+1e-12` identiques à
LIFE-012. Elle est le comparateur historique, y compris ses refus.

### M — ensemble résiduel probabiliste

Seize ridges résiduelles ARX, `alpha=1,0`. L'unité de bootstrap est le trial entier:
pour chaque membre et trial d'apprentissage, un poids Poisson(1) déterministe est tiré
dans l'espace RNG `bootstrap_member`. Aucun bootstrap de transitions autocorrélées.

La prédiction centrale est la moyenne des seize prédictions bornées. La variance brute
additionne:

- variance inter-membres;
- variance robuste des résidus publics, estimateur MAD gelé.

À chaque checkpoint, un unique facteur conformel symétrique est calculé sur les six
trials publics, exclus de l'ajustement, puis appliqué à la banque privée. Ce facteur
n'entre jamais dans la moyenne prédite.

## Protection de M

Après chaque trial d'apprentissage, un candidat complet est reconstruit à partir de tous
les trials d'apprentissage disponibles et de leurs poids bootstrap gelés. Il est accepté
si sa MAE moyenne sur les six trials publics vérifie:

```text
candidate_public_mae <= current_public_mae + 1e-12
```

Le modèle initial est le prior physique. Les trials publics sont des trials entiers,
non des séquences paires/impaires. Leur réutilisation adaptative est déclarée: cette
protection empêche une dégradation grossière mais ne prouve pas la généralisation.

Acceptations, refus, MAE et digests sont exportés. Un organisme avec zéro acceptation
est un échec de plasticité, jamais filtré ou remplacé.

## Détection d'une commande sans effet

Une banque faute séparée utilise les mêmes commandes que la banque privée, mais un
actionneur bloqué à l'angle courant. Elle n'est jamais utilisée pour l'ajustement ou la
calibration.

Score de faute au pas:

```text
abs(observed_next - predicted_mean) / max(predicted_sigma, 0,0879°)
```

Le détecteur compare les scores des trials normaux privés aux trials bloqués. La vérité
faute n'est accessible qu'à l'évaluation.

## Graines et RNG

- smoke: `19091..19096`, deux organismes par régime;
- test: `19201..19224`, huit par régime;
- statistique: `2026072706`.

Espaces SHA-256 disjoints: `organism`, `public_trials`, `learning_trials`,
`private_bank`, `fault_bank`, `primitive`, `bootstrap_member`, `statistics`.
Aucune graine LIFE n'est réutilisée.

Il n'existe aucun développement inter-organismes: tous les hyperparamètres sont gelés
ci-dessus. Le smoke qualifie l'implémentation et le mécanisme; le test reste fermé
jusqu'à toutes les portes smoke vertes.

## Smoke

Les six organismes exécutent les quatre modèles sur les mêmes observations. Portes:

1. plans, coûts, gardes, comptes, RNG et replays exacts;
2. banques publique/apprentissage/privée/faute disjointes par provenance et digest;
3. aucune fuite de régime, paramètres, `_limited_deg` ou banque privée;
4. M accepte au moins une mise à jour sur chacun des six organismes;
5. M termine avec MAE privée `<=90 %` du prior sur chacun;
6. aucun modèle ne produit NaN, variance négative ou intervalle inversé;
7. couverture 90 % de M entre 80 % et 98 % globalement, largeur médiane strictement
   inférieure à l'intervalle trivial `[10°,170°]`;
8. AUROC faute de M `>=0,75` sur chaque organisme;
9. second run analytique reproduit poids, facteurs conformels, prédictions et digests;
10. projection complète des 24 tests et quatre modèles `<=90 minutes`.

Une porte rouge clôt sans ouvrir 19201+.

## Test gelé

Métrique primaire: MAE privée finale de l'angle.

### H1 — M face au prior physique

- amélioration moyenne `>=15 %`;
- au moins 16/24 organismes favorables;
- moyenne favorable dans chaque régime;
- test apparié Monte-Carlo des signes, 200 000 tirages, graine statistique,
  `p<=0,05`.

### H2 — M face à la ridge LIFE

- amélioration moyenne `>=5 %`;
- au moins 16/24 favorables;
- moyenne favorable dans chaque régime;
- seconde comparaison dans la même famille Holm que H1, toutes `p_corrigé<=0,05`.

### H3 — plasticité et rétention

- au moins une acceptation sur 24/24 organismes;
- aucune mise à jour acceptée ne dégrade la MAE publique au-delà de `1e-12`;
- MAE privée finale non inférieure au meilleur checkpoint de plus de
  `0,02 × MAE_initiale`, test de non-infériorité apparié.

### H4 — incertitude

- couverture marginale de l'intervalle 90 % dans `[0,85;0,95]`;
- couverture dans `[0,80;0,98]` pour chaque régime;
- largeur médiane < `20°`;
- erreur de calibration absolue meilleure que l'ensemble sans facteur conformel.

### H5 — commande sans effet

- AUROC agrégée `>=0,85`;
- AUROC `>=0,75` dans chaque régime;
- TPR `>=0,80` au seuil donnant FPR normale `<=0,10`.

Les tests H1/H2 utilisent `learning/paired_stats.py`; H3 possède sa famille séparée.
H4/H5 sont des portes conjointes descriptives pré-enregistrées, sans sélection de seuil
sur le test.

## Décision

BODY-SCHEMA-001 est promu seulement si le smoke et H1–H5 sont verts et si Claude revoit
les résultats. La promotion qualifie un schéma corporel J1 probabiliste en simulation.
Elle ne qualifie ni J5, curriculum, causalité générale, transfert physique ou conscience.

En cas d'échec, aucune variante de sélecteur LIFE n'est relancée. Le rapport attribue
l'échec à plasticité, représentation, calibration ou détection selon la porte concernée.
