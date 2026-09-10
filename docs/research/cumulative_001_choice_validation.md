# CUMULATIVE-001 — validation comportementale du choix v2

Gel avant exécution : 2026-09-09. Le développement v2 est connu et positif ;
le contrôle v1 demeure négatif. Aucun résultat comportemental des corps ci-dessous
n'a été consulté. La recette neuronale et les poids après C sont inchangés.

Banque : les 12 corps de `cumulative_001_validation_v1.json`, distincts des six
corps de développement. Leurs apprentissages A→B→A→C sont terminés. Aucun
apprentissage supplémentaire dans cette épreuve. Les résultats prédictifs de ces
corps sont connus ; ceci valide l'usage comportemental choisi après développement,
pas une confirmation indépendante de toute la démarche.

Grille fixée : départs [52,5°, 82,5°, 97,5°, 127,5°] croisés avec échéances
[3, 5, 7, 9] pas, soit 16 situations par corps et 192 au total. Tous les départs
diffèrent du développement ; deux échéances sont nouvelles. Mêmes candidats,
préparation, observables, décision, juge, prior prudent et seuil terminal de 2°
que `cumulative_001_control_v2.md`. Aucun réglage après accès aux résultats.

Conditions : réseau avec rejeu, ridge cumulative, prior nominal, prior prudent,
cible la plus proche. Oracle réservé au juge. Les choix précèdent l'ouverture
des futurs contrefactuels. Scores publiés pour chaque corps et chaque condition.

Portes agrégées préspécifiées : réussite du réseau ≥90 % ; utilité ≥110 % du
meilleur témoin parmi prior/prior prudent/proche ; regret ≤20 % de l'utilité
oracle. Le résultat contre ridge sera rapporté même s'il est défavorable.
Le réseau naïf étant absent, aucune attribution du gain comportemental au seul
rejeu. Une réussite agrégée ne garantit pas une réussite pour chaque corps.

Exécution unique : `python -m learning.cumulative_001_choice --manifest
docs/research/cumulative_001_validation_v1.json --variant validation_v1 --validation`,
sous `learning.cumulative_001_budget`, budget commun 5400 s, plafond 900 s/invocation.
Le lanceur exporte graines et empreinte du code dans
`data/processed/experiments/cumulative_001/control/validation_v1/manifest.json`
avant simulation et refuse d'écraser la banque. Échec conservé si une porte échoue.
