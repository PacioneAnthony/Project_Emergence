# Simulation 2D - Reprise JEPA/LNN

Ce module applique la priorité immédiate de `jepa_lnn_robot_math.md`: construire un corps virtuel minimal avant le deep learning lourd.

## Ce qui est simulé

- Robot circulaire avec position, orientation, vitesse linéaire et vitesse angulaire.
- Servo horizontal limité en angle, en vitesse, et commandé par bloqueur d'ordre zéro PWM.
- Capteur ultrason par raycast sur murs et obstacles circulaires.
- Gyroscope simulé avec bruit, biais et latence.
- Bruit capteur, latence, glissement et domain randomization par épisode.
- Logs CSV contenant observation, action brute, action sécurisée, action appliquée par l'actuateur, état réel, reward, collision et distance vraie.

## Lancement rapide

```bash
python -m scripts.research.simulate --episodes 5 --steps 6000 --output data/raw/sim2d_log.csv
```

Le simulateur utilise par défaut un pas de `20 ms`, aligné sur un servo PWM classique à `50 Hz`. Pour tester une intégration plus fine avec maintien de commande:

```bash
python -m scripts.research.simulate --dt 0.01 --pwm-period 0.02 --episodes 5 --steps 6000 --output data/raw/sim2d_log.csv
```

La politique d'évitement scanne l'ultrason à `0.5 Hz` par défaut. Pour ajuster le rythme:

```bash
python -m scripts.research.simulate --scan-hz 0.75 --episodes 5 --steps 6000 --output data/raw/sim2d_log.csv
```

Pour voir le monde:

```bash
python -m scripts.research.simulate --episodes 1 --steps 600 --render
```

Pour générer une image finale:

```bash
python -m scripts.research.simulate --episodes 1 --steps 600 --save-final-frame data/raw/final_frame.png
```

Par défaut, une collision est journalisée mais ne termine pas l'épisode. Pour revenir à un mode plus punitif:

```bash
python -m scripts.research.simulate --collision-ends-episode
```

## Contrat observation/action

Observation minimale:

```text
[distance_ultrason, angle_servo, gyro_z]
```

Action minimale:

```text
[v_cmd, omega_cmd, servo_target]
```

Ce contrat est défini dans `common/types.py`. Le code d'apprentissage doit consommer ce contrat, que les valeurs viennent du simulateur ou plus tard de l'Arduino.

Dans les logs, `action_*` est la consigne demandée, `safe_action_*` est la consigne après clipping, et `actuator_action_*` est la commande effectivement appliquée après maintien PWM. `learning/datasets.py` utilise `actuator_action_*` quand ces colonnes existent.

## Préparation apprentissage

- `learning/datasets.py` charge les CSV de simulation en tableaux NumPy.
- `learning/jepa.py` contient un JEPA minimal sur observations capteurs.
- `learning/lnn.py` contient un squelette LNN à intégration Euler.
- `learning/train_jepa.py` entraîne le JEPA minimal si PyTorch est installé.
- `learning/evaluate_jepa.py` évalue le JEPA contre des baselines simples et produit des graphes.

Exemple après génération de logs:

```bash
python -m learning.train_jepa --log data/raw/sim2d_log.csv --epochs 2000 --context-steps 4
```

Puis évaluation:

```bash
python -m learning.evaluate_jepa --log data/raw/sim2d_log.csv --checkpoint models/sensor_jepa.pth
```

Les résultats sont écrits dans `data/processed/jepa_eval/metrics.json`, avec deux graphes si Matplotlib est disponible.

## Protocole recommandé actuel

Pour produire un corpus suffisamment long:

```bash
python -m scripts.research.simulate --episodes 10 --steps 6000 --seed 202 --output data/raw/sim2d_bootstrap_long.csv
```

Pour entraîner le JEPA contextuel:

```bash
python -m learning.train_jepa --log data/raw/sim2d_bootstrap_long.csv --epochs 10000 --batch-size 256 --context-steps 4 --early-stopping-patience 5 --output models/sensor_jepa_context4.pth
```

Pour évaluer:

```bash
python -m learning.evaluate_jepa --log data/raw/sim2d_bootstrap_long.csv --checkpoint models/sensor_jepa_context4.pth --output-dir data/processed/jepa_eval_context4
```

Pour entraîner un premier LNN seul par imitation des actions appliquées dans le simulateur:

```bash
python -m learning.train_lnn --log data/raw/sim2d_zoh_scan05_medium_001.csv --epochs 500 --sequence-length 64 --batch-size 256 --device cuda --output models/lnn_zoh_scan05_medium_001.pth --metrics-output data/processed/experiments/lnn_zoh_scan05_medium_001/metrics.json
```

Cette phase ne couple pas encore le JEPA. Elle vérifie seulement que la dynamique continue du LNN peut porter une politique sensorimotrice rapide à partir de `[distance_ultrason, angle_servo, gyro_z]`.

Pour tester le LNN en boucle fermée dans le simulateur:

```bash
python -m learning.rollout_lnn --checkpoint models/lnn_zoh_scan05_medium_002.pth --episodes 1 --steps 6000 --no-domain-randomization --render --output data/raw/lnn_rollout_visual.csv --metrics-output data/processed/experiments/lnn_rollout_visual/metrics.json
```

Le rollout utilise toujours la `SafetyLayer` et le bloqueur ZOH de l'environnement. Les actions journalisées permettent donc de comparer la commande demandée par le LNN, la commande sécurisée, puis la commande vraiment appliquée.

Si le LNN imite bien hors-ligne mais dérive en boucle fermée, utiliser une passe DAgger:

```bash
python -m learning.aggregate_lnn_data --checkpoint models/lnn_zoh_scan05_medium_002.pth --episodes 10 --steps 6000 --seed 1201 --dt 0.02 --pwm-period 0.02 --scan-hz 0.5 --no-domain-randomization --output data/raw/lnn_dagger_labels_001.csv --metrics-output data/processed/experiments/lnn_dagger_labels_001/metrics.json --device cuda
python -m learning.merge_sim_logs --inputs data/raw/sim2d_zoh_scan05_medium_001.csv data/raw/lnn_dagger_labels_001.csv --output data/raw/sim2d_zoh_scan05_medium_dagger_001.csv
python -m learning.train_lnn --log data/raw/sim2d_zoh_scan05_medium_dagger_001.csv --epochs 2500 --batch-size 256 --sequence-length 64 --state-dim 64 --hidden-dim 128 --lr 3e-4 --eval-every 50 --early-stopping-patience 20 --device cuda --output models/lnn_zoh_scan05_medium_dagger_002.pth --metrics-output data/processed/experiments/lnn_zoh_scan05_medium_dagger_002/metrics.json
```

`aggregate_lnn_data` fait rouler le LNN pour visiter ses propres états, mais écrit les labels experts dans `actuator_action_*`, qui restent donc la cible de `train_lnn`. Les colonnes `student_*` gardent l'action du LNN pour diagnostic. `merge_sim_logs` renumérote les épisodes afin que les séquences d'entraînement ne traversent jamais une frontière de fichier.

État actuel des checkpoints LNN:

- `models/lnn_zoh_scan05_medium_dagger_002.pth` est le meilleur contrôleur nominal: `1.21%` de collision en rollout déterministe, contre `20.66%` pour l'imitation pure.
- `models/lnn_zoh_scan05_medium_dagger_003.pth` améliore légèrement le rollout randomisé (`2.13%` contre `2.52%`), mais régresse en déterministe (`3.01%`). Il reste donc un checkpoint expérimental, pas le modèle par défaut.

## Couplage JEPA-LNN

Le premier couplage implémenté est volontairement simple: encoder un contexte causal JEPA gelé puis donner `[observation courante, latent JEPA]` au LNN.

Entraînement:

```bash
python -m learning.train_lnn --log data/raw/sim2d_zoh_scan05_medium_dagger_001.csv --jepa-checkpoint models/sensor_jepa_zoh_scan05_medium_001_decoder_refined.pth --epochs 2500 --batch-size 256 --sequence-length 64 --state-dim 64 --hidden-dim 128 --device cuda --output models/lnn_jepa_zoh_scan05_medium_dagger_001.pth --metrics-output data/processed/experiments/lnn_jepa_zoh_scan05_medium_dagger_001/metrics.json
```

Rollout:

```bash
python -m learning.rollout_jepa_lnn --checkpoint models/lnn_jepa_zoh_scan05_medium_dagger_001.pth --episodes 5 --steps 6000 --seed 1001 --dt 0.02 --pwm-period 0.02 --no-domain-randomization --output data/raw/lnn_jepa_zoh_scan05_medium_dagger_001_rollout_001.csv --metrics-output data/processed/experiments/lnn_jepa_zoh_scan05_medium_dagger_001_rollout_001/metrics.json --device cuda
```

Résultat: ce couplage direct améliore l'erreur offline (`0.306338` contre `0.348901` pour le LNN brut DAgger), mais dégrade fortement le rollout fermé (`7.73%` de collisions contre `1.21%`). Une passe DAgger spécifique JEPA-LNN a encore dégradé le rollout (`13.03%`).

Conclusion actuelle: garder `models/lnn_zoh_scan05_medium_dagger_002.pth` comme contrôleur actif. Le JEPA doit probablement être utilisé comme perte auxiliaire, critique prédictif ou évaluateur de candidats d'action, pas comme entrée directe non filtrée par une porte de la politique réflexe.

Diagnostic D1 sans réentraînement:

```bash
python -m learning.rollout_jepa_lnn --checkpoint models/lnn_jepa_zoh_scan05_medium_dagger_001.pth --latent-mode zero --episodes 5 --steps 6000 --seed 1001 --no-domain-randomization
python -m learning.rollout_jepa_lnn --checkpoint models/lnn_jepa_zoh_scan05_medium_dagger_001.pth --latent-mode mean --latent-mean-log data/raw/sim2d_zoh_scan05_medium_dagger_001.csv --episodes 5 --steps 6000 --seed 1001 --no-domain-randomization
```

Résultat: latent dynamique `7.73%`, latent zéro `7.75%`, latent moyen `56.13%` de collisions. Le latent dynamique seul n'explique donc pas l'échec; la politique couplée est fortement dépendante du point de fonctionnement latent et ne possède pas de fallback observation-only robuste.

Les diagnostics D3/D4 sont disponibles via:

```bash
python -m learning.diagnose_jepa_latent_shift --reference-log data/raw/sim2d_zoh_scan05_medium_001.csv --rollout-log data/raw/lnn_jepa_zoh_scan05_medium_dagger_001_rollout_001.csv --jepa-checkpoint models/sensor_jepa_zoh_scan05_medium_001_decoder_refined.pth --output data/processed/experiments/lnn_jepa_zoh_scan05_medium_dagger_001_latent_shift_d3/metrics.json --device cuda
python -m learning.diagnose_jepa_lnn_sensitivity --log data/raw/sim2d_zoh_scan05_medium_dagger_001.csv --checkpoint models/lnn_jepa_zoh_scan05_medium_dagger_001.pth --jepa-checkpoint models/sensor_jepa_zoh_scan05_medium_001_decoder_refined.pth --output data/processed/experiments/lnn_jepa_zoh_scan05_medium_dagger_001_sensitivity_d4/metrics.json --device cuda
```

D3 ne montre aucune dérive Mahalanobis (`p95 rollout/reference = 0.945`). D4 montre en revanche que le bloc latent domine la sensibilité d'action totale par un facteur `4.77`, principalement parce qu'il contient 128 dimensions contre 3 observations. La suite recommandée est S2: JEPA comme cible auxiliaire sur l'état caché LNN, sans latent dans la boucle d'inférence.

### S2 - JEPA comme perte auxiliaire

S2 conserve une politique d'inférence observation-only. Pendant l'entraînement, une tête auxiliaire lit l'état caché LNN et prédit le latent futur fourni par l'encodeur cible EMA du JEPA. Cette tête est retirée à l'inférence.

Exemple reproductible:

```bash
python -m learning.train_lnn --log data/raw/sim2d_zoh_scan05_medium_dagger_001.csv --jepa-aux-checkpoint models/sensor_jepa_zoh_scan05_medium_001_decoder_refined.pth --jepa-aux-weight 0.3 --jepa-aux-head-hidden-dim 128 --seed 4202 --epochs 2500 --batch-size 256 --sequence-length 64 --state-dim 64 --hidden-dim 128 --lr 3e-4 --eval-every 50 --early-stopping-patience 20 --device cuda --output models/lnn_jepa_aux_w03_001.pth --metrics-output data/processed/experiments/lnn_jepa_aux_w03_001/metrics.json
python -m learning.rollout_lnn --checkpoint models/lnn_jepa_aux_w03_001.pth --episodes 5 --steps 6000 --seed 1001 --no-domain-randomization --output data/raw/lnn_jepa_aux_w03_001_rollout_001.csv --metrics-output data/processed/experiments/lnn_jepa_aux_w03_001_rollout_001/metrics.json --device cuda
python -m learning.rollout_lnn --checkpoint models/lnn_jepa_aux_w03_001.pth --episodes 5 --steps 6000 --seed 2201 --output data/raw/lnn_jepa_aux_w03_001_rollout_randomized_001.csv --metrics-output data/processed/experiments/lnn_jepa_aux_w03_001_rollout_randomized_001/metrics.json --device cuda
```

Balayage obtenu avec une graine commune: `lambda=0.1` donne `3.82%` nominal / `1.79%` randomisé, `lambda=0.3` donne `5.22%` / `0.59%`, et `lambda=1.0` donne `2.23%` / `3.27%`. Le contrôle sans auxiliaire de même graine donne `3.14%` / `2.54%`.

S2 influence donc réellement la robustesse fermée, avec un gain très net sous randomisation pour `lambda=0.3`. Aucun candidat ne bat cependant le checkpoint actif sur les deux protocoles; `models/lnn_zoh_scan05_medium_dagger_002.pth` reste le contrôleur par défaut. Le rapport complet est dans `jepa_lnn_s2_results.md`.

### E1 - Réplication multi-graines

La variance inter-graines est maintenant considérée comme bloquante avant le schedule de `lambda`. La campagne E1 compare le contrôle, `lambda=0.3` et `lambda=1.0` sur les graines `4202`, `5202` et `6202`, puis ajoute deux contrôles de référence (`7301`, `7302`). Les runs `4202` existants sont réutilisés.

```bash
.venv/Scripts/python.exe -m scripts.research.run_lnn_e1 --device cuda
```

Le runner est reprenable: il ignore les checkpoints et rollouts déjà complets, maintient Windows éveillé pendant le calcul, puis met à jour `data/processed/experiments/lnn_e1_multiseed/summary.md`. Les résumés rapportent moyenne, écart-type et min-max entre graines pour les ticks de collision et les événements distincts d'entrée en collision.

Pour reconstruire uniquement le rapport sans lancer de calcul:

```bash
.venv/Scripts/python.exe -m scripts.research.run_lnn_e1 --summary-only
```

La promotion d'un modèle exige désormais une domination nominale et randomisée en moyenne sur au moins trois graines, avec un faible chevauchement min-max face aux répétitions observation-only. E2 reste suspendu jusqu'à la fin de cette campagne.

E1 est terminé. Les cinq répétitions observation-only donnent `3.30% +/- 0.47%` en nominal et `2.01% +/- 0.34%` en randomisé. Le `1.21%` nominal du checkpoint historique est donc un tirage exceptionnel. `lambda=0.3` réduit les ticks randomisés sur les trois graines (`2.01%` vers `1.10%` en moyenne), mais pas de façon stable les événements d'impact; il semble surtout accélérer la sortie de collision. `lambda=1.0` est abandonné pour variance excessive. Le rapport est dans `jepa_lnn_e1_results.md`.

### E3 - Sélection par mini-rollouts

Le mode E3 sélectionne le checkpoint sur le pire taux de collision entre des mini-rollouts nominaux et randomisés, avec les événements puis le rendement comme critères secondaires. Les graines de sélection (`3101`, `3201`) sont distinctes des graines finales (`1001`, `2201`).

```bash
python -m learning.train_lnn --log data/raw/sim2d_zoh_scan05_medium_dagger_001.csv --epochs 2500 --batch-size 256 --sequence-length 64 --state-dim 64 --hidden-dim 128 --lr 3e-4 --eval-every 50 --early-stopping-patience 0 --seed 4202 --device cuda --rollout-select --rollout-eval-every 250 --rollout-eval-episodes 5 --rollout-eval-steps 2000 --output models/lnn_e3_control_seed4202.pth --metrics-output data/processed/experiments/lnn_e3_control_seed4202/metrics.json
```

La tête JEPA auxiliaire reste compatible avec ce mode. E3 compare uniquement le contrôle et `lambda=0.3` sur trois graines; `lambda=1.0` n'est pas poursuivi.

Résultat E3 corrigé: après ajout d'une contrainte de locomotion (`v moyen >= 0.05`), `lambda=0.3` obtient `1.67% +/- 0.16%` nominal et `1.46% +/- 0.72%` randomisé, contre `3.47% +/- 0.93%` et `1.85% +/- 0.53%` pour le contrôle E3. Les événements nominaux baissent nettement, mais les événements randomisés restent équivalents. Le rapport complet est dans `jepa_lnn_e3_results.md`.

### E2 - Schedule du poids auxiliaire

E2 utilise un schedule cosine de `lambda=1.0` vers `0.1` et conserve la sélection E3 avec contrainte de locomotion:

```bash
.venv/Scripts/python.exe -m scripts.research.run_lnn_e2 --device cuda
```

Le runner exécute les graines `4202`, `5202`, `6202` et écrit son résumé dans `data/processed/experiments/lnn_e2_aux_schedule/summary.md`.

Résultat E2: `1.96% +/- 1.10%` nominal et `1.03% +/- 0.37%` randomisé. Le schedule améliore E3 en randomisé, y compris les événements d'impact, mais régresse et devient plus variable en nominal. Il n'est pas promu. Le rapport complet est dans `jepa_lnn_e2_results.md`; la suite passe à S4 MPC-lite.

### S4 - JEPA MPC-lite

Le wrapper S4 garde `dagger_002` comme réflexe et demande au prédicteur JEPA de comparer une action de base à des corrections structurées. Le protocole appairie chaque variante à la baseline sur trois graines nominales et trois graines randomisées:

```bash
.venv/Scripts/python.exe -m scripts.research.run_jepa_mpc_s4 --device cuda
```

Résultat: S4 est rejeté. `slow_only` donne `1.70%` nominal / `0.26%` randomisé contre `1.36%` / `0.26%` pour la baseline de diagnostic. Le profil directionnel `conservative` régresse à `2.56%` / `0.39%`. Aucune paire n'améliore le taux de collision; les événements ne baissent pas. Le décodeur de distance JEPA n'est donc pas un critique de collision suffisamment fiable. Rapport complet: `jepa_lnn_s4_results.md`.

La prochaine voie critique devra prédire directement un risque supervisé de collision future et démontrer sa calibration offline avant tout véto en boucle fermée.

Le premier benchmark de ce critique est disponible dans `collision_risk_results.md`. Sur un test séparé par épisodes, le contexte brut de 8 pas atteint une AP de `0.193`, contre `0.167` pour le latent JEPA et `0.035` pour la distance ultrason seule. Le risque est donc apprenable, mais le JEPA actuel reste moins informatif que son entrée brute. Aucun critique n'est encore activé en boucle fermée.

Pour une campagne longue reproductible:

```bash
python -m scripts.research.run_jepa_overnight --episodes 50 --steps 6000 --epochs 10000 --batch-size 2048 --latent-dim 128 --hidden-dim 512 --refine-decoder
```

Chaque run écrit un résumé et des logs dans `data/processed/experiments/<tag>/`. Le runner active par défaut un early stopping avec une patience de 5 validations sans amélioration.

Avec `--refine-decoder`, le runner ajoute une phase auxiliaire après l'entraînement JEPA: encoder et prédicteur sont gelés, puis seul `obs_decoder` est ajusté sur les latents prédits. Le checkpoint évalué devient alors `models/sensor_jepa_<tag>_decoder_refined.pth`.

Sous Windows, PyTorch peut ne pas être installé; le simulateur ne dépend que de NumPy et Matplotlib. L'entraînement peut rester dans l'environnement WSL/GPU.

## Simulation 3D MuJoCo (sim3d) - Phase A

Ajoutée le 2026-07-15 (D-006) comme piste parallèle pendant la conception du banc v1.0. Le paquet `sim3d/` est un backend MuJoCo qui expose exactement le contrat de `sim2d`: observation `[distance_ultrason, angle_servo, gyro_z]`, action `[v_cmd, omega_cmd, servo_target]`, mêmes `SafetyLayer`, bloqueur ZOH, limiteur de vitesse servo, clamps d'accélération, bruits capteurs, latence, domain randomization, reward et schéma CSV. La génération du monde réutilise `sim2d.world.World.generate`: une graine donnée produit la même arène en 2D et en 3D, extrudée en murs et cylindres.

Installation (environnement `.venv`):

```bash
.venv/Scripts/python.exe -m pip install -r requirements/research.txt
```

Génération de logs, mêmes options que le simulateur 2D:

```bash
python -m scripts.research.simulate3d --episodes 5 --steps 6000 --output data/raw/sim3d_log.csv
```

Visualisation interactive (viewer MuJoCo natif, caméra libre, `--realtime` pour un rythme temps réel):

```bash
python -m scripts.research.simulate3d --episodes 1 --steps 1500 --render --realtime
```

Image finale hors écran: `--save-final-frame data/raw/sim3d_frame.png`.

Rollout d'un checkpoint LNN existant dans le monde 3D via le backend optionnel de `rollout_lnn`:

```bash
python -m learning.rollout_lnn --backend sim3d --checkpoint models/lnn_zoh_scan05_medium_dagger_002.pth --episodes 5 --steps 6000 --seed 1001 --no-domain-randomization --device cuda
```

### Validation Phase A

Protocoles standard (5 épisodes x 6000 pas), checkpoint actif `lnn_zoh_scan05_medium_dagger_002.pth` entraîné uniquement en 2D:

| Protocole | Ticks collision | Événements |
|---|---|---|
| sim2d nominal graine 1001 (re-mesure) | `1.21%` | 61 |
| sim3d nominal graine 1001 | `1.20%` | 126 |
| sim3d randomisé graine 2201 | `0.98%` | 102 |

Le contrôleur 2D transfère donc en boucle fermée dans le monde MuJoCo sans réentraînement (métriques dans `data/processed/experiments/lnn_dagger_002_sim3d_rollout_001/` et voisins).

Écarts assumés par rapport à sim2d:

- en collision, le solveur de contact fait glisser le robot le long de l'obstacle au lieu de le figer; le taux de ticks est comparable mais les événements distincts sont environ deux fois plus nombreux (contacts intermittents);
- le gyroscope lit la vitesse angulaire réelle du corps rigide, pas la commande intégrée;
- le rangefinder est monté au bord du robot puis recalé au centre (`sensor_radial_offset`), pour rester comparable aux mesures 2D partant du centre;
- `--cone-rays N` approxime le cône ±15° du HC-SR04 par N rayons (minimum des lectures); `1` par défaut pour la parité stricte avec le rayon unique 2D.

Performance mesurée: environ 13 000 pas de contrôle par seconde et par instance (10 sous-pas physiques de 2 ms par pas de 20 ms), soit largement de quoi vectoriser des dizaines à centaines d'instances CPU en Phase C.

Phases suivantes prévues: B - jumeau numérique de la tête du banc v1.0 avec rendu caméra (corpus JEPA visuel, pré-validation du critère mécanique ratio gyro <= 3.0); C - vectorisation massive (multiprocessing CPU, puis MJX/WSL si RL ou entraînement par population).
