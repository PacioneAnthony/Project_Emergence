# RESILIENCE-002 v2 — validation de la récupération et du choix actif

2026-09-10 · fixé après six vies de développement, avant nouvelles données.

Développement : besoin actif = 100 % de réussite finale dans chacune des six vies,
91,48 % de l'utilité oracle, gain d'utilité post-rupture +17,77 % contre cycle.
Ces deux capacités passent leurs portes et justifient une validation sur douze
nouvelles vies `resilience-002/validation/v2`. Modèles réinitialisés, mêmes trois
politiques, distributions physiques, longueurs, interactions, updates, seuils,
catalogue, checkpoints et code gelé v2. Aucune ancienne vie réutilisée.

Portes confirmatoires inchangées pour `need` : réussite finale perturbée moyenne
≥90 %, minimum par vie ≥70 %, fraction oracle finale moyenne ≥80 % ; gain d'utilité
sur cycle fixe aux checkpoints perturbés 6 et fin ≥10 % pour qualifier le choix
actif. Uniforme est aussi publié. Une vie reste l'unité indépendante. Publier les
résultats de toutes les vies, y compris l'échec d'une porte ; aucune retouche en
fonction de la validation. Douze reprises exactes et égalité des budgets vérifiées.

**Le moniteur global n'est pas proposé à la qualification.** Le code d'analyse
gelé mesure l'honnêteté aux checkpoints après apprentissage : 0/18 clôtures
contredites et couverture 18/36 pour `need` en développement. Or le protocole
en prose n'excluait pas explicitement les checkpoints 0. L'audit complémentaire
les inclut : 10/28 états clos sont contredits, tous au premier checkpoint après
changement encore inobservé. La porte stricte <10 % échoue. Cette divergence de
périmètre est publiée ; le verdict favorable restreint ne qualifie pas le moniteur.
En validation, publier les deux dénominateurs et conserver le verdict strict.
L'impossibilité d'anticiper une rupture cachée ne transforme pas cet échec en succès.

La validation porte donc uniquement sur la récupération après expérience et sur
l'éventuel avantage du choix actif, capacités distinctes prévues au protocole.
Pas de promotion globale du noyau, ni de prétention à une résilience instantanée.
Budget partagé 5400 s / 900 s par invocation ; aucun budget supplémentaire.
Le manifeste, ce texte et l'audit sont liés par un reçu SHA-256 avant lancement.
