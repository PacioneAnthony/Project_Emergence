# Emergence - Spécification d'architecture développementale

Statut: proposition de référence pour revue technique  
Date: 2026-06-11  
Portée : objectifs scientifiques, architecture cible, contrat de données, apprentissage et jalons

Ordre opérationnel actuel (D-008, 2026-07-20): les mécanismes développementaux doivent
d'abord émerger, battre leurs baselines et se répliquer dans des simulations de réalisme
croissant. Les jalons physiques J0/J1 restent spécifiés mais sont suspendus jusqu'à une
décision explicite de retour au banc.

## 1. Vision du projet

Emergence vise un robot domestique développemental, capable d'acquérir progressivement des régularités sensorimotrices, perceptives et sociales à partir de son expérience dans une pièce partagée avec un humain.

Le robot ne poursuit pas une tâche externe fixe comme parcourir une distance, atteindre une cible ou maximiser un score de navigation. Il doit apprendre :

- ce que ses actions changent dans ses sensations ;
- quelles parties du flux sensoriel sont prévisibles, contrôlables ou indépendantes de lui ;
- quels phénomènes persistent et réapparaissent ;
- quelles configurations multimodales correspondent probablement à une même personne, un même objet ou un même contexte ;
- quelles compétences motrices simples produisent des effets reproductibles ;
- quand une situation est familière, nouvelle, dangereuse ou encore mal comprise ;
- comment intégrer de nouvelles expériences sans détruire les acquis précédents.

L'analogie avec un bébé humain est une inspiration fonctionnelle, pas une revendication d'équivalence biologique ou cognitive. Le projet cherche des mécanismes de développement cumulatif : contingences sensorimotrices, attention, habituation, familiarité, mémoire épisodique, apprentissage auto-supervisé et interaction sociale progressive.

## 2. Définition opérationnelle du succès

Le succès ne sera pas mesuré par une unique récompense. Il sera établi par une succession de capacités observables.

Le système est considéré comme évolutif s'il peut, dans cet ordre :

1. prédire les conséquences immédiates de ses mouvements de cou ;
2. distinguer les changements auto-produits des changements externes ;
3. apprendre des représentations stables de situations récurrentes ;
4. reconnaître la récurrence probable d'une voix ou d'une présence sans identité codée en dur ;
5. orienter son capteur vers une source intéressante en utilisant une compétence apprise ;
6. s'habituer aux événements devenus prévisibles et consacrer son activité à ceux qui offrent encore un progrès d'apprentissage ;
7. conserver des compétences anciennes après l'ajout de nouveaux capteurs ou de nouvelles expériences ;
8. utiliser une couche linguistique lente pour nommer, résumer ou mettre en relation des expériences, sans lui déléguer le contrôle moteur.

Une démonstration finale minimale pourrait être la suivante :

- le robot est posé dans une pièce pendant plusieurs sessions ;
- il explore visuellement par mouvements de cou bornés ;
- il construit une baseline de la pièce vide et des sons ambiants ;
- il réagit d'abord fortement à une voix nouvelle ;
- il apprend progressivement que certaines caractéristiques vocales et visuelles réapparaissent ensemble ;
- il anticipe mieux les conséquences de ses propres mouvements ;
- il s'oriente plus efficacement vers la présence familière ;
- il conserve cette familiarité après extinction et redémarrage ;
- il distingue cette familiarité d'une simple mémorisation d'une phrase précise.

## 3. Non-objectifs initiaux

Les objectifs suivants sont explicitement suspendus pendant la première phase :

- optimiser la distance parcourue ;
- apprendre une navigation autonome complète ;
- produire un langage humain fluide ;
- attribuer des émotions humaines au robot ;
- laisser un LLM commander directement le matériel ;
- effectuer un apprentissage par renforcement libre sur les moteurs ;
- apprendre les limites de sécurité par essai-erreur ;
- reconnaître nominativement une personne à partir d'un classifieur supervisé préprogrammé ;
- construire immédiatement une représentation unifiée de toutes les modalités.

Le contrôleur de navigation `dagger_002` reste un artefact et une future compétence de locomotion. Il ne constitue plus l'objectif principal du projet.

## 4. Organisme minimal physique

### 4.1 Matériel disponible

Le banc physique actuel comprend :

- un servomoteur MF90 comme cou horizontal à un degré de liberté ;
- un capteur ultrason HC-SR04 monté sur le cou ;
- une webcam Logitech BRIO 100 montée sur le cou, dont le microphone intégré est le microphone initial ;
- une IMU MPU-9250, MPU-6500 ou MPU-9255 selon le module effectivement branché, fixée directement sur la tête mobile ;
- un capteur piézoélectrique actuellement sans contact mécanique utile ;
- un microphone USB Trust GXT 232 disponible comme référence optionnelle, placé à côté du banc et non sur la tête ;
- deux potentiomètres 10 kOhm disponibles pour du prototypage de mesure d'angle ;
- un Arduino comme interface temps réel ;
- un PC Windows pour les pilotes matériels ;
- WSL/Linux et une RTX 5080 pour l'apprentissage et les modèles.

Le microphone intégré à la BRIO 100 est retenu pour J0. Avant J3, l'expérience F1 doit mesurer s'il préserve suffisamment l'identité vocale malgré les traitements du pilote. Le Trust GXT 232 servira de référence USB lors de cette comparaison ; sa position fixe à côté du banc devra être enregistrée dans les métadonnées de session.

Pour la vérité terrain d'angle de J1a, la cible est un capteur magnétique absolu AS5600 monté coaxialement avec un aimant diamétral. Le potentiomètre 10 kOhm peut servir à un prototype mécanique rapide, mais ne constitue pas le choix de référence si l'AS5600 peut être monté proprement.

### 4.2 Corps de première génération

La première génération ne doit utiliser que le cou comme moyen d'action. Cela crée une boucle d'agence simple et interprétable :

```text
commande servo
    -> rotation de la tête
    -> flux optique et cadrage modifiés
    -> distance ultrason mesurée sous un autre angle
    -> accélération et vitesse angulaire mesurées
    -> variation éventuelle du son reçu
```

Ce corps minimal suffit pour étudier :

- l'agentivité : reconnaître les effets de sa propre commande ;
- la permanence : retrouver une scène après un aller-retour ;
- l'attention active : choisir un angle d'observation ;
- la calibration motrice : relier consigne, inertie et angle réel ;
- l'association multimodale : voix, visage, distance et orientation ;
- l'habituation : réduire l'intérêt pour les transitions maîtrisées.

La locomotion sera ajoutée plus tard comme nouvelle famille de compétences, pas comme fondation cognitive.

### 4.3 Limites actuelles des capteurs

- Le HC-SR04 ne mesure qu'une distance dans un cône et ne représente pas une scène complète.
- Le MF90 est commandé en boucle ouverte dans le montage actuel. La consigne d'angle n'est pas une mesure de l'angle réel. Sans encodeur, potentiomètre externe ou retour mécanique accessible, l'angle ne peut être qu'estimé à partir de la commande et de l'IMU.
- Une webcam monoculaire ne fournit pas directement la profondeur ni l'identité d'une personne.
- Un microphone mono ne localise pas instantanément une source. Une localisation grossière peut cependant émerger par balayage actif du cou et comparaison du signal selon l'angle.
- L'IMU est solidaire de la tête mobile et mesure donc directement sa dynamique, sous réserve de calibrer son orientation par rapport à l'axe du cou.
- Le gyroscope mesure bien les changements rapides, mais son intégration dérive et ne fournit pas seul un angle absolu durable. Le schéma corporel devra représenter cette incertitude.
- Le piézo sans couplage mécanique ne mesure pas une caresse. Jusqu'à son montage sur une surface déformable, sa valeur doit être journalisée comme canal expérimental mais exclue des objectifs d'apprentissage.

### 4.4 Écarts entre le banc et le logiciel actuel

Le dépôt contient actuellement deux protocoles Arduino incompatibles : l'un à 9600 bauds et commande un angle brut, l'autre à 115200 bauds et utilise `M:<angle>` tout en publiant piézo et ultrason. Ils doivent être remplacés par un protocole unique et versionné.

Le firmware EMG1 publie désormais IMU, ultrason, piézo, état servo et synchronisation. La capture J0 regroupe ces flux avec la vidéo et l'audio dans un bus append-only horodaté. L'ancien pont texte et le prototype cognitif ont été retirés du chemin actif et conservés uniquement dans `archive/legacy_agent/`.

Ces écarts ne sont pas des détails d'intégration : leur résolution constitue précisément le jalon J0.

## 5. Principes d'architecture

### 5.1 Causalité avant performance

Toute prédiction utilise uniquement les informations disponibles au moment de la décision. Les horodatages d'acquisition, de réception, d'inférence, de commande et d'application doivent être conservés séparément.

### 5.2 Les actions font partie de la perception

Le robot ne peut pas apprendre les conséquences de ses actions si les commandes demandées, sécurisées et effectivement appliquées sont confondues. Les trois valeurs doivent être journalisées.

### 5.3 Plusieurs échelles de temps

- boucle matérielle et sécurité : 50 à 200 Hz selon le capteur ;
- intégration sensorimotrice LNN : cible 50 Hz ;
- encodeurs visuels : 10 à 30 Hz ;
- représentation acoustique : fenêtres de 20 à 100 ms ;
- JEPA multimodal : 5 à 20 Hz selon le coût ;
- mémoire épisodique : frontières d'événements, secondes à minutes ;
- LMM/LLM : asynchrone, de quelques secondes à plusieurs minutes ;
- consolidation : hors ligne pendant les phases de sommeil.

Ces fréquences sont des cibles de conception. La valeur effectivement mesurée et la latence doivent accompagner chaque paquet.

### 5.4 Modularité et ablations

Chaque module doit pouvoir être retiré ou remplacé. Une amélioration attribuée au JEPA, au LNN ou au LMM doit être comparée à une baseline plus simple utilisant les mêmes données.

### 5.5 Plasticité contrôlée

Le robot peut enregistrer en continu, mais les poids qui commandent le matériel ne sont pas modifiés librement pendant l'éveil. L'apprentissage principal se fait hors ligne, avec validation, comparaison à l'ancien checkpoint et retour arrière automatique.

## 6. Architecture cognitive cible

```text
Matériel et horloges
    |
    v
Bus d'événements sensoriels horodatés
    |------------------|------------------|------------------|
    v                  v                  v                  v
Proprioception      Vision             Audio             Contact
IMU/servo/ultra     encodeur spatial   encodeur acoust.  piézo futur
    |                  |                  |                  |
    +------------------+------------------+------------------+
                               |
                               v
                 État sensorimoteur rapide LNN
                               |
                 +-------------+-------------+
                 |                           |
                 v                           v
       JEPA multimodal prédictif      Détecteur d'événements
                 |                           |
                 +-------------+-------------+
                               |
                               v
              Mémoire épisodique et familiarité
                               |
                 +-------------+-------------+
                 |                           |
                 v                           v
       Motivation intrinsèque       LMM/LLM asynchrone
                 |                  professeur / résumé
                 +-------------+-------------+
                               |
                               v
                   Sélection de compétence
                               |
                               v
             Primitives motrices + couche de sécurité
                               |
                               v
                         Servomoteur
```

## 7. Rôle des modules

### 7.1 Couche matérielle et tronc cérébral

Cette couche est déterministe. Elle assure :

- acquisition des capteurs ;
- horodatage au plus près de la source ;
- filtrage minimal documenté ;
- maintien de la dernière commande si nécessaire ;
- bornes angulaires et vitesse maximale ;
- watchdog et retour à une position neutre ;
- arrêt matériel ou logiciel indépendant des réseaux ;
- télémétrie sur pertes de paquets, timeouts et saturation.

Elle ne contient ni curiosité ni décision sémantique.

### 7.2 Encodeurs sensoriels

Chaque modalité garde d'abord son propre espace et sa propre horloge.

**Proprioception et somesthésie**

- consigne servo ;
- angle estimé ou mesuré ;
- vitesse et accélération angulaires ;
- gyroscope et accéléromètre IMU ;
- distance ultrason, validité et timeout ;
- piézo brut, baseline, enveloppe et statut de montage ;
- indicateurs de santé matérielle.

**Vision**

La sortie principale ne doit pas être limitée aux classes YOLO. L'encodeur doit conserver des informations sur la géométrie, le mouvement et l'apparence. Les détections sémantiques pré-entraînées peuvent former une voie auxiliaire, jamais l'unique perception.

**Audio**

Deux voies sont obligatoires :

1. une représentation acoustique continue conservant timbre, rythme, volume, prosodie et sons non verbaux ;
2. une voie ASR, par exemple Whisper, produisant du texte lorsque la parole est suffisamment claire.

Le texte ne remplace pas le son. La familiarité vocale doit utiliser la voie acoustique et non la transcription seule.

Le volume de données propre au robot sera initialement insuffisant pour apprendre vision et audition depuis zéro. Des encodeurs pré-entraînés gelés ou adaptés légèrement sont donc acceptés. Ils constituent des acquis initiaux du système, comparables à des prior structurels, et doivent être distingués explicitement de ce que le robot apprend pendant ses propres sessions. Les adaptateurs, associations temporelles, prototypes et modèles prédictifs restent appris localement.

### 7.3 LNN : intégration sensorimotrice rapide

Le LNN ne doit pas encoder directement les pixels ou de longues formes d'onde. Il reçoit :

- les signaux corporels rapides ;
- des embeddings sensoriels compacts et horodatés ;
- l'action appliquée précédente ;
- la disponibilité et l'ancienneté de chaque modalité.

Son état continu représente la dynamique corporelle et le contexte sensorimoteur immédiat. Ses fonctions attendues sont :

- estimer le mouvement réel de la tête ;
- filtrer le bruit et les retards ;
- maintenir un état lorsque certaines modalités sont temporairement absentes ;
- prédire des grandeurs corporelles à court terme ;
- exécuter des primitives motrices stables ;
- exposer un résumé rapide au modèle du monde.

Le LNN n'est pas, à lui seul, la représentation complète du monde.

### 7.4 JEPA : représentation prédictive du monde

Le JEPA apprend un état latent multimodal à partir d'un contexte passé et prédit des cibles futures sous condition des actions.

Entrées causales possibles :

- historique des embeddings visuels et acoustiques ;
- état sensorimoteur LNN déjà observé ;
- actions effectivement appliquées ;
- masques de modalité et délais ;
- contexte lent de familiarité, sans identité supervisée obligatoire.

Cibles auto-supervisées :

- embeddings futurs à plusieurs horizons ;
- correspondance entre modalités synchrones ;
- effet d'une action sur le flux visuel et proprioceptif ;
- permanence d'une scène après un mouvement aller-retour ;
- frontières d'événements ;
- retour ou disparition d'une source acoustique/visuelle.

Le JEPA doit prédire des distributions ou une incertitude, pas seulement un point moyen. Les horizons recommandés pour le premier corps sont environ 100 ms, 500 ms, 2 s et 5 s.

Un latent n'est considéré utile que s'il bat le contexte brut sur une sonde tenue à part : conséquence d'action, récurrence, correspondance audio-vidéo ou risque futur. Une erreur de reconstruction faible ne suffit pas.

### 7.5 Mémoire

La mémoire comprend quatre niveaux :

- buffer sensoriel court : quelques secondes de données denses ;
- mémoire épisodique : segments délimités par événement, action ou changement de contexte ;
- prototypes de familiarité : représentations lentement mises à jour des phénomènes récurrents ;
- mémoire consolidée : modèles et compétences valides pendant le sommeil.

Un épisode doit contenir les données brutes ou des références vers elles, les embeddings versionnés, les actions, les prédictions, les erreurs, les événements et les interventions humaines.

La familiarité n'est pas un nom. C'est d'abord une estimation de récurrence et de cohérence multimodale. Une étiquette comme `personne_familière_1` peut émerger avant toute association au mot ou au nom de l'utilisateur.

### 7.6 Motivation intrinsèque

Le robot ne maximise pas la surprise brute. Une télévision bruyante ou du bruit aléatoire ne doit pas devenir infiniment attractif.

La difficulté n'est pas une étiquette fixe de l'environnement. Elle décrit la relation
entre les capacités actuelles du robot et une expérience candidate. Une même expérience
peut être d'abord trop incertaine, devenir apprenable, puis être maîtrisée et subir
l'habituation. Le système de production ne reçoit donc aucun niveau « facile/moyen/dur »
annoté à la main; les environnements à difficulté contrôlée sont réservés aux tests.

La priorité d'une expérience combine :

- progrès d'apprentissage : diminution récente de l'erreur sur une famille de situations ;
- contrôlabilité : dépendance mesurable entre une action et une conséquence ;
- nouveauté épisodique : situation rare mais comparable à des acquis ;
- compétence : opportunité de stabiliser une primitive partiellement apprise ;
- pertinence sociale : récurrence cohérente d'une voix, d'un visage ou d'une interaction ;
- coût et risque matériels ;
- habituation : diminution d'intérêt lorsque la prédiction devient fiable.

Une forme conceptuelle est :

```text
intérêt = progrès_prédiction
        + gain_contrôlabilité
        + nouveauté_bornée
        + cohérence_sociale
        - risque
        - coût_moteur
        - aléatoirité_irréductible
```

Les coefficients ne doivent pas être fixés une fois pour toutes. Ils doivent être tracés, bornés et soumis à ablations.

Après l'échec de la sonde régionale `active_exploration_001`, la première réalisation
testable est volontairement réduite. Elle utilise un descripteur continu état-action, un
progrès local, une incertitude réductible estimée par ensemble bootstrap, une habituation,
une pénalité d'imprévisibilité persistante et des portes de contrôlabilité/risque. Une
frontière de proximité s'élargit avec la baisse mesurée de l'erreur: le refuge initial et
la curiosité graduelle émergent ainsi de la compétence, pas d'un curriculum codé en dur.
Voir `docs/research/developmental_curiosity_probe.md`. Conformément à D-002, cette branche
reste hors chemin critique tant qu'elle ne bat pas round-robin+habituation et babbling.

TV-001 (2026-07-20) a ensuite testé `regional_lp_gain`, seul contrôle robuste de
DC-004/DC-005, avec un JEPA réellement entraîné face à une télévision à contenu i.i.d.
La campagne appariée sur 12 graines rejette à la fois le gain d'apprentissage structuré
(`-2,80 %` relatif en moyenne) et l'évitement du bruit (`28,28 %` de télévision contre
`25,19 %` pour babbling), avec tous les garde-fous passés. Aucun ordonnanceur de
motivation n'est donc promu. Le diagnostic ouvert est désormais la distinction entre
apprendre légitimement une invariance au bruit et gaspiller des interactions sur une
source irréductible; voir `docs/research/tv_real_jepa_001_results.md` et D-009.

### 7.7 Compétences et actions

L'action initiale n'est pas un angle arbitraire produit par un grand réseau. Le système choisit parmi des primitives paramétrées et sûres :

- maintenir la position ;
- micro-saccade gauche ou droite ;
- balayage lent d'un intervalle ;
- retour au centre ;
- orientation vers un angle candidat ;
- suivi visuel lent ;
- interruption et repos.

Le LNN peut apprendre l'exécution continue de ces primitives. Un sélecteur plus lent choisit laquelle essayer selon l'intérêt attendu et les limites de sécurité.

La bibliothèque de compétences doit être extensible. Une nouvelle compétence est promue si elle produit un effet reproductible, reste dans les limites et ne dégrade pas les anciennes.

### 7.8 LMM/LLM : professeur lent et outil métacognitif

Le LMM/LLM n'est ni le pilote ni la source de récompense fondamentale. Ses rôles possibles sont :

- résumer un épisode en langage ;
- proposer des relations testables entre événements ;
- associer une transcription à un contexte perceptif ;
- fournir des connaissances générales lorsque l'expérience seule est insuffisante ;
- suggérer une expérience parmi une liste sûre ;
- aider à nommer des prototypes déjà appris ;
- produire un journal lisible par l'humain ;
- signaler une incohérence entre la mémoire et une interprétation.

Ses sorties doivent être structurées, journalisées et traitées comme des hypothèses incertaines. Elles ne sont jamais injectées directement comme commandes moteur ni considérées comme vérité terrain.

Exemple de sortie autorisée :

```json
{
  "hypothesis": "la voix entendue ressemble à une présence déjà rencontrée",
  "confidence": 0.63,
  "proposed_safe_experiment": "balayage_lent",
  "requested_observations": ["audio_embedding", "face_embedding", "servo_angle"]
}
```

## 8. Contrat de données multimodal

### 8.1 Règle générale

Les données ne sont pas forcées immédiatement dans un unique vecteur synchronisé. Elles sont stockées comme événements asynchrones partageant une horloge monotone commune.

Chaque message contient au minimum :

```text
session_id
source_id
sequence_id
source_timestamp_ns
host_receive_timestamp_ns
payload
quality
calibration_version
```

### 8.2 Paquets recommandés

```text
ServoCommand
  requested_angle_deg
  requested_speed_deg_s
  command_timestamp_ns

ServoState
  estimated_angle_deg
  angle_source              # command_model, imu_fusion ou external_encoder
  angle_uncertainty_deg
  applied_target_deg
  moving
  saturation

UltrasonicSample
  distance_m
  valid
  timeout
  servo_angle_deg

IMUSample
  accel_m_s2[3]
  gyro_rad_s[3]
  magnetometer_optional[3]
  calibration_status

VideoFrame
  frame_id
  capture_timestamp_ns
  width
  height
  encoding
  exposure_metadata_optional

AudioChunk
  chunk_id
  start_timestamp_ns
  sample_rate_hz
  channels
  pcm_reference

PiezoSample
  raw_value
  baseline_corrected
  envelope
  mechanically_coupled
```

Les représentations dérivées sont des messages distincts qui référencent les identifiants sources et la version exacte du modèle.

### 8.3 Sessions et épisodes

Une session correspond à une période de fonctionnement continue. Un épisode est un segment sémantique dérivé, par exemple :

- mouvement du cou ;
- apparition ou disparition d'une voix ;
- changement visuel important ;
- contact ;
- intervention humaine ;
- période de repos ;
- erreur matérielle.

Les frontières d'épisode ne doivent jamais être utilisées comme information future pendant l'apprentissage en ligne.

## 9. Apprentissage pendant l'éveil et le sommeil

### 9.1 Éveil

Pendant l'éveil, le système :

- collecte et horodate ;
- maintient les boucles de sécurité ;
- exécute uniquement des checkpoints valides ;
- estime la nouveauté, la familiarité et l'incertitude ;
- choisit des expériences dans un catalogue sûr ;
- met à jour des statistiques légères et des mémoires non paramétriques ;
- ne remplace pas silencieusement les poids du contrôleur.

### 9.2 Sommeil

Pendant le sommeil, le système :

1. vérifie l'intégrité des données ;
2. segmente les épisodes ;
3. rééchantillonne les événements rares sans oublier les situations ordinaires ;
4. entraîne ou adapte les encodeurs et le JEPA ;
5. consolide les prototypes de familiarité ;
6. entraîne les compétences candidates ;
7. mesure les régressions sur un jeu de souvenirs gelé ;
8. teste dans un simulateur ou en replay avant tout essai physique ;
9. produit un rapport de promotion ;
10. conserve l'ancien checkpoint pour rollback.

### 9.3 Prévention de l'oubli

Toute mise à jour doit inclure :

- replay d'épisodes anciens représentatifs ;
- jeu de validation permanent et versionné ;
- tests par compétence ;
- mesure de dérive des embeddings ;
- évaluation des prototypes familiers ;
- conservation des checkpoints précédents ;
- limite du volume de paramètres modifiables lors d'une adaptation rapide.

## 10. Familiarité sociale

### 10.1 Ce qui doit être appris

Le système cherche une variable latente expliquant la récurrence conjointe de plusieurs indices :

- timbre et caractéristiques de voix ;
- rythme et prosodie ;
- transcription éventuelle ;
- apparence visuelle et mouvement ;
- direction ou angle du cou associé ;
- régularité temporelle et contexte de session ;
- conséquences d'interactions, par exemple orientation suivie d'une parole.

Il ne faut pas imposer que tous ces indices soient présents simultanément.

### 10.2 Progression attendue

1. détection d'un événement acoustique ;
2. distinction parole / bruit / silence ;
3. regroupement de segments acoustiques récurrents ;
4. association temporelle avec une présence visuelle ;
5. création d'un prototype multimodal stable ;
6. anticipation : une voix familière augmente la probabilité de retrouver une configuration visuelle associée ;
7. apprentissage optionnel d'un nom via langage.

### 10.3 Évaluation

- sessions d'apprentissage et de test séparées ;
- phrases nouvelles lors du test ;
- conditions de volume et distance variées ;
- présence de voix inconnues ;
- test audio seul, vision seule et combinaison ;
- courbes de faux rapprochements et faux rejets ;
- mesure de la vitesse d'habituation ;
- vérification que le système ne mémorise pas seulement le fond de la pièce.

Les données audio et vidéo de personnes doivent rester locales, documentées et supprimables.

## 11. Sécurité et éthique

### 11.1 Sécurité matérielle non apprenable

Pour le premier cou :

- plage angulaire logicielle initiale de 10 à 170 degrés, appliquée dans le firmware et dans le logiciel hôte ;
- vitesse et accélération bornées ;
- temps minimal entre commandes ;
- retour neutre sur perte de communication ;
- nombre maximal de changements de direction par minute ;
- période de repos après activité soutenue ;
- arrêt d'urgence accessible ;
- aucun mouvement pendant une mise à jour de modèle ;
- journal des saturations et commandes rejetées.

Anthony n'a constaté ni forçage, ni vibration, ni chauffe particuliers dans la plage 10 à 170 degrés. Cette observation autorise l'enveloppe initiale, mais J0 doit encore vérifier les extrémités sous la charge complète et journaliser toute saturation, vibration ou chauffe.

### 11.2 Interaction humaine

- aucune identification nominative implicite ;
- indication visible lorsque caméra ou microphone enregistrent ;
- commandes d'arrêt et d'oubli prioritaires ;
- stockage local par défaut ;
- quota initial de 200 Go pour les données du projet, extensible ultérieurement par SSD dédié ;
- conservation pilotée par pertinence et pression de quota plutôt que par une durée fixe ;
- à 160 Go utilisés, avertissement et revue des sessions ; à 180 Go, arrêt des nouveaux enregistrements bruts longs jusqu'à libération ou extension ;
- aucune suppression silencieuse en J0 : toute suppression de données brutes est explicite et journalisée ;
- pas d'envoi de données brutes à un service distant sans action explicite ;
- le LMM ne doit pas inventer une certitude sur l'identité, l'intention ou l'émotion d'une personne.

## 12. Métriques de développement

Les tableaux de bord doivent séparer au moins :

### 12.1 Intégrité du système

- taux de paquets perdus ;
- latence par modalité ;
- dérive d'horloge ;
- disponibilité capteur ;
- commandes rejetées et saturations ;
- température et charge si disponibles.

### 12.2 Modèle sensorimoteur

- erreur de prédiction multi-horizon ;
- calibration de l'incertitude ;
- gain sur une baseline persistance ;
- effet de l'action par rapport à une action permutée ;
- performance avec chaque modalité retirée ;
- séparation entre changement auto-produit et externe.

### 12.3 Motivation

- progrès de prédiction par famille d'événements ;
- calibration de l'incertitude épistémique et décroissance avec l'évidence locale ;
- rayon de frontière en fonction de la maîtrise, sans niveaux annotés ;
- répartition du temps entre compétences ;
- taux de répétition stérile ;
- sensibilité au bruit irréductible ;
- courbe d'habituation ;
- diversité des effets contrôlables découverts.

### 12.4 Mémoire et familiarité

- rappel d'épisodes tenus à part ;
- stabilité des prototypes entre sessions ;
- taux de confusion entre présences ;
- gain multimodal par rapport à audio seul et vision seule ;
- rétention après plusieurs cycles de sommeil.

### 12.5 Compétences

- taux de succès par primitive ;
- précision de retour à un angle ;
- reproductibilité des conséquences ;
- coût moteur ;
- régressions sur les compétences précédentes.

Une métrique globale unique est interdite pour les décisions de promotion.

## 13. Jalons proposés

### J0 - Instrumentation fiable

Objectif : obtenir un enregistrement rejouable et causal du banc physique.

Livrables :

- protocole série unique ;
- horloge monotone et identifiants de séquence ;
- flux servo, ultrason, IMU, vidéo et audio ;
- outil de replay sans matériel ;
- rapport de latence et pertes ;
- calibration mécanique du cou ;
- politique de quota de 200 Go avec mesure du volume par session et absence de suppression silencieuse ;
- piézo marqué inactif tant qu'il n'est pas couplé.

Critère de passage : une session de 30 minutes peut être rejouée en conservant l'ordre causal, sans trou silencieux non signalé.

### J1 - Schéma corporel du cou

Objectif : apprendre les conséquences proprioceptives d'une commande servo.

Expériences :

- impulsions faibles dans les deux directions ;
- retours au centre ;
- amplitudes et vitesses variées ;
- commandes sans mouvement comme contrôles.

Critère de passage : prédiction tenue à part de l'angle et de la vitesse meilleure que persistance, et détection fiable d'une commande sans effet.

Si aucun capteur d'angle absolu n'est ajouté, ce critère porte sur une estimation fusionnant commande et IMU, avec incertitude calibrée. La consigne servo seule ne peut pas servir de vérité terrain.

### J2 - Contingences visuelles actives

Objectif : prédire comment une rotation transforme la scène visuelle.

Critère de passage : le modèle choisit correctement, parmi plusieurs futurs visuels, celui correspondant à l'action appliquée ; les actions permutées dégradent nettement le score.

### J3 - Audition duale

Objectif : collecter simultanément représentation acoustique et transcription.

Critère de passage : les embeddings regroupent mieux une même source sur des phrases différentes que des sources différentes sur une même phrase. Whisper fournit une voie sémantique asynchrone sans bloquer la boucle rapide.

### J4 - Familiarité multimodale

Objectif : apprendre un prototype récurrent de la présence de l'utilisateur.

Contrainte de collecte : Anthony sera présent dans plus de 90 % des cas, mais deux à trois autres personnes peuvent participer séparément à des sessions occasionnelles. Le protocole doit donc réserver à au moins une autre personne réelle trois sessions distinctes et atteindre au moins dix sessions au total avant de conclure sur la ré-identification.

Critère de passage : sur des sessions et phrases nouvelles, la fusion audio-vidéo bat chaque modalité seule, le kNN sur embeddings gelés et un détecteur de présence trivial, tout en restant calibrée face à une personne inconnue.

### J5 - Curiosité par progrès et habituation

Objectif : choisir entre plusieurs expériences sûres sans récompense de tâche.

Critère de passage : face aux mêmes budgets, risques et primitives, le robot réduit
spontanément les répétitions d'une contingence maîtrisée, évite le bruit aléatoire et
revient vers une compétence encore améliorable. L'ordre doit émerger dans un espace
continu sans niveaux communiqués à l'agent. La comparaison obligatoire inclut babbling et
round-robin+habituation; les seuils d'allocation, de gain tenu à part, de couverture et de
variance entre graines sont pré-enregistrés avant campagne. Le learning progress régional
ayant échoué, l'implémentation continue de
`docs/research/developmental_curiosity_probe.md` reste une branche candidate, pas le
mécanisme par défaut.

### J6 - Mémoire épisodique et sommeil

Objectif : conserver et consolider les acquis entre sessions.

Critère de passage : amélioration sur les nouvelles données sans régression significative sur J1 à J5, avec rollback automatique si la règle échoue.

### J7 - LMM/LLM superviseur lent

Objectif : enrichir la mémoire et proposer des expériences sans piloter.

Critère de passage : les hypothèses structurées améliorent une tâche de rappel, de nomination ou de choix d'expérience face à une baseline sans LMM, sans hausse des violations de sécurité.

### J8 - Extension du corps

La locomotion, le contact piézo ou un second axe ne sont ajoutés qu'après stabilisation des jalons précédents. Chaque nouvel actionneur est introduit comme une extension du schéma corporel et doit repasser J0, J1 et les tests de non-régression.

## 14. Plan de migration du dépôt

### 14.1 À conserver

- simulateur, ZOH et couche de sécurité ;
- contrats observation/action comme précédente preuve de méthode ;
- outils de logs, replay, évaluation multi-graines et sélection de checkpoint ;
- séparation éveil/sommeil ;
- checkpoints de navigation comme branche historique ;
- diagnostics de causalité et de distribution.

### 14.2 À remplacer

- le vecteur monolithique de 256 dimensions concaténé sans synchronisation ;
- les encodeurs vision et audio placeholders ;
- la curiosité définie comme simple norme d'erreur instantanée ;
- l'acteur global apprenant directement toutes les actions ;
- l'intention LLM injectée sans contrat structuré ;
- le replay buffer limité à `(state, action, reward, next_state)` ;
- les fichiers `.pth` non accompagnés d'un manifeste complet.

### 14.3 Nouveaux composants attendus

```text
j0/                     # contrats, acquisition, recorder, replay et rapports
peripheral/brain_stem/  # firmware et protocole EMG1
windows_client/         # flash et capture Windows
tests/                  # validation active

common/                 # contrats partagés de la branche de recherche
sim2d/                  # corps virtuel historique
learning/               # entraînement et évaluations historiques
scripts/research/       # campagnes reproductibles
docs/research/          # résultats et décisions expérimentales
archive/legacy_agent/   # prototype cognitif antérieur à J0
```

Les futurs composants de segmentation, motivation, familiarité et registre de compétences seront ajoutés seulement au jalon qui les justifie.

## 15. Règles expérimentales

1. Une hypothèse doit être falsifiable avant l'entraînement.
2. Toute architecture complexe est comparée à une baseline simple.
3. Les splits se font par session ou épisode, jamais par lignes aléatoires adjacentes.
4. Les données de test restent gelées jusqu'à la décision finale.
5. Les effets sont reproduits sur plusieurs sessions physiques.
6. Les actions appliquées, pas seulement demandées, conditionnent les prédictions.
7. Toute utilisation du LMM fait l'objet d'une ablation sans LMM.
8. Une hausse de surprise n'est pas interprétée automatiquement comme un progrès.
9. Une nouvelle compétence ne remplace pas silencieusement une ancienne.
10. Aucun résultat en simulation ne vaut validation matérielle, et inversement.

## 16. Questions ouvertes pour la revue externe

1. Le LNN est-il nécessaire dès J1-J2, ou une baseline récurrente discrète suffit-elle avant d'introduire une ODE ?
2. Le JEPA multimodal doit-il utiliser un espace partagé unique ou des espaces par modalité reliés par prédiction croisée ?
3. Comment estimer proprement le progrès d'apprentissage sans favoriser les modalités les plus bruitées ?
4. Quel mécanisme de mémoire non paramétrique permet une familiarité rapide sans confondre contexte et identité ?
5. Comment séparer visuellement une personne du fond de la pièce sans supervision forte ?
6. Quelle représentation acoustique conserve le mieux l'identité de source tout en restant robuste au contenu verbal ?
7. À quel moment le LMM apporte-t-il un gain mesurable par rapport à des outils symboliques et des embeddings gelés ?
8. Le premier JEPA doit-il prédire des latents futurs, des transformations dues aux actions, ou les deux avec des têtes séparées ?
9. Quelle incertitude est nécessaire pour distinguer ignorance réductible et bruit irréductible ?
10. Quels tests prouvent qu'un prototype familier correspond à une présence et non au fond, à l'heure ou à une phrase mémorisée ?

## 17. Décision immédiate

La prochaine phase du projet ne poursuit pas l'optimisation du contrôleur de navigation. Elle commence par J0 : unifier le protocole physique et enregistrer des flux multimodaux causalement fiables.

Le premier apprentissage nouveau portera ensuite sur J1, le schéma corporel du cou. Vision, audition, familiarité sociale, motivation intrinsèque et LMM seront ajoutés dans cet ordre seulement lorsque les contrats de données et les baselines correspondantes seront mesurables.
