# LIFE-006 — compétences vers activation des expériences

Date: 2026-07-27  
Statut: implémenté et vérifié, simulation uniquement

## But

Retirer à l'appelant la construction manuelle de la liste de candidates. Un registre
déclaratif associe chaque état de compétence à zéro ou plusieurs expériences; les états
persistants déterminent alors automatiquement le sous-ensemble soumis au sélecteur sûr.

La chaîne devient:

`compétences persistantes → besoins actifs → candidates → sélecteur LIFE-002`

Les priorités et routes restent écrites par l'ingénieur. LIFE-006 n'apprend pas un
curriculum.

## Priorité des besoins

Ordre fixe:

1. `regressed` — urgence 4;
2. `unknown` — urgence 3;
3. `learning` — urgence 2;
4. `candidate` — urgence 1;
5. `validated` — urgence 0, surveillance éventuelle;
6. `suspended` — exclu sans exception.

Seules les routes du plus haut niveau d'urgence actuellement non vide sont activées.
Toutes les routes ex aequo sont conservées; le sélecteur transparent les départage
ensuite. Une compétence régressée préempte donc une acquisition inconnue, mais ne
modifie aucun des six `ExperimentSignals`.

## Route déclarative

Une `CompetenceNeedRoute` contient:

- un nom de compétence unique;
- les expériences autorisées pour chacun des cinq états non suspendus;
- un prior de démarrage à froid par expérience.

Une expérience peut servir plusieurs compétences. Les doublons sont fusionnés et la
preuve conserve tous les besoins qui l'ont activée. Une route vide pour un état signifie
qu'aucune expérience n'est demandée à cet état.

## Signaux

Pour chaque candidate activée:

- si LIFE-003 possède au moins un résultat complet, LIFE-002 recalcule ses signaux
  depuis tout l'historique vérifié;
- sinon, le prior froid déclaré est utilisé sans modification.

Le prior froid doit être un `ExperimentSignals` complet, borné et visible dans la
preuve avec `kind=cold_start_prior`. Il ne peut pas se présenter comme une observation.
La preuve observée conserve le digest LIFE-002 et porte
`kind=observed_history`.

Chaque preuve ajoute:

- l'urgence active;
- l'état et la compétence sources;
- la politique `highest_nonempty_need_urgency`;
- les besoins non activés et leur raison.

## Gardes

- noms de compétences uniques dans le registre;
- prior froid obligatoire pour toute expérience routable;
- aucune route `suspended`;
- au moins une route;
- aucun candidat inventé hors registre;
- si toutes les routes courantes sont vides ou suspendues, lever
  `NoActiveNeedError` sans écrire de proposition;
- les gardes du catalogue restent inchangées et ultérieures à l'activation.

## Smoke

Deux compétences:

- `bounded_servo_tracking`:
  - inconnue/apprentissage/candidate/régressée → `diagnose-servo`;
  - validée → `diagnose-servo` comme surveillance;
- `visual_scan_coverage`:
  - inconnue/apprentissage/candidate/régressée → `wide-scan`;
  - validée → aucune surveillance.

Portes:

1. À froid, les deux compétences inconnues activent les deux candidates; les priors
   sont audités et le sélecteur choisit mécaniquement l'une d'elles.
2. Après validation de `bounded_servo_tracking`, `visual_scan_coverage` inconnue est
   seule active car urgence 3 > 0.
3. Après régression servo injectée, `diagnose-servo` est seule active car urgence 4 > 3.
4. Si la compétence servo est suspendue, elle ne peut jamais activer une candidate.
5. Après historique, les signaux `diagnose-servo` portent une preuve observée et non le
   prior froid.
6. Un registre entièrement suspendu/vide ne persiste aucune proposition.
7. Redémarrage et reconstruction donnent la même activation.
8. Toute la suite reste verte.

## Interprétation

Un succès démontre un curriculum déclaratif piloté par l'état cognitif persistant. Il
ne démontre pas que l'organisme a découvert ses propres besoins, appris leur priorité
ou généré une expérience nouvelle. Ces étapes exigeraient une revue scientifique
distincte.

## Résultat d'ingénierie

À froid, `bounded_servo_tracking` et `visual_scan_coverage` inconnues activent
respectivement `diagnose-servo` et `wide-scan`; les deux preuves sont explicitement des
`cold_start_prior` et le prior gelé sélectionne `diagnose-servo`. L'exécution 17601
crée un historique: après redémarrage, `diagnose-servo` porte exactement la même preuve
`observed_history`, tandis que `wide-scan` reste froid.

Une validation servo laisse seulement le besoin visuel inconnu actif et l'exécution
17602 produit son premier historique. Une régression servo fait ensuite remonter
uniquement `diagnose-servo` à l'urgence 4. Une suspension retire cette route. Un
registre sans route active ne crée aucune proposition.

Les 50 tests KERNEL/LIFE ciblés et les 271 tests complets passent dans `.venv`.
LIFE-006 est close comme succès d'infrastructure sous D-032.
