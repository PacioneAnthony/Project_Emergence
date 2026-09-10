# Émergence — Handoff de session

Date : 2026-09-10.

Ce document dit **comment reprendre** et **ce qui a déjà été essayé**, campagne par
campagne. L'état courant — décision active, acquis, fermetures, actions par acteur — est
dans `PILOTAGE.md` et n'est pas répété ici.

## Reprendre ici

Lire dans cet ordre, et rien de plus pour démarrer :

1. `PILOTAGE.md` — état courant et règles permanentes
2. `CODEX_TASK_BRIEF.md` — le prompt de la phase ouverte par D-060
3. `PROPOSITION_SUBSTRAT.md` — l'argumentaire du changement de substrat
4. `DECISIONS.md` — D-060, D-061 et D-062
5. `DEVELOPMENTAL_ARCHITECTURE.md` — le cadrage D-056

Le détail d'une campagne close se lit à la demande : chaque entrée de l'historique
ci-dessous nomme son rapport. Il n'y a pas de lecture préalable obligatoire au-delà des
cinq documents ci-dessus.

Ordre de travail, arrêt à la première porte rouge : ajouter l'articulation d'inclinaison et
son contrat d'observation dans `sim3d/bench_model.py` et `sim3d/bench_env.py` ; construire
la tâche C1 — retrouver un objet désigné par son apparence ; écrire le seuil de marge ;
exécuter la sonde contre le témoin trivial et une borne supérieure ; publier ses deux
chiffres. **Aucun mécanisme cognitif, aucun pré-enregistrement et aucune banque de
confirmation avant que cette marge existe.** Si elle n'existe pas, le substrat est déclaré
épuisé et on n'y construit rien.

Réutiliser sans le réécrire : le noyau persistant, `FunctionalStore`,
`learning/paired_stats.py` pour toutes les portes statistiques, `learning/visual_jepa.py`,
et le banc `sim3d/bench_model.py` / `sim3d/bench_env.py`, qui contient déjà la pièce
meublée, les panneaux contrastés, l'éclairage, l'objet externe sur rail, la caméra
embarquée de 30° et son rendu.

État au moment de la reprise : 358 tests verts. Aucun processus, aucune réservation de
budget et aucune simulation ne restent actifs sur les campagnes closes ; leurs registres
`budget.sqlite` sont soldés.

## Règles qui bloquent un commit

- **Octets bruts (D-061).** `.gitattributes` déclare `* -text` : n'ajoute aucun attribut
  `text`, `eol` ni `working-tree-encoding`. Une normalisation de fin de ligne casse en
  silence les empreintes que gèlent les manifestes — le 10 septembre elle a réécrit onze
  sources `.py` et cassé 566 références dans 113 manifestes, toutes restaurées depuis. Si
  une empreinte ne correspond plus, l'anomalie est dans les octets et non dans le
  manifeste : on restaure les octets, on ne recalcule pas l'empreinte.
- **Archive des sources.** Toute source destinée au gel est copiée à côté de ses
  résultats, convention `source_v1`. C'est cette copie qui a rendu six des onze sources
  récupérables sans reconstruction. L'allègement documentaire de D-060 ne la supprime pas.
- **Sources gelées et banques closes.** Ne pas modifier une source gelée puis appeler cela
  une reprise. Ne pas réouvrir une banque consommée, ni régler une recette sur une
  validation déjà dépensée.
- **Graines.** Graines vierges à chaque campagne ; l'unité indépendante est l'organisme ou
  la vie, jamais le tick corrélé.
- **D-008.** Simulation uniquement : aucune action matérielle, aucun flash, aucun achat.

## Historique par campagne

Ordre chronologique par décision. Chaque entrée dit ce qui a été testé, le verdict, et ce
qui reste interdit. Un **non-résultat technique** signifie que l'hypothèse n'a pas été
testée, pas qu'elle est rejetée.

### J6-R001 et J6-AR001 — rejeu adaptatif (jusqu'à D-012)

J6-R001 est clos sans promotion : la valeur de rétention est établie sur B, mais H3
échoue. TV-001 et `regional_lp_gain` sont gelés par D-009.

J6-AR001 a passé sa revue pré-calcul avec quatre amendements bloquants, puis 181 tests et
le smoke 11991. La campagne a atteint le plafond pré-enregistré de 75 minutes pendant le
run `adaptive_replay` de 11313 : 12 triplets complets sur les 16 requis, 11314..11316
jamais ouvertes. D-012 interdit l'extension du plafond, la reprise et toute analyse
partielle. Aucune porte n'a été calculée ; l'hypothèse adaptative reste **non testée**.

Détail : `docs/research/j6_adaptive_replay_001_technical_stop.md`.

### REF-001 — réafférence par résidu conditionné à l'action (D-013 à D-016)

Question : le résidu d'un JEPA conditionné par l'action explique-t-il le mouvement propre
tout en détectant un objet dont le mouvement est externe et indépendant ?

Dispositif gelé avant implémentation : monde REF neuf avec vrai objet MJCF sur rail, RNG
objet distinct, corrélation action–déplacement `≤ 0,05`, `action_jepa` contre
`no_action_jepa` à capacité et calcul identiques, baselines `pixel_change` et
`pixel_change_action` obligatoires, cinq banques disjointes de 128 paires par bin, seuil
calibré uniquement sur le mouvement propre, six tests de supériorité sous Holm commun.

Portes chiffrées avant campagne, sans lesquelles les résultats ci-dessous ne se lisent
pas : H1 avantage d'erreur propre `≥ 0,05` ; H2 et H3 TPR absolue `≥ 0,75` et `≥ 0,70`
avec un avantage `≥ 0,10` face à chaque baseline ; H4 FPR globale `≤ 0,07` et aucun bin
au-dessus de `0,10`. Plafond 32 runs / 60 minutes, sans analyse partielle en cas d'arrêt.

Campagne complète : 16 paires / 32 runs en 31,80 minutes. **Les quatre hypothèses
échouent** — H1 `−0,00182` (IC BCa `[−0,00666 ; 0,00287]`, p `0,757`, 2/6 bins), H2 TPR
externe `0,37077`, H3 TPR mixte `0,14266`, H4 max par bin `0,11865` malgré une FPR globale
`0,06372`. Les gardes apprenant et indépendance passent.

La revue contradictoire a reproduit tous les calculs au chiffre près et a produit quatre
corrections durables : les succès face aux pixels en externe pur sont **non informatifs**
— `pixel_change` y a une TPR exactement nulle par décalage de domaine entre calibration
tête mobile et test tête tenue ; en mixte, `pixel_change = 0,13924` égale
`action_jepa = 0,14266` ; H4 révèle une instabilité réelle (`5/16` graines et `16/96`
cellules au-dessus des plafonds) ; la garde « action utile » était satisfaite
structurellement mais sans export chiffré. Exception d'audit sans portée décisionnelle :
une trame de `external_only` entre en collision avec `learner_validation` sur 12312, aucune
image du corpus d'entraînement ne collisionne avec une banque.

Clos sans promotion ni retuning. Ne relancer aucun run, ne modifier aucun seuil, ne
réutiliser aucune graine 12301..12316.

Rapport : `docs/research/reafference_001_results.md`.

### REF-002 — transport spatial par commande relative (D-017 à D-020)

Hypothèse neuve : la copie d'efférence exige un transport explicite de la carte spatiale
par une commande **relative**, plutôt qu'une concaténation de commande absolue au latent
global. `transport_jepa` contre `concat_relative_jepa`, `no_command_jepa`, `pixel_change`
et `yaw_warp`, banques appariées par strate de mouvement pour supprimer le décalage de
domaine de REF-001. H5 exige que permuter ou inverser les commandes dégrade le modèle
gelé, preuve que l'action est causalement utilisée.

La revue a rendu `AUTORISER AVEC CORRECTIONS BLOQUANTES` ; C1–C8 et R1–R6 intégrées
additivement. Correction centrale : les banques strictement statiques rendaient le score
normalisé dégénéré — elles deviennent des banques de micro-mouvement `2°`, H2 devient
descriptive, et H3 `mixed` est l'unique porte de détection.

Le smoke 13991 était vert (projection `48,11896` min sous plafond 75, ratio d'équité
temporelle `1,12630`). La campagne a terminé 13301..13312, soit 12 triplets / 36 runs. La
préparation de 13313 s'est arrêtée **avant tout entraînement** sur une collision bit à bit
entre une trame finale de `moving_self_calibration` et une trame finale de `mixed`. La
revue REF-003 a montré ensuite que l'objet pouvait sortir entièrement du champ dans environ
`3,06 %` des paires `mixed` : la collision révélait une manipulation visuellement nulle,
pas une coïncidence.

13314..13316 n'ont jamais été ouvertes. D-020 clôt en **non-résultat technique**.
Interdit de lire ou d'agréger les scores des 12 triplets, de reprendre 13313, ou de
modifier la garde post hoc.

Détail : `docs/research/reafference_002_technical_stop.md`.

### REF-003 — même hypothèse, visibilité contrôlée (D-021 à D-027)

Monde et espaces de graines neufs, modèles et portes de REF-002 amendé conservés puisque
l'hypothèse n'avait pas été testée. Les corrections portent sur l'attribuabilité :
disjonction bloquante par provenance et digest de paire, collisions corpus↔banques
bloquantes, champ garanti analytiquement avec marge `3°` puis vérifié par paire, rendu
contrefactuel par paire invisible aux modèles, effet objet `≥ 0,01` par paire et `≥ 0,05`
en moyenne par bin, aucun resampling après observation.

Trois tentatives de smoke ont été nécessaires. La première s'est arrêtée sur une différence
d'une paire dans le multiensemble des masques warp du bin 0 ; D-024 pose désormais chaque
banque à l'état pré-transition exact avec vitesse nulle. La deuxième s'est arrêtée sur un
ratio temporel `1,275399 > 1,25` ; D-025 intercale les conditions en ordre tournant et
synchronise CUDA autour de chaque durée. La troisième, 14991, est entièrement verte : ratio
`1,10334`, marge de champ résiduelle `2,22165°`, visibilité minimale `0,15308` en externe
pur et `0,05794` en mixte, zéro collision, projection `39,92741` min sous plafond 90.

La campagne a terminé 14301..14302 puis s'est arrêtée pendant la préparation de 14303 sur
deux paires `external_only` sous le seuil contrefactuel individuel, `0,004453` et
`0,006999 < 0,01`. Les objets étaient dans le champ : **la preuve angulaire ne garantit ni
l'absence d'occlusion ni un contraste photométrique local minimal.** C'est la leçon qui
fonde la porte de faisabilité de D-060.

14303 n'a reçu aucun entraînement et 14304..14316 n'ont jamais été ouvertes. D-027 clôt
en **non-résultat technique**. Interdit de lire ou d'agréger 14301..14302, de reprendre
14303, ou de remplacer les paires fautives. Toute suite REF exige protocole,
monde et graines neufs.

Détail : `docs/research/reafference_003_technical_stop.md`.

### KERNEL-001 et LIFE-001 à LIFE-008 — infrastructure persistante (D-018 à D-034)

Voie d'infrastructure menée en parallèle des campagnes scientifiques. Le paquet
`cognitive/` maintient des croyances incertaines et sourcées, segmente des épisodes sans
regarder le futur, ne conserve que des références et digests J0, suit les compétences et
produit des propositions sous gardes explicites. Une proposition ne contient aucun champ
d'actionnement.

Progression, chaque tranche étant vérifiée avant la suivante :

- **LIFE-001 et LIFE-002** — raccord sensation → signal → choix sûr → persistance. Les événements
  publics sont réduits en erreur, incertitude, couverture, exposition aux butées et coût
  moteur, avec une preuve SHA-256 par candidate ; aucun payload brut n'entre dans SQLite.
- **LIFE-003** — schéma v2. Une exécution relie une proposition unique à une session J0
  unique ; `begin`, `complete` et `abort` sont transactionnels. Le noyau refuse toute
  divergence de session, de digest ou de valeur agrégée.
- **LIFE-004** — `sim3d/life_executor.py` ne connaît que deux plans gelés et n'accepte
  aucune cible libre. Arrêt d'urgence, primitive inconnue et proposition falsifiée sont
  refusés avant journal ; une panne MuJoCo injectée annule journal, exécution et
  proposition.
- **LIFE-005** — schéma v3, évaluation de `bounded_servo_tracking` sur tout le plan,
  transitoire compris. Validation `≤ 9°`, régression `> 15°` ; le seuil initial `8°` a été
  rectifié avant clôture, le nominal déterministe valant `8,1884765625°`.
- **LIFE-006** — `cognitive/needs.py`. Les besoins régressés préemptent les inconnus ; une
  suspension est toujours exclue. Sans historique, un `cold_start_prior` est persisté.
- **LIFE-007** — `cognitive/supervisor.py` et journal de cycles, schéma v4. Reprise après
  sélection, après exécution J0 ou après application, sans dupliquer les effets. Une
  session ne peut plus être close avec un cycle actif.
- **LIFE-008** — endurance réelle sur 64 cycles et cinq régimes périodiques : 64
  exécutions complètes, 63 évaluations, 51 redémarrages, 12 arrêts d'urgence refusés, zéro
  résidu. SQLite+WAL `1 609 856` octets, J0 `356 910`, moyenne `30 730,71875` octets par
  cycle, intégrité `ok`. Une seconde invocation saute 64/64 cycles et retrouve le digest
  `3cab7044228bb20ec512f67e32d3de44cac7a292c51d03311c7b815d3ccf2616`.

La plomberie déterministe est qualifiée. Elle est conçue par l'ingénieur et ne démontre
aucune politique apprise.

Spécifications : `docs/research/kernel_001_spec.md`,
`docs/research/kernel_001_implementation.md`, `docs/research/life_001_recovery.md`.

### LIFE-009 à LIFE-012 — choix d'expérience et plasticité (D-035 à D-046)

Quatre tentatives de faire apprendre à un mécanisme *quel essai réduit son erreur*. Les
quatre sont mortes sur une porte de faisabilité ou de marge, **avant d'ouvrir la moindre
banque réservée**.

- **LIFE-009** (D-037) — le smoke 17991 passe intégrité, replay, comptes, reproductibilité
  et durée, mais l'oracle n'améliore greedy que de `2,383 %` au lieu des `10 %` exigés.
  Non-résultat de conception. Aucune graine 17901..17940 ou 18001..18024 ouverte.
- **LIFE-010** (D-040) — après son propre historique, `probe_step_hold` porte
  `predicted_risk = 0,75`, au-dessus de la limite catalogue `0,50`. La garde l'a
  correctement bloqué et le professeur ne pouvait plus rejouer son carré latin. Clos sans
  métrique, reprise ni banque.
- **LIFE-011** (D-043) — les 18 préflights 18491..18496 sont verts (`risk = 0`,
  `motor_cost = 0,09375`) et la porte 5 est verte, mais la porte 6 ferme la campagne :
  médiane oracle `16,8853 %`, minimum settling `4,4039 % < 5 %` sur 18496. Le professeur,
  la plaque de chronométrage et 18501..18624 n'ont jamais été ouverts.
- **LIFE-012** (D-046) — coût commun porté à 240°, taxonomie rampe/plateau/temps mort. La
  plaque 18791..18796 passe les trois portes d'intégrité et échoue aux trois portes
  scientifiques : 18793 refuse 24/24 mises à jour, marge oracle médiane `4,9404 %`, et
  l'oracle myope perd contre round-robin sur certains organismes. Ferme la famille LIFE.

Diagnostic transversal : la compétence n'est plastique nulle part sur ce banc, et l'oracle
myope n'est pas un majorant.

### BODY-SCHEMA-001 et 002 — prévision corporelle (D-047 à D-053)

**BODY-SCHEMA-001** (D-049) — excitation fixe identique, baselines persistance/prior/ridge
et ensemble probabiliste de ridges ARX bootstrapé par trial. Le smoke 19091..19096 rend
huit portes vertes et deux rouges : M atteint une MAE `0,3476..0,6910°`, accepte
`14..17/24` mises à jour et corrige le cas 18793, mais les petites cellules
conditionnelles sortent de `[0,80 ; 0,98]` sur quatre organismes, et le détecteur par
transition ne bat pas le mouvement trivial sur toutes les fautes. Clos sans ouvrir 19201+.

**BODY-SCHEMA-002** (D-053) — F est la ridge simple B2', E ne porte que l'incertitude, A
agrège causalement les innovations sur quatre pas. La revue r2 a été rédigée par Codex à la
demande d'Anthony, en remplacement de Claude ; C1–C6 intégrées sous D-052. La v1 a arrêté
un vérificateur de reprise à liste partagée ; la v2 corrige avec test et relance complète.
Aucun réglage n'a utilisé la validation.

Résultat conservé : six organismes de développement et six de validation neufs, F
validation **0,435° à un pas** et **0,579° à 0,5 s**, portes prévision / déroulement /
persistance vertes, prévisions et prochaine mise à jour reproduites dans un autre
processus. Calibration E et agence A **non qualifiées** par paquet ; validation sur formes
connues, sans confirmation statistique ni essai d'oubli.

Rapport : `docs/research/body_schema_002_results.md`.

### CUMULATIVE-001 — apprentissage cumulatif A→B→A→C (D-054, D-055)

Mandat d'Anthony : poursuivre jusqu'à des avancées prometteuses, en documentant aussi les
échecs. Six vies de développement puis 12 vies de validation complètes, recette gelée.

Réseau avec rejeu : MAE finale A/B/C `0,079515°`, −53,19 % contre le réseau naïf et
−77,92 % contre la ridge cumulative ; toutes les portes acquisition, rétention,
récupération et reprise passent ; retour en A avec un gain relatif moyen de `69,93 %` par
vie face au réseau neuf ; reprise interprocessus exacte sur 18 vies et les deux réseaux.
Choix v2 validé sur 192 situations neuves : 190 réussites, utilité `47,031°` contre prior
prudent `38,125°` et ridge `41,667°`, avec deux échecs `speed_dominant/1` et une prudence
excessive `settling_dominant/2`.

Négatifs conservés : le contrôle d'orientation v1 ne rend aucun gain de trajectoire et
davantage de commandes ; l'oubli naïf reste généralement faible, donc aucun oubli
catastrophique n'a été corrigé ; le gain comportemental n'est pas attribuable au seul
rejeu. Le candidat neuronal est persistant et qualifié sur ce banc, pas intégré au registre
actif de `CognitiveKernel`.

Publication reproductible sans rejouer les vies : `learning.cumulative_001_publish`.
Rapport : `docs/research/cumulative_001_results.md`.

### RESILIENCE-001 — récupération après rupture (D-056, D-057)

Cadrage D-056 appliqué : résilience, apprentissage intrinsèque et développement incarné
sont la direction ; la précision motrice reste une sonde locale.

V1 arrêt technique (alias Adam, corrigé et testé), sources archivées. V2 six vies
complètes, **non promue** : récupération fonctionnelle `−9,78 %` contre naïf, validation v2
non lancée. V3 six vies de développement puis 12 vies de validation neuves, toutes les
portes prévues passent : 24 changements détectés au premier essai, zéro fausse alarme
initiale, 24 sous-objectifs clos, 12 rappels, 12 reprises interprocessus exactes.
Post-rupture, utilité `16,782°` contre naïf `16,100°` (+4,24 %) et mémoire récente
`11,354°` (+47,81 %) ; réussite `93,52 %` pendant la récupération et `95,14 %` au dernier
checkpoint.

Limite prioritaire : en validation, life-04 ne réussit que `50 %` des choix après 12 essais
malgré une MAE de `0,0815°`. **Une clôture de sous-objectif prédictif ne prouve pas une
compétence fonctionnelle retrouvée.**

Rapport : `docs/research/resilience_001_results.md`.

### RESILIENCE-002 — besoin fonctionnel et choix d'expériences (D-058, D-059)

Cycle complet : prédiction terminale, promesses avant action, résultats vécus, besoin et
sélection de catégorie persistés atomiquement dans le noyau ; 18 reprises exactes. V1
stoppée après deux commits sur un score NumPy non relisible de façon sécurisée, sources et
vie partielle conservées ; v2 convertit le score en float natif sans modifier les règles
d'apprentissage.

Résultat négatif, le plus instructif de la série : gain actif `+17,77 %` contre cycle en
développement, **inversé à `−15,20 %`** sur douze vies de validation. Réussite finale
`143/144`, pire vie `91,67 %`, mais seulement `71,18 %` de l'oracle contre le seuil de
`80 %`. Cycle fixe `100 %` / `80,56 %`, uniforme `100 %` / `74,00 %`. Le sélecteur actif
n'est pas promu. Le moniteur d'honnêteté est contredit sur `22/57` états clos, `4/39` après
apprentissage ; couverture `54,17 %`. Life-03 montre le couplage fragile : alarme tardive
sans nouveau changement physique, marge globale `3,515°` et repli vers `5°` alors que
`23,333°` étaient disponibles, malgré `12/12` réussites — un succès d'action ne suffit pas
à prouver la résilience.

Rapport : `docs/research/resilience_002_results.md`.

### D-060 et D-061 — changement de substrat, et l'incident d'audit (10 septembre 2026)

D-060 acte que le banc lui-même était le problème et ouvre le substrat visuel à deux axes.
Voir `PILOTAGE.md` pour la décision active et `CODEX_TASK_BRIEF.md` pour le prompt.

D-061 acte un incident interne sans conséquence scientifique. Le dépôt déclarait
`*.py text eol=lf` alors que les manifestes gèlent des SHA-256 des octets bruts : un commit
a réécrit onze sources `.py` en LF et cassé 566 références d'empreintes dans 113
manifestes. La cause racine est fermée par `* -text`, et les onze sources ont été
restaurées à l'octet près — six depuis les archives `source_v1`, cinq reconstruites et
certifiées par les empreintes gelées elles-mêmes. Aucune empreinte n'a été réécrite, aucune
garde assouplie, aucun résultat modifié et aucun niveau de preuve déplacé.
