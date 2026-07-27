# LIFE-007 — superviseur de cycle persistant

Date: 2026-07-27  
Statut: implémenté et vérifié, simulation uniquement

## But

Enchaîner automatiquement les modules LIFE déjà validés:

`activate → select → execute → assess → complete`

Le superviseur ne définit aucune nouvelle politique. Il appelle LIFE-006 pour les
besoins, le catalogue pour les gardes, LIFE-004 pour MuJoCo, LIFE-003 pour le résultat
et LIFE-005 pour l'évaluation.

## Identité d'un cycle

Une requête stable contient:

- `cycle_id`;
- `execution_id`;
- `j0_session_id`;
- `seed`.

Le schéma mémoire v4 ajoute `development_cycles`. Un cycle référence une proposition
unique et conserve expérience, primitive, identités d'exécution, graine, phase,
timestamps, audit d'activation et résultat d'évaluation.

## Phases

- `selected`: proposition et cycle écrits atomiquement;
- `executed`: journal J0 complet et exécution LIFE-003 complète;
- `complete`: évaluation appliquée ou absence d'évidence suffisante consignée;
- `aborted`: exécution partielle ou défaillante; phase terminale.

Les transitions ne peuvent avancer que dans cet ordre. Un appel répété sur `complete`
retourne le même résultat sans nouvelle proposition, exécution ou évaluation.

## Reprise

Frontières reprenables:

1. crash après `selected`: reconstruire la proposition SQLite et lancer LIFE-004;
2. crash après exécution complète mais avant `executed`: reconnaître
   `experiment_executions.status=complete`, ne pas réexécuter, puis avancer;
3. crash après application LIFE-005 mais avant `complete`: recalculer le même digest,
   obtenir l'idempotence LIFE-005 et terminer le cycle.

Une exécution `running` dont le manifeste J0 reste `recording` après perte de processus
ne peut pas reprendre la physique. Le superviseur:

- passe exécution et proposition en `aborted/cancelled`;
- marque le cycle `aborted`;
- lève `CycleRecoveryError`.

Aucun retry automatique avec une nouvelle graine ou une nouvelle proposition n'est
autorisé dans le même cycle.

## Sélection atomique

Le superviseur appelle `propose_best` sans persister, puis écrit proposition et cycle
dans une transaction unique. L'audit de signal reçoit `cycle_id`. Il ne peut donc pas
exister de cycle sélectionné sans proposition, ni de proposition de superviseur sans
cycle.

## Évaluation

Un registre optionnel associe `experiment_id` à:

- compétence;
- critère `UpperBoundCriterion`;
- fenêtre;
- span servo;
- version de modèle analytique.

Si l'histoire contient moins d'essais que la fenêtre, le cycle finit avec
`assessment_status=insufficient_history`; aucune transition n'est créée. Sinon LIFE-005
est appliquée et son digest est consigné.

## Injection de panne d'ingénierie

Le smoke peut demander un arrêt propre après:

- `selected`;
- `executed`;
- `assessment_applied`.

Ces checkpoints n'altèrent aucune donnée ou politique; ils simulent une perte de
processus aux frontières pour vérifier la reprise.

## Portes du smoke

1. Cycle A arrêté après sélection, redémarré puis exécuté sans seconde proposition.
2. Cycle B arrêté après exécution, redémarré puis évalué sans seconde exécution.
3. Cycle C arrêté après application de l'évaluation, redémarré sans transition
   supplémentaire.
4. Un cycle complet répété est strictement idempotent.
5. Un changement d'identité de requête est refusé.
6. Un contexte devenu dangereux laisse le cycle `selected`, reprenable lorsque la
   sécurité revient.
7. Une exécution partielle simulée est abandonnée, jamais continuée.
8. Migration v3→v4 additive et migrations antérieures toujours vertes.
9. Aucune commande ou payload brut dans SQLite.
10. Toute la suite verte.

## Interprétation

Un succès démontre une autonomie procédurale minimale et reprenable en simulation. Les
besoins, plans, priors, seuils et priorités restent déclaratifs. Le superviseur ne
constitue ni une politique apprise, ni une autonomie physique, ni une conscience.

## Résultat d'ingénierie

Le cycle 17701 est arrêté après sélection, redémarré, exécuté puis terminé sans seconde
proposition; son premier résultat est correctement `insufficient_history`. Le cycle
17702 est arrêté après exécution, puis après application LIFE-005. Un troisième
processus réapplique le même digest sans transition supplémentaire et commit le cycle.
Les deux cycles ne produisent que deux propositions, deux exécutions et une évaluation.

Le contexte dangereux 17711 laisse le cycle sélectionné, puis la reprise sûre le
termine. L'exécution partielle 17721 laisse un manifeste `recording`; elle devient
`aborted`, l'exécution `aborted`, la proposition `cancelled` et lève
`CycleRecoveryError`. La sélection bloquée 17731 ne crée ni cycle ni proposition.

Une session ne peut pas être fermée proprement avec un cycle actif. La migration
v3→v4 conserve les évaluations, et les migrations v1/v2 restent vertes.

Les 55 tests KERNEL/LIFE ciblés et les 276 tests complets passent dans `.venv`.
LIFE-007 est close comme succès d'infrastructure sous D-033.
