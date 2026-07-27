# Émergence — Handoff de session

Date: 2026-07-27

## Instruction de reprise impérative

Lire dans cet ordre:

1. `PILOTAGE.md`
2. `SESSION_HANDOFF.md`
3. `DEVELOPMENTAL_ARCHITECTURE.md`
4. `CODEX_TASK_BRIEF.md`
5. `DECISIONS.md` — D-012 et D-013
6. `docs/research/j6_adaptive_replay_001_review.md`
7. `docs/research/j6_adaptive_replay_001_technical_stop.md`
8. `docs/research/reafference_001_preregistration.md`
9. `docs/research/reafference_001_review.md`
10. `docs/research/reafference_001_results.md`
11. `docs/research/reafference_001_analysis.json`
12. `docs/research/reafference_001_integrity.json`
13. `docs/research/reafference_001_results_review.md`
14. `docs/research/reafference_002_preregistration.md`
15. `docs/research/reafference_002_review.md`
16. `docs/research/reafference_002_smoke.md`
17. `docs/research/reafference_002_technical_stop.md`
18. `docs/research/reafference_003_preregistration.md`
19. `docs/research/reafference_003_review.md`
20. `docs/research/reafference_003_technical_stop.md`
21. `docs/research/kernel_001_spec.md`
22. `docs/research/kernel_001_implementation.md`
23. `docs/research/life_001_recovery.md`
24. `DECISIONS.md` — D-014 à D-027

REF-001 est maintenant close sous D-015/D-016. Ne relancer aucun run, ne modifier aucun seuil
et ne réutiliser aucune graine 12301..12316. La revue contradictoire des résultats est
intégrée avec cinq corrections documentaires. D-004 délègue à Codex les choix
techniques; D-008 interdit toute action physique, tout flash et tout achat.

## J6-AR001 — clôture technique

La revue pré-calcul a autorisé J6-AR001 après quatre amendements bloquants. C1–C4 ont été
intégrées avant code et calcul. L'implémentation a passé 181 tests et le smoke 11991,
notamment composition exacte des batchs, recomputabilité de `rho`, parité des suivis et
définition conditionnelle de la fraction TV.

La campagne a ensuite atteint le plafond pré-enregistré de 75 minutes pendant le run
`adaptive_replay` de 11313:

- 11301..11312: 12 triplets / 36 runs complets;
- 11313: `naive` et `uniform_50` complets, branche adaptative interrompue;
- 11314..11316: non ouvertes;
- 38 runs complets, mais seulement 12 des 16 triplets requis.

D-012 interdit l'extension du plafond, la reprise et toute analyse partielle. Aucune
porte B1/H1/H2/H3 n'a été calculée. L'hypothèse adaptative reste **non testée**, et non
rejetée. Les artefacts sont conservés uniquement pour audit technique.

## REF-001 — clôture expérimentale

D-013 passe à l'étape 3 du brief. La question est de savoir si le résidu d'un JEPA
conditionné par l'action explique le mouvement propre tout en détectant un objet dont le
mouvement est externe et indépendant.

Le pré-enregistrement `docs/research/reafference_001_preregistration.md` est gelé avant
implémentation:

- monde REF neuf avec vrai objet geom/joint MJCF sur rail horizontal;
- RNG objet distinct et corrélation absolue action–déplacement `≤0,05`;
- smoke 12991; campagne 12301..12316, n=16, maintenant complète;
- `action_jepa` contre `no_action_jepa` à capacité/calcul identiques;
- baselines simples obligatoires `pixel_change` et `pixel_change_action`;
- 12 000 images, 2 400 décisions, 4 500 pas AdamW par condition, batch 256;
- cinq banques disjointes de 128 paires par bin: calibration, self-test, externe pur,
  mixte et validation apprenant;
- seuil propre à chaque méthode/graine/bin, calibré uniquement sur le mouvement propre;
- H1: avantage d'erreur propre `≥0,05`;
- H2/H3: TPR action absolue `≥0,75/0,70` et avantage `≥0,10` face à chaque baseline;
- H4: FPR self-test globale `≤0,07`, aucun bin `>0,10`;
- six tests de supériorité sous Holm commun, IC BCa et tests exacts appariés;
- plafond 32 runs / 60 minutes, sans analyse partielle en cas d'arrêt.

La campagne complète a rendu un verdict mécanique négatif:

- smoke 12991 vert, 193 tests, projection 31,48 minutes;
- 16 paires / 32 runs complets en 31,80 minutes;
- H1 faux: `−0,00182`, IC BCa `[−0,00666; 0,00287]`, p `0,757`, 2/6 bins;
- H2 faux: TPR externe action `0,37077`; les succès face aux pixels sont non
  informatifs à cause d'un décalage de domaine, et action ne bat pas no-action;
- H3 faux: TPR mixte action `0,14266`, aucune supériorité robuste;
- H4 faux: FPR globale `0,06372`, mais max bin `0,11865`;
- gardes apprenant et indépendance vraies.

La revendication de réafférence n'est donc pas établie. REF-001 est close sans
promotion et sans retuning. La revue a reproduit tous les calculs au chiffre près.

Corrections durables: les succès pixel externes sont vides par décalage de domaine;
H4 est instable (`5/16` graines et `16/96` cellules au-dessus des plafonds); une
collision de trame sans portée existe entre deux banques sur 12312; la garde d'action
utile doit désormais être exportée; C5 n'a pas amendé le plafond et le temps consigné
exclut l'évaluation.

## REF-002 — clôture technique

D-017 maintient l'étape 3 avec une hypothèse neuve: la copie d'efférence requiert un
transport explicite de la carte spatiale par une commande **relative**, plutôt qu'une
concaténation de commande absolue au latent global.

REF-002 compare `transport_jepa` à `concat_relative_jepa`, `no_command_jepa`,
`pixel_change` et `yaw_warp`. Les banques sont appariées par strate de mouvement afin
qu'aucune baseline ne subisse le décalage de domaine de REF-001. H5 exige en plus que
permuter ou inverser les commandes dégrade le modèle gelé, preuve que l'action est
causalement utilisée.

Smoke hors protocole: 13991. Campagne: 13301..13316, 16 triplets / 48 runs prévus.
Claude Opus 5 a rendu `AUTORISER AVEC CORRECTIONS BLOQUANTES`. C1–C8 et R1–R6 ont été
intégrées additivement sous D-019.

Correction centrale: les banques strictement statiques rendaient le score normalisé
dégénéré. Elles deviennent des banques de micro-mouvement `2°`, H2 devient
SANITY-EXTERNAL descriptive, et H3 `mixed` est l'unique porte de détection. Les autres
amendements figent `yaw_warp`, l'équité effective, l'absence de fuite motrice,
l'unicité des banques, H5 et le périmètre temporel.

L'implémentation dans `learning/reafference_002.py` contient l'encodeur
`8×8×128`, trois conditions à capacité identique, transport nul identitaire, entrée
motrice pré-transition, prédicteur servo analytique, warp projectif et plans moteurs
appariés avec dérangement H5. Le smoke complet 13991 a ensuite passé toutes les gardes:
projection `48,11896` minutes, plafond initial 75 minutes non amendé, ratio temporel
`1,12630`.

La campagne a terminé 13301..13312: 12 triplets / 36 runs et 12 évaluations. La
préparation de 13313 a produit corpus, sept banques et manifeste, puis la garde
d'intégrité s'est arrêtée avant tout entraînement sur une collision bit à bit entre une
trame finale de `moving_self_calibration` et une trame finale de `mixed`. Les
provenances et états physiques étaient distincts; aucune trame du corpus ne
collisionnait avec une banque. 13314..13316 n'ont jamais été ouvertes.

D-020 clôt REF-002 comme non-résultat technique. Il est interdit de lire ou agréger les
scores des 12 triplets, de reprendre 13313 ou de modifier la garde post hoc. L'hypothèse
de transport spatial reste non testée.

## Direction active — REF-003

D-021 pré-enregistre une nouvelle tentative dans un monde et des espaces de graines
neufs. D-023 intègre le verdict Claude Opus 5
`AUTORISER AVEC CORRECTIONS BLOQUANTES`. Elle conserve les modèles, informations,
baselines, budgets, H1/H3/H4/H5 et seuils de REF-002 amendé. Les corrections portent
sur l'intégrité et la visibilité:

- disjonction bloquante des provenances, espaces RNG et digests de paires;
- collisions corpus↔banques bloquantes, collisions inter-banques descriptives;
- champ garanti analytiquement avec marge `3°` avant mesure;
- rendu contrefactuel par paire `external_only` et `mixed`, invisible aux modèles;
- effet objet `≥0,01` pour chaque paire et moyenne par bin `≥0,05`;
- aucun resampling ou remplacement après observation;
- SANITY-EXTERNAL absolue `≥0,70` et digests de l'héritage obligatoires.

Monde `REF3`, smoke 14991, campagne 14301..14316 et graine statistique 2026072701 sont
réservés et vierges. Le plafond initial de 90 minutes couvre les 1 536 rendus
contrefactuels par graine.

L'implémentation REF-003 conserve les cinq artefacts REF-002 hashés sans modification.
Elle ajoute le monde `3,6×4,1 m`, un rail `0,36 m`, une demi-largeur objet `0,32 m`,
un bearing par paire `U(−3°, +3°)`, des trajectoires sans clipping, les audits
contrefactuels isolés et un runner protégé. Onze tests dédiés et 247 tests complets sont
verts. Sur la graine d'ingénierie non réservée 14990, les 768 paires `mixed` ont un
effet minimal `0,04702` et les 768 `external_only` un minimum `0,04290`; toutes les
moyennes par bin dépassent `0,19`.

La première tentative smoke 14991 a terminé les trois entraînements puis s'est arrêtée
sur une différence d'une paire dans le multiensemble des masques warp du bin 0. Aucun
score n'a été interprété. D-024/I1 pose désormais chaque banque à l'état pré-transition
exact avec vitesse nulle; trois banques mobiles complètes sur 14990 ont ensuite six
multiensembles identiques. La tentative échouée est archivée sous
`tmp/ref3_smoke_attempt1_mask_mismatch`.

La seconde tentative s'est arrêtée avant données sur le ratio temporel
`1,275399 > 1,25`. D-025/I2 conserve seuil, opérations et nombre de mesures, mais
intercale les conditions en ordre tournant et synchronise CUDA avant/après chaque
durée. Sur 14990, le ratio devient `1,10978`. La tentative est archivée sous
`tmp/ref3_smoke_attempt2_timing_ratio`.

La troisième tentative 14991 est entièrement verte sous D-026: ratio temporel
`1,10334`, champ analytique vert avec marge résiduelle `2,22165°`, visibilité minimale
`0,15308` en externe pur et `0,05794` en mixte, zéro collision, contrefactuels
`2,70849 s`. La projection vaut `39,92741 min`; le plafond initial de 90 minutes n'est
pas amendé. Le manifeste porte les digests concordants et confirme qu'aucune graine
réservée n'était ouverte.

La campagne a terminé 14301..14302, puis s'est arrêtée pendant la préparation de 14303
sur deux paires `external_only` sous le seuil contrefactuel individuel: `0,004453` et
`0,006999 < 0,01`. 14303 n'a reçu aucun entraînement; 14304..14316 n'ont jamais été
ouvertes. Les objets étaient dans le champ, mais la preuve angulaire ne garantissait ni
absence d'occlusion ni contraste photométrique local.

D-027 clôt REF-003 comme non-résultat technique. Il est interdit de lire ou agréger les
scores 14301..14302, de reprendre 14303 ou de remplacer les paires fautives.

## Contexte durable

- J6-R001 reste clos sans promotion: uniform protège B, mais H3 échoue.
- J6-AR001 reste clos sans résultat scientifique sous D-012.
- TV-001 et `regional_lp_gain` restent gelés par D-009.
- J0/J1 physiques restent suspendus sous D-008; D-005 interdit tout nouvel essai moteur
  sur le banc v0.1.
- La clôture REF-001 est auditée sous D-016; aucune promotion n'est possible.

## KERNEL-001 — infrastructure cognitive persistante

D-018 ouvre une voie d'infrastructure parallèle à REF-002. Le paquet `cognitive/`
maintient des croyances incertaines et sourcées, segmente des épisodes sans regarder le
futur, conserve uniquement des références/digests J0, suit les compétences et produit
des propositions d'expérience sous gardes explicites.

Le replay J0 est idempotent et reprenable. Sessions, rotations d'épisodes et checkpoints
associés sont transactionnels. Une proposition ne contient aucun champ d'actionnement.

Le premier smoke LIFE-001 traverse deux sessions MuJoCo/J0 et une réouverture de base,
puis valide avec digest la primitive analytique `bounded_head_orientation`.

D-022 complète le cycle sur six graines MuJoCo hors REF: validation nominale,
régression injectée par réduction de vitesse servo, sélection auditée de
`recalibrate-servo`, redémarrage, récupération et revalidation tenue à part. Un
évaluateur à hystérésis produit les preuves sans modifier lui-même l'état; le catalogue
classe uniquement les candidates qui passent toutes les gardes et persiste l'audit.

D-028/LIFE-002 ajoute `cognitive/observed_signals.py`. Quatre sessions MuJoCo/J0
17201..17204 forment deux histoires candidates. Les événements publics
`requested_deg`/`as5600_deg` sont validés puis réduits en erreur, incertitude,
couverture, exposition aux butées et coût moteur. Ces résumés produisent les six signaux
du sélecteur et une preuve SHA-256 par candidate; aucun payload brut n'entre dans
SQLite.

Le smoke choisit `diagnose-servo`, persiste également la preuve de `wide-scan`, simule
un redémarrage avec session ouverte puis retrouve exactement les mêmes résumés, signaux
et digests par replay J0. Les 33 tests KERNEL/LIFE ciblés et les 254 tests complets sont
verts.

LIFE-002 prouve le raccord sensation→signal→choix sûr→persistance, pas une curiosité
optimale ou un diagnostic causal. La prochaine lacune est le cycle durable
proposition→exécution→résultat, aujourd'hui encore assemblé par l'appelant.

D-029/LIFE-003 porte la mémoire SQLite en v2 avec migration additive depuis v1. Une
exécution relie une proposition unique à une session J0 unique; `begin`, `complete` et
`abort` mettent à jour exécution et proposition dans une transaction. Seule une
complétion vérifiée peut poser le statut `executed`.

Le journal doit être clos, non tronqué et cohérent avec son manifeste. Le noyau relit
sa référence, recalcule le résumé LIFE-002 et refuse toute divergence de session,
digest ou valeur agrégée. `recompute_observed_history` reconstruit ainsi les histoires
sans assemblage manuel.

Le smoke 17311..17314 perd le processus pendant une exécution, la reprend, complète
quatre essais, reconstruit deux histoires, choisit `diagnose-servo`, redémarre encore et
retrouve les mêmes digests. Les doubles attributions, journaux ouverts, résultats
étrangers, sources altérées et fermetures avec exécution active sont refusés. Les
37 tests KERNEL/LIFE ciblés et les 258 tests complets sont verts.

LIFE-003 ne commande toujours rien. La prochaine tranche sûre est LIFE-004: un
adaptateur MuJoCo extérieur au noyau qui traduit uniquement des primitives autorisées
et bornées en essais J0.

D-030/LIFE-004 ajoute `sim3d/life_executor.py`, qui ne connaît que deux plans gelés:
douze pas à 40° pour `diagnose_bounded_servo` et douze pas 40°/140° pour
`scan_bounded_servo`. Il n'accepte aucune cible libre, revérifie la proposition SQLite
et le contexte de sécurité, puis crée le journal J0 et utilise LIFE-003 pour
l'attribution et la complétion.

Les graines 17421..17424 créent deux histoires de deux essais. LIFE-002 sélectionne
`diagnose-servo` depuis ces seules observations; l'exécuteur produit alors le cinquième
essai 17425. Après redémarrage, les histoires contiennent bien 3 résultats diagnose et
2 wide. Arrêt d'urgence, primitive inconnue et proposition falsifiée sont refusés avant
journal; une panne MuJoCo injectée annule journal, exécution et proposition. Les
41 tests KERNEL/LIFE ciblés et les 262 tests complets sont verts.

La boucle minimale observation→signal→proposition→simulation→J0→résultat→mémoire est
donc raccordée. Elle reste déterministe et conçue par l'ingénieur. LIFE-005 doit relier
les résultats à l'évaluation et aux transitions de compétence; toute politique apprise
ou génération ouverte de primitives demandera d'abord une revue Claude Opus 5.

D-031/LIFE-005 ajoute une évaluation de `bounded_servo_tracking` sur les deux derniers
résultats `diagnose-servo`. La métrique couvre tout le plan, transitoire compris:
erreur moyenne normalisée × 160°. Validation `≤9°`, régression `>15°`. Le seuil initial
`8°` a été rectifié avant clôture car le nominal déterministe vaut `8,1884765625°`;
les essais lents valent `47,59765625°`.

Le schéma v3 mémorise chaque application par digest. Évaluation, transitions et état
final sont atomiques; replay identique, preuve ancienne et compétence suspendue ne
peuvent pas avancer l'état. Le smoke 17501..17506 produit:
`unknown→learning→candidate→validated→regressed→learning→candidate→validated`, avec
redémarrage avant récupération. Les 45 tests KERNEL/LIFE ciblés et les 266 tests
complets sont verts.

LIFE-006 doit maintenant dériver l'ensemble des candidates depuis les compétences
inconnues/régressées. Les priorités resteront déclaratives; tout apprentissage du
curriculum demandera une revue Claude.

D-032/LIFE-006 ajoute `cognitive/needs.py`. Les besoins régressés préemptent les
inconnus, puis learning, candidate et surveillance validated; une suspension est
toujours exclue. L'urgence filtre les candidates sans modifier leurs six signaux.

Sans historique, un prior complet est persisté comme `cold_start_prior`. Dès qu'une
exécution existe, le replay LIFE-003 et l'estimateur LIFE-002 produisent
`observed_history`. Après 17601 et redémarrage, la preuve diagnose est observée et
bit-identique; la preuve wide reste froide. Validation servo active uniquement le
besoin visuel inconnu, exécuté sur 17602; une régression servo préempte ensuite ce
besoin. Un registre vide ou suspendu ne crée aucune proposition.

LIFE-006 a porté la vérification à 50 tests KERNEL/LIFE ciblés et 271 tests complets,
avant l'ajout du superviseur.

D-033/LIFE-007 ajoute `cognitive/supervisor.py` et le journal de cycles du schéma v4.
Proposition et cycle sont écrits atomiquement. Les phases `selected`, `executed`,
`complete` et `aborted` permettent de reprendre après sélection, après exécution J0 ou
après application LIFE-005 sans dupliquer les effets.

17701 reprend après sélection; 17702 reprend successivement après exécution et
évaluation. Ils produisent exactement deux propositions, deux exécutions et une
évaluation. 17711 reste sélectionné pendant l'arrêt d'urgence puis termine. 17721,
interrompu en pleine physique avec manifeste `recording`, est explicitement abandonné;
17731, bloqué avant sélection, ne crée rien. Une session ne peut plus être close avec
un cycle actif.

À la clôture de LIFE-007, les 55 tests KERNEL/LIFE ciblés et les 276 tests complets
étaient verts. La porte alors suivante était LIFE-008: éprouver plusieurs cycles et
pannes dans une campagne d'endurance bornée avant toute évolution vers des politiques
apprises.

D-034/LIFE-008 exécute réellement 64 cycles 17801..17864 avec cinq régimes périodiques.
Résultat: 64 propositions/exécutions/J0 complètes, 63 assessments, 51 redémarrages,
12 arrêts d'urgence refusés, zéro résidu actif. SQLite+WAL vaut `1 609 856` octets, J0
`356 910`, moyenne `30 730,71875` octets/cycle; intégrité `ok`.

Une seconde invocation saute 64/64 cycles et retrouve le digest
`3cab7044228bb20ec512f67e32d3de44cac7a292c51d03311c7b815d3ccf2616`
sans nouvel effet. Les 57 tests KERNEL/LIFE ciblés et les 278 tests complets sont verts.

La plomberie déterministe est désormais qualifiée. D-035 pré-enregistre LIFE-009:
une compétence ridge prédit l'effet immédiat du cou, tandis qu'une seconde ridge apprend
sur 32 organismes quel essai fine/medium/wide réduit son erreur. Huit organismes servent
à la validation et 24 neufs à la comparaison avec quatre baselines. Les banques privées,
paramètres MuJoCo cachés et métriques test sont interdits à l'inférence.

Le protocole et la demande de revue sont rédigés. Claude Opus 5 doit les revoir avant
tout code appris, smoke, génération de banque, entraînement ou calcul.

## Actions par acteur

Action Codex: préserver REF-003 close, attendre puis intégrer le verdict LIFE-009.
Action Anthony: transmettre `docs/research/life_009_review_request.md` à Claude Opus 5.
Action Claude Opus 5: écrire uniquement `docs/research/life_009_review.md`, sans calcul.
Blocage: code, smoke, banques, entraînement et calcul LIFE-009 interdits avant revue.
Toute nouvelle tentative REF exige monde non occlusible, graines neuves et revue pré-calcul.
