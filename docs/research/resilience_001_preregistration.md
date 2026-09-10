# RESILIENCE-001 — apprendre après une rupture, conserver et retrouver ses acquis

2026-09-10. D-056. Cadrage prioritaire d'Anthony : noyau résilient et apprentissage
intrinsèque ; la précision est un instrument de diagnostic, pas l'objectif final.
Auto-revue Codex non indépendante. Simulation seulement, anciens résultats conservés.

## Capacité visée

Un changement non annoncé rend l'ancien modèle inadéquat. Le noyau doit détecter
sa perte de fiabilité depuis ses observations, ouvrir un sous-objectif de récupération,
adapter sa mémoire et retrouver un fonctionnement utile. Le retour d'une dynamique
connue teste la réutilisation d'acquis archivés. Aucune étiquette de phase ni vitesse
physique cachée n'est fournie à l'apprenant ou au superviseur.

Ce premier lot n'établira pas encore la génération libre d'objectifs ni la compréhension
du monde humain. Le sous-objectif interne « rétablir la prévisibilité » est une règle
explicite ; le choix des expériences d'apprentissage reste fourni par le banc.

## Développement v1 fixé avant code et données

Six nouvelles vies, namespace `resilience-001/dev/v1`. Tirages indépendants : vitesse
initiale uniforme 480..720°/s, vitesse perturbée 120..240°/s, gain 8..12 et amortissement
0,10..0,20 constants. Trois phases de 12 essais de 64 pas : initiale, ralentissement
brutal, retour à la vitesse initiale. Le simulateur d'apprentissage reste continu,
sans remise au neutre entre essais ni remise à zéro lors du changement de vitesse.
Seule la limite de vitesse de commande change ; corps, état mécanique et capteurs
continuent. Les phases appartiennent exclusivement au banc et au juge.

Commandes communes aux méthodes : valeurs continues uniformes 30..150°, maintenues
3..12 pas, graines nouvelles par essai, sans queue neutre imposée. Réseaux neufs,
architecture et optimiseur CUMULATIVE-001 gelés, 64 updates × batch128 par essai.
Comparateurs : réseau figé après acquisition initiale ; naïf continu ; rejeu uniforme
cumulatif ; mémoire récente (quatre essais) ; superviseur proposé. L'arrêt du témoin
figé utilise la phase du banc, explicitement privilégiée, pas celle de l'agent proposé.
Tous les agents adaptatifs reçoivent exactement les mêmes transitions réalisées.

Superviseur proposé : même réseau à rejeu, buffer limité aux quatre essais récents.
Erreur préquentielle de l'essai mesurée AVANT apprentissage. Huit essais de rodage,
puis surprise si MAE > max(0,35°, 3×médiane des six dernières erreurs). Deux surprises
consécutives déclenchent « rétablir la prévisibilité ». Les anomalies ne remplacent
pas la référence de stabilité. Archiver une copie complète du modèle toutes les
quatre mises à jour d'essai stables, maximum six copies, sans identifiant de contexte.
À l'alarme, comparer les archives sur le dernier essai déjà observé : restaurer la
meilleure si son erreur est ≤70 % de l'erreur courante ; sinon conserver les poids
et vider le buffer obsolète. Ne pas effacer les archives. Trois essais consécutifs
sous le seuil clôturent le sous-objectif. Repos du détecteur de trois essais après
alarme ; référence réinitialisée aux erreurs de récupération après sa clôture.
Ces règles sont explicites, sans prétention d'émergence biologique.

## Mesures orientées résilience

Publier le délai de détection en essais, les fausses alarmes avant perturbation,
les sous-objectifs ouverts/clos, restaurations d'archives, coût et tailles mémoire.
Prédiction : erreur préquentielle et erreur tenue à part ; pas uniquement erreur finale.
Acquisition/perturbation/retour : évaluations à 0/3/6/9/12 essais, cibles continues,
huit essais tenus à part par phase, jamais fournis à l'apprenant.

Usage : choix d'une cible atteignable à échéance, procédure CUMULATIVE-001 v2 inchangée,
aux checkpoints 0/3/6/12 de chaque phase. Quatre départs nouveaux 57,5/77,5/102,5/132,5°,
échéances 4/6/8 pas, 12 situations par corps/checkpoint. Rapport d'utilité (distance
atteinte, zéro si erreur terminale >2°), réussite et regret face à l'oracle du juge.
Comparaison au naïf incluse. Tous choix AVANT observation des futurs du juge.

Repères de développement, à ne pas transformer en confirmation : détection ≤3 essais
sur ≥5/6 vies, ≤1 fausse alarme par vie avant rupture ; gain d'utilité moyen après
perturbation (checkpoints 3/6/12) ≥10 % face au modèle figé ; utilité ne baissant pas
de >5 % face au meilleur naïf/rejeu/récent. Au retour, publier aussi les cas défavorables
et l'aire d'erreur : une archive inutile reste un échec, pas une preuve de rétention.
Les chiffres d'erreur à un pas restent secondaires au fonctionnement après changement.
Si la manipulation n'affecte pas le témoin figé, qualifier le banc d'insuffisant.

## Intégration et reprise

Nouveau service expérimental dans la mémoire SQLite de CognitiveKernel, sans toucher
aux sources CUMULATIVE-001 gelées. Checkpoints intègres adressés par SHA-256, modèle,
Adam, RNG, buffers, archives, détecteur et sous-objectifs. Transaction unique pour
chaque essai : contenu, curseur, checkpoint et trace de décision. Réexécution idempotente,
contenu différent sous même identifiant refusé. Aucun checkpoint orphelin promu.
Registre du noyau : versions expérimentales candidates, pas de qualification universelle.
Reprise du service à une frontière d'essai, avec prédictions et prochaine mise à jour
identiques dans un autre processus. La persistance complète du simulateur hôte n'est
pas revendiquée : il continue pendant le redémarrage du service cognitif.

## Exécution et décisions

Budget propre RESILIENCE-001 : 90 minutes cumulées, 15 minutes par invocation,
supervision durable et tests inclus. Exporter manifeste et empreintes avant calcul.
Contrats puis première vie puis les cinq autres sans changer la recette. Conserver
les échecs techniques et scientifiques. Si développement prometteur, figer une
validation sur de nouvelles vies avant accès ; sinon conclure les limites du lot
et préparer une variante distincte, sans régler sur une validation consommée.
