# BODY-SCHEMA-002 r2 — prévision persistante : résultats de développement et validation

Date : 2026-09-09. Décision D-053. Simulation uniquement.

**La prévision corporelle simple est maintenant apprise, sauvegardée et rechargeable.**
La recette passe les critères fixés avant lecture sur six organismes de validation neufs.
Les six paquets de développement sont activés dans leurs mémoires cognitives respectives,
avec une portée explicite de développement. Ce résultat ne qualifie pas tout J1.

## Résultats

Chaque organisme apprend sa propre dynamique depuis une initialisation neuve. Les méthodes
partagent trials, ancres, occasions de sélection et bornes. Le témoin principal sans action
B3 a été choisi sur développement (MAE 3,981° contre 4,091° pour B13), avant validation.

| Banque | F à un pas | Prior à un pas | Sans action B3 à un pas | F à 0,1 s | F à 0,5 s |
|---|---:|---:|---:|---:|---:|
| Développement, 6 organismes | 0.413° | 2.113° | 3.981° | 0.548° | 0.713° |
| Validation, 6 organismes neufs | 0.435° | 1.433° | 4.326° | 0.464° | 0.579° |

Moyennes calculées par trial puis à poids égal par motif et organisme. Les erreurs
aux horizons sont terminales, en déroulement libre, sans observations futures fournies.
Le pas nominal vaut 0,02 s ; les horizons 5 et 25 utilisent respectivement 28 et 8
origines complètes par trial. La MAE à un pas sur les huit origines communes est aussi
exportée dans chaque rapport brut. Les diagnostics numériques décrivent le dernier
candidat ; les erreurs et saturations d’évaluation portent sur la version active sélectionnée. Les fenêtres ne sont pas des réplications indépendantes.

| Organisme de validation | F à un pas | F à 0,5 s | Critères prévision / déroulement / reprise |
|---|---:|---:|---|
| friction_dominant/0 | 0.483° | 0.683° | Verts / verts / verts |
| friction_dominant/1 | 0.456° | 0.619° | Verts / verts / verts |
| settling_dominant/0 | 0.374° | 0.506° | Verts / verts / verts |
| settling_dominant/1 | 0.390° | 0.514° | Verts / verts / verts |
| speed_dominant/0 | 0.489° | 0.591° | Verts / verts / verts |
| speed_dominant/1 | 0.418° | 0.561° | Verts / verts / verts |

Les six organismes respectent MAE à un pas ≤1°, gain ≥15 % contre prior et B3,
erreur terminale ≤2° à 0,1/0,5 s et supériorité à la persistance à ces horizons.
Ces critères ont été figés dans le manifeste de validation avant son ouverture. Ils
sont des objectifs logiciels, pas des tolérances de sécurité matérielle.

## Persistance réalisée

- Candidat et actif séparés ; données accumulées conservées lors des refus.
- Artefacts JSON immuables, empreintes contrôlées et tables additionnelles dans la mémoire SQLite du noyau.
- Application atomique du trial, de son contenu, du candidat et de son curseur ; rejeu ancien sans effet.
- Activation atomique de la version, des preuves et des états de capacité, sans transactions imbriquées.
- Pour F/B13/B3, mêmes paramètres, prévisions et prochaine mise à jour dans un nouveau processus,
  sur les douze organismes de développement et validation.
- Pour les six F activés, la requête servie par le registre reste identique après un nouveau redémarrage.
- Calibration et détection explicitement non qualifiées pour les paquets actifs. La preuve
  de déroulement de la recette en validation ne change pas silencieusement leur statut propre.

Les traces `pre_step_predictions.json` enregistrent la prévision F et sa version avant
l’appel à MuJoCo, puis l’observation correspondante. Les intervalles ne sont pas utilisés
pour cette capacité F. La reprise physique au milieu d’un trial n’est pas qualifiée ;
le livrable garantit les frontières de trials et la continuation de l’apprenant.

## Vérifications et budget

24 tests de contrat/persistance, 3 tests de fermeture de la validation, puis **327 tests
complets réussis en 25,52 s**. Les essais injectent des interruptions autour des écritures
et promotions, une corruption d’artefact et une dépendance privilégiée volontairement
fausse. Un tel calcul de sigma fait bien échouer le contrôle d’invariance.

Le superviseur extérieur réserve durablement le coût maximal d’une tentative. Une
interruption sans fin enregistrée conserve cette réservation. Les opérations bloquées
sont arrêtées avec leur arborescence de processus ; les tests et simulations historiques
de la suite sont conservativement inclus dans le budget. Les limites restent 15 minutes
par invocation et 60 minutes cumulées. Environ deux minutes de calcul et tests ont été
comptabilisées, essais échoués compris ; le registre SQLite donne le total exact.

La v1 de développement a arrêté la vérification de reprise avant publication des scores.
Une liste partagée par le snapshot restauré altérait la référence du vérificateur.
Le correctif, son test et la relance complète v2 sont consignés dans le journal ;
les anciens artefacts et le budget commun sont conservés.

## Limites et prochaine étape

Il s’agit d’une validation de configuration sur de nouveaux organismes, avec deux
organismes par régime, et des formes de commande déjà présentes dans le développement.
Aucun intervalle confirmatoire ni preuve de généralisation à de nouvelles familles de
commande n’est revendiqué. Les graines confirmatoires historiques sont restées fermées.

Le MAD global, la calibration d’un ensemble fourni et le moniteur ont une
implémentation et des contrôles synthétiques. L’entraînement bootstrap par trial
d’E n’est pas encore raccordé au cycle persistant. Ils n’ont pas été qualifiés sur les fautes MuJoCo : E et A restent en
développement. Aucun oubli, replay cumulatif A→B→A→C, apprentissage visuel ou J5
n’a été expérimenté dans ce lot. Les résultats positifs de F sont conservés séparément.

Action Codex suivante : préparer le protocole cumulatif distinct à partir de cette
capacité persistante, et un manifeste confirmatoire à nouvelles formes de commande
si une confirmation scientifique est recherchée. Le lancement de ces campagnes
reste soumis aux portes de revue prévues ; aucune action matérielle demandée.

## Artefacts et commandes

- [Contrat avec C1–C6](body_schema_002_preregistration.md)
- [Manifeste de développement v2](body_schema_002_dev_manifest.json)
- [Manifeste de validation gelé](body_schema_002_validation_manifest.json)
- [Journal des variantes](body_schema_002_development_log.md)
- [Résultats agrégés](body_schema_002_results.json)
- [Activation des paquets](../../data/processed/experiments/body_schema_002_r2_dev_v2/activation_receipt.json)
- [Portes de validation](../../data/processed/experiments/body_schema_002_r2_validation_v1/summary.json)

Les dossiers par organisme contiennent `report.json`, les trials, les prévisions émises,
les artefacts F/B, les bases SQLite, les requêtes/réponses de reprise et leurs digests.
Le budget et les logs sont dans `data/processed/experiments/body_schema_002_r2_dev_v1`.

Commandes exécutées depuis la racine du projet :

```powershell
.\.venv\Scripts\python.exe -m learning.body_schema_002_budget --kind tests -- -m pytest tests/test_body_schema_002.py -q
.\.venv\Scripts\python.exe -m learning.body_schema_002_budget --kind development -- -m learning.body_schema_002_experiment --organism first
.\.venv\Scripts\python.exe -m learning.body_schema_002_budget --kind development -- -m learning.body_schema_002_experiment --organism remaining
.\.venv\Scripts\python.exe -m learning.body_schema_002_budget --kind verification -- -m learning.body_schema_002_validation freeze
.\.venv\Scripts\python.exe -m learning.body_schema_002_budget --kind development -- -m learning.body_schema_002_validation run
.\.venv\Scripts\python.exe -m learning.body_schema_002_budget --kind tests -- -m pytest -q tests
.\.venv\Scripts\python.exe -m learning.body_schema_002_budget --kind verification -- -m learning.body_schema_002_validation activate-development
```

Le lanceur refuse de remplacer un organisme terminé ou de rouvrir la validation.
Une nouvelle variante de développement reçoit un dossier et un journal explicites.
La consultation/reprise d’un paquet utilise `BodyForecastStore` avec son run ID et
le digest de contrat présents dans les requêtes de restauration.
