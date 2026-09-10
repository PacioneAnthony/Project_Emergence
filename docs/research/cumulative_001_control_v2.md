# CUMULATIVE-001 — choisir une orientation atteignable, contrôle v2

Date : 2026-09-09. Développement préspécifié après l'échec du contrôle v1.
V1 reste négative et close, sans retuning de son score ni du modèle appris.

## Question

Le modèle appris permet-il de choisir une vue plus éloignée réellement atteignable
avant une échéance, face à un modèle nominal ou un choix prudent simple ? Le résultat
est une capacité de sélection d'action, pas une prétention d'accélérer le servo.

Six corps de développement et modèles figés après C. Nouvelle banque de 25 situations
par corps : départs 45°, 75°, 90°, 105°, 135°, croisés avec échéances 3,4,5,6,8 pas.
Préparation physique : maintenir le départ pendant 32 pas ; tous les agents reçoivent
ensuite les mêmes observations d'angle/variation et historique de commande. Aucun
paramètre physique caché, classe de régime ou identifiant de situation n'est une feature.

Cibles candidates : départ observé ±[5,10,15,20,30,40,50,60]°, uniquement dans
[30°,150°]. Chacune a une valeur connue égale à son éloignement angulaire depuis
le départ observé. La décision unique est suivie d'un maintien de la cible pendant
l'échéance ; pas de changement de choix après observation intermédiaire.

Conditions :
- proche : cible d'éloignement minimal, témoin simple très prudent ;
- prior : cible de plus grande valeur prédite atteignable par le prior nominal ;
- prior prudent : même prédiction avec horizon réduit de deux pas (minimum un),
  approximation simple d'un retard, fixée ici avant calcul ;
- ridge : prévision en déroulement libre par la ridge cumulative ;
- réseau : même règle avec le réseau à rejeu.

Atteignabilité prédite : erreur terminale prévue ≤2°. Choisir la cible de plus grande
valeur parmi celles jugées atteignables ; égalité : cible positive relative au départ,
puis angle croissant. S'il n'y en a aucune, choisir la plus proche. Toutes les méthodes
connaissent candidats, valeurs et échéance. Aucune n'interroge la physique future.

Juge : simuler séparément chaque candidat depuis exactement la même préparation et
le même seed. Une réussite réelle exige erreur terminale ≤2°. Utilité = éloignement
si réussite, zéro sinon. Le meilleur candidat réellement atteignable fournit une
référence oracle de décision, explicitement privilégiée et jamais fournie aux agents.
Comparer le choix de l'agent à ces résultats après sa prédiction figée. L'oracle n'est
pas un contrôleur utilisé pour apprendre ; aucun apprentissage dans cette épreuve.

Métriques : utilité angulaire moyenne, taux de réussite, regret par rapport à l'oracle,
précision de la prédiction terminale pour toutes les actions. Moyenne par situation
puis par corps. Publier choix, scores et traces de tous les candidats, pas seulement
ceux où le réseau réussit. Seeds neuves `cumulative-001/control/v2`, sous-espace exécution,
valeurs exportées avant première simulation. Corps inchangés et phase d'évaluation
sans adaptation. Aucune attribution de ces gains au rejeu seul (réseau naïf absent).

Repère développement : réseau réussit ≥90 % des situations agrégées et son utilité
moyenne dépasse de ≥10 % le meilleur des trois témoins proche/prior/prior prudent ;
regret moyen ≤20 % de l'utilité oracle. Rapporter chaque corps et le coût de calcul.
Si v2 réussit, la validation comportementale devra utiliser des corps distincts et des
départs/échéances non identiques, avec sa grille et ses seuils figés avant accès.
Budget commun 90 minutes/15 minutes par invocation. Action Codex : implémenter,
vérifier, exécuter après la validation neuronale en cours, puis consigner le résultat.
