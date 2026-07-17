# Sonde pré-enregistrée: exploration active par progrès d'apprentissage

Date de pré-enregistrement: 2026-07-17 (avant exécution). Arbitrage: Anthony.
Filiation: `visual_bench_probe.md` (H1-v3 validée le 2026-07-17). Cette sonde est le test
par lequel le module « motivation par learning progress », sorti du chemin critique par
D-002, peut regagner sa place avec des chiffres.

## Question

À budget d'expérience égal, une tête qui **choisit ses consignes servo pour maximiser son
progrès d'apprentissage** apprend-elle plus vite qu'une tête qui bouge au hasard - plus
vite au sens du modèle prédictif (ratio pred/copie) et de la représentation (pose lisible)?

## Dispositif

Boucle itérative sur le jumeau du banc (`sim3d/bench_env.py`), 8 rounds par run:
collecte de 2 500 images (64x64, 10 Hz) puis 60 epochs d'entraînement du VisualJEPA
horizon-conditionné de v3 (latent 128, k tiré dans 1..5, action fournie) sur tout le
buffer accumulé. Budget total: **20 000 images par run** (~9% du corpus v3: la question
est l'efficacité d'échantillonnage à petit budget).

Deux conditions, **appariées au maximum**:

- mêmes pièces (graines de pièces identiques par index d'épisode), même cadence de
  décision (une consigne toutes les 0,5 s), même modèle, mêmes hyperparamètres, même
  budget de collecte et d'entraînement;
- **`active`**: la consigne est choisie par progrès d'apprentissage régional
  (8 bins sur 10-170°, fenêtre glissante de 40 erreurs par bin, LP = erreur moyenne
  ancienne moitié - moitié récente, initialisation optimiste des bins sous-échantillonnés,
  epsilon-greedy 0,2); l'erreur attribuée au bin est l'erreur de prédiction latente à
  k=5 sur la fenêtre de décision écoulée;
- **`babbling`**: la consigne est tirée uniformément dans 10-170° à chaque décision
  (seule la règle de choix diffère).

Évaluation après chaque round sur un **jeu de validation fixe et externe**: les épisodes
de validation du corpus v3 (pièces 204-239, jamais vues en collecte), sous-échantillonnés
à 5 000 paires par horizon pour les rounds intermédiaires, évaluation complète au round
final. 3 graines (4301-4303) par condition, 6 runs.

## Hypothèses et critères (fixés avant exécution)

- **H-A1 (prédiction)**: au budget final, le ratio pred/copie sur paires en mouvement à
  k=3 (l'horizon le plus sensible d'après v3) est plus bas pour `active` que pour
  `babbling`, en moyenne sur 3 graines avec intervalles min-max disjoints.
- **H-A2 (représentation)**: idem pour la MAE de la sonde d'angle.
- **Critères secondaires** (rapportés, non décisifs): avantage cumulé sur les courbes
  par round (efficacité d'échantillonnage); ratio à k=1 et k=5.
- **Garde-fou**: l'entropie de couverture angulaire (histogramme AS5600, 16 bins) est
  rapportée par condition; un effondrement de `active` sur une seule région invaliderait
  l'interprétation « exploration » même en cas de gain métrique.

## Limites assumées

- Le progrès d'apprentissage régional (à la Oudeyer) est la forme la plus simple de la
  famille; un échec ne condamne pas les variantes plus riches (progrès par modèle interne,
  ensembles), il condamne la variante minimale.
- Environnement à un seul degré de liberté moteur et faible bruit irréductible: le piège
  « surprise = bruit » est peu probable ici; ce dispositif ne le teste pas.
- Simulation uniquement; la réplication sur banc réel reste un point de passage ultérieur.

## Résultats

Renseignés après campagne dans `data/processed/experiments/active_exploration_001/summary.md`.
