# CUMULATIVE-001 — apprentissage cumulatif et usage du modèle du cou

Date : 2026-09-09. D-054. Nouveau mandat d'Anthony : poursuivre de façon autonome
jusqu'à des avancées notables et prometteuses, utiliser la RTX 5080 et consigner
avancées comme échecs. Simulation uniquement, sans achat ni service payant.

## Question et séparation des preuves

Une même instance apprend-elle successivement de nouvelles distributions de mouvements,
conserve-t-elle ses acquis et retrouve-t-elle A plus efficacement qu'une instance neuve ?
Une prévision plus juste aide-t-elle ensuite une orientation simulée mesurable ?
Les phases A→B→A→C ci-dessous sont de nouveaux travaux autorisés par ce mandat ; les
anciennes campagnes et réserves restent fermées. Aucun résultat de ce cycle ne sera
présenté comme confirmation indépendante d'une hypothèse fondatrice.

## Développement : variante initiale fixée avant code et calcul

Six vies indépendantes, deux corps par régime vitesse/établissement/friction, avec
paramètres tirés dans les plages BODY-SCHEMA-002. Le corps reste le même dans une vie.
A explore principalement [30°,90°], B [90°,150°], retour A, puis C [30°,150°].
Les distributions sont définies par le générateur ; leurs noms ne sont jamais des
features. Le contexte est observable à travers l'angle et les commandes. On ne demande
pas au modèle de distinguer deux physiques cachées identiques à son entrée.

Chaque phase contient 12 essais de 64 pas. Chaque essai commence au neutre dans un
simulateur réinitialisé, de manière identique entre méthodes ; la mémoire apprise
n'est jamais réinitialisée entre phases. Les cibles ont des maintiens entiers 2..10 pas,
sont tirées sur une grille de 5°, et le dernier segment revient au neutre. A et son
retour utilisent des essais nouveaux de la même distribution. Les évaluations fixes
contiennent 8 essais distincts par domaine et n'alimentent aucun entraînement.
Les entrées F causales et le pas 0,02 s sont repris sans modification du code gelé.

Comparer :

1. prior nominal ;
2. ridge courante : ajustée sur les 4 derniers essais, sans mémoire longue ;
3. ridge cumulative : ajustée sur tous les essais de la vie ; mémoire et coût publiés ;
4. MLP résiduel 13→64→64→1, ReLU, prior nominal, GPU, apprentissage naïf ;
5. même MLP avec 50 % de rejeu uniforme de transitions des essais antérieurs.

Ridge : alpha=1, normalisation ajustée uniquement sur ses données d'apprentissage,
intercept non pénalisé, même solveur r2. MLP : features causales brutes mises aux
échelles fixes de F, sortie résiduelle ×12°, Adam lr=0,001, batch=128, 64 mises à jour
par essai, MSE du résidu/12. Pas d'arrêt choisi sur les scores d'évaluation. Mêmes
initialisations neuronales appariées ; même nombre d'interactions, mises à jour et
exemples par batch. Les ridges sont comparateurs pratiques, pas une égalisation
artificielle de coût avec le réseau. Publier les secondes CPU/GPU séparément.

MLP naïf : batch entièrement tiré dans le nouvel essai ; rejeu : 64 nouvelles
transitions et 64 transitions uniformes de la mémoire passée, ou 128 nouvelles si
la mémoire est vide. Le buffer est une mémoire complète de la petite vie, sans
priorité par erreur. Les choix aléatoires de batch ne reçoivent aucune donnée du juge.
L'état de l'optimiseur, les RNG et les données utiles font partie du checkpoint.

Évaluer à 0, 3, 6, 9, 12 essais de chaque phase : MAE tenue à part sur A/B/C. Avant
retour A, conserver la mesure d'oubli après B ; comparer ensuite avec des apprenants
neufs recevant exactement les essais du retour A (mêmes budgets). Ne pas présenter
une mesure d'ajustement du buffer comme une preuve de rétention.

## Provenance et intégrité

Nouvel espace SHA-256 `cumulative-001/dev/v1`, sous-espaces corps, commande, exécution,
initialisation et batches. Entiers 32 bits supérieurs à 100000 et distincts des valeurs
inventoriées ; valeurs exportées avant génération dans le manifeste. Hacher suites
complètes de commandes et angles sans métadonnées, avec angle initial. Vérifier les
collisions entre apprentissage et évaluation au sein d'une vie. Les scores privés ne
règlent ni normalisation ni sélection. Réutilisation de ces vies permise en développement
seulement, avec toutes variantes journalisées ; validation ultérieure sur corps et
formes nouveaux, recette figée avant accès.

## Ce qui constituerait un progrès utile

D'abord vérifier un apprentissage réel dans chaque domaine : erreur finale <1° et
gain d'au moins 30 % contre le prior, comme objectifs de développement initiaux.
Mesurer l'oubli de A après B en degrés, avec seuil pratique indicatif 0,2°. Si le
naïf n'oublie pas suffisamment, ne pas revendiquer l'intérêt d'une consolidation.
Pour un candidat cumulatif : erreur A après B ≤ erreur A fin d'apprentissage +0,2°,
et acquisition B ≤1° ; comparer acquisition C et rétention A/B après C. Au retour A,
comparer aire sous la courbe d'erreur aux apprenants neufs, sans compter les checkpoints
corrélés comme des vies supplémentaires. Une baseline simple réussissant ces critères
est un résultat positif pour l'organisme, même si le réseau/rejeu ne gagne pas.

Ces seuils guident le développement ; ils seront figés à nouveau AVANT une validation
si le dispositif change. Les six vies ne sont pas une campagne confirmatoire. Tout
échec de faisabilité, de précision ou d'oubli est publié avec son niveau de preuve.

## Usage comportemental après le développement

Si un modèle atteint une précision utile, concevoir et figer une épreuve distincte
sur de nouvelles orientations, mêmes limites [30°,150°] et budgets de pas. Comparer
commande directe de cible, prior utilisé pour planifier et modèle appris utilisé
par le même planificateur. Ne pas conclure sur la seule MAE : erreur de pose réalisée,
délai et coût de mouvement doivent départager les contrôleurs. Aucun mouvement matériel.
Les détails exacts de cette épreuve seront consignés avant son premier calcul.

## Budget et reprises

Première itération : 90 minutes cumulées maximum, 15 minutes par invocation, toutes
simulations et tous tests inclus. Supervision extérieure et réservation durable du
coût selon `learning/body_schema_002_budget.Budget`, nouveau registre propre à ce
cycle. Utiliser réellement CUDA pour les réseaux, sans besoin de saturer la VRAM
avec un petit problème. Sauvegardes immuables aux frontières de phases et essais ;
reprise sous code/configuration identiques seulement. Nouvelle variante si code ou
recette change après exposition, sans effacer les échecs ni remettre le budget à zéro.

## Auto-revue pré-calcul

Auteur : Codex, non indépendant. Risques explicitement vérifiés avant interprétation :
(1) mêmes domaines jugés pour chaque méthode ; (2) aucune étiquette A/B/C dans les
features ; (3) pas de future donnée dans la mémoire de rejeu ; (4) mêmes updates naïf/
rejeu ; (5) comparaison neuve au retour A ; (6) distinction prévision et comportement ;
(7) nouveaux corps et suites de commande ; (8) checkpoint incluant Adam et RNG.
La nouveauté architecturale neuronale est une baseline réversible ; l'acquis ridge
persistant demeure conservé. Toute promotion sera documentée avec preuves et limites.

Action Codex : implémenter, tester, exécuter le développement borné, consigner chaque
variante et poursuivre selon les résultats. Action Anthony : aucune. Action Claude :
aucune attente imposée par le nouveau mandat ; une contre-revue future reste possible.
