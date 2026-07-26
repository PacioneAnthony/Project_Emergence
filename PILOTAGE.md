# Émergence — Tableau de pilotage

Dernière mise à jour: 2026-07-26

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
| Direction | D-017: REF-002, transport sensorimoteur spatial explicite |
| Pré-enregistrement REF-002 | Gelé avant code dans `reafference_002_preregistration.md` |
| Porte courante | Revue contradictoire pré-calcul REF-002 |
| KERNEL-001 | Noyau cognitif persistant minimal implémenté sous D-018 |
| Vérification KERNEL-001 | 22 tests dédiés; 215 tests complets verts dans `.venv` |
| LIFE-001 smoke | Deux sessions MuJoCo/J0 et reprise; primitive analytique validée |
| Prochaine intégration | LIFE-001: régression/récupération et choix d'expérience |

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

## Actions par acteur

Action Codex: maintenir REF-001 close; préparer LIFE-001 sans contourner la porte
REF-002 et sans relier KERNEL-001 à un actionneur physique.
Action Anthony: aucune.
Action Claude: auditer `docs/research/reafference_002_preregistration.md` avec le prompt
exact de `CLAUDE_REVIEW_REQUEST.md`.
Blocage: revue pré-calcul REF-002; aucun code, smoke 13991 ou graine 13301..13316 avant
verdict favorable et corrections intégrées. Ce blocage ne concerne pas LIFE-001 tant
qu'il n'implémente, ne calibre ni n'évalue aucun composant REF-002.
