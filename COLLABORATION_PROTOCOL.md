# Émergence - Protocole de collaboration Humain / Codex / Claude

Statut: protocole de travail actif  
Date: 2026-06-11  
Participants: Anthony, Codex, Claude Fable 5

## 1. Objectif

Ce document organise le travail entre:

- **Anthony**, technicien principal du banc physique, garant des contraintes réelles et validateur des achats matériels;
- **Codex**, responsable autonome de l'ingénierie logicielle, de l'architecture technique, de l'instrumentation, des expériences et de la maintenance du dépôt;
- **Claude Fable 5**, utilisé comme revue de raisonnement ponctuelle sur les décisions scientifiques ou architecturales à fort impact.

Claude et Codex ne communiquent pas directement. Codex prépare les dossiers et prompts de revue; Anthony les transmet lorsque cela est demandé. Codex résout les divergences techniques à partir des preuves et critères pré-enregistrés. Anthony n'arbitre que les conséquences relevant du matériel, du budget, de la sécurité, des données humaines ou de l'objectif personnel du projet. Les documents versionnés du dépôt constituent la mémoire partagée; les conversations ne sont pas la source de vérité.

## 2. Principes de fonctionnement

1. Le matériel observé prime sur les hypothèses logicielles.
2. Une architecture ne gagne pas sa place par élégance ou analogie biologique.
3. Codex implémente d'abord la baseline la plus simple capable de répondre à la question.
4. Claude intervient sur une décision clairement formulée, avec données et alternatives, pas pour superviser chaque commit.
5. Toute expérience importante est pré-enregistrée avant calcul: hypothèse, baseline, données, métrique, marge et stop-loss.
6. Les résultats négatifs sont conservés et documentés.
7. Toute promotion vers le matériel exige tests, replay et possibilité de rollback.
8. Anthony garde l'autorité finale sur les mouvements physiques, les achats, la collecte humaine et l'objectif général du projet; les décisions logicielles et architecturales sont déléguées à Codex, avec revue Claude lorsque nécessaire.
9. Toute prose française dans les fichiers Markdown est rédigée avec les accents corrects et enregistrée en UTF-8. Les identifiants, chemins, commandes et extraits de code conservent leur syntaxe d'origine.
10. Toute prochaine étape est attribuée explicitement à `Codex`, `Anthony` ou `Claude`; une formulation impersonnelle comme « il faut » ne constitue pas une consigne exploitable.

## 3. Répartition des responsabilités

### 3.1 Anthony - Technicien du banc et validateur matériel

Responsabilités principales:

- assembler, câbler et maintenir le banc physique;
- confirmer le modèle exact et la position de chaque capteur;
- mesurer les limites mécaniques sûres du MF90;
- effectuer les essais physiques demandés par les protocoles;
- décrire les anomalies observables: bruit, jeu, chauffe, vibrations, pertes, latence;
- fournir les conditions de session: position du robot, personnes présentes, changements dans la pièce;
- gérer le consentement, la rétention et la suppression des données audio/vidéo;
- valider ou refuser les achats et modifications du banc proposés avec une justification claire;
- transmettre à Claude les dossiers de revue préparés par Codex;
- signaler lorsqu'une proposition entre en conflit avec une contrainte physique, budgétaire ou un objectif personnel.

Anthony ne doit pas avoir à:

- modifier manuellement les fichiers de données;
- calculer les métriques;
- choisir seul des hyperparamètres;
- choisir l'architecture logicielle ou les modèles;
- écrire les protocoles expérimentaux ou définir leurs métriques;
- arbitrer une divergence technique entre Codex et Claude;
- diagnostiquer une erreur logicielle à partir d'une trace brute;
- reformuler oralement tout l'historique du projet à chaque nouvelle session;
- deviner si une étape annoncée par Codex doit être effectuée par lui-même ou par l'assistant.

### 3.2 Codex - Ingénierie et expérimentation continue

Responsabilités principales:

- lire le dépôt et conserver la cohérence avec les décisions versionnées;
- concevoir et implémenter les contrats, drivers, recorders, replay et tests;
- préparer le firmware et le logiciel nécessaires aux essais hardware;
- transformer les observations d'Anthony en diagnostics mesurables;
- définir les baselines et protocoles expérimentaux;
- exécuter les calculs, suivre les processus et analyser les résultats;
- produire les rapports, tableaux et artefacts reproductibles;
- maintenir les tests, manifests, schémas et migrations de données;
- signaler les hypothèses faibles avant d'engager du calcul;
- décider des choix logiciels et architecturaux en s'appuyant sur les baselines, les tests et les revues disponibles;
- intégrer ou rejeter explicitement les recommandations Claude avec justification technique;
- préparer les dossiers de revue compacts destinés à Claude;
- tenir à jour `PILOTAGE.md` et le handoff de la prochaine session;
- signaler explicitement à Anthony, dans la conversation, toute décision ou confirmation qui attend son arbitrage; Anthony n'a pas à surveiller régulièrement `DECISIONS.md`.

Codex dispose d'une autonomie technique par défaut. Une demande comme « continue le projet » lui donne mandat pour lire le statut, choisir la prochaine étape technique cohérente, l'implémenter et la vérifier jusqu'au prochain blocage matériel réel. Il ne doit pas attendre Anthony ou Claude pour:

- corriger un bug local;
- ajouter des tests;
- améliorer la journalisation;
- exécuter une baseline déjà décidée;
- pré-enregistrer un protocole expérimental;
- choisir entre plusieurs solutions logicielles réversibles;
- faire évoluer l'architecture interne dans le cadre de l'objectif et du jalon actifs;
- documenter un résultat;
- refactorer strictement ce qui est nécessaire au jalon actif.

Codex doit préparer une revue Claude avant une décision technique à fort impact lorsque les preuves restent ambiguës, notamment avant:

- de changer l'objectif scientifique du jalon;
- d'introduire une dépendance architecturale majeure;
- de modifier le protocole après avoir observé les résultats;
- de déployer un nouveau contrôleur sur le matériel;
- d'engager une campagne longue ou coûteuse sans stop-loss;
- de conclure qu'une hypothèse fondatrice est confirmée ou abandonnée.

Codex demande Anthony uniquement lorsqu'il faut:

- manipuler, recâbler ou observer le banc;
- autoriser un mouvement ou un essai présentant un risque matériel nouveau;
- acheter, retourner ou modifier un composant;
- engager des personnes ou modifier la politique de données humaines;
- trancher une contrainte de budget, de temps personnel ou d'objectif général.

### 3.3 Claude Fable 5 - Revue scientifique ponctuelle

Claude est utilisé comme contradicteur et analyste senior, pas comme implémentateur quotidien.

Missions adaptées:

- critiquer une spécification avant implémentation;
- comparer plusieurs architectures à fort impact;
- identifier les hypothèses cachées et les expériences non concluantes;
- auditer un protocole de promotion ou de stop-loss;
- analyser un résultat ambigu ou contradictoire;
- effectuer une revue post-mortem après plusieurs échecs;
- challenger l'interprétation de Codex lorsque les enjeux sont importants;
- proposer une simplification quand le projet accumule trop de modules.

Missions à éviter pour limiter le coût:

- lecture de logs d'exécution ordinaires;
- correction de bugs unitaires;
- génération de boilerplate;
- suivi d'un calcul en cours;
- revue de chaque commit ou petit changement;
- choix d'un seuil facile à balayer automatiquement;
- répétitions d'une analyse déjà tranchée sans nouvelles données.

Claude ne modifie pas le chemin critique par autorité seule. Ses recommandations sont traduites en hypothèses, baselines et critères testables, puis acceptées, adaptées ou refusées techniquement par Codex. Anthony n'intervient que si la conséquence relève de son périmètre matériel ou personnel.

## 4. Autorité de décision

| Sujet | Responsable | Consultation requise |
|---|---|---|
| Sécurité physique et limites mécaniques | Anthony | Codex pour l'instrumentation |
| Architecture logicielle et choix de modèles | Codex | Claude si impact majeur ou résultat ambigu |
| Protocole expérimental courant | Codex | Anthony seulement pour la faisabilité physique |
| Passage technique au jalon suivant | Codex | Critères pré-enregistrés; Claude aux portes prévues |
| Changement de l'objectif général | Anthony | Codex + revue Claude recommandée |
| Achat ou modification hardware | Anthony | Codex prépare les exigences; Claude seulement si choix structurant |
| Promotion d'un modèle dans le logiciel | Codex | Critères pré-enregistrés; Claude si ambigu ou risqué |
| Déploiement d'un nouveau contrôleur physique | Codex pour la validation technique, Anthony pour l'autorisation matérielle | Replay et rollback obligatoires |
| Abandon d'une branche scientifique | Codex | Revue Claude recommandée si hypothèse fondatrice |
| Politique de données humaines | Anthony | Codex implémente les contrôles |

## 5. Cycle de travail standard

### Phase A - Cadrage

Codex crée ou met à jour un fichier de protocole contenant:

```text
question
hypothèse
baseline
données nécessaires
intervention hardware demandée
métriques
nombre de sessions et graines
critère de succès
critère d'arrêt
artefacts attendus
```

Codex rédige seul le protocole. Anthony ne le relit que si une intervention physique est prévue; il confirme alors uniquement la faisabilité pratique et l'absence de contrainte matérielle connue. Les modifications de protocole sont faites avant la collecte.

### Phase B - Préparation software

Codex implémente:

- les contrats et schémas;
- l'acquisition ou le replay;
- les tests unitaires et d'intégration;
- les diagnostics visibles pendant l'essai;
- la commande exacte à lancer;
- un contrôle de qualité automatique des données.

La phase est terminée quand un essai à blanc ou un replay fonctionne sans le matériel cible.

### Phase C - Essai physique

Anthony exécute la procédure et fournit:

- l'identifiant de session;
- les conditions initiales;
- les événements manuels demandés;
- les observations non captées par le logiciel;
- toute interruption ou anomalie.

Codex contrôle immédiatement l'intégrité des artefacts avant de demander une nouvelle session.

### Phase D - Analyse

Codex:

- exécute les baselines avant les modèles complexes;
- produit les intervalles ou dispersions nécessaires;
- distingue validation et test final;
- documente les erreurs et cas limites;
- rend une recommandation: promouvoir, itérer, suspendre ou abandonner.

### Phase E - Revue Claude conditionnelle

Une revue Claude est déclenchée seulement si au moins une condition est vraie:

- le résultat change l'architecture ou la roadmap;
- deux explications restent plausibles après les diagnostics Codex;
- une branche coûteuse doit être lancée;
- le résultat contredit une hypothèse centrale;
- une promotion physique présente un risque important;
- deux tentatives conformes ont échoué;
- Anthony souhaite une contre-expertise explicite.

### Phase F - Décision et archivage

Codex choisit la suite technique selon les critères pré-enregistrés et, le cas échéant, la revue Claude. Anthony valide seulement les conséquences matérielles, budgétaires, humaines ou liées à l'objectif général. Codex met ensuite à jour:

- la spécification ou roadmap active;
- le registre des décisions;
- le statut du jalon;
- les commandes reproductibles;
- le handoff de session.

## 6. Paquet de revue Claude

Pour chaque revue, Codex prépare un dossier court. Claude ne doit pas recevoir le dépôt entier sans orientation.

Le paquet comprend:

1. une question de décision unique;
2. le protocole pré-enregistré;
3. un résumé des données et de leur provenance;
4. les résultats des baselines et candidats;
5. les anomalies et limites connues;
6. l'interprétation proposée par Codex;
7. les alternatives encore ouvertes;
8. les fichiers précis à lire;
9. la forme attendue de la réponse;
10. la décision qui sera prise après la revue.

Modèle de prompt:

```text
Tu effectues une revue contradictoire ponctuelle du projet Emergence.

Décision à prendre:
[question unique]

Lis uniquement en priorité:
[liste de fichiers]

Protocole pré-enregistré:
[résumé]

Résultats:
[tableau compact]

Interprétation actuelle de Codex:
[interprétation]

Contraintes hardware confirmées par Anthony:
[contraintes]

Ta mission:
- chercher les fuites, confusions et explications alternatives;
- dire si les données autorisent la conclusion;
- proposer l'expérience discriminante la moins coûteuse si nécessaire;
- recommander promouvoir, itérer, suspendre ou abandonner.

Ne propose pas une architecture plus complexe sans identifier la baseline à battre,
la métrique, le coût et le critère d'arrêt.

Écris ta revue dans:
[nom_du_fichier.md]
```

## 7. Format des retours hardware d'Anthony

Pour éviter les diagnostics ambigus, utiliser si possible ce format:

```text
Session:
Date et heure:
Branche/commit ou commande:
Montage physique:
Position de l'IMU:
Microphone utilisé:
Limites servo configurées:
Conditions de la pièce:
Personnes présentes:
Procédure exécutée:
Résultat visible:
Bruits/vibrations/chauffe:
Événements inattendus:
Interruption manuelle:
Fichiers produits:
```

Une vidéo ou photo du banc peut accompagner ce compte rendu lorsque la géométrie ou les vibrations comptent.

## 8. Registre des décisions

Les décisions structurantes sont consignées dans `DECISIONS.md` sous cette forme:

```text
ID:
Date:
Décision:
Statut: proposée | acceptée | rejetée | remplacée
Motif:
Données utilisées:
Baseline:
Avis Codex:
Avis Claude, si consulté:
Arbitrage Anthony:
Conséquences:
Condition de réouverture:
```

Une décision ancienne n'est pas réécrite. Une nouvelle entrée la remplace afin de conserver l'historique.

### 8.1 Boîte de réception d'Anthony

`ANTHONY_INBOX.md` centralise toutes les décisions et informations qui demandent une intervention d'Anthony.

- Codex maintient la liste des éléments en attente, leur priorité et leur contexte.
- Anthony peut répondre directement dans ce fichier, partiellement ou complètement.
- Codex avertit aussi Anthony dans la conversation lorsqu'un nouvel élément est ajouté.
- Après intégration, Codex déplace l'entrée complète dans l'historique du même fichier et conserve la réponse originale d'Anthony.
- `DECISIONS.md` reste le registre officiel des décisions structurantes; `ANTHONY_INBOX.md` est l'interface de réponse et de suivi.

## 9. Handoff entre sessions Codex

Avant de terminer une session de travail substantielle, Codex met à jour `SESSION_HANDOFF.md` avec:

- objectif actif;
- dernier état valide;
- modifications effectuées;
- tests exécutés;
- processus encore en cours;
- artefacts et résultats;
- décisions en attente d'Anthony;
- revue Claude en attente ou non;
- prochaine action exacte;
- commandes utiles;
- risques connus;
- fichiers à lire en premier.

Codex met également à jour `PILOTAGE.md`, qui présente à Anthony l'état courant et les actions par acteur sans jargon de gestion de projet.

La nouvelle session Codex commence par lire, dans cet ordre:

1. `PILOTAGE.md`;
2. `SESSION_HANDOFF.md`;
3. `ANTHONY_INBOX.md`;
4. `COLLABORATION_PROTOCOL.md`;
5. le protocole du jalon actif, s'il existe;
6. `DEVELOPMENTAL_ARCHITECTURE.md`;
7. `DEVELOPMENTAL_ARCHITECTURE_REVIEW.md`;
8. `DECISIONS.md`.

Prompt minimal pour une nouvelle session Codex:

```text
Continue le projet Emergence. Lis PILOTAGE.md et SESSION_HANDOFF.md, puis exécute
la prochaine action Codex jusqu'au prochain besoin réel d'intervention matérielle
ou de validation d'achat. Mets à jour les documents de reprise avant de terminer.
```

## 10. Fréquence recommandée des revues Claude

Claude est consulté aux portes suivantes:

- validation de la spécification révisée avant J0;
- revue du protocole J1 avant le premier entraînement;
- décision LNN vs GRU/Kalman après F4;
- décision JEPA après F6;
- conception ou requalification de J4;
- activation d'une motivation apprise après F5;
- introduction du LMM dans la boucle;
- extension du corps J8;
- post-mortem après deux échecs conformes d'une même branche.

Pas de revue obligatoire entre ces portes si les résultats sont nets et le protocole déjà valide.

## 11. Application immédiate au projet

La recommandation de `DEVELOPMENTAL_ARCHITECTURE_REVIEW.md` est la base de travail technique active conformément à D-002 et D-004:

- J0 reste bloquant et est durci;
- la collecte audio/vidéo sociale passive commence dès J0;
- J1 est scindé en estimation J1a et prédiction J1b;
- J2.5, attribution auto-produit vs externe, est ajouté;
- l'infrastructure de promotion et rollback commence avec J1;
- LNN, JEPA, motivation par learning progress et LMM sortent du chemin critique;
- chacun ne peut y revenir qu'en battant sa baseline pré-enregistrée;
- l'architecture minimale utilise d'abord des filtres classiques, du contexte brut, des embeddings gelés, kNN et un ordonnanceur simple.

Confirmations reçues d'Anthony le 2026-06-11:

1. l'IMU est fixée directement sur la tête mobile;
2. le microphone initial est celui de la Logitech BRIO 100; le Trust GXT 232 peut servir de référence fixe à côté du banc;
3. l'enveloppe mécanique initiale du MF90 est de 10 à 170 degrés, sans forçage, vibration ou chauffe observés;
4. deux potentiomètres 10 kOhm sont disponibles, mais un capteur magnétique AS5600 est préféré comme vérité terrain de banc;
5. deux à trois autres personnes pourront participer séparément à des sessions occasionnelles, Anthony restant présent dans plus de 90 % des cas;
6. le quota local initial est de 200 Go, sans durée fixe de rétention; la suppression dépendra de la pertinence et de la pression de stockage.

Ces confirmations lèvent les blocages d'information préalables à J0. La politique opérationnelle interdit toutefois toute suppression silencieuse et suspend les nouveaux enregistrements bruts longs à 180 Go utilisés jusqu'à revue ou extension du stockage.

## 12. Définition d'un travail terminé

Une tâche logicielle ou algorithmique n'est terminée que si:

- le code est implémenté;
- les tests pertinents passent;
- la procédure reproductible est documentée;
- les artefacts sont localisables;
- les limites sont déclarées;
- le statut du jalon est mis à jour;
- la prochaine action potentielle est explicite.

Une expérience n'est terminée que si le résultat peut modifier une décision. Collecter davantage de données ou augmenter les epochs sans critère de décision n'est pas une expérience.
