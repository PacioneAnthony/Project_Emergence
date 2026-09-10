# CUMULATIVE-001 — épreuve d'orientation, variante comportementale v1

Date : 2026-09-09. Fixé avant calcul de cette épreuve. Développement, aucune confirmation.

Question : le modèle appris en A→B→A→C améliore-t-il une orientation réalisée ?
Corps : les six vies de développement, paramètres inchangés. Modèles figés après C.
Aucun apprentissage, réglage, normalisation ou sélection de checkpoint pendant l'épreuve.

Conditions : commande directe de la cible ; planification avec prior ; même planification
avec ridge cumulative ; même planification avec réseau à rejeu. Le réseau naïf reste
une comparaison prédictive, sans multiplier ici les choix de contrôleurs.

Douze épisodes par corps, 48 transitions à 50 Hz. Départ physique au neutre et reset
identique pour toutes les conditions. Première cible aux pas 0..23, seconde 24..47.
Cibles tirées indépendamment dans la grille 42,5..137,5° par incréments de 5°, avec
écart entre les deux ≥20°. Nouvelles graines `cumulative-001/control/v1`, sous-espaces
cible et exécution ; valeurs et traces exportées avant simulation. Les déplacements
simulés restent dans l'enveloppe physique du banc ; commandes bornées [30°,150°].

Planificateur : à chaque pas, sept commandes constantes candidates cible +
[-24,-12,-6,0,6,12,24]°, bornées et dédupliquées. Prédire cinq transitions sans
observations intermédiaires, en mettant à jour angle et variation avec les prévisions.
Coût = 0,7×erreur terminale absolue + 0,3×erreur moyenne du chemin +
0,002×variation absolue de commande depuis la précédente. Égalité : plus petit coût
de variation de commande, puis plus petite commande. Le planificateur ne reçoit que
la cible courante, jamais la prochaine consigne ou le modèle caché du simulateur.
Exécuter seulement la première commande puis observer. Même planificateur pour les
trois modèles. La commande directe est une baseline pratique sans calcul de modèle.

Métriques : moyenne absolue de suivi sur tous les pas, erreur finale de chaque palier,
premier délai pour entrer dans ±1° durant deux pas consécutifs (non-réussites explicites),
déplacement commandé total, déplacement réellement observé. Agrégation par épisode
puis par corps, sans traiter les pas comme des réplications indépendantes.

Repère de progrès comportemental : réduction moyenne ≥10 % de l'erreur de suivi contre
la commande directe et contre le prior planifié, sans dégradation moyenne de l'erreur
finale de plus de 0,2°. Publier tous les corps et coûts, même si ces critères échouent.
Une baisse de MAE prédictive n'implique pas ce succès. Si l'épreuve échoue, documenter
le planificateur et la distribution des actions avant une nouvelle variante préspécifiée.

Budget : registre commun CUMULATIVE-001, 15 min par invocation et 90 min cumulées.
Action Codex : implémenter, vérifier le déroulement et exécuter après fin des six vies.
Action Anthony : aucune ; aucun mouvement réel autorisé ou exécuté.
