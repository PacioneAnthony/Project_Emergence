# Émergence — Tableau de pilotage

Dernière mise à jour : 2026-09-12.

Ce document dit où en est le projet **aujourd'hui** : la décision active, les règles qui
tiennent, ce qui est acquis, ce qui est fermé. L'historique détaillé campagne par campagne
est dans `SESSION_HANDOFF.md`. Les arbitrages font foi dans `DECISIONS.md` : en cas de
désaccord entre ce tableau et le registre, c'est le registre qui a raison.

## Règles permanentes

- **D-004** — Codex décide des choix logiciels et expérimentaux. Il ne fait pas trancher
  l'implémentation par Anthony.
- **D-008** — Simulation uniquement : aucune action matérielle, aucun flash, aucun achat.
  **D-005** interdit tout nouvel essai moteur sur le banc v0.1.
- **D-056** — Direction : noyau résilient, apprentissage intrinsèque, développement
  incarné. La précision motrice est une sonde locale, pas un objectif.
- **D-060** — La sonde de marge s'applique **au banc** avant toute conception de
  mécanisme, et non à la variante après coup.
- **D-062** — Un seul rôle d'agent. Codex, Claude ou un autre agent sont
  interchangeables ; aucun document ne transite par Anthony pour atteindre un autre agent.
  La revue contradictoire subsiste comme fonction : elle est faite par un agent qui n'a pas
  produit le travail.
- **D-061** — Les octets bruts des sources sont l'unité d'audit. `.gitattributes` reste à
  `* -text` ; aucun attribut `text`, `eol` ni `working-tree-encoding` n'est ajouté. Une
  empreinte qui ne correspond plus signale un problème dans les octets et jamais dans le
  manifeste : on restaure les octets, on ne recalcule pas l'empreinte. Toute source gelée
  reste archivée à côté de ses résultats, convention `source_v1`.
- Tout mécanisme est comparé à une baseline simple recevant la même information. Un
  mécanisme inspiré du vivant qui ne bat pas une baseline bête n'est pas un progrès, c'est
  une complexité non payée.
- Les banques closes ne sont pas réouvertes, les sources gelées ne sont pas modifiées, et
  les acquis conservent leur niveau de preuve **et** leurs limites.

## Décision active — D-060 : changement de substrat

Anthony a retenu l'option (a) de `PROPOSITION_SUBSTRAT.md` le 10 septembre 2026. Le banc à
un axe observé par cinq scalaires n'est plus le substrat des travaux cognitifs. La vision
entre dans la boucle : l'observation devient image plus proprioception, une articulation
d'inclinaison est ajoutée au jumeau MuJoCo, et l'angle du cou cesse d'être l'état du monde
pour devenir un pointeur vers une portion du monde. L'espace sensorimoteur passe d'environ
5,3 vues à une quinzaine de cellules.

Motif. Sur les neuf campagnes de LIFE-009 à RESILIENCE-002, toutes menées sur le même
banc, la régression réussit toujours — jusqu'à 0,0795° d'erreur d'angle — et toute porte
mesurant la connaissance de soi ou la qualité d'un choix échoue ou ne se réplique pas. Le
banc ne contient pas les problèmes que ces mécanismes prétendent résoudre.

Trois capacités enchaînées, chacune opposée à son témoin simple le plus fort : **C1**
retrouver un objet désigné par son apparence, contre le retour au dernier angle vu ;
**C2** localiser un changement sous budget de mouvements, contre balayage uniforme et
différence de pixels par cellule ; **C3** conserver C1 en apprenant C2. Elles sont
promues séparément et gardent chacune leur niveau de preuve.

Critère d'abandon fixé d'avance : si C1 ne montre pas de marge exploitable entre témoin
trivial et borne supérieure, ce substrat est déclaré épuisé à son tour et aucun mécanisme
n'y est construit. C'est un résultat, pas un échec. Le seuil chiffré s'écrit **avant** que
la sonde tourne ; un seuil choisi en voyant les chiffres n'est pas une porte.

Allègement documentaire : un pré-enregistrement, un rapport, un journal par capacité. Le
développement redevient libre — déboguer, essayer et jeter sans rebaptiser chaque
correction en hypothèse ni consommer de banque confirmatoire. La confirmation est rare et
réservée à une capacité dont la marge est établie. L'allègement porte sur les documents et
jamais sur l'archive des sources gelées.

Budget mesuré le 10 septembre et non estimé : 9 242 pas/s en physique seule, 1 878 pas/s
avec rendu 128×128 (37,6× le temps réel), 18 720 images/s d'entraînement VisualJEPA sur
RTX 5080. Le goulot est le simulateur et non le GPU, d'un facteur dix : agrandir le réseau
ne coûte presque rien, collecter l'expérience coûte tout. Une campagne complète avec
vision tient dans l'heure.

## Actions par acteur

**L'agent** — étapes 1 et 2 faites le 11 septembre : l'axe d'inclinaison existe, le contrat
d'observation est à deux consignes, les quinze cellules ont du contenu et la tâche C1 est
construite et mesurée. **Étape 3 faite, trois sondes jouées.** Chacune a écrit ses seuils
avant tout chiffre, gelé ses sources avant sa banque, et joué cette banque une seule fois.

- **v1**, 60 pièces : faisabilité 54/60 = 90,0 %, borne de Wilson 79,9 % contre 80 %. Échec
  à une pièce près, et sur la borne — un défaut de puissance, puisqu'à 60 pièces le
  dispositif ne pouvait pas passer à sa propre cible.
- **v2**, 200 pièces, référence rendue sous l'éclairage de la pièce : faisabilité
  178/200 = **89,0 %**, Wilson [83,9 % ; 92,6 %]. La borne passe largement ; c'est le taux
  lui-même qui manque, **de deux pièces**. Relecture déterministe : zéro écart sur 200.

**Verdict des deux premières : REJETÉE — FAISABILITÉ.** Ce n'est pas le critère d'abandon de D-060,
réservé à une marge absente : le substrat n'est pas épuisé, c'est la tâche C1 qu'on corrige.

Les 22 échecs de la v2 tiennent à **deux objets sur huit** ; les six autres sont lus 153 fois
sur 153. Le cube orange rate 15 fois sur 15 de façon identique — référence en classe de
teinte 2, objet vu en classe 1 — et le cylindre magenta 7 fois pour une raison photométrique,
dont 5 où son descripteur est vide alors que le garde de visibilité l'avait accepté. Réparer
l'un **ou** l'autre suffisait à passer la porte.

Crainte écrite avant la v3, puis **réfutée par elle** : l'écart de succès du balayage était
tombé de +23,3 points en v1 à +6,5 en v2 pendant que la tâche devenait plus lisible, et je
m'attendais à le voir atteindre la parité. Il remonte à +11,0 en v3, l'oracle ayant progressé
plus vite que lui.

- **v3**, 300 pièces, palette aux teintes séparées de trois classes et à saturation uniforme,
  garde de visibilité mesurant dans les termes du lecteur : faisabilité 298/300 = **99,3 %**,
  Wilson [97,6 % ; 99,8 %]. **Elle passe.** Marge : témoin de mémoire 49,3 %, écart +50,0
  points [BCa +44,0 ; +55,3] à coût égal ; balayage exhaustif 88,3 %, écart +11,0 points
  [BCa +7,7 ; +14,7] pour quinze mouvements de plus.

**VERDICT DE LA v3 : MARGE EXPLOITABLE** — le premier verdict vert du programme D-060.

Le contrôle de manipulation tient : **le témoin de mémoire tombe de 86,3 % à 10,9 % quand les
objets ont bougé**, tandis que le balayage, qui n'a pas de mémoire à tromper, reste à 86,3 %
puis 90,5 %. Dans les pièces stables, mémoire et balayage marquent exactement le même score,
132 sur 153.

**Portée exacte du résultat, resserrée par la revue (correction B2).** La marge publiée est
une propriété de **C1 v3 avec `p(brassage) = 0,5`**, la palette v3, le lecteur à 24 classes et
le moteur gelé. La dissociation brassé/stable est un contrôle de manipulation, pas une
découverte indépendante : le témoin de mémoire échoue après brassage par construction, et
l'amplitude agrégée de l'écart est pilotée par une probabilité que l'agent a lui-même fixée.
Un écart perceptif de 12,4 points subsiste d'ailleurs dans les pièces stables. Les taux
agrégés et les taux conditionnels sont toujours publiés ensemble ; rien n'est extrapolé à une
autre valeur de `p`. Changer `p`, la palette, le lecteur, le garde ou le rendu exige une
nouvelle sonde de marge avant construction.

**Ce que ce verdict autorise, sous condition** : le pré-enregistrement de C1, **une fois B1
levée**. D-060 l'interdisait « avant que la marge existe » ; elle existe, mais la revue
constate qu'elle n'a pas été mesurée contre le témoin simple le plus fort disponible.

**Ce qu'il n'autorise pas** : dire que C1 résiste aux politiques simples. Le balayage résout
88,3 % des pièces sans mémoire ni apprentissage — il paie quinze mouvements au lieu d'un. Le
coin vide est « juste **et** économe », et il est étroit. Rien n'est dit de l'apprenabilité :
il y a de la place, pas la preuve qu'un mécanisme saura l'occuper.

Où se trouve la marge en succès, mesuré : le balayage perd 33 pièces que l'oracle lit, et
quand il échoue la distance qu'il retient est *plus petite* que quand il réussit — il trouve
un faux ami. C'est l'écart entre lire les pixels exacts d'un objet et lire une cellule
entière. Un mécanisme qui viserait cette marge devrait apprendre à isoler un objet de sa
cellule.

Détail : `docs/research/c1_journal.md`, entrées 1 à 9. Le prompt complet est dans
`CODEX_TASK_BRIEF.md`.

**Réserve de l'étape 1, traitée.** Le contenu ne vivait que dans la rangée centrale ;
il est maintenant placé dans les quinze cellules par `sim3d/bench2_content.py`, via le
paramètre `wall_panels` de `build_bench_mjcf`, sans toucher au banc gelé.

**Anthony** — rien de bloquant, mais une décision attend : `ANT-011` dans
`ANTHONY_INBOX.md` — ouvrir ou non la phase des mécanismes sur C1, maintenant que la marge
existe. Aucun mécanisme ne sera construit avant sa réponse. Les deux demandes matérielles de
juin, `ANT-008` (kit AS5600) et `ANT-009` (banc v1.0), restent en sommeil et sans objet sous
D-008 et D-060, avec leur propre question : les fermer, ou les garder en sommeil en vue d'un
retour au matériel ?

**Revue contradictoire** — **rendue le 12 septembre** par GPT Astra, qui n'a pas produit ce
travail. Verdict : **AUTORISER AVEC CORRECTIONS BLOQUANTES**
(`docs/research/c1_margin_review.md`). Elle a reproduit l'ordre des commits, les quinze
empreintes du manifeste v3 et tous les chiffres publiés à partir du résultat brut. Aucune de
ses recommandations n'est rejetée ; son arithmétique a été revérifiée contre les données
brutes avant intégration.

- **B1, bloquante — LEVÉE le 12 septembre.** Le témoin simple le plus fort disponible
  — « mémoriser, vérifier la seule cellule mémorisée, ne balayer qu'après réfutation » — a été
  joué sur 100 pièces neuves, `C1EpisodeV3` strictement inchangé, avec les quatre variantes
  non dominées retenues sur graines de développement. Faisabilité 99/100 ; **aucune variante
  n'est proche de l'oracle**, la plus économe gardant une marge en coût de +7,02 mouvements
  [BCa +5,53] contre un seuil durci de 3. Verdict **MARGE EXPLOITABLE**.
- **B2, bloquante** — resserrer explicitement la portée à C1 v3 à `p = 0,5`. Faite, ci-dessus.
- **P1 à P4** — à intégrer dans le pré-enregistrement de C1 une fois B1 levée : baseline
  adaptative comme comparateur primaire, séparation stricte information admissible / oracle /
  notation, distinction entre gain mnésique et gain perceptif, et gel du défaut de frontière
  de la palette plutôt que sa correction silencieuse.

**B1 et B2 sont levées, et le pré-enregistrement de C1 est écrit** :
`docs/research/c1_preregistration.md`, campagne **C1-M1**, commité avant la première ligne de
code du mécanisme. Il fixe la question, l'hypothèse, trois portes de comparaison, l'information
admissible, deux métriques, les marges, 310 graines neuves et la règle d'arrêt, et intègre
P1 à P4. **Il engage la construction, donc il est lui-même soumis à contradiction sous D-062
avant tout code de mécanisme.**

La baseline adaptative **égale le balayage exhaustif pour la moitié du prix** — 90,0 % de
succès pour 8,02 mouvements contre 15,93. Le coin laissé à un mécanisme n'est donc pas le
contraste 1 contre 16 que suggérait la v3. Sous P1, c'est elle le comparateur primaire, pas
l'oracle.

**Et il est plus étroit encore que cela, par une objection que l'agent porte contre son propre
travail.** Le repli de cette baseline visite les quatorze cellules restantes sans jamais
s'arrêter. Une politique qui s'arrête au premier appariement suffisant coûterait **4,52
mouvements au lieu de 8,02**, ramenant la marge en coût contre l'oracle de 7,02 à **3,52**.
B1 survit — 3,52 reste au-dessus du seuil durci de 3 — mais la moitié de l'espace annoncé
était un artefact de la baseline. Cette politique devient la **porte 3** du
pré-enregistrement, jamais une simple référence.

Et une règle de vérification triviale est déjà un **détecteur de changement quasi parfait** :
elle accepte la réponse mémorisée dans 90,9 % des pièces stables et 4,4 % des pièces brassées.
« Se souvenir, et ne vérifier que lorsque c'est utile » s'écrit donc en trois lignes. Les
erreurs qui restent sont perceptives et non mnésiques — les politiques adaptatives réussissent
mieux quand les objets ont bougé (93,3 %) que quand ils sont restés en place (87,3 %), parce
qu'une pièce stable leur fait hériter des erreurs de lecture de la mémoire.

**Blocage** — aucun.

## Suivre les expériences en direct

```
.venv/Scripts/python.exe -m scripts.research.c1_live
```

puis ouvrir http://127.0.0.1:8765/ — ou la configuration `c1-live` du navigateur intégré.
La page montre en direct ce que voit la tête, à la résolution exacte de l'agent ; la pièce
vue de derrière le robot, avec l'axe du regard et les bords du champ tracés dans la scène ;
les quinze cellules, la phase en cours, la consigne contre l'angle réel, et une alerte si
la tête s'arrête loin de sa cellule ou si l'état de la simulation cesse d'être fini.
L'affichage tourne à 0,3 fois le temps réel, le vrai servo étant trop rapide pour l'œil.

Sous la grille, quatre graphes suivent les épisodes à mesure qu'ils s'accumulent. Deux
répondent à « est-ce que ça progresse ? » : le taux de succès cumulé par politique, avec
son intervalle de confiance à 95 % et le niveau du hasard, et le nombre de mouvements par
épisode — les deux quantités que la sonde de l'étape 3 comparera entre témoin et oracle.
Deux répondent à « la simulation fait-elle quelque chose d'absurde ? » : l'écart de
pointage à chaque arrêt face au seuil d'alerte, et la visibilité de l'objet le moins
visible de chaque pièce face au seuil du garde. Tant que seul l'oracle répond, les deux
premiers sont plats par construction : rien n'apprend encore.

Elle regarde sans jamais modifier l'expérience : un test vérifie qu'un épisode observé,
rendu à chaque pas, produit exactement les mêmes images et le même résultat qu'un épisode
non observé. La réponse y est pour l'instant donnée par l'oracle — une démonstration du
déroulé, pas une politique ; la sonde de l'étape 3 s'y branchera.

## Acquis conservés

Aucun n'est promu à une qualification universelle ; le registre du noyau reste candidat.

### Infrastructure cognitive persistante — KERNEL-001 et LIFE-001 à LIFE-008 (D-018 à D-034)

Noyau persistant : croyances sourcées et incertaines, segmentation d'épisodes sans regard
sur le futur, suivi de compétences, propositions sous gardes explicites, replay J0
idempotent et reprenable, schéma mémoire v4 avec migrations additives vérifiées. La boucle
observation → signal → proposition → simulation → J0 → résultat → mémoire est fermée et
transactionnelle.

L'endurance LIFE-008 a exécuté 64 cycles réels : 64 propositions et exécutions complètes,
63 évaluations, 51 redémarrages, 12 arrêts d'urgence refusés, zéro résidu actif. Une
seconde invocation saute 64/64 cycles et retrouve le digest
`3cab7044228bb20ec512f67e32d3de44cac7a292c51d03311c7b815d3ccf2616` sans nouvel effet.

Limite : cette plomberie est déterministe et conçue par l'ingénieur. Elle ne démontre
aucune politique apprise, aucune curiosité optimale, aucun diagnostic causal et aucune vie
physique continue.

### Prévision corporelle persistante — BODY-SCHEMA-002 (D-053)

Validation sur six organismes neufs : MAE moyenne F **0,435° à un pas**, contre 1,433°
pour le prior et 4,326° pour le témoin sans action B3 ; **0,579° à 0,5 s**. Toutes les
portes de prévision, de déroulement et de reprise sont vertes. Les six paquets F de
développement sont activés dans leurs mémoires ; prédictions servies et continuation
exactes après redémarrage.

Limites : la calibration E et la détection d'actionneur A restent **non qualifiées**. La
validation porte sur de nouveaux organismes mais des formes de commande connues — ce n'est
pas une confirmation scientifique. Reprise physique intra-essai non qualifiée.

Rapport : `docs/research/body_schema_002_results.md`.

### Apprentissage cumulatif — CUMULATIVE-001 (D-055)

Six vies de développement puis 12 vies neuves A→B→A→C complètes, recette gelée. Réseau
avec rejeu : MAE finale A/B/C **0,079515°**, soit −53,19 % contre le réseau naïf et
−77,92 % contre la ridge cumulative. Retour en A : erreur réduite de **69,93 %** en
moyenne par vie face à une instance neuve. Reprises CUDA exactes sur 18 vies × deux
réseaux. Choix avant échéance validé sur 192 situations : 190 réussites, utilité 47,031°
contre prior prudent 38,125° et ridge 41,667°.

Limites : le contrôle d'orientation v1 est **négatif** et conservé comme tel — aucun gain
de trajectoire et davantage de commandes. L'oubli naïf est généralement faible : aucune
preuve d'oubli catastrophique corrigé. Le gain comportemental n'est pas attribuable au
seul rejeu. Le candidat neuronal est sauvegardé, pas activé dans `CognitiveKernel`.

Rapport : `docs/research/cumulative_001_results.md`.

### Récupération après rupture — RESILIENCE-001 (D-057)

Service neuronal dans la mémoire SQLite du noyau, archives, détecteur, sous-objectifs de
récupération, plasticité temporaire, commits atomiques. V3 : six vies de développement
puis 12 vies de validation neuves, toutes les portes prévues passent. 24 changements
détectés au premier essai, zéro fausse alarme initiale, 24 sous-objectifs clos,
12 rappels, 12 reprises interprocessus exactes. Post-rupture : utilité 16,782° contre naïf
16,100° (+4,24 %) et mémoire récente 11,354° (+47,81 %). Réussite 93,52 % pendant la
récupération, 95,14 % au dernier checkpoint.

Limite prioritaire : en validation, life-04 ne réussit que **50 % des choix** après
12 essais malgré une MAE de 0,0815°. Une clôture de sous-objectif prédictif ne prouve donc
pas une compétence fonctionnelle retrouvée. Au retour, le rappel ne domine pas toutes les
mesures. Aucune autonomie ouverte n'est revendiquée.

Rapport : `docs/research/resilience_001_results.md`.

### Persistance du besoin et du choix — RESILIENCE-002 (D-059)

Prédiction terminale, promesses avant action, résultats vécus, besoin et sélection de
catégorie persistés atomiquement dans le noyau ; 18 reprises interprocessus exactes sur
les six vies de développement et les douze de validation.

Résultat négatif conservé, et c'est le point important : le gain actif **+17,77 % en
développement s'inverse à −15,20 % en validation** contre cycle fixe. Réussite finale
active 99,31 %, pire vie 91,67 %, mais utilité/oracle 71,18 % sous le seuil de 80 %. Cycle
fixe 100 %/80,56 %, uniforme 100 %/74,00 %. **Le choix actif n'est pas promu** ; le cycle
reste la référence, sans qualification universelle. Le moniteur d'honnêteté échoue :
22 clôtures contredites sur 57 tous checkpoints, 4 sur 39 après apprentissage — les deux
dénominateurs sont explicités.

Rapport : `docs/research/resilience_002_results.md`.

## Fermé sans promotion

Ces campagnes ne sont ni réouvertes, ni réglées, ni recalculées. Leurs conclusions, y
compris négatives, restent valides dans leurs limites déclarées. Un **non-résultat
technique** signifie que l'hypothèse n'a pas été testée, et non qu'elle est rejetée.

| Campagne | Verdict | Cause |
|---|---|---|
| J6-R001 | Clos sans promotion | Valeur de rétention établie sur B, mais H3 échoue |
| J6-AR001 | Non-résultat technique (D-012) | Plafond de 75 min atteint pendant 11313 ; 12 triplets sur 16 requis |
| TV-001, `regional_lp_gain` | Gelés (D-009) | — |
| REF-001 | Clos sans promotion (D-015/D-016) | H1 `−0,00182`, H2 TPR `0,37077`, H3 TPR `0,14266`, H4 max bin `0,11865` : les quatre échouent |
| REF-002 | Non-résultat technique (D-020) | Arrêt d'intégrité avant entraînement sur 13313 : collision bit à bit révélant une manipulation visuellement nulle |
| REF-003 | Non-résultat technique (D-027) | Arrêt sur effet contrefactuel `0,004453` et `0,006999 < 0,01` : la preuve angulaire ne garantit ni l'absence d'occlusion ni le contraste local |
| LIFE-009 | Non-résultat de conception (D-037) | Marge oracle `2,383 %` au smoke, contre les `10 %` exigés |
| LIFE-010 | Clos (D-040) | `probe_step_hold` devient inéligible, risque `0,75 > 0,50` |
| LIFE-011 | Clos (D-043) | Marge settling minimale `4,4039 % < 5 %` sur 18496 |
| LIFE-012 | Clos (D-046) | Portes 4 à 6 rouges ; marge médiane `4,9404 %`, oracle myope non majorant. Ferme la famille LIFE |
| BODY-SCHEMA-001 | Clos (D-049) | Portes 7 et 8 rouges : cellules conditionnelles hors `[0,80 ; 0,98]` sur quatre organismes, détecteur battu par le mouvement trivial |
| Famille à gain fractionnel | Histoire (D-009) | `developmental_curiosity.py`, `fractional_curiosity_benchmark.py`, `pooled_curiosity.py` : une reprise exigerait une hypothèse neuve, pas un réglage |

Diagnostic transversal de la famille LIFE : la compétence n'est plastique nulle part et
l'oracle myope n'est pas un majorant. C'est ce motif, répété neuf fois, qui a conduit à
D-060.

## Données hors Git à ne pas perdre

Les dossiers de campagne sont exclus de Git et ne seraient reproductibles qu'au prix d'un
recalcul complet.

| Dossier | Contenu |
|---|---|
| `data/processed/experiments/resilience_001` | environ 339 Mo, données et noyaux |
| `data/processed/experiments/resilience_002` | environ 112,9 Mo |
| `data/processed/experiments/cumulative_001` | poids après C, corpus, checkpoints B avec sondes de reprise, courbes, choix bruts |
| `data/processed/experiments/body_schema_002_r2_*` | artefacts de développement et de validation |
