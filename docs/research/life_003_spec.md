# LIFE-003 — attribution proposition, exécution et résultat

Date: 2026-07-27  
Statut: implémenté et vérifié, simulation uniquement

## But

Fermer la lacune laissée par LIFE-002: les essais J0 ne doivent plus être assemblés
manuellement en histoires candidates. Chaque essai doit être durablement attribué à la
proposition qui l'a motivé, puis son résumé doit être vérifiable depuis le journal
source après redémarrage.

Le cycle visé est:

`proposition sûre → exécution référencée → résultat agrégé → histoire → nouveaux signaux`

Le noyau ne lance toujours aucune commande. L'appelant exécute la primitive autorisée et
fournit un journal J0; le noyau ne fait qu'enregistrer l'intention, vérifier le résultat
observé et reconstruire l'histoire.

## Schéma durable

Une `experiment_execution` contient uniquement:

- un `execution_id`;
- le `proposal_id` unique qui l'autorise;
- l'`experiment_id` recopié et vérifié;
- le `session_id` J0 unique et la référence du répertoire source;
- les dates de début et de fin;
- un statut `running`, `complete` ou `aborted`;
- le digest source et le résumé `ServoTrialSummary` pour une exécution complète.

Ni événement brut, ni payload capteur, ni commande d'actionneur ne sont stockés dans
SQLite. Une proposition ne peut autoriser qu'une exécution et une session J0 ne peut
être attribuée qu'à une expérience.

## Transitions et atomicité

- `begin`: la proposition doit appartenir à la session cognitive active et être
  `proposed` ou `accepted`; l'exécution devient `running` et la proposition `accepted`
  dans une transaction.
- `complete`: l'exécution doit être `running`; le résumé doit porter le même
  `experiment_id` et le même `session_id` J0. Résumé, digest, fin et statut
  `executed` de la proposition sont écrits dans une transaction.
- `abort`: une exécution `running` devient `aborted` et sa proposition `cancelled`
  atomiquement.
- La répétition exacte de `begin` ou `complete` est idempotente. Toute collision
  d'identité avec des valeurs différentes est refusée.

Le schéma mémoire passe de v1 à v2. L'ouverture d'une base v1 applique uniquement la
migration additive LIFE-003 dans une transaction; une version inconnue reste refusée.

## Vérification depuis J0

À la complétion, le noyau:

1. ouvre la référence J0 enregistrée;
2. vérifie que son manifeste et ses événements appartiennent au `session_id` attendu;
3. recalcule `ServoTrialSummary` avec le contrat LIFE-002;
4. persiste uniquement ce résumé et son digest.

`recompute_observed_history(experiment_id)` relit toutes les exécutions complètes dans
l'ordre de fin, recalcule chaque résumé depuis sa référence J0 et exige l'égalité
stricte avec SQLite. Une source absente ou modifiée est une erreur d'intégrité, jamais
un résultat silencieusement ignoré.

## Portes du smoke

Le smoke doit:

1. créer plusieurs propositions et exécutions sur plusieurs sessions MuJoCo/J0;
2. vérifier les refus d'une proposition étrangère, d'une double attribution et d'un
   résultat de mauvais candidat;
3. simuler un redémarrage pendant une exécution puis la compléter;
4. reconstruire automatiquement deux histoires candidates;
5. dériver les signaux LIFE-002 et sélectionner une nouvelle proposition;
6. retrouver après un second redémarrage les mêmes histoires et digests;
7. prouver l'absence de payload brut et de commande dans SQLite;
8. migrer une base v1 représentative sans perdre ses propositions.

## Interprétation

Un succès valide la chaîne de provenance et la reconstruction durable. Il ne signifie
pas que l'expérience choisie a été physiquement exécutée de manière autonome, que son
effet est causal ou que le score LIFE-002 est scientifiquement optimal. Ces extensions
restent soumises aux portes de sécurité et aux revues prévues par D-004/D-008.

## Résultat d'ingénierie

Le smoke 17311..17314 reprend une exécution après perte du processus, complète quatre
essais attribués, reconstruit automatiquement deux histoires et choisit
`diagnose-servo` avec les signaux LIFE-002. Un second redémarrage retrouve les mêmes
digests. Les gardes refusent journal ouvert, double attribution, résultat étranger,
fermeture avec exécution active, modification directe en `executed` et source J0
altérée. Une base v1 représentative migre en v2 sans perdre sa proposition.

Les 37 tests KERNEL/LIFE ciblés et les 258 tests complets passent dans `.venv`.
LIFE-003 est close comme succès d'infrastructure sous D-029.
