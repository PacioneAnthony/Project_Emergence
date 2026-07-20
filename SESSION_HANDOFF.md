# Émergence — Handoff de session

Date: 2026-07-20

## Instruction de reprise impérative

Lire dans cet ordre:

1. `PILOTAGE.md`
2. `SESSION_HANDOFF.md`
3. `DEVELOPMENTAL_ARCHITECTURE.md`
4. `CODEX_TASK_BRIEF.md`
5. `docs/research/j6_replay_001_preregistration.md`
6. `docs/research/j6_replay_001_review.md`
7. `docs/research/j6_replay_001_results.md`
8. `CLAUDE_REVIEW_REQUEST.md`
9. `docs/research/j6_replay_001_results_review.md`, si Claude l'a déposé
10. `DECISIONS.md` et `COLLABORATION_PROTOCOL.md`

Si la revue de résultats existe, Codex applique immédiatement son verdict. Sinon, la
porte de revue reste active: aucune promotion J6, aucun retuning et aucune nouvelle
graine. D-004 délègue à Codex les choix logiciels et expérimentaux; D-008 interdit les
actions physiques, achats et flashs.

## Objectif actif

Faire auditer contradictoirement les résultats J6-R001 avant toute promotion, puis
intégrer le verdict et choisir seul la suite scientifique conforme aux règles gelées.

## Travail J6-R001 terminé

- La revue préalable `docs/research/j6_replay_001_review.md` a conclu **AUTORISER AVEC
  CORRECTIONS BLOQUANTES**.
- L'amendement pré-calcul daté du 2026-07-20 dans le pré-enregistrement reprend B1, B2
  et B3 avant toute implémentation de campagne, smoke et graine réservée.
- `sim3d/bench_model.py` accepte des lumières paramétrées et construit un vrai panneau
  damier en geoms MJCF; `sim3d/j6_domains.py` fixe A/B/C sans overlay écran-space du
  landmark. La télévision historique reste celle de `learning/tv_exploration.py`.
- `learning/j6_replay.py` implémente les corpus partagés, banques A/B/C équilibrées et
  disjointes, erreur bornée `pred/(pred+copy)`, adaptation naïve, replay uniforme et
  replay priorisé. La priorité `p_i ∝ error_i + 1e-3` est mesurée une fois à k=3 sur
  les anciens épisodes d'entraînement, puis gelée pour la session.
- B3 est assuré par un checkpoint post-A unique chargé par les trois branches. Les
  poids et évaluations post-A sont assertés identiques sur le smoke.
- `scripts/research/run_j6_replay.py` est résumable au niveau run, maintient l'éveil,
  refuse la campagne sans `--review-accepted` et smoke vert, contrôle les manifestes,
  les 36 runs et le plafond cumulatif de 90 minutes.
- `tests/test_j6_replay.py` couvre le monde, la formule gelée et la garde de revue.
  Suite complète: **175 tests réussis**.

## Exécutions valides

- `python scripts/research/run_j6_replay.py --smoke`: graine hors protocole 10991,
  **PASS** sur les sept contrôles demandés.
- Le smoke confirme: secteurs landmark A/B/C, luminance B/A `≤ 0,85`, chromaticité C/A
  `≥ 5 %`, corpus bit-identique, B3, budgets 12 000/2 400/1 500, au moins 64 ancres par
  compétence structurée et aucune fuite, priorités sommant à 1 avec TV par domaine,
  régressions absolues et relatives A/B.
- `python scripts/research/run_j6_replay.py --review-accepted`: graines 10301..10312,
  12 triplets / 36 runs complets, **26,9 minutes** cumulées, sous le plafond 90 minutes.
- Les artefacts locaux résumables sont sous
  `data/processed/experiments/j6_replay_001/` et restent ignorés par Git.
- Les exports nécessaires à la revue distante sont versionnés:
  `docs/research/j6_replay_001_analysis.json` et
  `docs/research/j6_replay_001_runs.json`.

## Résultats selon les portes gelées

- **B1/A non satisfaite:** régression relative naïve moyenne `0,03970`, IC BCa
  `[0,00073; 0,11566]`. Le seuil `0,05` manque; H1A est **NON INTERPRÉTABLE**, pas
  rejetée.
- **B1/B passe:** moyenne `0,14141`, IC `[0,09219; 0,17862]`.
- **H1B passe:** gain uniform−naive relatif `0,15056`, IC `[0,10660; 0,20527]`,
  p Holm `0,000488`, `6/6` bins. Le gain absolu `0,05013`, IC
  `[0,03406; 0,07138]`, est positif: accord B2.
- H1A aurait un gain relatif positif `0,06593`, mais n'est pas interprétable sous B1 et
  n'atteint aussi que `4/6` bins.
- **H2 échoue A/B:** gains relatifs `-0,00005` et `0,00395`, bornes basses négatives,
  p Holm `0,83545`, `4/6` bins chacun. Lecture M1: aucune valeur ajoutée démontrée à
  cette puissance, pas preuve d'inutilité.
- **H3 échoue** pour uniform (p Holm `0,08203`, pire bin C `+14,25 %`) et priorisé
  (p Holm `0,08765`, pire bin `+13,47 %`).
- La garde apprenant passe sans échec. La garde TV passe: excès priorisé moyen d'environ
  `+0,0006` point en B et `−0,104` point en C, très sous `+5 points`.
- Application mécanique actuelle: `uniform_replay` non promu et
  `error_prioritized_replay` non promu. Cette conclusion reste suspendue à l'audit
  Claude, sans changement des seuils ni interprétation inter-domaines A/B.

## Paquet de revue prêt

- Rapport: `docs/research/j6_replay_001_results.md`
- Analyse: `docs/research/j6_replay_001_analysis.json`
- 36 runs auditables: `docs/research/j6_replay_001_runs.json`
- Contexte et prompt exact: `CLAUDE_REVIEW_REQUEST.md`
- Sortie attendue: `docs/research/j6_replay_001_results_review.md`

## Contexte durable du projet

- TV-001 est rejeté et gelé par D-009; sa sonde motivation demeure dormante jusqu'à
  décision après J6. `docs/research/tv_real_jepa_001_results_review.md` avait imposé
  « J6 D'ABORD ».
- La navigation 2D et la famille fractionnelle sont historiques et ne doivent pas être
  réactivées sans hypothèse nouvelle.
- J0/J1 physiques restent spécifiés mais suspendus sous D-008. D-005 interdit tout
  nouvel essai moteur sur le banc fragile v0.1.
- `DEVELOPMENTAL_ARCHITECTURE.md` reste la vision cible; les mécanismes doivent battre
  des baselines simples à information et budget comparables avant promotion.

## Actions par acteur

Action Codex: après dépôt de `docs/research/j6_replay_001_results_review.md`, vérifier
le verdict, mettre à jour les décisions et engager seul la suite autorisée sans retuning
sur J6-R001.
Action Anthony: aucune.
Action Claude: exécuter le prompt exact de `CLAUDE_REVIEW_REQUEST.md` et écrire
`docs/research/j6_replay_001_results_review.md`.
Blocage: revue contradictoire des résultats requise avant toute promotion ou nouveau
protocole successeur.
