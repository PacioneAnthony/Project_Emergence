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

## Résultats (2026-07-17, 20 min de campagne)

- **H-A1 REJETÉE**: ratio k=3 mouvement final `0.747 +/- 0.010` pour `active` contre
  `0.732 +/- 0.014` pour `babbling` - le babbling fait légèrement mieux, la moyenne n'est
  même pas favorable à l'actif.
- **H-A2 REJETÉE**: MAE angle `22.8 +/- 0.9` contre `20.8 +/- 2.1` - même sens.
- Garde-fou: l'actif a bien concentré son échantillonnage (entropie `0.794` contre
  `0.994`) sans s'effondrer; la concentration n'a simplement rien rapporté.

**Conséquence D-002: le module « motivation par learning progress », dans sa forme
minimale régionale, ne regagne pas sa place.** Il reste hors du chemin critique.

Lecture: dans cet environnement à un seul degré de liberté moteur et aux pièces
statistiquement homogènes, toutes les régions angulaires sont à peu près également
apprenables; la couverture uniforme est alors quasi optimale et la sélectivité de
l'actif est un coût sans bénéfice. Le LP régional n'avait littéralement rien de
différentiel à exploiter. La sonde condamne la variante minimale ici, pas la famille:
le test discriminant serait un environnement **hétérogène** (une région au stimulus
imprévisible - du bruit inapprenable - contre des régions structurées), où le LP doit
théoriquement éviter le piège du bruit alors que le babbling y gaspille son budget.

Observation annexe (non pré-enregistrée): les deux conditions montrent une courbe en U -
le ratio sur le juge externe s'améliore jusqu'à ~7 500 images puis se dégrade jusqu'au
budget final. L'entraînement continu sur un buffer on-policy croissant dérive de la
distribution du juge externe (collectée par un babbling différent). Toute future sonde
de ce type devra soit ancrer l'évaluation dans la distribution de collecte, soit
mélanger un tampon de rejeu, soit s'arrêter sur validation.

Aucune suite lancée sans arbitrage.
