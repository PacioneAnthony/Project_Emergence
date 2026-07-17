# Sonde pré-enregistrée: contingence sensorimotrice visuelle sur le jumeau du banc

Date de pré-enregistrement: 2026-07-16 (avant exécution de la campagne nocturne).
Statut: branche recherche expérimentale, conforme à D-002 (aucune promotion dans le
chemin critique sans battre les baselines pré-enregistrées ci-dessous).

## Question

Un encodeur visuel entraîné en prédiction latente (style JEPA) sur la caméra du
jumeau du banc v1.0 apprend-il la **contingence sensorimotrice** de la tête,
c'est-à-dire: connaître sa propre commande servo améliore-t-il la prédiction de
l'image suivante, et la pose de la tête devient-elle lisible dans le latent?

## Dispositif

- Corpus: `sim3d/bench_corpus.py`, 120 pièces re-tirées par graine, 90 s par pièce,
  babbling moteur mixte (maintiens, balayages sinusoïdaux, saccades), capture 10 Hz,
  images 128x128 stockées, entraînement en 64x64. Graine de base 7000.
- Modèle: `learning/visual_jepa.py` - encodeur convolutionnel (latent 128) +
  prédicteur MLP conditionné par l'action normalisée; cible stop-gradient +
  régularisation variance/covariance, comme `SensorJEPA`.
- Entraînement: `learning/train_visual_jepa.py`, split train/val **par épisodes**
  (15% de pièces jamais vues), AdamW, early stopping sur le ratio de validation.
- Runs: 2 variantes x 3 graines (4301, 4302, 4303), mêmes hyperparamètres:
  - `action`: le prédicteur reçoit la commande servo;
  - `no_action`: entrée action mise à zéro (même capacité, aucune information motrice).

## Baselines et hypothèses (fixées avant exécution)

Baseline de prédiction: **copie du latent** (prédire z_t pour z_t+1), calculée sur
les mêmes latents; métrique principale `pred_to_copy_ratio` (< 1 = le prédicteur
bat la copie), insensible à l'échelle du latent.

- **H1 (contingence motrice)**: sur les 3 graines, le ratio de validation moyen de
  `action` est inférieur à celui de `no_action`, avec des intervalles min-max
  disjoints. Sinon, l'information motrice n'apporte rien au modèle actuel.
- **H2 (pose dans le latent)**: la sonde linéaire d'angle (sin/cos sur latent gelé)
  atteint une MAE < 5 degrés sur les pièces de validation. Une MAE proche du hasard
  (~45 degrés sur 10-170) signifie que le latent n'encode pas la pose.
- **H3 (profondeur, secondaire)**: la sonde linéaire de distance ultrason atteint
  un R2 > 0.5 sur validation.

## Limites assumées

- Simulation uniquement (pièces synthétiques, éclairage simplifié): aucune
  conclusion sur le transfert réel avant des données du banc physique.
- La commande servo est le seul degré de liberté moteur: la contingence apprise est
  minimale par construction.
- Un échec de H1 avec réussite de H2 resterait informatif: latent posé mais
  prédicteur mal conditionné (cf. l'échec du couplage JEPA-LNN direct en 2D).

## Résultats campagne v1 (2026-07-16, 29.6 min)

Résumé dans `data/processed/experiments/visual_night_001/summary.md`:

- H1: moyenne favorable à `action` (`0.9286` contre `0.9329`) mais intervalles non disjoints - **non validée**;
- H2 et H3 rejetées **sur le checkpoint sélectionné**, mais l'historique montre la MAE d'angle en amélioration continue (34.6° vers 14.5° à l'epoch 96, toujours décroissante à l'arrêt) et le R2 distance vers 0.39.

Diagnostic: le critère de sélection/arrêt (ratio pred/copie global) favorise les latents quasi-statiques du début d'entraînement et coupe pendant que la représentation s'améliore encore. De plus, ~ la moitié des paires sont quasi statiques (l'action n'y a rien à prédire), ce qui dilue H1.

## Amendement v2 (pré-enregistré le 2026-07-16 avant exécution, après v1)

Changements et justifications:

1. **Budget fixe 400 epochs, pas d'early stopping, checkpoint = état final** (`--select final`): supprime le conflit sélection/représentation identifié en v1.
2. **Évaluation stratifiée**: ratio pred/copie séparé sur paires en mouvement (`|delta AS5600| > 5°`) et statiques. **H1-v2**: sur les paires en mouvement, `action` bat `no_action` en moyenne avec intervalles min-max disjoints (3 graines).
3. **Corpus étendu à 240 pièces** (mêmes 120 premières réutilisées, graine de base inchangée); le split de validation par épisodes se déplace en conséquence.
4. H2 (MAE < 5°) et H3 (R2 > 0.5) inchangées, évaluées sur le checkpoint final.

Le modèle, ses hyperparamètres et la baseline copie restent strictement identiques à v1. Résultats v2: `data/processed/experiments/visual_night_002/summary.md`.

## Résultats campagne v2 (2026-07-17, 246 min, 6 runs de 400 epochs)

- **H1 globale: rejetée.** Ratio global > 1 pour toutes les variantes: sur un corpus dominé par des paires quasi statiques, la copie du latent reste imbattable en moyenne.
- **H1-mouvement: moyenne favorable, non validée au critère strict.** Sur les paires en mouvement, `action` donne `0.9070 +/- 0.0152 [0.8949, 0.9241]` contre `0.9315 +/- 0.0090 [0.9223, 0.9404]` pour `no_action`. Direction cohérente sur les 3 graines, mais un chevauchement résiduel (0.9241 > 0.9223) empêche la validation pré-enregistrée. Effet suggestif, pas concluant à n=3.
- **Observation exploratoire (non pré-enregistrée, la plus nette de la campagne):** le conditionnement par l'action améliore fortement la lisibilité de la pose dans le latent: MAE d'angle `14.56 +/- 1.00 [13.44, 15.37]` avec action contre `23.01 +/- 0.48 [22.50, 23.45]` sans action - intervalles totalement disjoints. L'information motrice structure la représentation visuelle même quand elle n'améliore que marginalement la prédiction.
- **H2 rejetée** (MAE 14.6 deg >> 5 deg): la pose est présente mais imprécise dans un latent de 128 entraîné 400 epochs.
- **H3 rejetée** (R2 distance ~0.16): la profondeur n'est presque pas linéairement décodable.

Lecture d'ensemble: la contingence sensorimotrice minimale est apprenable en simulation, son signal le plus robuste étant représentationnel (sonde d'angle) plutôt que prédictif. Suites candidates (à arbitrer, aucune lancée): plus de graines pour trancher H1-mouvement; horizon de prédiction multi-pas (l'action compte davantage à 0.3-0.5 s); latent plus grand ou entraînement plus long pour H2; et à terme la comparaison aux mêmes sondes sur les données réelles du banc v1.0.

## Protocole v3 - horizon conditionné (pré-enregistré le 2026-07-17, arbitré par Anthony)

Motivation: à 0.1 s d'horizon, la moitié des paires sont quasi statiques et la copie est
presque imbattable - le dispositif v2 est structurellement défavorable à H1. Par ailleurs,
Anthony souligne qu'un horizon codé en dur est artificiel (le système nerveux module ses
échelles de temps) et que la voie JEPA/LeCun vise une prédiction en espace de représentation,
pas une reconstruction parfaite. Réponses de conception:

- **un seul prédicteur conditionné par l'horizon** (pas un modèle par k): il reçoit le latent
  courant, la séquence des commandes servo `a_t..a_t+k-1` (zéro-paddée) et `k/k_max`; à
  l'entraînement, k est tiré uniformément dans {1..5} (0.1 à 0.5 s). L'horizon devient une
  entrée continue du même système - la grille {1,3,5} n'est que l'instrument de mesure;
- le contrôle `no_action` perd les commandes mais **garde l'horizon** (même capacité, même
  connaissance du "jusqu'où", seule l'information motrice disparaît);
- la prédiction reste en espace latent avec cible stop-gradient (voie JEPA), inchangée.

Hypothèses v3 (fixées avant exécution):

- **H1-v3**: à k=5 (0.5 s) sur les paires en mouvement, `action` bat `no_action` en moyenne
  avec intervalles min-max disjoints sur 3 graines;
- **critère secondaire**: l'avantage moyen de `action` croît avec k sur {1, 3, 5};
- H2 et H3 inchangées (sondes sur latent gelé, checkpoint final).

Dispositif identique à v2 par ailleurs: corpus 240 pièces réutilisé tel quel, 2 variantes x
3 graines (4301-4303), 400 epochs à budget fixe, checkpoint final, latent 128.
Résultats v3: `data/processed/experiments/visual_night_003/summary.md`.

## Résultats campagne v3 (2026-07-17, 252 min)

- **H1-v3: VALIDÉE.** Sur les paires en mouvement, `action` bat `no_action` avec intervalles
  min-max disjoints sur les 3 graines à **tous** les horizons: k=1 `0.813` contre `0.847`
  (avantage +0.034), k=3 `0.698` contre `0.770` (+0.072), k=5 `0.661` contre `0.716` (+0.055).
  Le conditionnement par l'horizon a même débloqué le cas k=1 que v2 laissait en chevauchement.
  C'est la première hypothèse pré-enregistrée validée de cette ligne de recherche: **la
  contingence sensorimotrice visuelle est apprise et exploitée en prédiction**.
- **Critère secondaire (croissance monotone avec k): non satisfait.** L'avantage culmine à
  k=3 (0.3 s) puis décroît légèrement à k=5. Interprétation (non testée): à ~600°/s un
  déplacement servo typique s'achève en 0.15-0.3 s; à 0.5 s la cible est souvent atteinte et
  l'issue redevient plus prévisible sans le détail des commandes.
- **Effet représentationnel répliqué et renforcé**: MAE d'angle `11.75 +/- 0.36` avec action
  contre `24.90 +/- 1.33` sans - troisième réplication, intervalles disjoints.
- H1 globale toujours rejetée (paires statiques dominantes, attendu). **H2 rejetée** mais en
  progression (14.6 -> 11.7 deg). **H3 rejetée** (R2 ~0.28).

Bilan de la ligne v1-v3: contingence sensorimotrice démontrée en simulation au sens
pré-enregistré (H1-v3), effet représentationnel robuste (3 réplications), précision de pose
et profondeur encore insuffisantes (H2/H3). Suites candidates, à arbitrer: pousser H2
(latent plus grand, entraînement long, babbling plus riche); exploiter le modèle en
**exploration active** (choisir la commande qui maximise le progrès de prédiction - la tête
deviendrait pilotée par l'IA dans le viewer); préparer la réplication des sondes sur les
premières données réelles du banc v1.0 quand il existera.
