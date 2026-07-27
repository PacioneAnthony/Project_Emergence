# LIFE-002 — signaux de choix dérivés des observations

Date: 2026-07-27  
Statut: implémenté et vérifié, simulation uniquement

## But

Remplacer, dans le smoke LIFE, les valeurs `ExperimentSignals` écrites à la main par
des signaux déterministes calculés depuis des événements `servo_state` réellement
produits par `BenchHeadEnv` et enregistrés dans les journaux J0.

Cette tranche ne prétend ni résoudre la curiosité générale, ni apprendre une politique,
ni établir une relation causale. Elle vérifie une propriété d'infrastructure nécessaire
à l'objectif final: une IA développementale persistante doit pouvoir choisir une
expérience sûre à partir de sa propre histoire sensorimotrice, expliquer ce choix et
recalculer la même explication après redémarrage.

## Frontières

- Le noyau reste indépendant de MuJoCo et ne commande aucun actionneur.
- Le sélecteur continue de recevoir des `ExperimentSignals`; LIFE-002 fournit un
  estimateur observationnel en amont.
- Les événements bruts restent dans les journaux J0 append-only. SQLite ne reçoit que
  la proposition, ses valeurs agrégées, les paramètres de calcul et les digests des
  sources.
- Les bornes de sécurité du catalogue restent prioritaires sur le score.
- Les labels ou états internes de MuJoCo ne sont pas utilisés: seuls
  `requested_deg`, `as5600_deg`, les métadonnées publiques de l'événement et l'ordre du
  journal sont admissibles.

## Unité de mesure

Un essai est une séquence non vide d'événements `servo_state` appartenant:

- à une seule session;
- à un seul `source_id`;
- à un seul `calibration_version`;
- à un `experiment_id` fourni par l'appelant et non déduit d'un résultat.

Chaque événement doit annoncer un payload valide et contenir deux nombres finis,
`requested_deg` et `as5600_deg`, compris dans les bornes servo configurées. L'ordre
fourni est conservé et les identités `(session_id, source_id, sequence_id)` doivent être
uniques.

Le résumé d'un essai contient:

- `mean_absolute_error`: moyenne de
  `abs(requested_deg - as5600_deg) / servo_span`, bornée à 1;
- `error_uncertainty`: écart-type population des erreurs normalisées, borné à 1;
- `coverage_bins`: bins de commande visités;
- `boundary_exposure`: fraction des observations dont la commande ou la mesure est à
  moins de `boundary_margin_deg` d'une butée;
- `motor_cost`: variation totale, depuis `neutral_deg` puis entre commandes
  successives, divisée par `servo_span * event_count` et bornée à 1;
- un SHA-256 de la projection canonique des événements effectivement utilisés.

Les valeurs brutes ne figurent pas dans le résumé.

## Passage des essais aux signaux

Pour un candidat, les essais sont ordonnés comme fournis. Ils sont séparés en une
moitié ancienne et une moitié récente; avec un seul essai, la partie ancienne est vide.

Les six signaux sont:

- `epistemic_gain = clip(mean_recent_error + mean_recent_uncertainty)`;
- `learning_progress = clip(mean_old_error - mean_recent_error)`, ou zéro sans histoire
  ancienne;
- `novelty = nombre de bins récents absents de l'histoire ancienne / bin_count`;
- `controllability = 1 - mean_recent_error`;
- `predicted_risk = max(boundary_exposure récente)`;
- `motor_cost = mean(motor_cost récent)`.

`predicted_risk` est ici un proxy empirique conservateur issu de l'exposition passée,
pas une prédiction causale apprise. Cette limite doit rester visible dans la preuve.

La preuve de signal contient la version du schéma, les paramètres, les identifiants de
session, les résumés, les digests sources et les valeurs finales. Son propre digest est
le SHA-256 de son JSON canonique.

## Intégration au choix

`SafeExperimentCatalog.propose_best` accepte facultativement une preuve par candidat.
Il vérifie qu'une preuve est fournie exactement pour chaque candidat lorsqu'une table
de preuves est présente, puis l'attache à l'audit persistant. Le score, le tie-break et
les portes de sécurité ne changent pas.

Une proposition reste une intention révisable: elle ne doit contenir ni
`servo_target`, ni vitesse, ni commande d'actionneur.

## Portes du smoke

Le smoke d'intégration doit:

1. produire au moins deux histoires candidates sur plusieurs sessions MuJoCo/J0;
2. calculer les signaux uniquement depuis les replays J0;
3. sélectionner et persister une proposition avec les preuves des candidats;
4. fermer puis rouvrir le noyau;
5. relire les mêmes journaux et obtenir des résumés, signaux et digests identiques;
6. retrouver en SQLite la preuve complète sans payload brut ni commande d'actionneur;
7. laisser toute la suite de tests verte.

## Interprétation

Un succès valide le câblage observation → résumé → signal → choix sûr → persistance.
Il ne valide pas la qualité scientifique des coefficients, une motivation intrinsèque,
une compétence générale ou un transfert au robot physique. Toute promotion de ce type
demanderait une expérience pré-enregistrée et une revue contradictoire distinctes.

## Résultat d'ingénierie

Les quatre sessions MuJoCo/J0 17201..17204 produisent deux histoires candidates. Le
sélecteur choisit `diagnose-servo`, persiste les preuves des deux candidates, puis un
nouveau processus recalcule exactement les mêmes résumés, signaux et digests depuis les
journaux. Les 33 tests KERNEL/LIFE ciblés et les 254 tests complets passent dans
`.venv`. LIFE-002 est donc close comme succès d'infrastructure sous D-028.
