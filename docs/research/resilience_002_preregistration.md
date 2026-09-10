# RESILIENCE-002 — besoins fonctionnels et choix d'expériences

2026-09-10 · D-058 · fixé avant code et données. Suite autorisée par Anthony.
Priorité : résilience et apprentissage intrinsèque. Auto-revue non indépendante.
Simulation uniquement ; anciennes banques et sources inchangées.

## Question

Une petite mémoire de résultats réellement vécus permet-elle de garder ouvert un
besoin d'apprentissage tant que les promesses de fonctionnement restent peu fiables ?
Choisir des expériences selon ces lacunes apporte-t-il plus qu'un catalogue parcouru
systématiquement ? Distinguer ces deux questions : un moniteur honnête peut être utile
même si l'ordonnanceur actif ne dépasse pas un témoin simple.

## Variante v1

Six vies nouvelles `resilience-002/dev/v1`. Vitesse initiale 420..720°/s, vitesse
perturbée 90..240°/s, gain 8..12, amortissement 0,10..0,20. Longueurs initiale et
perturbée tirées indépendamment entre 14 et 18 essais inclus ; retour 16 essais.
Instants inconnus de l'agent. Chaque politique possède un simulateur physique continu
du même corps ; aucune remise à zéro entre essais. Trois politiques : cycle fixe,
choix uniforme, choix selon besoin. Même architecture et budgets d'interaction/update.

Un essai contient quatre épisodes : maintenir un départ tiré dans 75..105° pendant
24 pas, puis une commande pendant huit pas. Échéance demandée tirée dans [4,6,8].
Toutes les transitions physiques sont comptées, y compris la préparation : 128 pas
par essai. Catalogue proposé au noyau : petits déplacements 5..15°, moyens 15..30°,
grands 30..60°. Valeur et direction tirées ; inversion de direction si nécessaire
pour garder la cible dans 30..150°. Même réalisation aléatoire par essai/politique,
le choix de catégorie explique les différences d'expérience. Le catalogue est écrit,
pas découvert spontanément. Aucune récompense ou annotation privée du juge reçue.

Le modèle fonctionnel prédit directement l'angle à l'échéance, avec observation
causale F et horizon/8 en entrée : MLP 14→64→64→1, ReLU, résidu ×12° ajouté au
prior nominal angle+clip(cible-angle,±12×h). Dernière couche initialement nulle.
Adam 0,001, 64 updates par essai, batch128, moitié nouveaux exemples et moitié
mémoire des huit derniers essais (256 exemples), ou tous nouveaux si vide.
Chaque épisode vécu fournit huit exemples h=1..8 depuis son observation initiale.
Les angles futurs deviennent des cibles d'apprentissage après observation ; ils
n'entrent jamais dans une prévision. Aucun corpus de futurs contrefactuels appris.

Un écart terminal vécu >max(3°, quatre fois la médiane des 12 derniers écarts)
après six essais déclenche une rupture : vider le rejeu obsolète et les preuves
récentes de fiabilité, conserver les poids et rouvrir le besoin. Même règle pour
les trois politiques ; le besoin peut aussi se rouvrir sur promesse non tenue.

## Besoin interne et choix

Prévision et promesse gelées avant chaque action. Promesse : distance prévue à la
cible + marge ≤2°. Marge = maximum de 0,25° et quantile 90 % des 16 derniers écarts
terminaux vécus, ou 2° si moins de huit observations. Le juge n'entre pas dans ce calcul.
Garder un historique maximal de 24 résultats vécus, avec catégorie et promesse.
Besoin clos seulement après au moins 12 résultats, au moins deux dans chaque
catégorie, quantile 90 % des écarts ≤2°, au moins trois promesses réussies et
aucune promesse ratée dans cette fenêtre. Une clôture peut être contredite par le
juge tenu à part ; publier cette contradiction, pas seulement le nombre de clôtures.

Politique selon besoin : choisir d'abord une catégorie non observée ; ensuite
score = médiane des quatre derniers écarts /2 (plafond5) +2/sqrt(nombre observé).
Après deux choix consécutifs identiques, forcer la catégorie la moins observée
parmi les autres. Scores calculés seulement depuis résultats vécus. Cycle fixe
0→1→2 ; uniforme via RNG persisté. Tous choix et justifications enregistrés.
On teste une forme restreinte de sélection intrinsèque, pas une autonomie ouverte.

## Évaluation indépendante et critères

Aux checkpoints 0,6,fin de chaque phase : choix de cibles à distance
±[5,10,15,20,30,40,50,60]°, départs 55/80/100/130°, échéances 4/6/8.
Prévision terminale directe et marge observée, même règle de décision pour chaque
politique : plus grande distance jugée atteignable, sinon cible la plus proche.
Tous choix précèdent les futurs du juge. Aucun apprentissage ou sélection depuis
ces résultats. Utilité = distance si cible atteinte à 2° près, zéro sinon.
Publier réussite, fraction de l'utilité oracle, pire vie, sous-objectifs et clôtures
contredites (besoin clos alors que réussite tenue à part <80 % OU utilité/oracle <70 %).

Repères développement : moins de 10 % de clôtures contredites, besoin clos dans au
moins 50 % des checkpoints après apprentissage pour éviter le toujours-ouvert ;
réussite finale après rupture ≥90 % agrégée et ≥70 % dans chaque vie ; utilité/oracle
≥80 % agrégée. Comparaison active/cycle : gain d'utilité post-rupture ≥10 % pour
revendiquer une valeur propre de sélection intrinsèque, sinon conserver le témoin
simple. Rapporter aussi uniforme, sans choisir ensuite un témoin avantageux.
Unité indépendante = vie. Ce sont des portes séparées, aucune moyenne favorable
ne masque l'échec du pire corps. Une validation neuve n'est préparée que pour une
capacité passant ses portes ; tout échec ou changement exige une variante distincte.

## Persistance et budget

État complet du modèle, Adam, RNG, mémoire, résultats, besoin et choix persisté
atomiquement dans la mémoire du noyau. Interruption après publication/avant commit/
après commit testée ; idempotence et contenu divergent refusé. Reprise dans un autre
processus vérifiant prochaine décision et prochaine mise à jour, pendant que le
simulateur hôte continue. Sources et manifeste gelés avant calcul, graines distinctes,
aucun remplacement de vie terminée. Budget propre 5400 s, 900 s/invocation, tests,
analyses et variantes échouées inclus, RTX 5080. Consigner résultats et limites.
