# RESILIENCE-001 v3 — plasticité temporaire à forte surprise

2026-09-10. Fixé après les six vies v2 et AVANT code/calcul v3. V2 reste complète
et négative sur son critère de coût fonctionnel face au meilleur témoin adaptatif.
Sa validation prévue n'est pas lancée : condition de déclenchement non satisfaite.

Résultat motivant : après perturbation, utilité superviseur 17,292° contre naïf
19,167° (−9,78 %), mémoire récente 12,361°, rejeu cumulatif 0,231°, figé 0°.
L'attente de deux anomalies et le mélange avec les anciennes transitions retardent
la récupération. Cette interprétation motive une nouvelle recette ; elle n'est pas
une preuve causale séparée de l'effet de chacune de ses deux modifications.

Conserver banc, mesures, six vies dev puis éventuellement douze vies de validation,
comparateurs, budgets, étapes physiques continues et contrats de reprise. Sources
v2 conservées ; nouveau lanceur v3 et sous-classe du superviseur, sans modifier v2.
Nouvelles graines `resilience-001/dev/v3`, apprenants neufs pour toute vie.

Deux modifications explicites, sans phase ni paramètre caché :

1. Une forte surprise, MAE préquentielle > max(1°, 6×médiane de référence), déclenche
   immédiatement la même réponse que deux surprises modérées. Les huit essais de
   rodage, seuil modéré, repos et clôture restent inchangés.
2. Après une alarme, apprendre pendant trois essais exclusivement sur les transitions
   de l'essai courant (même nombre de mises à jour). Les nouvelles transitions sont
   quand même mémorisées. Ensuite rétablir le rejeu à mémoire récente. Archives
   immuables, rappel par pertinence observée et sous-objectifs conservés. Inclure
   le compteur de plasticité dans l'état persistant et sa vérification interprocessus.

Même critère fonctionnel principal : gain sur figé, déficit ≤5 % face au meilleur
naïf/rejeu/récent pendant la récupération (checkpoints 3/6/12). Détection ≤3 essais
sur ≥5/6 vies, au plus une fausse alarme initiale par vie. Reprise exacte obligatoire.
Publier le retour et les échecs locaux. Si toutes les portes passent, figer une
validation neuve de la recette complète avant accès. Pas de tuning sur validation.

La réponse intrinsèque demeure une règle écrite, pas une découverte autonome
d'objectifs. La création du besoin de récupération dépend d'observations ; le choix
des expériences d'apprentissage reste imposé par ce premier banc. Budget commun
RESILIENCE-001 inchangé, 5400 s / 900 s par invocation, v1/v2 incluses.
