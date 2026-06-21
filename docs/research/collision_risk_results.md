# Critique supervisé de collision future

Date: 2026-06-11

## Objectif

S4 a montré que la distance ultrason décodée par le JEPA n'est pas un objectif MPC fiable. Cette expérience remplace ce proxy par un label explicite: une collision surviendra-t-elle dans les 25 prochains pas, soit 0.5 seconde ?

Les pas déjà en collision sont exclus. Les actions de contexte DAgger utilisent `student_actuator_action_*` quand ces colonnes existent, car elles ont produit la trajectoire observée.

## Données et protocole

Corpus:

- rollout nominal de `dagger_002`;
- rollout randomisé de `dagger_002`;
- `lnn_dagger_labels_001.csv`;
- `lnn_dagger_labels_002.csv`.

Chaque fichier est séparé par épisodes en trois blocs disjoints: entraînement, validation pour l'early stopping et calibration, puis test final. Le test n'est jamais utilisé pour choisir l'epoch.

Trois scores sont comparés:

- MLP sur latent JEPA gelé + action courante;
- MLP sur contexte brut de 8 pas + action courante;
- distance ultrason courante seule.

Les têtes sont calibrées sur la validation par une transformation logistique scalaire. Le runner est:

```bash
python -m learning.train_collision_risk --logs data/raw/lnn_zoh_scan05_medium_dagger_002_rollout_001.csv data/raw/lnn_zoh_scan05_medium_dagger_002_rollout_randomized_001.csv data/raw/lnn_dagger_labels_001.csv data/raw/lnn_dagger_labels_002.csv --jepa-checkpoint models/sensor_jepa_zoh_scan05_medium_001_decoder_refined.pth --epochs 60 --patience 8 --batch-size 8192 --device cuda --output models/jepa_collision_risk_001.pth --metrics-output data/processed/experiments/jepa_collision_risk_001/metrics.json
```

## Résultats test

Taux positif test: 3.45%, sur 34 981 exemples.

| modèle | AP | AUROC | rappel à 5% FPR | précision | Brier | ECE |
|---|---:|---:|---:|---:|---:|---:|
| contexte brut + action | 0.193 | 0.794 | 28.1% | 16.7% | 0.0310 | 0.0168 |
| latent JEPA + action | 0.167 | 0.782 | 23.3% | 14.3% | 0.0316 | 0.0175 |
| distance ultrason | 0.035 | 0.402 | 10.4% | 6.9% | 0.0337 | 0.0182 |

## Lecture

Le risque futur est apprenable et le contexte temporel bat très nettement le seuil ultrason. Le latent JEPA apporte lui aussi un signal utile, mais il reste inférieur au contexte brut sur toutes les métriques de discrimination. Le JEPA actuel supprime donc une partie de l'information utile à l'anticipation des collisions.

Le rappel de 28% à 5% de faux positifs reste trop faible pour promouvoir directement ce critique comme véto. La sensibilité des trajectoires observée en S4 rendrait un taux de faux positifs de 5% potentiellement coûteux.

## Décision

- conserver `models/jepa_collision_risk_001.pth` comme artefact de recherche;
- ne pas l'activer dans le contrôleur;
- utiliser ce benchmark comme test S3: un JEPA adapté aux trajectoires student-visited doit au minimum dépasser le score `raw_context_action` ou réduire nettement son écart avant toute nouvelle tentative MPC;
- S5 FiLM reste une voie indépendante, mais elle devra également prouver que le latent contient un signal utile au-delà du contexte brut.
