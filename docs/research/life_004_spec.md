# LIFE-004 — exécuteur MuJoCo borné

Date: 2026-07-27  
Statut: implémenté et vérifié, simulation uniquement

## But

Fermer la boucle de simulation sans déplacer l'actionnement dans le noyau:

`signaux observés → proposition sûre → primitive MuJoCo → journal J0 → résultat attribué`

LIFE-004 ne crée pas une politique motrice. Il fournit un adaptateur déterministe qui
traduit un petit vocabulaire symbolique en cibles servo bornées dans le jumeau
numérique. Aucun matériel, port série, firmware ou backend interchangeable n'est
accessible depuis cet adaptateur.

## Frontières

- Le module réside sous `sim3d/`, pas sous `cognitive/`.
- Il accepte une `ExperimentProposal` déjà persistée par le noyau.
- Il vérifie que l'identité, la session, le candidat et la primitive de l'objet reçu
  correspondent à la ligne SQLite.
- Il ne modifie jamais le score, les croyances ou la rationale.
- Il ne reçoit pas une séquence de commandes libre: la séquence provient exclusivement
  d'un registre local de primitives gelées.
- Ses seules sorties durables sont un journal J0 et le résultat LIFE-003 agrégé.

## Primitives initiales

- `diagnose_bounded_servo`: douze pas à `40°`;
- `scan_bounded_servo`: douze pas alternant `40°` et `140°`.

Chaque plan doit:

- contenir entre 1 et 64 pas;
- utiliser uniquement des nombres finis;
- rester dans les bornes servo MuJoCo `[10°, 170°]`;
- avoir un SHA-256 de sa représentation canonique.

Le registre refuse les doublons. Ni la proposition ni ses métadonnées ne peuvent
remplacer les cibles du registre.

## Garde d'exécution fraîche

Juste avant de créer l'exécution, l'adaptateur exige:

- aucun arrêt d'urgence;
- simulateur déclaré sain;
- aucune mise à jour de modèle en cours;
- quota `ok` ou `warning`;
- primitive encore présente dans `allowed_primitives`;
- session cognitive active et identique à celle de la proposition;
- proposition SQLite encore `proposed`.

Une proposition sûre au moment du choix peut donc être refusée si le contexte a changé.

## Cycle d'exécution

1. Créer un `SessionRecorder` J0 neuf avec proposition, exécution, primitive, graine et
   digest du plan dans le manifeste.
2. Appeler `begin_experiment_execution`.
3. Construire `BenchHeadEnv(BenchConfig(seed))`.
4. Exécuter chaque cible du plan et écrire un événement public `servo_state`.
5. Fermer le journal avec statut `complete`.
6. Appeler `complete_observed_execution`, qui relit et vérifie le journal.

Toute exception après `begin` ferme le journal en `aborted`, passe l'exécution LIFE-003
en `aborted` et la proposition en `cancelled`, puis remonte l'erreur originale.

## Portes du smoke

Le smoke doit:

1. exécuter au moins deux essais de chaque primitive sur des graines neuves;
2. reconstruire les histoires et dériver les signaux LIFE-002;
3. sélectionner une nouvelle proposition depuis ces seuls signaux;
4. exécuter cette proposition sans fournir de cible libre;
5. redémarrer et retrouver l'essai supplémentaire dans l'histoire attendue;
6. refuser contexte devenu dangereux, primitive inconnue et objet proposition falsifié;
7. injecter une panne MuJoCo et vérifier l'abandon atomique;
8. prouver que SQLite ne contient ni payload brut ni cible servo;
9. laisser toute la suite verte.

## Interprétation

Un succès démontre une boucle développementale minimale entièrement raccordée en
simulation. Les primitives restent écrites par l'ingénieur et le score observationnel
reste heuristique. LIFE-004 ne valide donc ni autonomie motrice générale, ni curiosité
optimale, ni transfert physique, ni causalité apprise.

## Résultat d'ingénierie

Les graines 17421..17424 produisent automatiquement deux essais par primitive. Les
histoires reconstruites alimentent LIFE-002, qui sélectionne `diagnose-servo`; la
proposition est ensuite exécutée sur 17425 sans séquence de cible fournie par l'appelant.
Après redémarrage, l'histoire `diagnose-servo` contient trois résultats attribués et
`wide-scan` deux.

Les gardes 17401..17403 refusent arrêt d'urgence, identité falsifiée et primitive non
enregistrée avant création d'une session J0. La panne injectée 17411 laisse journal,
exécution et proposition respectivement `aborted`, `aborted` et `cancelled`.

Les 41 tests KERNEL/LIFE ciblés et les 262 tests complets passent dans `.venv`.
LIFE-004 est close comme succès d'infrastructure sous D-030.
