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

## Résultats

Renseignés après la campagne dans `data/processed/experiments/visual_night_001/summary.md`.
