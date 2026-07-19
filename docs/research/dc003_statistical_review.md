# Revue contradictoire DC-003 — audit statistique et méthodologique

Date: 2026-07-20. Auteur: Claude (revue contradictoire, session dédiée).
Périmètre: audit de DC-003 (gain fractionnel sur mondes randomisés), validité du critère
min–max, conception de la porte statistique appariée et du prochain protocole.
Contrainte respectée: aucun calcul lancé, aucun fichier de campagne modifié; le verdict
historique de DC-003 (non promu) n'est pas réinterprété.

Fichiers audités: `learning/developmental_curiosity.py`,
`learning/curiosity_benchmark.py`, `learning/interventional_curiosity_benchmark.py`,
`learning/fractional_curiosity_benchmark.py`, `scripts/research/run_fractional_curiosity.py`,
`docs/research/developmental_curiosity_probe.md`,
`data/processed/experiments/developmental_curiosity_003/{summary.md,metrics.json}`,
tests associés.

## A. Verdict exécutif

DC-003 contient un signal apparié réel et fort contre babbling et round-robin (20/20,
test des signes p ≈ 2·10⁻⁶), et le critère min–max était effectivement invalide —
doublement: il ignore l'appariement et il était structurellement insatisfiable à cause du
plancher d'erreur 0.10. Mais le récit « quasi-succès » omet un fait central:
**regional_lp, le contrôle historique rejeté, bat fractional sur la métrique primaire dans
15 mondes sur 20** (0.1056 contre 0.1067), et le benchmark fournit à la politique un gain
interventionnel **sans aucun bruit d'évaluation**, ce qui rend DC3-H2 quasi tautologique.
Décision: réplication inchangée sur 6301..6320 avec porte appariée pré-enregistrée, suivie
obligatoirement d'un DC-004 durci (ancres bruitées, layout permuté, contrôle
informationnel) avant toute simulation visuelle. Ni abandon, ni retouche d'algorithme.

## B. Problèmes méthodologiques par gravité

### Gravité 1 — regional_lp exclu de la porte d'efficacité

DC3-H1 ne compare fractional qu'à babbling et round-robin. Or, d'après `metrics.json`, la
différence appariée fractional − regional_lp sur l'erreur structurée est **défavorable sur
15/20 mondes** (moyenne +0.0011, ~1 % relatif; pire cas graine 5316: +0.0140). L'avantage
réel de fractional sur regional_lp n'est pas l'apprentissage mais l'évitement du bruit
(4.90 % contre 13.55 %) — et une partie de cet écart est mécanique: regional_lp explore
avec ε = 0.2 contre ε = 0.05 pour fractional, ce qui lui impose un plancher de visites en
zone bruit (~0.2 × largeur de la bande ≈ 4–5 points). Le titre honnête de DC-003 est
« fractional égale le LP régional en apprentissage tout en visitant 2.8× moins le bruit »,
pas « fractional bat ses baselines ».

### Gravité 1 — le gain interventionnel est un oracle sans variance

Dans `curiosity_benchmark.py` (`ContinuousLearningWorld.intervene`), le troisième retour
(`observed`, moyenne des observations bruitées) est **jeté** par le harnais DC-003
(`fractional_curiosity_benchmark.run_condition`): la composante stochastique du monde
(`noise_table`) n'atteint jamais aucune politique. Les ancres utilisent `anchor_noise`,
fixé une fois par point de grille — donc en zone bruit, `before == after` exactement et le
gain fractionnel vaut 0 de façon déterministe. La « zone aléatoire » est en réalité une
zone déterministe inapprenable; DC3-H2 mesure l'évitement d'une région où le signal de la
politique est un zéro parfait, garanti par construction. Corollaire grave pour le
transfert: le clip `max(before − after, 0)` (`developmental_curiosity.py`,
`FractionalInterventionalCuriosity.score_components`) créerait un **biais positif
systématique en zone bruitée** dès que l'évaluation d'ancre devient stochastique
(mini-batchs, JEPA réel) — précisément le régime jamais testé.

### Gravité 1 — plancher d'erreur et compression

L'erreur structurée a un plancher analytique de 0.10; fractional est en moyenne à 0.0067
au-dessus, et sur les mondes faciles toutes les politiques saturent (≈ 0.1000–0.1005, y
compris babbling à 0.1005 sur la graine 5301). Le critère min–max exigeait donc
`max(fractional) < 0.1005`, c'est-à-dire saturer le plancher à 0.5 % près sur les 20
mondes, y compris ceux à `structured_tau = 40`. La porte n'était pas seulement mal
adaptée: elle était **vacueuse**. Le plancher compresse aussi les tailles d'effet et rend
les moyennes relatives (17.79 %) flatteuses — l'essentiel du gain vient de quelques mondes
difficiles (5302: 0.089 d'écart; 5318: 0.070).

### Gravité 2 — le benchmark encode partiellement le comportement recherché

Trois mécanismes:

1. la métrique `structured_error()` est une fonction décroissante de l'étalement des
   visites dans la bande structurée — exactement ce que la pression de couverture
   `sqrt(1 + evidence/8)` optimise, pression ajoutée après le diagnostic « bande étroite »
   de DC-002 sur la même famille de mondes. Les graines neuves protègent contre
   l'overfitting aux graines, pas à la famille — DC-003 est la troisième itération dessus;
2. le layout est monotone sur tous les mondes (base à gauche, structuré au milieu, bruit à
   droite) et home = 0.10 est toujours dans la base (`base_limit ≥ 0.20`): l'expansion de
   frontière depuis home rencontre géométriquement le structuré avant le bruit. La
   « progression développementale » de DC3-H3 est en partie un manipulation check du
   couple home/frontier, pas une émergence;
3. le monde n'a ni oubli ni interférence: l'exposition ne fait que croître, aucun gain
   n'est jamais négatif. Idéalisation forte par rapport à tout apprenant réel.

### Gravité 2 — asymétrie d'information non contrôlée

Fractional reçoit `(before, after)`; les contrôles ne reçoivent que `after`. C'est le
mécanisme testé, donc défendable, mais le protocole confond alors deux contributions: la
valeur de l'**information** interventionnelle et la valeur de la **politique** qui
l'exploite. Un contrôle « regional_lp nourri au gain before−after » est nécessaire pour
les séparer. Noter aussi que le pré-enregistrement DC-002 disait les contrôles « exposés
aux mêmes résultats avant/après » — le code ne le fait pas; divergence mineure mais
réelle.

### Gravité 3 — écart doc/code sur le 20/20

`run_fractional_curiosity.py` ne vérifie que la **moyenne** des différences appariées, pas
les 20/20 signes revendiqués dans le probe doc. Les vérifications ponctuelles dans
`metrics.json` confirment la revendication (y compris les cas serrés 5301 et 5313 face au
round-robin), mais elle n'est produite par aucun code — à automatiser dans le prochain
script.

## C. Audit du code et des risques de fuite

Ce qui est **correct**:

- mondes réellement appariés: même graine → mêmes paramètres cachés (`seed + 300_000`),
  instance fraîche par condition, même graine de politique (`seed + 400_000`);
- budgets identiques: 300 interventions × 4 échantillons pour les quatre conditions;
- la politique ne voit ni `base_limit`, ni `noise_limit`, ni l'exposition de l'oracle;
- les métriques oracle (`structured_error`, `noise_fraction`, allocation) utilisent les
  vraies frontières de chaque monde, identiquement pour toutes les conditions;
- les tests couvrent le déterminisme, le budget exact et les bornes de paramètres.

Ce qui constitue une **fuite ou un avantage de fait**:

- l'oracle de gain sans variance décrit en B — la fuite principale: le monde répond à la
  question « est-ce apprenable ? » sans bruit;
- les ancres de candidats {0, 0.10, 1.0} injectées à chaque tour dans le choix de
  fractional, qui garantissent la disponibilité permanente de home (asymétrie de
  candidature face aux baselines, pas d'information);
- la circularité partielle métrique / pression-de-couverture.

Aucune fuite des frontières ou des paramètres cachés vers la politique n'a été trouvée.

## D. Interprétation correcte de DC-003

**Vrai signal, mais circonscrit, et preuve insuffisante pour la revendication implicite.**

Le signal réel: un ordonnanceur à gain fractionnel évite presque totalement une région
inapprenable (4.9 % du budget) sans payer de coût d'apprentissage face aux baselines
naïves — apparié, répliqué sur 20 mondes hétérogènes, sign test p ≈ 2·10⁻⁶, dz ≈ 1.0 face
au babbling. Ce n'est pas un artefact pur: babbling et round-robin subissent les mêmes
mondes et le même plancher.

La preuve insuffisante: la supériorité sur **l'ensemble** des contrôles n'existe pas
(regional_lp fait mieux sur l'erreur), et l'évitement du bruit est démontré uniquement
dans un régime où le signal de non-apprenabilité est noiseless et déterministe.

Sur le critère min–max: oui, il était invalide dans un protocole apparié hétérogène — il
teste l'homogénéité des mondes, pas l'effet de la politique — et le plancher le rendait de
surcroît insatisfiable. Le refus de réinterpréter DC-003 après coup était la bonne
décision; cette revue ne modifie pas le verdict historique, elle définit la suite.

## E. Prochain protocole pré-enregistrable

### DC-003R — réplication strictement inchangée

Monde, politiques, budgets, coefficients identiques; seul le script d'analyse change.

- **Graines**: 6301..6320, jamais utilisées, conformes au plan initial.
- **Budget**: 1 200 échantillons = 300 interventions × 4, quatre conditions inchangées.
- **Hypothèses gelées**:
  - **R-H1 (efficacité, primaire)**: réduction relative appariée moyenne de l'erreur
    structurée ≥ 10 % face à babbling **et** face à round-robin. Test: permutation exacte
    par retournement de signe sur les 20 différences appariées (2²⁰ = 1 048 576
    affectations, énumération exhaustive), unilatéral, correction de Holm sur les deux
    comparaisons, α famille = 0.05. Exigence additionnelle: borne inférieure de l'IC
    bootstrap BCa à 95 % (10 000 rééchantillons de mondes) de la réduction relative
    moyenne > 0.
  - **R-H1b (non-infériorité face à regional_lp)**: moyenne appariée
    (erreur_fractional − erreur_regional_lp) ≤ 5 % relatif, testée par la même permutation
    en cadre de non-infériorité. Marge fixée maintenant, avant le run, comme la moitié de
    l'effet minimal de R-H1; choisie en connaissance des données de développement — la
    protection est qu'elle s'applique à des graines vierges.
  - **R-H2, R-H3, couverture, stabilité**: inchangées par rapport au gel DC-003, avec en
    plus un test de permutation apparié sur la fraction bruit face à babbling.
- **Taille d'effet minimale**: 10 % relatif (déjà gelée); dz et rank-biserial rapportés à
  titre descriptif, sans rôle de porte.
- **Promotion**: toutes les portes passent → promotion vers DC-004.
- **Arrêt**: R-H1 échoue face aux deux baselines → arrêt de la famille d'ordonnanceurs,
  revue conceptuelle. R-H1b seul échoue → pas de promotion: la valeur ajoutée face au LP
  régional n'est pas démontrée et la piste honnête devient « LP régional + garde
  anti-bruit ».

### DC-004 — durcissement, pré-enregistré avant exécution, algorithme gelé

Nécessaire parce que DC-003R, même réussi, ne lève pas les objections de construction (B).
Quarante mondes, graines 7301..7340, mêmes budgets. Trois manipulations:

1. **ancres bruitées**: before/after perturbés par un bruit gaussien d'écart-type 0.02
   puis 0.05, pour tester le biais du clip `max(gain, 0)`;
2. **layout permuté**: sur la moitié des mondes, la bande de bruit est placée **entre** la
   base et le structuré, home restant fourni dans la base — teste si la politique sait
   franchir une région inapprenable au lieu de bénéficier de la géométrie;
3. **contrôle informationnel**: regional_lp recevant before−after comme signal, pour
   séparer information et mécanisme.

Portes DC-004: à σ = 0.05, l'erreur structurée de fractional reste sous celle de babbling
et sa fraction bruit sous 15 %; face à regional_lp+gain, non-infériorité en erreur (même
marge de 5 %) et fraction bruit strictement inférieure; tests appariés identiques à
DC-003R.

### Conditions avant simulation visuelle plus riche

DC-003R promu **et** DC-004 passé intégralement, en particulier la robustesse aux ancres
bruitées — un monde visuel réel n'offrira jamais d'oracle de gain noiseless. Un échec de
DC-004(1) renvoie en conception, pas en simulation visuelle.

## F. Modifications de code strictement nécessaires

1. **Nouveau script d'analyse** (par exemple `scripts/research/run_fractional_replication.py`
   + module `learning/paired_stats.py`): permutation exacte par signes, bootstrap BCa,
   Holm, comptage explicite des signes 20/20, non-infériorité. Le script DC-003 existant
   et ses artefacts restent intacts — le verdict historique n'est pas réécrit.
2. **DC-004**: générateur de mondes à layout permuté, option de bruit d'ancre dans
   `intervene()`, baseline `regional_lp_gain` — nouveaux fichiers, sans toucher
   `fractional_curiosity_benchmark.py`.
3. **Aucune modification** de `developmental_curiosity.py`: coefficients, frontier,
   bandwidth et pression de couverture gelés tels quels jusqu'après DC-004.

## G. Décision finale

**Répliquer, puis durcir — ne pas abandonner, ne pas retoucher l'algorithme.** DC-003R
d'abord, avec la porte appariée de la section E, car le signal apparié face à babbling et
round-robin est trop robuste pour être un artefact de graine. Mais la promotion vers la
simulation visuelle est conditionnée à DC-004, car les trois faiblesses de construction —
oracle de gain sans bruit, géométrie monotone favorable, absence de comparaison à
regional_lp — sont exactement celles qui feraient échouer le transfert. Si fractional ne
survit pas aux ancres bruitées ou ne justifie pas sa valeur face à un LP régional recevant
la même information, la conclusion honnête sera que DC-003 a validé la *mesure
interventionnelle*, pas l'*ordonnanceur*.
