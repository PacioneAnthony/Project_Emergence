# Émergence — Tableau de pilotage

Dernière mise à jour: 2026-07-27

Codex décide des choix logiciels et expérimentaux sous D-004. Simulation uniquement
sous D-008.

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
| BODY-SCHEMA-001 | Pré-enregistrement J1 prêt sous D-047; aucun code/calcul |
| Prochaine porte | Verdict Claude Opus 5 pré-calcul BODY-SCHEMA-001 |

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

Action Codex: préserver LIFE close et attendre la revue BODY-SCHEMA-001.
Action Anthony: transmettre `docs/research/body_schema_001_review_request.md` à Claude.
Action Claude Opus 5: écrire uniquement `docs/research/body_schema_001_review.md`.
Blocage: code/calcul BODY-SCHEMA-001 et toute campagne J5 interdits avant verdict.
Toute suite REF exige protocole, monde et graines neufs.
