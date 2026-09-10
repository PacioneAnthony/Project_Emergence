# RESILIENCE-001 — journal des progrès et échecs

2026-09-10. Cadrage D-056 : résilience et apprentissage intrinsèque prioritaires.

## v1 — arrêt technique après la première vie

Six tests initiaux passent, intégration au noyau avec commits atomiques et reprises.
Première vie effectuée : changements détectés après deux essais, archive rappelée
au retour, reprise interprocessus exacte. Ces traces exploratoires restent conservées.

Un audit supplémentaire soupçonne un alias de tenseurs Adam dans la restauration
d'archive. Le nouveau test `test_recalled_optimizer_cannot_mutate_the_saved_archive`
échoue effectivement : une mise à jour de la copie modifie l'archive. Les poids
eux-mêmes étaient copiés ; la mémoire de l'optimiseur ne l'était pas nécessairement.

Décision : arrêter v1, ne pas exécuter les cinq autres vies et ne pas analyser cette
banque incomplète comme preuve de résilience. Les sources exactes sont archivées
dans `data/processed/experiments/resilience_001/source_v1`, avec empreintes du manifeste.
Le budget de v1 et du test échoué reste chargé au cycle commun.

## v2 — correction d'intégrité avant nouvelle exécution

Copie profonde de l'état avant `load_state_dict`, test de non-mutation de l'archive.
Même recette, seuils, architecture, comparateurs et tâches que le protocole v1.
Nouvel espace de graines `resilience-001/dev/v2` et six nouvelles vies ; la première
vie de v1 n'est pas incorporée au résultat de v2. Aucune adaptation des seuils aux scores.
Manifeste et sources gelés avant calcul. Reprises et archives seront revérifiées.

## v2 complète — récupération réelle, surcoût face au naïf

Six vies complètes et 343 tests verts. Surprises détectées en deux essais sur 5/6
ralentissements et 6/6 retours, aucune fausse alarme initiale. Onze sous-objectifs
ouverts puis clos, six rappels d'archives. Reprises exactes ; 864 situations et
123 fichiers vérifiés, continuité mécanique et trajectoires distinctes contrôlées.

Après ralentissement (moyenne des checkpoints 3/6/12) : utilité adaptatif 17,292°,
naïf 19,167°, mémoire récente 12,361°, rejeu cumulatif 0,231°, figé 0°. L'adaptatif
retrouve 98,61 % de réussite au dernier checkpoint mais perd 9,78 % d'utilité pendant
la récupération face au naïf, au-delà des 5 % tolérés. Portes : 4/5 passent.
V2 n'est donc pas promue, et sa validation conditionnelle n'est pas lancée.

Le rejet d'expériences obsolètes est utile ici. La meilleure précision finale
(adaptatif 0,107°, naïf 0,121°) ne compense pas une récupération fonctionnelle plus lente.
Au retour, l'archive réduit l'aire d'erreur face au naïf mais ne domine pas toutes
les utilités. Pas de preuve générale de supériorité du superviseur.

## v3 — plasticité courte déclenchée par forte surprise

Nouvelle recette préspécifiée dans `resilience_001_v3.md`, nouvelles vies et sources.
Une forte surprise peut déclencher immédiatement la réponse ; trois essais sans
rejeu précèdent le retour à une mémoire récente. L'expérience récente est conservée,
les archives restent immuables. Règle de réponse interne explicite, pas exploration
autonome ouverte. Neuf tests passent, dont reprise au milieu d'une période de plasticité.
Sources et poids v2 conservés ; budget cumulé inchangé.

## v3 développement complet — critères satisfaits

Six nouvelles vies : douze changements détectés au premier essai observé, aucune
fausse alarme initiale ; douze sous-objectifs clos, six rappels. Reprises exactes
pendant la plasticité. Utilité post-rupture 17,778° contre naïf 17,755° (quasi-égalité,
pas une large supériorité), récente 12,778°, rejeu 0,162°, figé 0°.
Réussite sur checkpoints 3/6/12 : 98,61 % ; au checkpoint final : 100 %.
Les cinq portes passent. 345 tests verts. 864 situations et 126 fichiers audités.
Recette conservée pour validation sur 12 nouvelles vies, protocole fixé avant accès.

Incident de préparation de validation : l'enrichissement facultatif du manifeste
par métadonnées a rencontré un JSON de résultats dans un glob de manifestes et a
échoué avant toute écriture. Le manifeste original créé reste inchangé et gelé
(SHA-256 853ae0fce80353ab8550ae97e439b61e167ea64e32e608989490f482a0a864c4).
Le protocole de validation existait avant lancement. Le contrôle supplémentaire
de collision avec toutes les graines résilience a été fait juste après lancement :
zéro collision, reçu séparé `resilience_001_validation_v3_provenance.json`.
Aucun code, seuil, poids ou manifeste modifié sur la validation.

## Validation v3 complète — récupération répliquée, fragilité restante

Douze nouvelles vies, recette inchangée. Les 24 changements sont détectés dès le
premier essai ; aucune fausse alarme initiale ; 24 sous-objectifs clos selon le
critère interne, 12 rappels d'archives et 12 reprises exactes. Cinq portes vertes.
Utilité post-rupture : superviseur 16,782°, naïf 16,100°, récent 11,354°, rejeu
0,602°, figé 0°. Gain +4,24 % sur naïf, +47,81 % sur récent. Réussite agrégée
checkpoints 3/6/12 : 93,52 % ; dernier checkpoint 137/144, soit 95,14 %.

Échec local prioritaire : life-04 atteint seulement 50 % de réussite finale après
ralentissement, utilité 5° contre oracle 11,667°, malgré MAE 0,0815°. Sous-objectif
prédictif clos ne signifie donc pas compétence fonctionnelle retrouvée. Ne pas
utiliser ce cas de validation pour régler la recette ; en dériver une nouvelle
question et de nouveaux cas. Au retour, archives rappelées mais pas de domination
sur toutes les mesures : aire d'erreur moins bonne que mémoire récente.

Publication : 234 empreintes, 1728 situations vérifiées, figure inspectée, mémoires
du noyau rechargées. 345 tests verts ; sources identiques au reçu. Budget final
1022,517 s / 5400 s, 22 invocations, aucune réservation restante. Données environ
339 Mo hors Git. Tous les échecs antérieurs et leurs coûts restent conservés.

Décision D-057 : service expérimental intégré et récupération locale répliquée,
pas noyau universellement résilient. Priorité suivante : le besoin interne doit
conduire au choix d'expériences et se clore sur une capacité réellement retrouvée,
avec nouvelles perturbations. La compréhension du monde/humain reste hors portée
de ce jalon. Rapport : `resilience_001_results.md`. Aucune action Anthony requise.
