# RESILIENCE-001 v3 — validation neuve de la réponse à forte surprise

2026-09-10. Fixé avant tout accès aux résultats de validation. La validation v2
n'a pas été lancée, son seuil fonctionnel de développement ayant échoué.

Condition de lancement : toutes les portes de développement v3 passent sur les
six vies complètes. Si ce n'est pas le cas, ce document reste une proposition
non exécutée. Aucun changement des seuils ou de recette après connaissance des scores.

Douze nouvelles vies sous `resilience-001/validation/v3`. Même dispositif et code
v3 gelé, mêmes distributions de paramètres et grille d'évaluation, graines neuves
pour corps, commandes, initialisation, batches et exécution. Apprenants neufs ; pas
de transfert de poids de développement. Cette validation teste la même famille de
ruptures de vitesse, pas toutes les perturbations possibles d'un organisme.

Critères hérités, appliqués à la banque entière :

- détecter le ralentissement en ≤3 essais sur au moins 10/12 vies ;
- au plus une fausse alarme par vie durant l'acquisition initiale ;
- utilité après perturbation ≥110 % du figé et strictement supérieure si figé zéro ;
- utilité au moins égale à 95 % du meilleur naïf/rejeu/mémoire récente ;
- reprise interprocessus exacte sur toutes les vies, état complet de plasticité inclus.

Utilité : moyenne égale des checkpoints 3/6/12 après rupture puis des vies, distance
angulaire atteinte si erreur terminale ≤2°, zéro sinon. Les mêmes futurs sont jugés
après fixation de tous les choix. Prévision secondaire, délai, sous-objectifs,
rappels et clôtures, coûts et échecs par vie publiés. Au retour : utilité, réussite
et aire d'erreur, aucun gain de rappel présumé. Les situations répétées ne sont pas
des organismes indépendants. Toutes les portes nécessaires à une qualification
globale ; sinon conserver seulement les capacités étayées et les échecs.

Pas d'ouverture de banques historiques, remplacement de vie, tuning ou arrêt choisi
sur un score favorable. Budget commun 5400 s, plafond 900 s/invocation. Auto-revue
Codex non indépendante. Procédure reproductible et publication vérifiant mémoire,
trajectoires, métriques comportementales et empreintes.
