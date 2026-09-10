# BODY-SCHEMA-001 — schéma corporel probabiliste avant reprise de J5

Date: 2026-07-27
Statut: autorisé avec amendements B1–B6 intégrés; implémentation et smoke autorisés
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

## Amendements pré-calcul issus de la revue BODY-SCHEMA-001

Date d'intégration: 2026-07-27. B1–B6 sont additifs et priment sur toute formulation
antérieure incompatible. Aucune graine 19091+ n'a été ouverte avant ce gel.

### B1 — substrat déterministe et partition réelle des trajectoires

L'AS5600 simulé ne contient aucun bruit aléatoire: pour un organisme et des cibles
donnés, sa trajectoire est déterministe; la graine d'exécution n'affecte que les autres
capteurs. La quantification vaut exactement `0,087890625°`. Une réplication privée exige
donc une trajectoire différente, pas une nouvelle graine.

Chaque motif possède douze instances de 32 pas. Les waypoints et durées de segments
ci-dessous gèlent exhaustivement leurs cibles. Toutes démarrent depuis 90°, finissent à
90°, restent dans `[30°,150°]` et coûtent 240°.

```text
impulsion waypoints: 150,90,30,90
durées i0..i11:
[8,8,8,8] [5,11,7,9] [6,10,6,10] [7,9,5,11]
[9,7,11,5] [10,6,10,6] [11,5,9,7] [4,12,8,8]
[9,4,11,8] [8,8,4,12] [12,8,8,4] [6,8,12,6]

renversement waypoints: 60,90,120,90,60,90,120,90
durées i0..i11:
[4,4,4,4,4,4,4,4]
rotations 0..7 de [2,3,4,5,6,5,4,3]
[1,7,1,7,1,7,1,7] [7,1,7,1,7,1,7,1]
[2,6,2,6,2,6,2,6]

micro waypoints: 75,90,105,90 répété quatre fois
durée i0: [2]×16
pour i1..i11: [2]×16, avec la position (i−1) portée à 3 et
la position ((i−1)+5) mod 16 portée à 1
```

Rôles sans recouvrement, identiques pour les trois motifs:

- i0: protection;
- i1: calibration;
- i2..i9: apprentissage;
- i10..i11: banque privée;
- faute: i10..i11 appariées, actionneur modifié.

La porte de contenu exige des digests de plan et couples `(digest, step)` disjoints entre
rôles normaux. Pour chaque organisme, aucune suite AS5600 de deux rôles différents ne
peut être égale à `1e-9`. Provenances et digests de session restent également disjoints.

### B2 — protection et calibration séparées

Les 24 trials d'apprentissage sont ajustés; les trois trials de protection décident seuls
les acceptations; les trois trials de calibration calculent seuls le facteur conformel;
les six trials privés mesurent seuls la compétence. Aucune trajectoire ne remplit deux
fonctions.

La calibration reste conditionnée aux acceptations antérieures: sa garantie est
approximative, pas conforme exacte. Sa taille effective est exportée à chaque checkpoint.

### B3 — bases gelées et comparaison équitable

`B2` conserve les treize features LIFE et l'ajustement pair/impair historique.

`B2'` utilise les mêmes treize features et `alpha=1,0`, mais ajuste les 32 transitions
des mêmes trials que M et utilise le même ensemble de protection que M.

Chaque membre de M utilise dix-huit features analytiquement normalisées:

1. les treize features LIFE, dans leur ordre gelé;
2. `(previous_angle_delta/12)²`;
3. `error×previous_angle_delta/(160×12)`;
4. `command_delta×previous_angle_delta/(160×12)`;
5. `abs(previous_angle_delta)/12`;
6. `(clip(error,−12,12)/12)×(previous_angle_delta/12)`.

M diffère donc de B2' par cette base enrichie, le bootstrap par trial et l'agrégation.
H2 compare M à B2' avec le seuil 5 %. M contre B2 historique reste descriptif, hors Holm.

### B4 — critère J1, incertitude et fautes

H0 compare M à la persistance B0 sur l'angle et `Δangle`; H1 compare M au prior physique
sur les deux métriques; H2 compare M à B2' sur les deux. La famille Holm primaire contient
exactement ces six tests. Chaque test exige au moins 16/24 favorables, une moyenne
favorable par régime et Monte-Carlo unilatéral `p_corrigé<=0,05`. H1 conserve 15 % et H2
5 % sur les deux métriques; H0 exige une moyenne strictement favorable.

La banque faute possède deux conditions appariées de même taille:

- `blocked`: angle maintenu;
- `degraded`: vitesse maximale divisée par trois.

Le détecteur trivial `abs(observed_next-current_angle)` est rapporté. M doit atteindre
ses seuils absolus séparément sur blocked et degraded et une AUROC au moins égale au
trivial. Seule degraded porte une revendication de schéma corporel. Le seuil opérationnel
TPR/FPR est choisi sur les six smoke et gelé avant test.

H4 ajoute largeur médiane `<6×MAE_privée_finale_M` et couverture `[0,80;0,98]` sur rampes,
plateaux et chaque tercile de déplacement prédit. Un intervalle constant ne suffit pas.

### B5 — plancher privilégié et plasticité conditionnelle

Le modèle diagnostique P utilise la base de M augmentée de `_limited_deg/160` et de la
vitesse articulaire normalisée. Il ne fournit rien à M, n'entre dans aucune hypothèse et
ne peut être promu.

La marge disponible vaut `(MAE_prior−MAE_P)/MAE_prior`. Si elle est `>=0,10`, M doit
accepter au moins une mise à jour; sous 0,10, M doit seulement ne pas dégrader la
protection au-delà de `1e-12`. Aucun organisme n'est filtré.

Le cas publié 18793 est rejoué hors portes avec ses paramètres exacts:
`speed=600`, `gain=12,798604369285723`, `damping=0,12651930739806627`,
`friction=0,0147`, `armature=0,0002`. Il ne compte dans aucune moyenne et détermine
seulement si le refus historique relève du modèle ou d'une absence de marge.

### B6 — spécifications numériques

Pour chaque classe rampe/plateau:

```text
sigma_bruit = 1,4826 × MAD(résidus du modèle courant sur calibration)
sigma² = variance inter-membres + sigma_bruit²
score conforme = abs(résidu)/sigma
q = quantile empirique 0,90, interpolation "higher"
intervalle = moyenne ± q×sigma
```

Aucun quantile gaussien n'est ajouté. Un membre bootstrap de poids total nul retourne
exactement le prior physique et contribue à la variance inter-membres.

La non-infériorité H3 utilise
`d_i=(MAE_best_i−MAE_final_i+0,02×MAE_initial_i)/MAE_initial_i`, puis
`monte_carlo_sign_flip_pvalue(d, alternative="greater", n_resamples=200000,
seed=2026072706)`.

L'incertitude qualifiée ici est épistémique sur un canal déterministe et quantifié; elle
ne modélise ni bruit, hystérésis ou non-linéarité d'un AS5600 physique.
