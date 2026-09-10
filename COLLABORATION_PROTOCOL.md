# Émergence — Protocole de collaboration

Statut : protocole de travail actif.
Version : 2.0, réécrite le 2026-09-11 sous D-062. La version 1.0 du 2026-06-11 séparait
Codex, ingénieur permanent, et Claude, contradicteur ponctuel joignable seulement par
transmission d'Anthony. Cette séparation a cessé de décrire le travail réel.

## 1. Participants

- **Anthony** — technicien du banc physique, garant des contraintes réelles, seul
  décideur sur le matériel, le budget, les données humaines et l'objectif du projet.
- **L'agent** — Codex CLI, Claude, ou tout autre agent disponible, de façon
  interchangeable. Un agent lit le dépôt, décide, implémente, vérifie et documente.

Il n'y a qu'un rôle d'agent. Aucun document ne transite par Anthony pour atteindre un
autre agent : un agent qui a besoin d'une contradiction ouvre une session distincte et lui
donne le dossier directement.

Les documents versionnés du dépôt constituent la mémoire partagée. **Les conversations ne
sont pas la source de vérité.**

## 2. Principes de fonctionnement

1. Le matériel observé prime sur les hypothèses logicielles.
2. Une architecture ne gagne pas sa place par élégance ou analogie biologique. Un
   mécanisme inspiré du vivant qui ne bat pas une baseline bête n'est pas un progrès,
   c'est une complexité non payée.
3. L'agent implémente d'abord la baseline la plus simple capable de répondre à la
   question, et la fait recevoir la même information que le mécanisme testé.
4. Toute expérience importante est pré-enregistrée avant calcul : hypothèse, baseline,
   données, métrique, marge et stop-loss. Le seuil s'écrit avant que la mesure tourne ; un
   seuil choisi en voyant les chiffres n'est pas une porte.
5. Sous D-060, la sonde de marge s'applique **au banc** avant toute conception de
   mécanisme, et non à la variante après coup.
6. Les résultats négatifs sont conservés et documentés, avec leurs limites.
7. Sous D-061, les octets bruts des sources sont l'unité d'audit. `.gitattributes` reste à
   `* -text` ; une empreinte qui ne correspond plus signale un problème dans les octets et
   jamais dans le manifeste.
8. Toute promotion vers le matériel exige tests, replay et possibilité de rollback.
9. Anthony garde l'autorité finale sur les mouvements physiques, les achats, la collecte
   humaine et l'objectif général. Les décisions logicielles et expérimentales sont
   déléguées à l'agent (D-004).
10. Toute prose française des fichiers Markdown est rédigée avec les accents corrects et
    enregistrée en UTF-8. Les identifiants, chemins, commandes et extraits de code
    conservent leur syntaxe d'origine.
11. Toute prochaine étape est attribuée explicitement à `Anthony` ou à `l'agent`. Une
    formulation impersonnelle comme « il faut » ne constitue pas une consigne exploitable.

## 3. Répartition des responsabilités

### 3.1 Anthony

Fait :

- assembler, câbler et maintenir le banc physique ;
- confirmer le modèle exact et la position de chaque capteur ;
- mesurer les limites mécaniques sûres du MF90 ;
- exécuter les essais physiques demandés par les protocoles ;
- décrire les anomalies observables : bruit, jeu, chauffe, vibrations, pertes, latence ;
- fournir les conditions de session : position du robot, personnes présentes, changements
  dans la pièce ;
- gérer le consentement, la rétention et la suppression des données audio et vidéo ;
- valider ou refuser les achats et modifications du banc ;
- signaler lorsqu'une proposition entre en conflit avec une contrainte physique,
  budgétaire ou un objectif personnel.

N'a pas à :

- modifier manuellement des fichiers de données ni calculer des métriques ;
- choisir des hyperparamètres, une architecture logicielle ou des modèles ;
- écrire les protocoles expérimentaux ou définir leurs métriques ;
- arbitrer une divergence technique entre deux agents ;
- diagnostiquer une erreur logicielle à partir d'une trace brute ;
- transporter un dossier d'un agent à un autre ;
- reformuler oralement l'historique du projet à chaque session ;
- deviner si une étape annoncée doit être exécutée par lui ou par l'agent.

### 3.2 L'agent

Fait :

- lire le dépôt et conserver la cohérence avec les décisions versionnées ;
- concevoir et implémenter contrats, drivers, recorders, replay et tests ;
- définir les baselines et les protocoles expérimentaux ;
- exécuter les calculs, suivre les processus et analyser les résultats ;
- produire rapports, tableaux et artefacts reproductibles ;
- maintenir tests, manifestes, schémas et migrations ;
- signaler les hypothèses faibles **avant** d'engager du calcul ;
- ouvrir une revue contradictoire quand les conditions de la section 5 sont réunies, et
  intégrer ou rejeter explicitement ses recommandations avec une justification technique ;
- tenir à jour `PILOTAGE.md`, `SESSION_HANDOFF.md` et `ANTHONY_INBOX.md` ;
- signaler dans la conversation ce qui attend Anthony. Anthony n'a pas à surveiller
  `DECISIONS.md` ni `ANTHONY_INBOX.md`.

Autonomie par défaut. « Continue le projet » vaut mandat pour lire le statut, choisir la
prochaine étape technique cohérente, l'implémenter et la vérifier jusqu'au prochain blocage
réel. L'agent n'attend personne pour corriger un bug, ajouter des tests, améliorer la
journalisation, exécuter une baseline déjà décidée, pré-enregistrer un protocole, choisir
entre plusieurs solutions logicielles réversibles, faire évoluer l'architecture interne
dans le cadre du jalon actif, documenter un résultat, ou refactorer ce que le jalon exige.

Demande Anthony uniquement pour :

- manipuler, recâbler ou observer le banc ;
- autoriser un mouvement ou un essai présentant un risque matériel nouveau ;
- acheter, retourner ou modifier un composant ;
- engager des personnes ou modifier la politique de données humaines ;
- trancher une contrainte de budget, de temps personnel ou d'objectif général.

## 4. Autorité de décision

| Sujet | Décide | Contradiction requise |
|---|---|---|
| Sécurité physique et limites mécaniques | Anthony | — |
| Achat ou modification matérielle | Anthony | L'agent prépare les exigences |
| Politique de données humaines | Anthony | L'agent implémente les contrôles |
| Changement de l'objectif général | Anthony | Revue contradictoire recommandée |
| Architecture logicielle et choix de modèles | L'agent | Si impact majeur ou résultat ambigu |
| Protocole expérimental courant | L'agent | Anthony seulement pour la faisabilité physique |
| Passage au jalon suivant | L'agent | Critères pré-enregistrés ; revue aux portes prévues |
| Promotion d'un modèle | L'agent | Critères pré-enregistrés ; revue si ambigu ou risqué |
| Abandon d'une branche scientifique | L'agent | Revue recommandée si hypothèse fondatrice |
| Déploiement d'un contrôleur physique | L'agent valide, Anthony autorise | Replay et rollback obligatoires |

## 5. Cycle de travail

**A — Cadrage.** L'agent écrit ou met à jour un protocole contenant : question, hypothèse,
baseline, données nécessaires, intervention matérielle demandée, métriques, nombre de
sessions et de graines, critère de succès, critère d'arrêt, artefacts attendus. Anthony ne
le relit que si une intervention physique est prévue, et confirme alors seulement la
faisabilité pratique. Les modifications de protocole se font avant la collecte.

**B — Préparation.** Contrats et schémas, acquisition ou replay, tests unitaires et
d'intégration, diagnostics visibles pendant l'essai, commande exacte à lancer, contrôle
qualité automatique des données. La phase se termine quand un essai à blanc ou un replay
fonctionne sans le matériel cible.

**C — Essai physique**, si le protocole en prévoit un. Anthony exécute et fournit
l'identifiant de session, les conditions initiales, les événements manuels demandés, les
observations non captées par le logiciel et toute interruption. L'agent contrôle
l'intégrité des artefacts avant de demander une nouvelle session.

**D — Analyse.** Baselines avant les modèles complexes, intervalles ou dispersions,
distinction entre validation et test final, erreurs et cas limites documentés, puis une
recommandation : promouvoir, itérer, suspendre ou abandonner.

**E — Revue contradictoire, conditionnelle.** Elle est ouverte si au moins une condition
est vraie :

- le résultat change l'architecture ou la direction ;
- deux explications restent plausibles après diagnostic ;
- une branche coûteuse doit être lancée ;
- le résultat contredit une hypothèse centrale ;
- une promotion physique présente un risque important ;
- deux tentatives conformes ont échoué ;
- Anthony demande une contre-expertise.

**La revue est faite par un agent qui n'a pas produit le travail, dans une session
distincte.** C'est la seule contrainte de forme, et elle n'est pas négociable : un agent
qui se relit lui-même ne contredit rien. Peu importe lequel — ce qui compte est qu'il
arrive sans le raisonnement qui a mené au résultat.

**F — Décision et archivage.** L'agent choisit la suite selon les critères pré-enregistrés
et, le cas échéant, la revue. Anthony valide les conséquences matérielles, budgétaires,
humaines ou d'objectif. L'agent met ensuite à jour la spécification active, le registre des
décisions, le statut du jalon, les commandes reproductibles et les documents de reprise.

## 6. Dossier de revue contradictoire

Le relecteur ne reçoit pas le dépôt entier sans orientation. Le dossier comprend : une
question de décision unique, le protocole pré-enregistré, un résumé des données et de leur
provenance, les résultats des baselines et des candidats, les anomalies et limites connues,
l'interprétation proposée, les alternatives encore ouvertes, les fichiers précis à lire, la
forme attendue de la réponse, et la décision qui sera prise ensuite.

```text
Tu effectues une revue contradictoire du projet Emergence. Tu n'as pas produit ce
travail et tu n'es pas tenu par le raisonnement qui y a mené.

Décision à prendre :
[question unique]

Lis en priorité :
[liste de fichiers]

Protocole pré-enregistré :
[résumé]

Résultats :
[tableau compact]

Interprétation actuelle :
[interprétation]

Contraintes matérielles confirmées par Anthony :
[contraintes]

Ta mission :
- chercher les fuites, confusions et explications alternatives ;
- dire si les données autorisent la conclusion ;
- proposer l'expérience discriminante la moins coûteuse si nécessaire ;
- recommander promouvoir, itérer, suspendre ou abandonner.

Ne propose pas une architecture plus complexe sans identifier la baseline à battre,
la métrique, le coût et le critère d'arrêt.

Écris ta revue dans :
[nom_du_fichier.md]
```

Une revue écrite est commitée directement sur `main`, sans attendre qu'on le demande.

## 7. Format des retours matériels d'Anthony

```text
Session :
Date et heure :
Branche/commit ou commande :
Montage physique :
Position de l'IMU :
Microphone utilisé :
Limites servo configurées :
Conditions de la pièce :
Personnes présentes :
Procédure exécutée :
Résultat visible :
Bruits/vibrations/chauffe :
Événements inattendus :
Interruption manuelle :
Fichiers produits :
```

Une photo ou une vidéo du banc peut accompagner ce compte rendu quand la géométrie ou les
vibrations comptent.

## 8. Registre des décisions

Les décisions structurantes sont consignées dans `DECISIONS.md`. Une décision ancienne
**n'est jamais réécrite** : une nouvelle entrée la remplace et l'historique reste lisible.

Une entrée porte : identifiant, date, décision, statut, motif, données utilisées, baseline,
l'avis de l'agent qui propose, l'avis de la revue contradictoire si elle a eu lieu,
l'arbitrage d'Anthony, les conséquences, et la condition de réouverture. Les entrées
récentes tiennent en prose continue plutôt qu'en champs ; les deux formes sont acceptées.

`ANTHONY_INBOX.md` est l'interface de réponse : l'agent y tient ce qui attend Anthony,
Anthony y répond avec ses mots, partiellement ou complètement, et sa réponse passe à
l'historique du fichier **mot pour mot, jamais reformulée**.

## 9. Reprise de session

Une nouvelle session lit, dans cet ordre :

1. `PILOTAGE.md` — état courant et règles permanentes ;
2. `CODEX_TASK_BRIEF.md` — le prompt de la phase active ;
3. `PROPOSITION_SUBSTRAT.md` — l'argumentaire du substrat actuel ;
4. `DECISIONS.md` — les décisions actives, aujourd'hui D-060 à D-062 ;
5. `DEVELOPMENTAL_ARCHITECTURE.md` — le cadrage D-056.

`SESSION_HANDOFF.md` donne l'historique campagne par campagne et se lit à la demande.

Avant de terminer une session substantielle, l'agent met à jour `PILOTAGE.md` — état,
actions par acteur — et `SESSION_HANDOFF.md` — ce qui a été essayé, avec les verdicts et
les interdits. Prompt minimal :

```text
Continue le projet Emergence. Lis PILOTAGE.md et CODEX_TASK_BRIEF.md, puis exécute la
prochaine action jusqu'au prochain besoin réel d'arbitrage humain. Mets à jour les
documents de reprise avant de terminer.
```

## 10. Contraintes matérielles confirmées

Confirmées par Anthony le 2026-06-11 et toujours en vigueur. Plusieurs sont directement
reprises par le jumeau MuJoCo.

1. L'IMU est fixée directement sur la tête mobile.
2. Le microphone initial est celui de la Logitech BRIO 100 ; le Trust GXT 232 peut servir
   de référence fixe à côté du banc. C'est de cette webcam que vient le champ de 30° de la
   caméra du jumeau.
3. L'enveloppe mécanique du MF90 est de **10° à 170°**, sans forçage, vibration ni chauffe
   observés. Ce sont les bornes du jumeau.
4. Deux potentiomètres 10 kΩ sont disponibles ; un capteur magnétique AS5600 reste préféré
   comme vérité terrain, achat en sommeil sous D-008 (voir `ANTHONY_INBOX.md`, ANT-008).
5. Deux à trois autres personnes pourront participer séparément à des sessions
   occasionnelles, Anthony restant présent dans plus de 90 % des cas.
6. Le quota local initial est de 200 Go, sans durée fixe de rétention : revue à 160 Go,
   suspension des enregistrements bruts longs à 180 Go, **aucune suppression silencieuse**.

Sécurité toujours active : plus aucun essai moteur sur le montage v0.1 (D-005), et
simulation uniquement (D-008).

## 11. Direction active

Le cadrage D-056 est la direction : noyau résilient, apprentissage intrinsèque,
développement incarné, précision motrice secondaire. D-060 a déplacé le substrat vers la
vision dans la boucle sur un cou à deux axes ; le banc à un axe observé par cinq scalaires
n'est plus le terrain des travaux cognitifs.

Les jalons J0 à J8 du plan de juin restent la carte du retour au matériel, mais ils ne
décrivent pas le travail courant et ne fixent plus les portes de revue. L'état qui fait foi
est dans `PILOTAGE.md`.

## 12. Définition d'un travail terminé

Une tâche logicielle n'est terminée que si le code est implémenté, les tests pertinents
passent, la procédure reproductible est documentée, les artefacts sont localisables, les
limites sont déclarées, le statut du jalon est à jour et la prochaine action est explicite.

Une expérience n'est terminée que si le résultat peut modifier une décision. Collecter
davantage de données ou augmenter les epochs sans critère de décision n'est pas une
expérience.
