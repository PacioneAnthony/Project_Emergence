# Émergence — Tableau de pilotage

Dernière mise à jour: 2026-09-10

Codex décide des choix logiciels et expérimentaux sous D-004. Simulation uniquement
sous D-008.

## Décision active — D-060 : changement de substrat

Anthony a retenu l'option (a) de `PROPOSITION_SUBSTRAT.md` le 10 septembre 2026. Le banc
à un axe observé par cinq scalaires n'est plus le substrat des travaux cognitifs. La
vision entre dans la boucle et une articulation d'inclinaison est ajoutée au jumeau
MuJoCo : l'observation devient image plus proprioception, et l'espace sensorimoteur passe
d'environ 5,3 vues à une quinzaine de cellules.

Motif : sur les neuf campagnes de LIFE-009 à RESILIENCE-002, la régression réussit
toujours — jusqu'à 0,0795° — et toute porte mesurant la connaissance de soi ou la qualité
d'un choix échoue ou ne se réplique pas. Le banc ne contient pas les problèmes que ces
mécanismes prétendent résoudre.

Trois capacités enchaînées, chacune opposée à son témoin simple le plus fort : C1
retrouver un objet désigné par son apparence ; C2 localiser un changement sous budget de
mouvements ; C3 conserver C1 en apprenant C2.

**Règle contraignante nouvelle.** La sonde de marge s'applique au banc avant toute
conception de mécanisme. Si l'écart entre témoin trivial et borne supérieure n'est pas
exploitable, la tâche est rejetée avant qu'une ligne de mécanisme ne soit écrite. Si C1
ne montre pas cette marge, ce substrat est déclaré épuisé à son tour.

**Allègement.** Un pré-enregistrement, un rapport, un journal par capacité. Le
développement redevient libre ; la confirmation est rare et réservée à une capacité dont
la marge est établie.

Budget mesuré le 10 septembre : 1 878 pas/s avec rendu 128×128 (37,6× le temps réel) et
18 720 images/s d'entraînement sur RTX 5080. Le goulot est le simulateur, pas le GPU.

Prochaine action Codex : ajouter l'axe d'inclinaison et son contrat d'observation,
construire C1, exécuter la sonde de marge, publier ce seul chiffre, s'arrêter à la
première porte rouge. Cadrage D-056 et D-008 inchangés ; aucune action Anthony requise.
Les sections suivantes conservent les acquis antérieurs et leurs limites.

## Jalon antérieur — D-059 : RESILIENCE-002 terminé

Mémoire des résultats vécus, annonces avant action et choix d'expériences désormais
persistés atomiquement dans le noyau ; 358 tests verts, 18 reprises interprocessus
exactes sur les six vies dev et douze de validation. Registre candidat uniquement.

Résultat scientifique négatif conservé : le gain actif +17,77 % en développement
s'inverse à −15,20 % en validation contre cycle fixe. Réussite finale active 99,31 %,
pire vie 91,67 %, mais utilité/oracle 71,18 % <80 %. Cycle 100 %/80,56 %, uniforme
100 %/74,00 %. Ne pas promouvoir le choix actif ; garder le cycle comme référence,
sans qualification universelle. Le moniteur échoue : 4/39 clôtures contredites après
apprentissage, 22/57 tous checkpoints. Les deux dénominateurs sont explicités.

V1 : échec de relecture d'un score NumPy après deux commits, sources/vie archivées.
V2 : conversion float native, nouvelles banques et mêmes règles. Life-03 validation
montre une alarme tardive et une marge globale qui forcent des actions de 5° malgré
23,333° disponibles. Un succès d'action ne suffit pas à prouver la résilience.

Lire `docs/research/resilience_002_results.md`, le journal, les JSON d'analyse,
audits, diagnostics et reçus. Données sous `data/processed/experiments/resilience_002`,
environ 112,9 Mo hors Git à conserver. Budget final 618,561 s /5400 s, 19 invocations,
aucune réservation ou simulation active ; 431+885 empreintes nouvelles et 375 anciennes
vérifiées sans écart. Bancs et protocoles figés, aucune retouche des vies consommées.

Point de reprise suivant : préparer une expérience neuve qui distingue lacune
locale, changement global et validité des preuves avant de guider l'exploration.
Aucun nouveau cycle de calcul n'est lancé. Priorité : résilience et apprentissage
intrinsèque (D-056), précision motrice secondaire. Aucune action Anthony requise.
Les sections suivantes conservent les acquis antérieurs.

## Jalon antérieur — D-057 : récupération et limites de résilience

Cadrage Anthony D-056 appliqué : résilience, apprentissage intrinsèque et développement
incarné sont la direction ; la précision motrice reste une sonde locale.
RESILIENCE-001 terminé : service neuronal dans la mémoire SQLite du noyau, archives,
détecteur, sous-objectifs de récupération et plasticité temporaire, commits atomiques.

V1 arrêt technique (alias Adam corrigé/testé), sources archivées. V2 six vies complètes,
non promue : récupération fonctionnelle −9,78 % contre naïf ; validation v2 non lancée.
V3 six vies dev puis 12 nouvelles vies de validation, toutes les portes prévues passent.
24 changements détectés au premier essai, zéro fausse alarme initiale, 24 sous-objectifs
clos, 12 rappels, 12 reprises interprocessus exactes. Post-rupture : utilité 16,782°
contre naïf 16,100° (+4,24 %) et mémoire récente 11,354° (+47,81 %). Réussite 93,52 %
pendant récupération, 95,14 % au dernier checkpoint. 345 tests verts.

Limite prioritaire : validation life-04 ne réussit que 50 % des choix après 12 essais,
malgré une MAE de 0,0815°. Une clôture de sous-objectif prédictif ne prouve donc pas
une compétence fonctionnelle retrouvée. Au retour, le rappel ne domine pas toutes
les mesures. Le choix des expériences est encore imposé, la règle de récupération
est écrite ; aucune autonomie ouverte ou compréhension humaine n'est revendiquée.

Lire `docs/research/resilience_001_results.md`, son graphique, le journal, les JSON
v2/dev-v3/validation-v3 et le reçu des 345 tests. Données et noyaux sous
`data/processed/experiments/resilience_001`, environ 339 Mo exclus de Git à conserver.
Validation v3 auditée : 234 empreintes et 1728 situations. Budget final 1022,517 s
sur 5400 s, 22 invocations ; aucun processus ou réservation inachevés.

Service utilisable comme candidat expérimental persistant ; versions du registre
encore candidates, sans promotion universelle. Prochaine étape : relier besoin
interne, choix d'expériences et clôture sur fonctionnement observé, puis varier les
perturbations et leurs instants. Nouvelle variante et nouveaux cas avant calcul ;
ne pas régler sur la validation consommée ni réouvrir les anciennes banques.
Aucune intervention Anthony requise. Les sections suivantes sont historiques.

## Acquis antérieur — D-055 (mandat D-054)

Mandat d'Anthony réalisé pour ce cycle : avancées notables, calcul RTX 5080,
succès et échecs consignés. CUMULATIVE-001 : six vies de développement puis
12 vies neuves A→B→A→C complètes, recette gelée. MAE finale A/B/C du réseau avec
rejeu 0,079515° : −53,19 % contre réseau naïf, −77,92 % contre ridge cumulative.
Retour A : erreur réduite de 69,93 % en moyenne par vie face à une instance neuve.
Reprises CUDA exactes sur 18 vies × deux réseaux ; 336 tests verts.

Choix avant échéance validé sur 192 situations : 190 réussites ; utilité +23,36 %
contre prior prudent, +12,88 % contre ridge. Contrôle d'orientation v1 négatif
conservé : aucun gain de trajectoire et plus de commandes. Oubli naïf généralement
faible : aucune preuve d'oubli catastrophique corrigé. Candidat neuronal sauvegardé,
pas encore activé dans CognitiveKernel. Aucune vie physique continue revendiquée.

Lire le [bilan complet](docs/research/cumulative_001_results.md), son JSON et
`cumulative_001_log.md`. Données/checkpoints : `data/processed/experiments/cumulative_001`.
Budget consommé 496,812 s / 5400 s, aucune invocation inachevée. Ne pas relancer
les banques terminées. Prochain travail ciblé : intégration au noyau puis rupture
de dynamique observable et récupération sous nouvelle variante préspécifiée.
Les sections D-053 et « Situation actuelle » ci-dessous sont l'historique conservé ;
leurs anciennes attentes procédurales ne révoquent pas D-054/D-055.

## Acquis antérieur — D-053

**Prévision corporelle persistante réalisée.** C1–C6 intégrées sous D-052 ; la revue
est de Codex à la demande d'Anthony, en remplacement de Claude. La variante v2 passe
le développement sur six organismes, puis la validation de recette sur six autres.

Validation : MAE moyenne F **0,435° à un pas**, contre **1,433°** pour le prior et
**4,326°** pour le témoin sans action B3 ; **0,579° à 0,5 s**. Toutes les portes de
prévision, déroulement et reprise sont vertes. Les six paquets F de développement
sont activés dans leurs mémoires ; prédictions servies et continuation exactes au
redémarrage. **327 tests verts**. Environ 121 s de calcul/tests sur le plafond 3600 s.

[Rapport et limites](docs/research/body_schema_002_results.md).
Calibration E et détection A restent non qualifiées. La validation porte sur de
nouveaux organismes et des formes connues ; ce n'est pas une confirmation scientifique.
La revue reçue n'autorise ni confirmation, ni J5, ni vie cumulative A→B→A→C.

Prochaine action Codex : préparer le protocole cumulatif distinct en utilisant cet
acquis, ou le manifeste confirmatoire à nouvelles formes de commande avant sa revue.
Aucune transmission actuelle, aucun achat ni essai matériel demandés à Anthony.

## Situation actuelle

| Élément | État |
|---|---|
| J6-R001 | Clos; valeur de rétention établie sur B, aucune promotion à cause de H3 |
| J6-AR001 | Clos par D-012 comme **non-résultat technique** après plafond de 75 min |
| Intégrité J6-AR001 | C1–C4 intégrées; 181 tests et smoke 11991 verts; aucune analyse partielle |
| Direction | Étape 3 close sous D-015; prochaine hypothèse suspendue à l'audit |
| Nouveau jalon | REF-001 — séparer changement auto-produit et changement externe |
| Pré-enregistrement | Gelé dans `docs/research/reafference_001_preregistration.md` |
| Revue REF-001 | « AUTORISER AVEC CORRECTIONS BLOQUANTES »; C1–C5 intégrées sous D-014 |
| Smoke REF-001 | Vert; 193 tests; projection 31,48 min sous plafond 60 min |
| Campagne REF-001 | Complète: 16 paires / 32 runs, 31,80 min consignées |
| Résultat REF-001 | H1–H4 échouent; gardes apprenant et indépendance passent |
| Décision | D-015: variante close sans promotion ni retuning |
| Revue résultats REF-001 | `AUTORISER AVEC CORRECTIONS`; recalcul identique |
| Direction | D-017: transport sensorimoteur spatial explicite |
| REF-002 | Close sous D-020 comme **non-résultat technique**; aucune analyse partielle |
| État REF-002 | Smoke 13991 vert; 12 triplets complets; arrêt d'intégrité avant entraînement 13313 |
| Cause REF-002 | Manipulation hors champ révélée par collision; aucune collision corpus↔banques |
| Nouveau jalon | REF-003 — même hypothèse non testée, visibilité externe contrôlée |
| Pré-enregistrement REF-003 | Gelé dans `docs/research/reafference_003_preregistration.md` sous D-021 |
| Revue REF-003 | `AUTORISER AVEC CORRECTIONS BLOQUANTES`; C1–C8 intégrées sous D-023 |
| Porte courante | REF-003 close; aucune reprise ou analyse partielle autorisée |
| Implémentation REF-003 | Monde paramétrique, contrefactuels, digests et runner protégés en place |
| Vérification REF-003 | 11 tests dédiés; 247 tests complets verts; banques non réservées vertes |
| Smoke REF-003 | T3 verte sous D-026; projection 39,93 min; plafond 90 min non amendé |
| Campagne REF-003 | Arrêtée sur visibilité en préparation 14303 |
| Résultat REF-003 | Close sous D-027 comme **non-résultat technique**; aucune analyse |
| KERNEL-001 | Noyau cognitif persistant minimal implémenté sous D-018 |
| Vérification KERNEL-001 | 22 tests dédiés; 215 tests complets verts dans `.venv` |
| LIFE-001 | Validation, régression injectée, choix sûr, redémarrage et récupération verts |
| LIFE-002 | Signaux recalculés depuis quatre sessions MuJoCo/J0; preuves persistantes et reproductibles |
| LIFE-003 | Attribution proposition→session J0→résultat, reprise et reconstruction automatiques vertes |
| LIFE-004 | Boucle observation→choix→exécution MuJoCo→résultat fermée sous registre borné |
| LIFE-005 | Acquisition→régression→récupération pilotée par résultats J0, replay idempotent |
| LIFE-006 | Candidates activées par besoins persistants; froid→observé et urgences vérifiés |
| LIFE-007 | Cycle complet persistant; reprises aux frontières et abandon intra-essai vérifiés |
| Schéma mémoire | v4; migrations additives v1→v2→v3→v4 vérifiées |
| LIFE-008 | 64 cycles, 51 reprises, 12 refus sûrs, zéro résidu; toutes portes vertes |
| Digest LIFE-008 | `3cab7044228bb20ec512f67e32d3de44cac7a292c51d03311c7b815d3ccf2616` |
| Vérification KERNEL/LIFE | 61 tests ciblés; suite complète actuelle 282 tests verts |
| Revue LIFE-009 | `AUTORISER AVEC CORRECTIONS BLOQUANTES`; B1–B7 intégrées sous D-036 |
| LIFE-009 | Close au smoke sous D-037; marge oracle 2,383 % < 10 % |
| Intégrité LIFE-009 | 17991 seule; banques développement/validation/test jamais ouvertes |
| Revue LIFE-010 | `AUTORISER AVEC CORRECTIONS BLOQUANTES`; B1–B7 intégrées sous D-039 |
| LIFE-010 | Close sous D-040; step_hold devient inéligible à risque 0,75 > 0,50 |
| Intégrité LIFE-010 | Début 18191 seulement; aucune métrique ou banque réservée |
| Revue LIFE-011 | `AUTORISER AVEC CORRECTIONS BLOQUANTES`; B1–B6 intégrées sous D-042 |
| LIFE-011 | Close sous D-043; marge settling minimale 4,4039 % < 5 % |
| Intégrité LIFE-011 | Préflights verts; aucun professeur ni banque 18501+ |
| Revue LIFE-012 | Autoriser avec B1–B5; voie B intégrée sous D-045 |
| LIFE-012 | Close sous D-046; portes 4–6 rouges |
| Diagnostic LIFE | compétence non plastique partout; oracle myope non majorant |
| Revue BODY-SCHEMA-001 | Autoriser avec B1–B6; intégrées sous D-048 |
| BODY-SCHEMA-001 | Clos sous D-049; portes 7 et 8 rouges, aucune graine 19201+ |
| Acquis BODY-SCHEMA-001 | MAE 0,35..0,69°; 18793 corrigé; B2' simple ≈ M |
| BODY-SCHEMA-002 | D-053 : F persistante, développement 6/6 et validation 6/6 verts ; E/A non qualifiés |
| Prochaine porte | Protocole cumulatif distinct ou manifeste confirmatoire ; aucune campagne suivante ouverte |

## Clôture de J6-AR001

Après le smoke vert, le runner a atteint le plafond gelé pendant `adaptive_replay` de
11313. Les graines 11301..11312 ont trois conditions complètes; 11313 n'a que deux runs
complets; 11314..11316 n'ont pas été ouvertes. Le protocole exigeait 16 triplets.

Il n'y a donc ni calcul des portes, ni rapport scientifique, ni promotion, ni rejet de
l'hypothèse adaptative. Le plafond n'est pas étendu et la campagne n'est pas reprise.
Les détails auditables sont dans
`docs/research/j6_adaptive_replay_001_technical_stop.md`.

## Clôture de REF-001

REF-001 compare deux JEPA de capacité et budget identiques — avec action et avec action
mise à zéro — ainsi que deux baselines analytiques `pixel_change` et
`pixel_change_action`. Un vrai objet MJCF suit une trajectoire indépendante du
babbling; son état et ses labels ne sont jamais fournis aux modèles.

Les cinq banques tenues à part séparent calibration du seuil, test du mouvement propre,
changement externe pur, mouvement mixte et garde apprenant. La promotion exige à la fois:

- une meilleure explication du mouvement propre par l'action;
- une TPR externe supérieure aux deux baselines en externe pur et mixte;
- une FPR tenue à part basse;
- toutes les gardes d'apprentissage, visibilité, indépendance, fuite, équité et budget.

Le smoke 12991 a exécuté la répétition complète exigée par C5. La projection de
31,48 minutes tenait sous le plafond initial de 60 minutes, qui n'a donc pas été
amendé. La campagne 12301..12316 a ensuite terminé 32/32 runs en 31,80 minutes.

H1 échoue (`−0,00182`, 2/6 bins favorables), H2 échoue (TPR externe `0,37077`), H3
échoue (TPR mixte `0,14266`) et H4 échoue sur le plafond par bin (`0,11865` malgré une
FPR globale `0,06372`). Les deux apprenants apprennent et les gardes d'indépendance
passent.

La revue contradictoire reproduit tous les calculs au chiffre près. Les comparaisons
pixel « gagnées » en externe pur sont non informatives: `pixel_change` y a une TPR
exactement nulle à cause d'un décalage de domaine entre calibration tête mobile et test
tête tenue. En mixte, régime apparié, `pixel_change=0,13924` égale
`action_jepa=0,14266`. H4 révèle aussi une instabilité réelle: `5/16` graines dépassent
la FPR globale et `16/96` cellules dépassent `0,10`.

Exception d'audit sans portée décisionnelle: une trame de départ de `external_only`
entre en collision avec `learner_validation` sur 12312; aucune image du corpus
d'entraînement ne collisionne avec une banque. La garde « action utile » était
satisfaite structurellement mais sans export chiffré. C5 n'a pas été déclenché
(`amended=false`), et les 31,80 minutes excluent le temps d'évaluation.

## Clôture de REF-002

Le smoke 13991 complet était vert: projection `48,11896` minutes sous le plafond initial
de 75 minutes, ratio d'équité temporelle `1,12630` et toutes les gardes satisfaites.
La campagne a terminé 13301..13312, soit 12 triplets / 36 runs et 12 évaluations.

La préparation de 13313 s'est arrêtée avant entraînement lorsqu'une trame finale de
`moving_self_calibration` a collisionné bit à bit avec une trame finale de `mixed`.
Les provenances, pièces et RNG étaient distincts; aucune image du corpus d'entraînement
ne collisionnait avec une banque. La revue REF-003 a montré que l'objet pouvait sortir
entièrement du champ dans environ `3,06 %` des paires `mixed`: la collision révélait une
manipulation visuellement nulle, pas une simple coïncidence.

D-020 applique le contrat gelé: pas de reprise, pas de modification post hoc de la
garde et aucune lecture ou agrégation des scores 13301..13312. REF-002 ne rejette ni ne
confirme l'hypothèse. Les détails sont dans
`docs/research/reafference_002_technical_stop.md`.

## Clôture de REF-003

D-021/D-023 ouvrent un nouveau pré-enregistrement avec monde et graines neufs. Le
contraste, les modèles et les portes de REF-002 amendé restent inchangés, car
l'hypothèse n'a pas été testée. La correction porte sur l'attribuabilité:

- disjonction bloquante par provenance et digest de paire;
- collisions corpus↔banques bloquantes et inter-banques descriptives;
- visibilité garantie sur l'enveloppe avec marge `3°`, puis vérifiée par paire;
- aucune paire invisible resamplée ou remplacée après observation.

Le smoke 14991 était vert, puis 14301..14302 ont terminé. La préparation de 14303 s'est
arrêtée avant entraînement sur deux paires `external_only` dont l'effet
contrefactuel valait `0,004453` et `0,006999 < 0,01`. Les objets étaient dans le champ:
la preuve angulaire ne garantissait pas l'absence d'occlusion ou un contraste local
minimal.

D-027 applique le contrat: pas de reprise, remplacement ou analyse de 14301..14302.
REF-003 reste un non-résultat technique.

## Actions par acteur

Action Codex : conserver les artefacts et préparer le prochain protocole à partir de
la prévision persistante ; aucune nouvelle attente de la revue r2, déjà intégrée.
Action Anthony : aucune intervention requise pour le lot terminé.
Prochaine revue : uniquement après préparation du protocole distinct concerné.
Confirmation, anciennes réserves, J5, A→B→A→C et matériel restent fermés.
Toute suite REF exige protocole, monde et graines neufs.
