# CUMULATIVE-001 — validation de la recette cumulative

Date : 2026-09-09. Fixé après six vies de développement et avant toute vie de validation.
La banque de validation est neuve, n'est pas une confirmation scientifique générale,
et ne sera pas utilisée pour régler les modèles ou sélectionner des vies favorables.

Recette identique à v1 : corps constant dans une vie ; A→B→A→C, 12 essais de 64 pas
par phase ; mêmes cinq comparateurs et contrôle neuf au retour A. Apprenants neufs
par vie ; initialisations appariées naïf/rejeu. Données d'évaluation sans apprentissage.
Réseau principal choisi sur développement : MLP avec rejeu uniforme 50/50, sans changement
d'architecture, d'optimiseur, de taux d'apprentissage ni de budget d'updates.

Douze vies neuves, quatre par régime, espace `cumulative-001/validation/v1`. Les corps,
les graines de modèles et les suites de commandes sont nouveaux. Même famille de
générateurs ; la portée reste ce simulateur et ces familles d'excitation. Valeurs des
graines exportées et contrôlées avant génération dans le manifeste JSON. L'ensemble
de la banque est consommé une seule fois ; un échec est conservé, sans remplacement.

Critères par capacité, fixés avant lecture :

- Acquisition utile : pour le réseau principal, MAE ≤1° et amélioration ≥30 % contre
  prior dans le domaine courant à la fin de chaque phase A/B/C, sur chaque vie.
- Rétention : A après B ≤ A fin de phase A +0,2° ; A et B après C restent chacun
  dans +0,2° de leur score de fin de phase d'acquisition, sur chaque vie.
- Récupération : au retour A, moyenne des cinq checkpoints (0/3/6/9/12 essais) réduite
  d'au moins 20 % en moyenne face au réseau neuf avec rejeu, et au moins 9/12 vies
  favorables. Publier aussi l'aire trapézoïdale, sans appeler les checkpoints des vies.
- Reprise : paramètres, prévisions, optimiseur/RNG et prochaine mise à jour identiques
  après chargement dans un nouveau processus, sur les 12 vies.
- Valeur prédictive de la solution : moyenne A/B/C après C comparée à réseau naïf,
  ridge cumulative et prior ; publier écarts appariés, gains relatifs et chaque vie.
  Un gain moyen ≥15 % sur naïf et ridge est un repère secondaire, pas une condition
  pour effacer un résultat positif de rétention/récupération.

Une absence d'oubli du naïf >0,2° signifie que la résistance à un oubli important
n'est toujours pas démontrée. Ne pas modifier le problème pour fabriquer cette preuve
après lecture. La rétention et la valeur de la réutilisation d'expérience restent mesurables.

Analyse : unité indépendante = vie ; moyenne égale des trois domaines puis des vies.
Intervalles bootstrap BCa à 95 %, 10000 tirages, via learning/paired_stats.py, sur les
différences appariées de MAE après C. Graines statistiques préfixées SHA-256 avec noms
de contraste. Intervalles descriptifs de cette validation de recette, sans déclaration
de découverte fondatrice ni assimilation à une non-infériorité universelle.

L'épreuve d'orientation reste une preuve distincte. Son éventuel échec ne change ni
cette recette ni ses critères ; il sera consigné et traité par une variante de contrôle
séparément préspécifiée. Aucun modèle n'est activé dans le système physique.

Budget : mêmes 90 minutes cumulées et 15 minutes par invocation, ledger du cycle
CUMULATIVE-001. Action Codex : exécuter les douze vies puis publier tous les résultats.
Action Anthony : aucune. Réserves et expériences anciennes conservées fermées.
