# RESILIENCE-001 v2 — validation de la recette de récupération

2026-09-10. Document fixé avant création et accès à la banque de validation.
Il ne modifie pas les seuils de développement. La v1 arrêtée pour alias d'optimiseur
reste exclue. Code v2, architecture, détecteur, archives et comparateurs inchangés.

Douze vies neuves `resilience-001/validation/v2`, mêmes distributions de paramètres,
nouveaux corps, initialisations et commandes. Pas d'héritage des poids de développement.
Même simulateur et grille comportementale : validation de recette dans cette famille,
pas une preuve de transfert à tous les types de perturbations ni d'autonomie ouverte.
Trois phases continues, 12 essais par phase, ralentissement non annoncé puis retour.
L'agent ne reçoit ni phase, ni vitesse, ni signal du juge.

Déclenchement de cette validation : développement fonctionnel prometteur face au
modèle figé et sans déficit >5 % face au meilleur témoin adaptatif. Une détection
insuffisante demeure un échec distinct ; la validation ne l'efface pas et ne sert
pas à modifier le détecteur. Si le déclenchement fonctionnel échoue, ne pas lancer.

Critères maintenus : détection de la perturbation ≤3 essais sur au moins 10/12 vies ;
au plus une fausse alarme initiale par vie ; utilité du superviseur après perturbation,
moyenne égale des checkpoints 3/6/12 puis des vies, ≥110 % de celle du modèle figé
et strictement supérieure si ce témoin vaut zéro ; utilité ≥95 % de celle du meilleur
naïf/rejeu/récent. Reprise complète exacte sur 12/12 vies. Une qualification globale
de la recette exige toutes ces portes ; publier séparément les capacités qui passent.

Retour : publier les délais de détection, rappels et clôtures, utilités, taux de
réussite et aires d'erreur contre les quatre comparateurs. Aucun gain d'archive
présumé. Aucun arrêt choisi sur un score favorable, remplacement de vie ou tuning.
Unité indépendante : vie. Les situations et checkpoints d'une même vie sont corrélés.

Intégrité : nouvelles graines contrôlées, source gelée, aucune duplication de
trajectoire complète apprentissage/évaluation au sein d'une vie, contrôles du
registre et checkpoints, transitions mécaniques continues et budgets d'updates
appariés des quatre agents adaptatifs. Les deux bras `recent` et `adaptive` isolent
l'ajout de détection/archives au-delà de la mémoire récente.

Budget commun RESILIENCE-001 : 5400 s au total et 900 s/invocation, essais perdus
et tests inclus. Revue Codex non indépendante. Les candidats du noyau restent
expérimentaux tant qu'une qualification bornée n'a pas été inscrite explicitement.
