# LIFE-009 — curriculum appris pour la prédiction sensorimotrice

Date: 2026-07-27  
Statut: pré-enregistrement proposé pour revue contradictoire; aucun calcul autorisé  
Portée: simulation MuJoCo uniquement

## Question

Une politique apprise hors ligne peut-elle choisir, à partir du seul état cognitif
observable, la prochaine expérience bornée qui améliore le plus vite une compétence
sensorimotrice elle-même apprise?

LIFE-009 vise directement la première capacité de l'architecture développementale:
prédire la conséquence immédiate d'un mouvement de cou. Il ne suffit pas de faire
changer un statut de compétence. Le modèle prédictif doit réellement réduire son erreur
sur des transitions tenues à part.

## Hypothèse

Un prédicteur de progrès régularisé, entraîné sur des organismes simulés réservés, peut
généraliser à de nouveaux organismes et obtenir une aire sous la courbe d'erreur plus
basse qu'une politique analytique d'incertitude, sous le même budget d'essais, sans
augmenter matériellement le coût moteur ni sacrifier une région du domaine.

Le succès qualifierait une première politique de curriculum apprise. Il ne démontrerait
ni curiosité générale, ni découverte autonome de besoins ou de plans, ni causalité dans
le monde réel.

## Compétence apprise

Nom: `neck_one_step_prediction`.

À partir des observations publiques J0 disponibles avant une transition, le modèle
prédit l'angle AS5600 au pas suivant. Les entrées autorisées sont:

- angle AS5600 courant;
- cible bornée demandée au pas suivant;
- variation d'angle observée au pas précédent;
- direction et amplitude de l'erreur cible-courant.

Le modèle est une régression ridge sur une base fixe et documentée:

- constante;
- angle courant et cible, normalisés sur `[10°,170°]`;
- variation précédente normalisée;
- erreur signée;
- bases charnières séparées par direction aux amplitudes `0°, 15°, 40°, 70°,
  110° et 160°`.

Le coefficient de ridge est fixé à `1e-3` après standardisation des colonnes sur les
seules données d'apprentissage de l'organisme. La constante n'est pas pénalisée. Avant
qu'un ajustement soit identifiable, le prior prédit l'angle courant. Aucun hyperparamètre
du modèle de compétence ne sera choisi à partir des banques de validation ou de test.

Chaque organisme conserve son propre modèle. Aucun poids de compétence, transition ou
résumé d'un autre organisme n'est injecté dans un organisme évalué.

## Expériences candidates

Trois primitives MuJoCo fermées, de 12 pas, partent d'un reset MuJoCo à `90°` et
terminent à `90°`:

- `probe_fine`: `(75, 90, 105, 90)` répété trois fois;
- `probe_medium`: `(50, 90, 130, 90)` répété trois fois;
- `probe_wide`: `(20, 90, 160, 90)` répété trois fois.

Les cibles sont immuables, dans `[10°,170°]`, non paramétrables par la politique et
exécutées par le contrat LIFE-004. Toutes les candidates passent encore les gardes
fraîches du catalogue. La politique apprise ne peut ni créer une primitive, ni modifier
une cible, une limite, un quota ou un arrêt d'urgence.

Les trois routes LIFE-006 sont actives pour `unknown`, `learning`, `candidate` et
`regressed`. Leurs priors froids sont identiques et gelés:
`epistemic_gain=0.5`, `learning_progress=0.5`, `novelty=0.5`,
`controllability=0.5`, `predicted_risk=0.1`, `motor_cost=0.5`. Dès qu'une primitive
possède un historique, `life006_transparent_score` emploie sans modification
l'estimateur observationnel LIFE-002 actuel.

Chaque organisme reçoit 24 cycles. Un cycle produit exactement une proposition, une
exécution J0 complète, une mise à jour du modèle de compétence et un assessment
persistant. Les trois primitives ont le même nombre de pas; leur déplacement angulaire
réel est mesuré et traité comme une garde, pas supposé égal.

## Organismes simulés

Un organisme est un `BenchHeadEnv` dont les paramètres cachés restent constants pendant
ses 24 cycles. Ils sont tirés une fois depuis des distributions gelées:

- `max_speed_deg_s ~ U[360,720]`;
- `position_gain ~ U[8,12]`;
- `velocity_damping ~ U[0.12,0.18]`;
- `joint_frictionloss ~ U[0.012,0.018]`;
- `joint_armature ~ U[1.6e-4,2.4e-4]`.

La quantification et les bruits capteurs restent ceux de `BenchSensorConfig`. Les
paramètres cachés, états MuJoCo internes et graines ne sont jamais des features de la
politique ou du modèle de compétence. Ils sont conservés seulement dans le manifeste
d'intégrité.

Le smoke doit vérifier avant toute campagne que les 40 configurations développement et
validation et les 24 configurations test:

- construisent un modèle MuJoCo valide;
- terminent les trois primitives sans saturation, NaN ou sortie de bornes;
- présentent une erreur initiale strictement positive sur la banque d'évaluation;
- ne produisent aucune collision de digest de configuration entre banques.

Un échec arrête le protocole. Il n'autorise ni resampling, ni réduction de domaine.

## Banque privée d'évaluation

Chaque organisme possède une séquence fixe de 48 transitions qui couvre les deux
directions et les six amplitudes charnières, dans un ordre dérivé d'un espace RNG
distinct. Les observations vraies sont générées une fois, avant les 24 cycles, puis
figées.

Cette banque:

- n'est jamais ajoutée aux données d'ajustement de la compétence;
- n'est jamais exposée aux features ou au choix de la politique;
- n'est jamais ajoutée à l'historique LIFE-002/LIFE-003;
- sert uniquement au professeur sur les banques développement/validation et à
  l'évaluation différée sur la banque test;
- utilise l'état courant vrai comme entrée de chaque prédiction à un pas, sans rollout
  autorégressif.

La métrique de compétence est la MAE en degrés sur les 48 transitions. Sont également
gelées la MAE par amplitude et la pire MAE parmi les six amplitudes.

## Politique apprise

La politique `learned_progress_ridge_v1` prédit, pour chaque candidate sûre, la réduction
relative de MAE privée produite par sa prochaine mise à jour. À l'inférence, elle choisit
le maximum, puis l'identifiant lexicographique en cas d'égalité exacte.

Le vecteur candidat ne contient que:

- identifiant one-hot de la primitive;
- index de cycle normalisé;
- nombre total de transitions apprises;
- compte, moyenne des résidus d'ajustement et incertitude ridge pour chacune des six
  amplitudes;
- mêmes trois résumés restreints aux amplitudes couvertes par la candidate;
- dernière primitive choisie et nombre de répétitions consécutives;
- six `ExperimentSignals` LIFE-002 disponibles;
- coût moteur historique moyen de la candidate.

Les paramètres cachés, MAE privée courante, labels futurs, métriques test et statut
d'une autre politique sont interdits.

Le régresseur de politique est une ridge multivariable, constante non pénalisée,
coefficient `1e-3`, entrées et cible standardisées sur la seule banque développement.
La cible professeur est
`clip((MAE_avant - MAE_après) / max(MAE_avant, 1e-6), -1, 1)`.
Les poids et paramètres de standardisation sont gelés avant d'ouvrir la banque test.
La politique ne se réentraîne pas pendant les 24 cycles test.

## Construction des exemples professeur

Banque développement: graines organisme `17901..17932`.

Une trajectoire équilibrée, définie par le carré latin des trois primitives et l'index
de graine, produit les états pré-décision. À chacun de ces états, trois branches
contrefactuelles copient:

- l'état MuJoCo public et caché;
- le modèle de compétence et ses données;
- les états RNG;
- la mémoire cognitive pertinente.

Chaque branche exécute exactement une candidate et calcule son label professeur sur la
banque privée. Les branches non suivies ne rejoignent jamais l'histoire principale.
La branche indiquée par le carré latin devient l'état suivant. Il en résulte
`32 × 24 × 3 = 2 304` exemples avant tout filtrage; aucun exemple ne peut être supprimé
selon son label.

Banque validation: graines `17933..17940`, même construction, jamais utilisée pour
ajuster les poids ou la standardisation. Elle vérifie seulement les portes de prédiction
ci-dessous. Aucun choix d'hyperparamètre ou nouveau fit n'est autorisé après sa lecture.

## Politiques comparées

Banque test: graines organisme `18001..18024`.

Chaque graine est rejouée depuis un état initial et des flux aléatoires identiques sous:

1. `learned_progress_ridge_v1`;
2. `greedy_uncertainty`, baseline principale: candidate sûre dont l'incertitude ridge
   moyenne sur ses amplitudes est maximale;
3. `life006_transparent_score`: score LIFE-002/LIFE-006 actuel, sans modification;
4. `round_robin`: ordre fixe `fine,medium,wide`;
5. `uniform_random`: tirage uniforme dans un espace RNG réservé.

Les égalités des baselines sont départagées lexicographiquement. Toutes ont le même
modèle de compétence, prior, évaluateur, 24 cycles, catalogue, quotas et gardes. Les
bruits de primitive sont indexés par `(graine organisme, cycle, primitive)` afin qu'une
même candidate au même cycle reçoive le même bruit, indépendamment de la politique.

Un oracle qui lit les trois progrès contrefactuels peut être rapporté comme plafond
descriptif. Il n'entre dans aucune porte de promotion.

## Résultats gelés

Pour chaque politique et graine:

- courbe MAE privée aux instants 0..24;
- aire trapézoïdale normalisée par `24 × MAE_initiale`, plus basse = meilleure;
- MAE finale;
- pire MAE finale parmi les six amplitudes;
- coût moteur cumulé en degrés;
- fréquence des primitives;
- propositions bloquées, exécutions incomplètes et résidus transactionnels.

La métrique primaire est l'aire normalisée. Aucune métrique par primitive, coefficient
de politique ou trajectoire test n'est consultée avant que les 24 graines et les cinq
politiques soient complètes.

## Portes pré-calcul

Toutes les portes suivantes sont nécessaires.

### P0 — intégrité et apprentissage

- 32/32 organismes développement, 8/8 validation et 24/24 test admissibles sans
  remplacement;
- exactement 2 304 exemples professeur d'apprentissage, 576 de validation et aucun
  recouvrement de digest ou de graine;
- aucune feature interdite et aucune donnée privée dans SQLite ou les entrées politique;
- sur validation, corrélation de rang de Spearman prédiction-cible `>=0.20`;
- sur validation, MAE de prédiction au moins 10 % plus basse que la constante égale à
  la moyenne développement;
- poids bit-identiques après réentraînement avec les mêmes entrées.

### P1 — progrès primaire

Sur les 24 différences appariées
`AUC_greedy_uncertainty - AUC_learned`:

- moyenne relative favorable `>=5 %` de l'AUC de `greedy_uncertainty`;
- au moins 16/24 graines strictement favorables;
- test exact de permutation des signes unilatéral `p<=0.05`.

La baseline principale est fixée avant calcul; elle ne sera pas remplacée par la moins
bonne baseline après observation.

### P2 — baselines secondaires

L'AUC apprise doit être strictement meilleure en moyenne que chacune des trois baselines
secondaires. Les trois tests de permutation unilatéraux sont corrigés par Holm et
doivent chacun rester `<=0.05`.

### P3 — absence de raccourci

- MAE finale moyenne apprise au plus
  `MAE_finale_greedy + 0.02 × MAE_initiale`;
- pire MAE finale moyenne apprise `<=1.10 ×` celle de `greedy_uncertainty`;
- coût moteur moyen appris `<=1.10 ×` celui de `greedy_uncertainty`;
- au moins deux primitives différentes choisies dans chacune des moitiés de campagne
  agrégées sur les 24 graines;
- aucun choix non sûr, aucune cible modifiée, aucune exécution incomplète et aucun cycle
  actif résiduel.

### P4 — reproductibilité

Une seconde exécution analytique sur les artefacts gelés retrouve exactement poids,
choix, comptes, métriques, tests et digest logique, sans nouvelle exécution J0.

## Décision

`PROMOUVOIR` exige P0, P1, P2, P3 et P4 vertes. La promotion autorise seulement
l'intégration de la politique gelée comme sélecteur optionnel en simulation KERNEL/LIFE.
Le sélecteur déclaratif reste le défaut jusqu'à une qualification d'endurance distincte.

Toute porte rouge donne `NE PAS PROMOUVOIR`. Les résultats restent publiés; aucun
retuning sur validation ou test, remplacement de graine, nouvelle baseline ou seconde
campagne n'est autorisé sous LIFE-009. Une nouvelle tentative exige un nouvel
identifiant, de nouvelles banques et un nouveau pré-enregistrement.

## Exécution et plafond

- smoke fonctionnel: graine `17991`, après verdict Claude seulement;
- plafond initial campagne complète: 60 minutes murales;
- le smoke exécute un organisme complet sous les cinq politiques et mesure une
  projection conservatrice;
- si la projection dépasse 60 minutes, arrêt technique avant ouverture des banques;
- si le plafond est atteint en campagne, arrêt technique, aucun résultat partiel;
- aucun amendement de plafond sans nouvelle revue contradictoire pré-calcul.

Les artefacts minimaux sont les manifests de banques, digests de configuration et de
plans, dataset professeur, paramètres de standardisation, poids, journaux J0, courbes
par graine, rapport de portes et environnement logiciel. Les données brutes restent
hors SQLite.

## Règles d'arrêt

Arrêt immédiat sur fuite entre banques, feature interdite, donnée test lue avant gel des
poids, collision de provenance, configuration invalide, resampling, divergence
numérique, cible hors registre, garde contournée, duplication transactionnelle,
intégrité SQLite/J0 rouge ou plafond dépassé.

L'arrêt conserve les artefacts auditables et interdit toute analyse partielle des
métriques scientifiques.

## Limites déclarées

- le professeur utilise en simulation une banque privée plus informative que ce qui
  serait disponible en continu sur le robot;
- les trois plans et le besoin de prédiction restent conçus par l'ingénieur;
- les variations d'organisme sont paramétriques, pas une diversité ouverte du monde;
- la politique apprend un choix parmi trois expériences, pas une expérience nouvelle;
- la compétence porte sur la dynamique immédiate du cou, pas encore sur la
  réafférence visuelle ni sur une présence sociale;
- aucune conclusion physique n'est permise sous D-008.
