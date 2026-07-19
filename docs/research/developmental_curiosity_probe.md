# Curiosité développementale continue — conception et plan de validation

Date: 2026-07-17. Statut: branche expérimentale implémentée; DC-001 exécuté et rejeté.
Filiation: échec de la sonde régionale `active_exploration_probe.md`; D-002 et D-007.

## Problème corrigé

La sonde `active_exploration_001` divisait l'angle du servo en huit régions fixes et
cherchait la plus forte baisse récente de MSE latente. Cette variante a concentré la
collecte sans gain, pour trois raisons:

1. les régions du jumeau étaient statistiquement homogènes et n'offraient aucun
   différentiel utile;
2. la difficulté était définie par une partition choisie à la main;
3. la MSE latente changeait d'échelle lorsque l'encodeur était réentraîné, ce qui
   rendait le progrès partiellement non comparable entre rounds.

L'objectif n'est donc plus « aller d'un niveau facile vers un niveau difficile ».
Une expérience doit devenir intéressante relativement à l'état courant de l'agent:
familière au départ, apprenable lorsque son incertitude peut diminuer, maîtrisée lorsque
l'erreur devient faible, ou délaissée lorsque l'erreur reste irréductible.

## Mécanisme implémenté

`learning/developmental_curiosity.py` fournit un ordonnanceur indépendant du modèle et
du nombre de dimensions. Chaque expérience est décrite par un vecteur continu normalisé
état-action. Pour la tête actuelle, l'adaptateur utilise simplement:

```text
descripteur = (angle courant normalisé, angle cible normalisé)
```

Il n'existe ni classe « facile/difficile », ni frontière sémantique, ni ordre imposé.
Pour chaque candidat, l'ordonnanceur estime:

- **familiarité**: densité locale d'expériences comparables;
- **progrès**: baisse locale de l'erreur récente par rapport à l'erreur ancienne;
- **incertitude épistémique**: désaccord d'un petit ensemble bootstrap de régressions
  noyau, élevé dans les zones encore mal connues et décroissant avec les observations;
- **imprévisibilité irréductible**: erreur ou variance locale persistante malgré une
  familiarité suffisante et sans progrès;
- **habituation**: pénalité des expériences familières déjà bien prédites;
- **contrôlabilité et risque**: portes externes génériques, prévues dans l'API même si le
  jumeau rigide à un axe utilise provisoirement contrôlabilité=1 et risque=0.

Le score opérationnel est une combinaison traçable de ces termes, jamais une métrique
globale de promotion. Une frontière continue limite au départ la distance aux expériences
connues. Son rayon augmente uniquement lorsque la médiane d'erreur récente baisse par
rapport à la référence initiale. Cela produit le comportement recherché:

```text
base familière -> voisinage encore apprenable -> extension graduelle
             \-> situation maîtrisée: habituation
             \-> situation imprévisible: pénalité d'irréductibilité
```

Le bootstrap porte ici sur la surface d'erreur état-action et non sur plusieurs JEPA
complets: c'est une approximation CPU peu coûteuse. Une future promotion devra vérifier
sa calibration face à un véritable ensemble de prédicteurs, sans supposer qu'elle lui est
équivalente.

## Intégration

`learning/active_exploration.py` accepte désormais trois conditions:

- `babbling`: contrôle uniforme historique;
- `active`: learning progress régional historique, conservé pour reproductibilité;
- `developmental`: ordonnanceur continu décrit ici.

La nouvelle condition mesure l'erreur par la transformation bornée
`MSE_prediction / (MSE_prediction + MSE_copie)` plutôt qu'en MSE latente brute. Elle
conserve l'ordre du ratio prédiction/copie, reste dans `[0, 1]` lorsque la copie est
quasi parfaite et réduit la dérive d'échelle de l'encodeur. La mémoire locale est bornée
aux 2 048 observations les plus récentes pour conserver un coût en ligne fini. Les métriques par round
journalisent aussi `mastery`, `frontier`, le nombre d'observations et l'histogramme des
cibles. La campagne historique `run_active_exploration.py` reste volontairement à deux
conditions: ajouter silencieusement une troisième condition modifierait un protocole déjà
exécuté.

Exécution unitaire possible, sans constituer une campagne concluante:

```bash
.venv/Scripts/python.exe -m learning.active_exploration \
  --condition developmental --seed 4301 --device cuda \
  --output models/dev_curiosity_seed4301.pth \
  --metrics-output data/processed/experiments/dev_curiosity_seed4301/metrics.json
```

## Validation sans curriculum subjectif

Les environnements contrôlés ne servent pas à fournir des niveaux au robot. Ils jouent le
rôle de tests unitaires dont nous connaissons la réponse attendue.

### Étape A — invariants synthétiques (livrée)

Les tests `tests/test_developmental_curiosity.py` vérifient:

- refuge initial près du descripteur sûr;
- élargissement de la frontière après baisse mesurée de l'erreur;
- préférence pour une région dont l'erreur décroît;
- habituation d'une région maîtrisée;
- rejet d'une région à erreur élevée persistante et bruitée;
- réduction du désaccord bootstrap avec l'évidence locale;
- blocage par risque ou absence de contrôlabilité.

### Étape B — banc discriminant contrôlé (à pré-enregistrer)

Construire un monde continu, sans zones visibles par l'agent, contenant trois mécanismes
physiques vérifiables par l'expérimentateur: une contingence déjà simple, une contingence
structurée apprenable et un stimulus aléatoire indépendant de l'action. Comparer à budget
égal:

1. babbling uniforme;
2. round-robin + habituation, baseline obligatoire de C10;
3. learning progress régional rejeté;
4. curiosité développementale continue.

Les critères devront porter séparément sur l'allocation de temps, le gain tenu à part, la
couverture, l'évitement du bruit et la variance entre graines. Les seuils seront gelés avant
le premier run; aucun seuil n'est déduit après observation.

## Pré-enregistrement DC-001 — banc discriminant continu

Date de gel: 2026-07-17, avant toute exécution de la campagne. Statut initial:
**pré-enregistré, non exécuté**.

### Monde caché à la politique

Un axe continu `x in [0,1]` représente des expériences candidates. La politique ne reçoit
que `x` et sa propre erreur après sélection. La dynamique est lissée entre trois mécanismes
connus uniquement de l'évaluateur:

- voisinage de la base (`x` approximativement sous 0.28): contingence simple, erreur
  initiale faible et saturation rapide;
- domaine structuré (`x` approximativement entre 0.28 et 0.78): erreur initiale haute mais
  réductible par des observations locales;
- domaine aléatoire (`x` approximativement au-dessus de 0.78): erreur élevée avec bruit
  indépendant des visites, donc non apprenable.

Les transitions utilisent des sigmoïdes, pas des frontières fournies à l'agent. L'exposition
est une densité noyau continue des visites précédentes; aucune politique n'observe le nom
des mécanismes ni le compteur d'exposition de l'oracle.

### Conditions et budget

- `developmental`: implémentation continue proposée;
- `babbling`: tirage uniforme;
- `round_robin_habituation`: grille uniforme, priorité aux expériences peu visitées et
  habituation relative quand leur erreur devient basse;
- `regional_lp`: huit régions et fenêtre glissante, ablation historique rejetée.

Budget: 1 200 décisions par run, mêmes grilles candidates et mêmes réalisations de bruit
appariées lorsque c'est possible, 20 graines `5101..5120`. Aucun réseau neuronal et aucun
GPU: ce test isole l'ordonnanceur de la qualité du JEPA.

### Métriques tenues par l'oracle

- `structured_error_final`: erreur réductible moyenne finale sur une grille tenue à part du
  domaine structuré, calculée depuis l'exposition locale et sans bruit d'observation;
- `noise_fraction`: fraction des décisions dans le domaine aléatoire;
- `coverage_entropy`: entropie normalisée sur 20 bins continus;
- signature temporelle: allocation base/structuré/bruit dans les premiers 20%, les 40%
  centraux et les derniers 20% du budget.

### Hypothèses gelées

- **DC-H1 efficacité**: `developmental` réduit la moyenne de
  `structured_error_final` d'au moins 10% face à `babbling` **et**
  `round_robin_habituation`; les 20 différences appariées sont favorables en moyenne et
  les intervalles min-max des valeurs finales sont disjoints face aux deux baselines.
- **DC-H2 bruit**: sa `noise_fraction` moyenne est au moins 50% plus basse que celle de
  `babbling`, et strictement plus basse que celles de `round_robin_habituation` et
  `regional_lp`.
- **DC-H3 progression**: sur au moins 16 graines sur 20, la base reçoit plus de 50% des
  décisions du premier quintile, le domaine structuré plus de 50% des décisions des 40%
  centraux, et le bruit moins de 15% du dernier quintile.
- **Garde-fou couverture**: entropie moyenne `developmental >= 0.65`. Un échec interdit
  d'interpréter un éventuel gain comme curiosité générale.

DC-H1 est le critère principal. DC-H2 et DC-H3 testent le mécanisme; leur échec empêche une
promotion même si DC-H1 passe. Les résultats ne peuvent modifier ces seuils; toute
correction de protocole crée `DC-002` et conserve DC-001 comme résultat.

## Résultats DC-001 — 2026-07-17

Campagne terminée en 41 s CPU. Artefacts:
`data/processed/experiments/developmental_curiosity_001/`.

| condition | erreur structurée finale | fraction bruit | entropie couverture |
|---|---:|---:|---:|
| developmental | `0.2533 +/- 0.0999` | `0.0466 +/- 0.0171` | `0.7816 +/- 0.0527` |
| babbling | `0.1125 +/- 0.0021` | `0.2274 +/- 0.0133` | `0.9948 +/- 0.0015` |
| round-robin+habituation | `0.1185 +/- 0.0005` | `0.3665 +/- 0.0040` | `0.9683 +/- 0.0019` |
| learning progress régional | `0.1025 +/- 0.0009` | `0.0911 +/- 0.0094` | `0.9547 +/- 0.0053` |

- **DC-H1 REJETÉE**: la variante développementale augmente l'erreur structurée de 125%
  face au babbling et de 114% face à round-robin+habituation. Sa variance entre graines
  est également très élevée (`0.115..0.463`).
- **DC-H2 VALIDÉE**: seulement 4.66% du budget va au bruit, soit environ 80% de moins que
  le babbling, et moins que les deux autres contrôles.
- **DC-H3 REJETÉE**: 11 graines sur 20 satisfont la signature temporelle, sous le seuil
  pré-enregistré de 16. La moyenne montre bien base puis structuré, mais plusieurs runs
  retournent tardivement vers la base familière.
- **Garde-fou couverture VALIDÉ**: entropie moyenne `0.782`, au-dessus de `0.65`.

### Cause diagnostiquée

Le mécanisme réussit à reconnaître une région réellement bruitée, mais confond une
contingence structurée lente avec de l'imprévisibilité irréductible. Après quelques
observations d'une zone difficile, les membres bootstrap s'accordent sur une erreur encore
élevée: le désaccord épistémique baisse avant que la compétence ait eu le temps de
progresser. La pénalité `irreducible` domine alors le score et repousse l'agent vers la base
familière. Selon les priors bootstrap, cette boucle produit soit une bonne traversée, soit
un attracteur de refuge, d'où la forte variance.

Le test falsifie donc l'approximation centrale de DC-001: **l'accord d'un ensemble de
régressions de l'erreur ne mesure pas à lui seul si cette erreur est réductible par
apprentissage**. Il mesure surtout si la surface d'erreur courante est connue.

Conséquence D-002: aucune promotion. Le prochain protocole éventuel doit être nommé
DC-002 et estimer la réductibilité par intervention d'apprentissage: erreurs sur ancres
fixes avant/après mise à jour, ou ensemble de modèles dont le désaccord porte sur les
conséquences prédites. Il devra supprimer l'attracteur de retour au familier sans perdre
l'évitement du bruit démontré ici. Une simple retouche des poids sur DC-001 serait du
sur-ajustement au benchmark et n'est pas autorisée.

### Étape C — monde continu non annoté

Retirer les mécanismes artificiels et comparer sur des pièces et perturbations continues.
Le sélecteur ne reçoit que ses descripteurs, erreurs, estimations de contrôlabilité et de
risque. Promotion uniquement s'il bat `round-robin + habituation` et `babbling` sur au
moins trois graines avec intervalles pré-enregistrés, sans effondrement de couverture.

### Étape D — banc réel

Seulement après J0/J1/J2 et la qualification mécanique. Le risque matériel devient une
porte dure; la curiosité ne peut jamais contourner les limites servo, l'arrêt d'urgence ou
les primitives sûres.

## Limites encore ouvertes

- Le progrès reste une différence de statistiques bruitées; il faut mesurer sa calibration
  et sa sensibilité à la taille de fenêtre.
- L'erreur ratio prédiction/copie est plus comparable que la MSE brute, mais un jeu
  d'ancres rejoué avant/après chaque entraînement serait plus rigoureux.
- La contrôlabilité doit être estimée par action réelle contre action permutée, comme le
  propose la revue, avant toute campagne de promotion.
- La dérive en U observée dans les deux conditions historiques impose validation externe,
  replay équilibré ou arrêt sur validation dans la future sonde.
- L'ordonnanceur est une branche de recherche. Il ne réintègre pas le chemin critique par
  son existence; il doit battre les baselines de D-002.

## Pré-enregistrement DC-002 — progrès interventional sur ancres fixes

Date de gel: 2026-07-20, avant exécution. Statut initial: **pré-enregistré, non exécuté**.
Filiation: DC-001; priorité simulation-first D-008.

### Correction testée

DC-002 conserve exactement le monde continu caché de DC-001 mais change l'information de
progrès. Une décision sélectionne une coordonnée `x`, puis consomme quatre exemples locaux.
La même ancre déterministe est évaluée juste avant et juste après cette micro-mise à jour:

```text
gain_interventional(x) = erreur_ancre_avant(x) - erreur_ancre_après(x)
```

Le bruit propre à l'ancre est identique avant et après: il ne peut créer artificiellement
un progrès. La politique reçoit seulement `x`, les deux erreurs et leur différence. Elle
ne reçoit toujours ni les mécanismes cachés, ni leurs frontières, ni l'exposition calculée
par l'oracle.

L'ordonnanceur continu utilise la moyenne locale récente des gains, sa borne de confiance,
la familiarité, l'habituation quand erreur et gain deviennent faibles, et une pénalité
d'improductivité uniquement après plusieurs interventions à gain nul. Il ne réutilise pas
la pénalité d'irréductibilité de DC-001.

### Conditions et budget

- `interventional`: nouvelle politique DC-002;
- `babbling`, `round_robin_habituation`, `regional_lp`: contrôles inchangés dans leur
  principe et exposés aux mêmes résultats avant/après;
- 1 200 exemples par run = 300 interventions de quatre exemples;
- 20 graines de développement `5201..5220`;
- si et seulement si toutes les portes passent, réplication sans modification sur les
  graines `6201..6220`.

### Hypothèses gelées

- **DC2-H1 efficacité**: erreur structurée finale moyenne au moins 10% plus basse que
  babbling et round-robin+habituation, différences appariées favorables et intervalles
  min-max disjoints face aux deux;
- **DC2-H2 bruit**: fraction bruit au moins 50% plus basse que babbling et strictement plus
  basse que les deux autres contrôles;
- **DC2-H3 progression**: sur au moins 16/20 graines, plus de 50% des interventions du
  premier quintile sur la base, plus de 50% des 40% centrales sur le structuré et moins de
  15% du dernier quintile sur le bruit;
- **garde-fou couverture**: entropie moyenne sur 20 bins au moins `0.65`;
- **stabilité**: écart-type de l'erreur structurée interventional inférieur ou égal à
  celui de babbling.

La campagne est promue vers réplication seulement si DC2-H1/H2/H3, couverture et stabilité
passent ensemble. Toute correction ultérieure devient DC-003; aucun poids n'est retouché
après observation de DC-002.

## Résultats DC-002 — 2026-07-20

DC-002 est terminé sur les graines `5201..5220`. Aucune réplication n'a été lancée.

| condition | erreur structurée finale | fraction bruit | entropie |
|---|---:|---:|---:|
| interventional | `0.1717 +/- 0.1095` | `0.0612 +/- 0.0308` | `0.7694 +/- 0.0963` |
| babbling | `0.1125 +/- 0.0028` | `0.2143 +/- 0.0164` | `0.9874 +/- 0.0041` |
| round-robin+habituation | `0.1095 +/- 0.0007` | `0.3033 +/- 0.0071` | `0.9773 +/- 0.0031` |
| learning progress régional | `0.1019 +/- 0.0011` | `0.1198 +/- 0.0289` | `0.9415 +/- 0.0096` |

- DC2-H1 rejetée: erreur 53% au-dessus du babbling;
- DC2-H2 validée: le bruit reste fortement évité;
- DC2-H3 rejetée: 7/20 signatures;
- couverture validée, stabilité rejetée;
- promotion vers réplication: non.

La mesure avant/après corrige partiellement DC-001: plusieurs graines atteignent le
plancher (`~0.103`), mais quelques trajectoires restent catastrophiques (`jusqu'à 0.570`).
Deux défauts sont observés. Premièrement, l'agent exploite parfois une bande très étroite
du domaine structuré: une forte allocation « structurée » ne garantit donc pas sa
couverture. Deuxièmement, le gain était normalisé par le 75e percentile de ses propres
gains; lorsque ceux-ci deviennent minuscules, un résidu local est artificiellement
réamplifié. DC-002 est conservé tel quel et rejeté.

## Pré-enregistrement DC-003 — gain fractionnel et mondes randomisés

Date de gel: 2026-07-20, avant exécution. Statut initial: **pré-enregistré, non exécuté**.

DC-003 apporte deux corrections de principe:

1. valeur d'une intervention = `(avant - après) / avant`, sans normalisation endogène;
2. rendement productif divisé par `sqrt(1 + evidence_locale / 8)` afin que la politique
   couvre les contingences apprenables au lieu d'exploiter indéfiniment une seule bande.

Le test n'utilise plus un monde unique. Pour chaque graine, l'oracle tire sans les révéler:
frontière de base dans `[0.20,0.35]`, frontière de bruit dans `[0.70,0.85]`, vitesse
d'apprentissage structuré dans `[16,40]`, largeur de généralisation dans `[0.025,0.060]`
et amplitude du bruit dans `[0.15,0.35]`. Les quatre politiques partagent le même monde
par graine.

Budget et contrôles: 1 200 exemples, 300 interventions, conditions `fractional`,
`babbling`, `round_robin_habituation`, `regional_lp`, graines `5301..5320`. Réplication
inchangée sur `6301..6320` seulement si toutes les portes passent.

Hypothèses gelées:

- **DC3-H1**: erreur structurée au moins 10% sous babbling et round-robin, différences
  appariées favorables et intervalles min-max disjoints;
- **DC3-H2**: bruit au moins 50% sous babbling et inférieur aux deux autres contrôles;
- **DC3-H3**: sur au moins 16/20 graines, distance médiane à la base plus faible dans le
  premier quintile que dans les 40% centraux, majorité structurée au centre et moins de
  15% de bruit à la fin;
- couverture moyenne `>=0.65` et écart-type d'erreur inférieur ou égal à babbling.

Aucune modification après résultats; un échec arrête cette famille d'ordonnanceurs avant
simulation visuelle et déclenche une revue conceptuelle plutôt qu'un DC-004 immédiat.

## Résultats DC-003 — 2026-07-20

| condition | erreur structurée | fraction bruit | entropie |
|---|---:|---:|---:|
| fractional | `0.1067 +/- 0.0077` | `0.0490 +/- 0.0128` | `0.9032 +/- 0.0208` |
| babbling | `0.1298 +/- 0.0296` | `0.2368 +/- 0.0592` | `0.9867 +/- 0.0029` |
| round-robin+habituation | `0.1199 +/- 0.0194` | `0.3092 +/- 0.0671` | `0.9762 +/- 0.0053` |
| learning progress régional | `0.1056 +/- 0.0067` | `0.1355 +/- 0.0499` | `0.9434 +/- 0.0134` |

- gain moyen: `17.79%` face au babbling et `11.01%` face au round-robin;
- différences appariées favorables sur `20/20` mondes face aux deux baselines;
- bruit réduit à `4.90%`, DC3-H2 validée;
- progression graduelle `19/20`, DC3-H3 validée;
- couverture et stabilité validées;
- **DC3-H1 formellement rejetée** car les intervalles min-max bruts ne sont pas disjoints;
- promotion vers réplication: non, conformément au protocole.

Le résultat est scientifiquement prometteur mais la porte statistique est mal adaptée au
nouveau dispositif randomisé: comparer le maximum d'un monde difficile au minimum d'un
autre monde facile ignore l'appariement. Les différences par graine sont pourtant toutes
favorables. Ce défaut n'autorise pas à réécrire DC3-H1 après coup ni à lancer la réplication
prévue. La prochaine action est une revue statistique du protocole; toute reprise devra
pré-enregistrer un critère apparié (intervalle de confiance ou test de permutation sur les
différences) et conserver DC-003 comme quasi-succès non promu.
