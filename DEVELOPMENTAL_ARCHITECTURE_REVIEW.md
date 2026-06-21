# Revue contradictoire de la spécification développementale

Statut : revue critique externe de `DEVELOPMENTAL_ARCHITECTURE.md`
Date : 2026-06-11
Sources : `DEVELOPMENTAL_ARCHITECTURE.md`, les documents de `docs/research/`, `README.md` et le prototype conservé dans `archive/legacy_agent/`.
Mandat : ne pas confirmer les choix. Identifier les hypothèses faibles, les complexités prématurées et les expériences non concluantes.

---

## 1. Verdict exécutif

La spécification est nettement meilleure que ce que le dépôt a produit jusqu'ici : elle encode les leçons durement acquises (baselines obligatoires, splits par session, actions appliquées vs demandées, sondes tenues à part, promotion multi-protocoles). Le recentrage J0-first sur l'instrumentation est la décision la plus juste du document.

Mais la spécification contient une contradiction interne majeure : **elle énonce des règles épistémiques qui, appliquées aux propres résultats du projet, disqualifient plusieurs de ses composants centraux**. La règle 7.4 (« un latent n'est utile que s'il bat le contexte brut sur une sonde tenue à part ») est déjà falsifiée pour le JEPA actuel par `docs/research/collision_risk_results.md` (AP 0.193 brut vs 0.167 latent, AUROC 0.794 vs 0.782, rappel 28.1% vs 23.3% — le latent perd sur *toutes* les métriques). Pourtant le JEPA reste au centre du diagramme d'architecture, sur le chemin critique vers la mémoire et la familiarité. De même, le LNN est positionné par défaut au cœur de l'intégration sensorimotrice alors que la tâche J1 (estimer/prédire l'état d'un servo 1-DDL) est un problème de filtrage d'état classique, et que l'historique du projet démontre que les modèles entraînés portent une variance inter-graines du même ordre que les effets mesurés (E1 : la référence 1.21% est un tirage exceptionnel ; les réplications donnent 3.30% ± 0.47%).

Le second défaut structurel est l'ordonnancement linéaire des jalons alors que les besoins en données sont cumulatifs : J4 (familiarité) exigera des semaines de sessions sociales qui devraient commencer à être enregistrées dès J0. Le troisième est l'absence de quantification : aucun jalon ne précise le nombre de graines, de sessions ou les marges qui rendraient son critère de passage opposable — exactement l'erreur que E1 a corrigée a posteriori pour la navigation.

**Recommandation : B — simplifier avant implémentation**, avec rétrogradations explicites : LNN, JEPA, motivation à 7 termes et LMM deviennent des branches expérimentales conditionnées à des sondes pré-enregistrées, et non des composants de l'architecture par défaut. Détail en §12.

---

## 2. Hypothèses acceptées

Ces choix résistent à la critique et ne doivent pas être rouverts sans fait nouveau :

- **J0 d'abord.** Aucun apprentissage fiable n'était possible avec deux firmwares incompatibles, les encodeurs placeholders du prototype archivé et sans horodatage causal. La spécification a raison de faire de l'instrumentation le jalon bloquant.
- **Abandon de la navigation comme objectif.** Le corpus expérimental (couplage direct : 7.73% puis 13.03% de collisions ; S4 rejeté sur 12 comparaisons sur 12) justifie le pivot.
- **Le LLM jamais sur les moteurs, sorties structurées, ablation sans-LMM obligatoire.** Correct et non négociable.
- **Voie acoustique distincte de la voie ASR.** La familiarité vocale par transcription seule serait une erreur de catégorie ; la séparation est la bonne décision.
- **Encodeurs pré-entraînés gelés acceptés comme priors.** Le volume de données propre au robot ne permettra pas d'apprendre la vision depuis zéro ; la distinction explicite acquis initial / appris localement est saine.
- **Sécurité non apprenable, plasticité contrôlée, rollback.** Conforme aux leçons du projet.
- **Journalisation des trois niveaux de commande** (demandée, sécurisée, appliquée) et splits par session. Directement issus des erreurs passées ; à conserver.
- **Le corps minimal cou-seul.** Un degré de liberté est suffisant pour étudier agentivité, habituation et calibration motrice, et insuffisant pour masquer les échecs derrière la complexité — c'est une vertu.

---

## 3. Erreurs ou risques critiques

Chaque entrée suit le format : affirmation / pourquoi elle peut être fausse / test le moins coûteux / résultat confirmant / résultat conduisant à l'abandon.

### C1 — « Le JEPA multimodal est le modèle du monde central »

- **Affirmation.** Le diagramme §6 place le JEPA sur le chemin critique : LNN → JEPA → mémoire/familiarité → motivation.
- **Pourquoi c'est probablement faux.** Le seul test quantitatif disponible du latent JEPA comme représentation (critique de collision) montre qu'il *détruit* de l'information par rapport au contexte brut. D1 a montré qu'en boucle fermée le contenu dynamique du latent n'apportait rien (latent gelé à zéro : 7.75% vs latent dynamique : 7.73%). Rien ne garantit qu'un JEPA multimodal sur le nouveau corps fera mieux ; l'hypothèse par défaut devrait être l'inverse.
- **Test le moins coûteux.** Reproduire le protocole de `docs/research/collision_risk_results.md` sur le nouveau corps dès que J1-J2 produisent des données : sonde gelée « conséquence d'action » et « récurrence » sur (a) contexte brut multimodal, (b) latent JEPA. C'est déjà la règle 7.4 de la spécification — il suffit de la rendre *bloquante* pour l'entrée du JEPA dans l'architecture.
- **Confirmé si** le latent bat le contexte brut avec une marge supérieure à la variance inter-graines sur au moins deux sondes.
- **Abandonné si** le contexte brut domine ou égale le latent sur les sondes de J2 et J4 : le JEPA reste alors une branche de recherche, et la mémoire/familiarité se construit sur embeddings gelés + contexte brut.

### C2 — « Le LNN est l'intégrateur sensorimoteur de première génération »

- **Affirmation.** §7.3 : le LNN estime le mouvement réel, filtre le bruit, maintient l'état, prédit à court terme, exécute les primitives.
- **Pourquoi c'est probablement faux.** Ce sont six fonctions dont les trois premières sont résolues optimalement (au sens des hypothèses gaussiennes) par un filtre de Kalman ou complémentaire, avec incertitude calibrée *par construction* — précisément ce que J1 exige. Un LNN n'offre aucune garantie de calibration, ajoute la variance d'entraînement démontrée par E1, exige le GPU, et son seul avantage théorique (temps continu, échantillonnage irrégulier) est couvert par un GRU recevant Δt en entrée. L'historique du projet (RMSE offline non prédictive, 5/6 sélections E3 divergentes du minimum de RMSE) montre le coût réel de chaque modèle entraîné supplémentaire.
- **Test le moins coûteux.** Sur les mêmes logs J1 : persistance, modèle linéaire (commande → Δgyro), Kalman/complémentaire, GRU petit, LNN petit. 3 graines pour les modèles entraînés. Budget : quelques heures de GPU, zéro matériel.
- **Confirmé si** le LNN bat le Kalman ET le GRU au-delà de la dispersion inter-graines sur des sessions tenues à part.
- **Abandonné si** le Kalman atteint le critère J1 seul : le LNN est différé jusqu'à ce qu'une tâche le justifie (exécution de primitives complexes, J8+).

### C3 — Critères de jalons non quantifiés : la leçon E1 n'est pas propagée

- **Affirmation.** Chaque jalon a un « critère de passage » qualitatif (« meilleure que persistance », « bat chaque modalité seule »).
- **Pourquoi c'est insuffisant.** E1 a prouvé que la variance inter-graines invalide les comparaisons mono-graine, et le projet a dû amender sa règle de promotion a posteriori. Les ticks de collision autocorrélés ont aussi montré que l'échantillon effectif est bien plus petit que le nombre de pas. Aucun critère J1-J7 ne précise graines, sessions, ni marges. Tels quels, les jalons seront « passés » par des tirages chanceux, exactement comme `dagger_002`.
- **Test le moins coûteux.** Aucun : c'est une correction d'écriture. Chaque critère doit pré-enregistrer N graines (≥3 pour tout modèle entraîné), M sessions physiques distinctes (≥3), la métrique, la marge de non-infériorité et la baseline à battre.
- **Confirmé / abandonné.** Sans objet — à appliquer avant tout entraînement.

### C4 — La collecte de données sociales commence trop tard

- **Affirmation.** L'ordre J0→J4 implique que les données de familiarité ne deviennent pertinentes qu'au jalon J4.
- **Pourquoi c'est faux.** J4 exige des récurrences *inter-sessions* sur des semaines (sessions et phrases nouvelles au test, conditions variées, voix inconnues). C'est la ressource la plus lente du projet — pas le GPU, pas le code : le temps calendaire de présence humaine. Si l'enregistrement passif ne commence qu'après J3, J4 stagne des semaines de plus.
- **Test le moins coûteux.** Aucun test : décision de planification. Dès que le recorder J0 fonctionne, chaque session — y compris les sessions de debug J1-J2 — enregistre audio/vidéo avec consentement et métadonnées (qui est présent, sans étiquette d'identité dans les features).
- **Risque si ignoré.** J4 devient le goulot calendaire du projet entier.

### C5 — Estimation d'angle : risque de circularité de la vérité terrain

- **Affirmation.** J1 : « prédiction de l'angle et de la vitesse meilleure que persistance », angle estimé par fusion commande/IMU avec incertitude calibrée.
- **Pourquoi c'est fragile.** Si la « vérité terrain » de l'angle est elle-même la fusion commande+IMU, et que le prédicteur reçoit la commande en entrée, le critère peut être satisfait en apprenant le modèle de commande de l'estimateur — une tautologie. La calibration de l'incertitude est alors invérifiable. De plus, valider une estimation sans aucune mesure indépendante n'est pas possible, même en principe.
- **Test le moins coûteux.** Deux options : (a) ~2-5 € : un encodeur magnétique AS5600 ou un potentiomètre couplé à l'axe, utilisé *uniquement comme vérité terrain de banc*, pas en production ; (b) 0 € : rapporteur imprimé fixé à la base + repère sur la tête + photos à des consignes connues, plus recalage périodique sur butées mécaniques. L'option (a) coûte moins qu'une journée de débat.
- **Confirmé si** l'estimation fusionnée atteint une erreur RMS ≤ 2-3° avec incertitude couvrant ~90% des erreurs sur une session de 30 min incluant des mouvements variés.
- **Abandonné si** l'erreur dépasse ~5-8° ou dérive sans borne : acheter le capteur d'angle et le déclarer dans `angle_source` (le contrat de données le prévoit déjà : `external_encoder`).

### C6 — Reformulation recommandée de J1 : prédire des grandeurs *mesurées*

- **Affirmation.** J1 cible l'angle, une grandeur estimée.
- **Pourquoi c'est sous-optimal.** Le gyroscope Z et l'accéléromètre sont des mesures directes. « Prédire gyro_z(t+h) et accel(t+h) connaissant l'historique de commandes et de mesures » est un critère sans circularité, falsifiable contre persistance et modèle linéaire, et capture exactement la contingence sensorimotrice visée. L'angle absolu devient un livrable séparé d'*estimation* (avec sa propre validation C5), pas la cible de *prédiction*.
- **Test.** Gratuit : c'est une reformulation du critère avant l'entraînement.

### C7 — Familiarité avec une seule personne : le contraste n'existe pas

- **Affirmation.** J4 : « la fusion audio-vidéo bat chaque modalité seule et reste calibrée face à une voix inconnue ».
- **Pourquoi c'est probablement infaisable tel quel.** L'environnement réel contient essentiellement une personne. Avec un seul positif, « familier vs inconnu » dégénère en « présence vs absence » — qu'un détecteur de mouvement + énergie audio résout sans apprentissage. Les « voix inconnues » devront venir de haut-parleurs (signature acoustique propre : le système peut apprendre « enceinte vs humain vivant » au lieu de « inconnu vs familier ») ou de jeux de données publics (décalage de domaine). Le risque de conclure à tort est maximal sur ce jalon.
- **Test le moins coûteux.** Avant tout modèle : embeddings locuteur pré-entraînés (type ECAPA) sur les enregistrements du robot ; mesurer si la similarité intra-locuteur inter-sessions dépasse la similarité avec des négatifs publics ET des négatifs rejoués par enceinte. Inviter au moins une seconde personne réelle sur ≥3 sessions.
- **Confirmé si** la séparation existe dans l'espace gelé avec les deux types de négatifs et au moins deux personnes réelles.
- **Abandonné (rétrogradé) si** seuls des négatifs synthétiques sont disponibles : J4 est requalifié honnêtement en « ré-identification inter-sessions + calibration contre négatifs synthétiques », sans revendication de discrimination de personnes.

### C8 — Le microphone de webcam peut détruire l'identité vocale en amont

- **Affirmation.** §4.1 : « le microphone intégré à la webcam peut suffire pour les premiers essais ».
- **Pourquoi c'est risqué.** AGC, suppression de bruit et compression des pilotes webcam normalisent précisément les indices (énergie relative, spectre fin, dynamique) dont dépend l'identité de locuteur. Si la chaîne d'acquisition écrase ces indices, J3 et J4 échoueront pour une raison matérielle indétectable dans les métriques de modèle.
- **Test le moins coûteux.** Une heure : enregistrer la même personne, mêmes phrases, à 3 distances et 2 volumes ; calculer les similarités d'embeddings locuteur ; comparer avec un téléphone ou un micro USB de référence.
- **Confirmé si** la similarité intra-locuteur reste stable à travers distances/volumes et nettement au-dessus de l'inter-locuteur.
- **Abandonné si** l'AGC écrase la structure : achat d'un micro USB (~20 €) avant J3 — pas après l'échec de J4.

### C9 — Fuites temporelles : les risques réels ne sont pas ceux listés

- **Affirmation.** §8 et §15.3 couvrent la causalité (horodatages séparés, frontières d'épisodes jamais utilisées en ligne, splits par session).
- **Ce qui manque.** Les fuites les plus probables dans un pipeline asynchrone multimachine sont : (a) **normalisation calculée sur la session entière** (moyenne/écart-type incluant le futur) appliquée aux fenêtres d'entraînement ; (b) **interpolation/rééchantillonnage centré** utilisant des échantillons postérieurs à t ; (c) **horloges non alignées** entre Arduino (`micros()`), Windows (capture webcam — les pilotes assignent souvent l'heure d'arrivée, pas d'exposition) et WSL (inférence), créant des décalages qui font entrer du « futur physique » dans des fenêtres « passées » ; (d) **latence audio inconnue** des buffers circulaires des pilotes.
- **Test le moins coûteux.** Test du clap : un événement physique unique visible et audible (clap devant la caméra, LED + bip commandés par l'Arduino) ; mesurer le désalignement inter-modal reconstruit par le bus. À intégrer comme livrable J0.
- **Confirmé si** le désalignement résiduel est borné, mesuré, et journalisé par session (< ~20 ms après correction, soit un pas de boucle).
- **Abandonné si** le jitter inter-horloges est non stationnaire et > 1 pas de boucle : il faut alors un protocole de synchronisation actif (ping périodique RTT/2, offset journalisé) avant tout apprentissage multimodal.

### C10 — Motivation par progrès d'apprentissage : l'estimateur est plus bruité que le signal

- **Affirmation.** §7.6 : la priorité combine 7 termes, dont le progrès de prédiction par « famille de situations ».
- **Pourquoi c'est fragile.** (a) Le progrès est la *dérivée* d'une courbe d'erreur bruitée : sur les fenêtres courtes d'une session de 30 min, l'estimateur de pente sera dominé par la variance — le même problème que les ticks autocorrélés d'E1, en pire. (b) La « famille de situations » est soit codée à la main (acceptable au début), soit apprise (circulaire : la partition dépend du modèle dont on mesure le progrès). (c) Sept termes pondérés sont inidentifiables avec les volumes de données disponibles : aucune ablation ne pourra attribuer un comportement à un coefficient. (d) Avec un seul DDL dans une pièce statique, l'espace des contingences apprenables peut saturer en quelques heures ; après quoi progrès ≈ 0 partout et le comportement dégénère vers le repos — issue que la formule prédit mais que la spécification ne discute pas.
- **Test le moins coûteux.** Hors robot, en replay : injecter dans les logs un canal artificiel parfaitement apprenable (sinus dépendant de la commande) et un canal de bruit pur ; vérifier que l'estimateur de progrès les classe correctement, et mesurer en combien de temps. Puis comparer l'ordonnanceur LP complet à deux baselines : choix aléatoire de primitive, et round-robin avec décroissance d'habituation (compteur, zéro apprentissage).
- **Confirmé si** LP classe les deux canaux correctement en < ~10 min de données et bat les deux baselines sur des signatures comportementales pré-enregistrées (allocation de temps, évitement du canal bruit).
- **Abandonné si** round-robin + habituation est indistinguable : adopter l'ordonnanceur simple et réduire la formule à 2-3 termes (progrès, habituation, risque).

### C11 — « Détecteur d'événements » et segmentation épisodique : composant central non défini

- **Affirmation.** Le diagramme §6 contient un « Détecteur d'événements » et la mémoire dépend de « frontières d'événements ».
- **Pourquoi c'est un risque.** Aucun mécanisme, aucun jalon, aucun critère ne le définit, alors que la mémoire épisodique (J6), la familiarité (J4) et la motivation (J5) en dépendent tous. Un composant non spécifié dont trois jalons dépendent est une dette de conception majeure.
- **Correction minimale.** Première génération : seuils déclaratifs (début/fin de mouvement servo, VAD audio, delta visuel), versionnés, sans apprentissage. La segmentation apprise est différée.

### C12 — La prévention de l'oubli mesure la dérive mais ne la résout pas

- **Affirmation.** §9.3 : replay, jeu de validation gelé, mesure de dérive des embeddings, checkpoints conservés.
- **Pourquoi c'est incomplet.** (a) Les prototypes de familiarité sont des vecteurs dans l'espace d'un encodeur versionné ; à chaque promotion d'encodeur, tous les prototypes deviennent invalides. Mesurer la dérive ne dit pas quoi faire. La seule solution robuste : conserver les données brutes et ré-encoder les prototypes à chaque promotion — ce qui impose une politique de rétention brute (volume : de l'ordre de 1-2 Go/session de 30 min en vidéo compressée + audio ; chiffrable, mais à budgéter dès J0). (b) Le « jeu de souvenirs gelé » vieillit : la pièce change, les capteurs sont recalibrés ; au bout de quelques mois il mesure la dérive du monde, pas l'oubli du modèle. Il faut une politique de versionnement et de dépréciation des jeux gelés. (c) §12 interdit toute métrique globale unique, mais le rollback automatique (§9.2) exige une règle déterministe — contradiction à résoudre : promotion = conjonction de tests par capacité avec marges de non-infériorité pré-enregistrées ; un seul échec = pas de promotion.

---

## 4. Composants prématurés ou inutiles

| Composant | Statut recommandé | Justification |
|---|---|---|
| LNN comme intégrateur J1 | **Prématuré** — branche expérimentale gated par C2 | Tâche de filtrage classique ; variance d'entraînement démontrée (E1) ; aucun besoin du temps continu non couvert par GRU+Δt |
| JEPA multimodal central | **Prématuré** — gated par la règle 7.4 rendue bloquante | Falsifié sur la seule sonde existante (collision risk) ; D1 montre un latent dynamiquement inutile en boucle fermée |
| Interpolation géodésique, métrique riemannienne, flot de Ricci (`docs/research/jepa_lnn_robot_math.md` §5, §11) | **Inutile à horizon visible** | Aucune expérience du projet n'a jamais atteint le niveau où ces régularisations seraient le facteur limitant ; complexité pure |
| Motivation à 7 termes | **Prématuré** — réduire à 2-3 termes | Coefficients inidentifiables ; baseline round-robin+habituation non encore battue (C10) |
| LMM/LLM « professeur » (J7) | **Différable sans coût** | Aucun jalon antérieur n'en dépend ; la seule utilité immédiate défendable est le journal de session lisible (outillage développeur, pas cognition) |
| Segmentation d'événements apprise | **Prématurée** | Seuils déclaratifs d'abord (C11) |
| Espace latent multimodal unifié | **Correctement suspendu** par §3 — maintenir la suspension | La question ouverte 16.2 (espaces par modalité + prédiction croisée) est la voie basse-complexité ; commencer là |
| Piézo | **Correctement exclu** | Rien à ajouter ; le marquage `mechanically_coupled` dans le contrat est la bonne pratique |
| Whisper | **Acceptable dès J3** | Asynchrone, gelé, hors boucle rapide ; risque faible. Seule réserve : C8 sur le micro en amont |

---

## 5. Architecture minimale recommandée

Le critère de conception : chaque boîte doit être soit déterministe, soit accompagnée de sa baseline triviale dans le même livrable.

```text
Matériel + synchronisation d'horloges mesurée (J0, test du clap)
    |
Bus d'événements horodatés, recorder append-only, replay déterministe
    |
    |-- Proprioception : filtre complémentaire/Kalman (commande + gyro + ZUPT
    |     + recalage butées), incertitude calibrée, validé contre capteur de banc (C5)
    |-- Vision : encodeur pré-entraîné gelé (5-10 Hz) + flux optique
    |-- Audio : log-mel + embedding locuteur gelé + VAD ; Whisper asynchrone
    |
Prédicteurs sensorimoteurs : persistance -> linéaire -> GRU
    (LNN seulement si C2 le justifie)
    |
Familiarité : prototypes non paramétriques (kNN à décroissance temporelle)
    sur embeddings gelés — zéro entraînement en première génération
    |
Ordonnanceur d'expériences : catalogue de primitives sûres
    + habituation par compteur (LP seulement si C10 le justifie)
    |
Mémoire : épisodes parquet + index ; rétention brute budgétée ;
    re-encodage des prototypes à chaque promotion d'encodeur
    |
Sécurité codée en dur (inchangée par rapport à la spécification §11.1)
```

Branches expérimentales (jamais sur le chemin critique tant que leur sonde n'est pas gagnée) : JEPA multimodal (sonde C1), LNN (sonde C2), motivation LP (sonde C10), LMM (ablation J7).

Cette architecture atteint les capacités 1 à 6 de la définition du succès (§2 de la spécification) sans un seul réseau entraîné de bout en bout au-delà d'un GRU. Si elle y parvient, le projet aura appris quelque chose d'important : les mécanismes développementaux élémentaires ne requièrent pas l'appareillage lourd. Si elle échoue à un point précis, ce point devient la justification *mesurée* du composant complexe correspondant — ce qui est exactement la manière dont un composant devrait gagner sa place.

---

## 6. Révision détaillée des jalons J0 à J8

### J0 — Instrumentation fiable : **conserver, durcir**

Ajouts requis :

- protocole série **binaire** versionné (le format texte actuel `P:x|D:y` à 115200 bauds laisse peu de marge : IMU 100-200 Hz + ultrason + piézo en ASCII saturent le lien ; budget de bande passante à chiffrer dans le livrable) ;
- **test du clap** pour la calibration de synchronisation audio/vidéo/IMU (C9) et protocole d'offset d'horloges Windows/WSL/Arduino journalisé par session ;
- politique de **rétention des données brutes** (volume/session, durée, suppression) — condition de C12 ;
- démarrage de la **collecte sociale passive** (C4) dès que le recorder tourne ;
- décision documentée sur le **capteur d'angle de banc** (C5) — l'acheter coûte moins cher que d'en débattre.

Critère de passage : inchangé (session 30 min rejouable, ordre causal, pas de trou silencieux), plus : désalignement inter-modal mesuré < 1 pas de boucle.

### J1 — Schéma corporel du cou : **scinder en J1a / J1b**

- **J1a (estimation)** : angle + vitesse par fusion commande/IMU, incertitude calibrée, validés contre la vérité terrain de banc (C5). Livrable : `ServoState` avec `angle_uncertainty_deg` honnête.
- **J1b (prédiction)** : prédire des grandeurs *mesurées* — gyro_z et accéléromètre futurs à 100 ms / 500 ms — conditionnées aux commandes (C6). Échelle de baselines obligatoire : persistance → linéaire → Kalman → GRU → (LNN si justifié). Critère quantifié : battre la persistance ET le modèle linéaire sur ≥3 sessions tenues à part, ≥3 graines pour tout modèle entraîné, marge > dispersion inter-graines.
- La « détection de commande sans effet » est conservée telle quelle : c'est un excellent critère, mesurable par silence gyroscopique après commande.

### J2 — Contingences visuelles actives : **conserver, ajouter la baseline géométrique**

Le critère (choisir le futur visuel correspondant à l'action ; actions permutées dégradent le score) est bon mais peut être satisfait par la géométrie seule : une rotation de caméra produit un flux optique quasi déterministe. Baseline obligatoire : prédicteur flux-optique/homographie sans apprentissage (ou régression linéaire commande → décalage). Le modèle appris doit battre cette baseline, sinon J2 valide la trigonométrie, pas un modèle du monde.

### Nouveau J2.5 — Attribution auto-produit vs externe : **jalon manquant**

La capacité 2 de la définition du succès (« distinguer les changements auto-produits des événements externes ») est l'affirmation développementale centrale du projet — et elle n'a pas de jalon. Elle n'apparaît que comme métrique (§12.2). Proposition : prédire le flux sensoriel sous modèle propre (J1b + J2) ; le résidu pendant le mouvement propre doit rester bas ; un changement externe provoqué (complice qui agite un objet, bruit déclenché) doit produire un résidu élevé *y compris pendant un mouvement propre simultané*. Critère : AUROC de détection d'événement externe > seuil pré-enregistré, dans les deux conditions (tête immobile / tête en mouvement).

### J3 — Audition duale : **conserver, conditionner au test micro**

Le critère (regroupement par source > regroupement par phrase) est le bon. Préalables : C8 (test AGC du micro, une heure) et précision du protocole : combien de sessions, combien de locuteurs, négatifs rejoués par enceinte identifiés comme tels.

### J4 — Familiarité multimodale : **requalifier honnêtement**

En l'état, le critère est probablement intestable (C7). Requalification : « ré-identification inter-sessions calibrée », avec exigence minimale de ≥2 personnes réelles sur ≥10 sessions et négatifs des deux types (enceinte + datasets). La baseline à battre est double : (a) kNN sur embeddings gelés sans aucun apprentissage local ; (b) détecteur de présence trivial (énergie audio + différence d'images). Si (a) suffit, c'est une excellente nouvelle — la familiarité de première génération est gratuite — et l'apprentissage local doit prouver un gain au-delà.

Le contrôle « le système ne mémorise pas le fond de la pièce » (§10.3) doit devenir un test exécutable : session avec une personne différente au même endroit/horaire ; si le prototype « familier » s'active autant, c'est un détecteur de décor.

### J5 — Curiosité : **conserver l'objectif, réduire le mécanisme**

Critère actuel qualitatif. Le rendre falsifiable via C10 : canal apprenable + canal bruit injectés, signatures comportementales pré-enregistrées, baselines aléatoire et round-robin+habituation. Le mécanisme par défaut est l'ordonnanceur simple ; LP n'entre que s'il bat l'ordonnanceur simple.

### J6 — Mémoire et sommeil : **scinder : l'infrastructure remonte, la consolidation reste**

L'infrastructure de promotion (checkpoints versionnés, jeux gelés, non-régression, rollback) est nécessaire dès le *premier* réentraînement de J1b — pas au jalon 6. La déplacer dans J0/J1. La consolidation à proprement parler (rééchantillonnage, adaptation des encodeurs) reste en J6, avec la résolution de la contradiction rollback/métrique unique (C12c).

### J7 — LMM/LLM : **différer ; garder le journal**

Aucune dépendance amont. L'ablation prévue est la bonne règle, mais la baseline doit inclure « suggestion aléatoire depuis le même catalogue sûr » — un LLM qui bat « rien » mais perd contre « aléatoire » est un coût net. Le seul livrable immédiat justifié : génération de rapports de session lisibles (outillage).

### J8 — Extension du corps : **conserver**

La règle « chaque actionneur repasse J0/J1 » est exactement la bonne. Ajouter : tout nouvel actionneur est acheté *avec* son retour de position (encodeur ou potentiomètre) — la leçon C5 ne doit pas être réapprise.

### Dépendances corrigées

```text
J0 ──┬── J1a ── J1b ──┬── J2 ── J2.5 ──┐
     │                │                 ├── J5 ── J6(consolidation) ── J7? ── J8
     ├── J3 ──────────┴── J4 ──────────┘
     └── collecte sociale passive (continue dès J0)
J6(infrastructure de promotion) : dès J1b
```

J3 ne dépend pas de J1/J2 : paralléliser.

---

## 7. Baselines obligatoires

Aucun composant appris n'est évalué sans la sienne. Liste opposable :

1. **Persistance** et **modèle linéaire** — toute prédiction sensorimotrice (J1b, J2).
2. **Filtre de Kalman / complémentaire** — estimation d'état (J1a) et prédiction courte (J1b).
3. **GRU/TCN à budget de paramètres égal** — face à tout LNN, 3 graines minimum chacun.
4. **Flux optique / homographie sans apprentissage** — J2.
5. **Embeddings pré-entraînés gelés + kNN** — J3, J4 : la familiarité « gratuite » à battre.
6. **Détecteur de présence trivial** (énergie audio + différence d'images) — J4.
7. **Ordonnanceur aléatoire** et **round-robin + habituation par compteur** — J5.
8. **Contexte brut multimodal** — face à tout latent JEPA, sur chaque sonde (règle 7.4, rendue bloquante ; protocole déjà éprouvé par `docs/research/collision_risk_results.md`).
9. **Sans-LMM** et **suggestion aléatoire du catalogue** — J7.
10. **Seuil ultrason brut** — tout critique de risque (déjà établi : AUROC 0.402, facile à battre, mais à conserver comme plancher).

---

## 8. Expériences falsifiables prioritaires

Classées par rapport information/coût décroissant. F1-F4 tiennent dans une semaine et désamorcent les quatre plus gros risques.

| id | hypothèse testée | coût | confirme si | abandonne si |
|---|---|---|---|---|
| F1 | Le micro webcam préserve l'identité vocale (C8) | 1 h | similarité intra-locuteur stable inter-distances | structure écrasée → micro USB avant J3 |
| F2 | L'angle est estimable par commande+IMU (C5) | 1 j + 5 € | RMS ≤ 2-3°, incertitude couvrante | > 5-8° ou dérive → encodeur permanent |
| F3 | La synchronisation inter-horloges est bornée (C9) | 0.5 j | désalignement < 1 pas de boucle, stationnaire | jitter non stationnaire → protocole de sync actif avant tout multimodal |
| F4 | Le LNN apporte un gain sur GRU/Kalman en J1b (C2) | 2-3 j GPU | gain > dispersion inter-graines, ≥3 graines | sinon LNN différé à J8+ |
| F5 | L'estimateur de progrès distingue apprenable/bruit (C10) | 1-2 j, en replay | classement correct < 10 min de données | LP remplacé par habituation simple |
| F6 | Le latent JEPA bat le contexte brut sur une sonde du nouveau corps (C1) | 2-3 j une fois J2 atteint | latent > brut sur ≥2 sondes, marge > variance | JEPA reste hors architecture |
| F7 | La familiarité capture la personne, pas le décor (C7) | 1 session avec complice | prototype discrimine personnes au même endroit/horaire | requalification en détecteur de présence ; revoir J4 |
| F8 | Une seconde personne réelle est régulièrement disponible (C7) | 0 (logistique) | ≥2 personnes, ≥10 sessions planifiables | J4 requalifié dès maintenant, pas après échec |

---

## 9. Critères d'arrêt et de promotion

### Règles de promotion (durcies depuis §7.4 de `docs/research/jepa_lnn_coupling_strategy.md`)

1. Tout critère de jalon est **pré-enregistré** avant le premier entraînement : métrique, baseline, N graines (≥3 pour modèles entraînés), M sessions (≥3, tenues à part), marge de non-infériorité.
2. Promotion = **conjonction** de tests par capacité (pas de métrique globale, conformément à §12) ; un échec = pas de promotion ; rollback automatique sur cette règle déterministe — ce qui résout la contradiction C12c.
3. Tout composant appris doit battre sa baseline de §7 **au-delà de la dispersion inter-graines**. Un chevauchement min-max face à la baseline = non promu (règle E1, généralisée).
4. La sélection de checkpoint utilise la métrique de la capacité cible, jamais une perte d'entraînement offline (règle E3 : 5/6 sélections divergentes du minimum de RMSE).

### Règles d'arrêt (stop-loss par branche)

- **LNN** : deux tentatives conformes au protocole F4 sans gain → gelé jusqu'à J8.
- **JEPA** : F6 perdu sur le nouveau corps → le JEPA n'entre pas dans l'architecture ; une nouvelle tentative exige un changement structurel documenté (pas « plus d'epochs » — règle déjà actée en §6 du document de couplage).
- **Motivation LP** : F5 perdu ou baseline round-robin indistinguable sur les signatures J5 → ordonnanceur simple adopté définitivement pour la première génération.
- **J4 plein** : F8 non satisfait sous 4 semaines → requalification officielle du jalon (ré-identification), mise à jour de la spécification.
- **LMM** : perd contre la suggestion aléatoire → retiré de la boucle expérimentale, conservé comme générateur de journal.
- Règle générale : un module qui échoue deux fois face à sa baseline triviale est rétrogradé en branche expérimentale et **sort du chemin critique** ; il ne peut y revenir que par une sonde gagnée, pas par décision d'architecture.

---

## 10. Questions non résolues

1. **Combien de personnes distinctes sont réellement accessibles**, à quelle fréquence ? La réponse conditionne J4 plus que tout choix de modèle (F8).
2. **Le MF90 survivra-t-il à des semaines de service ?** Micro-servo à pignons sous charge de capteurs, sollicité en oscillations : usure, jeu croissant (qui invalide lentement la calibration C5), échauffement. Prévoir le suivi du jeu mécanique dans la télémétrie et un servo de rechange.
3. **Budget de stockage brut** : la rétention nécessaire à C12 (ré-encodage des prototypes) est-elle tenable sur des mois ? Chiffrer en Go/semaine au livrable J0.
4. **Qu'est-ce qu'un « événement »** ? La segmentation déclarative (C11) est un palliatif ; la question ouverte 16-style demeure : quel critère de frontière est stable inter-sessions ?
5. **Partition des « familles de situations »** pour le progrès d'apprentissage : codée à la main d'après quoi ? Le catalogue de primitives est un candidat naturel (une famille = une primitive × un contexte grossier), mais cela reste à valider.
6. **L'IMU est-elle solidaire de la tête ?** La spécification (§4.3) pose la question sans y répondre. Toute la chaîne C5/C6 suppose que oui. À trancher physiquement avant J0.
7. **Précision de synchronisation atteignable** entre Windows, WSL2 et Arduino sans matériel dédié — F3 y répondra, mais si la réponse est mauvaise, le contrat multimodal entier doit prévoir des fenêtres d'incertitude temporelle explicites.
8. **Espaces latents par modalité + prédiction croisée vs espace unifié** (question 16.2 de la spécification) : la revue recommande de commencer par les espaces séparés, mais c'est un a priori de simplicité, pas un résultat.

---

## 11. Plan concret des trois prochaines étapes

### Étape 1 — J0 durci (1-2 semaines)

Protocole série binaire unique versionné ; budget de bande passante mesuré ; bus horodaté complet (servo, ultrason, IMU, vidéo, audio) ; recorder append-only + replay déterministe ; test du clap et offsets d'horloges journalisés (F3) ; politique de rétention brute ; collecte sociale passive activée ; trancher la position de l'IMU (question 10.6). Livrable : session de 30 min rejouable + rapport de latence/désalignement.

### Étape 2 — Levée des inconnues matérielles (1 week-end, en parallèle de l'étape 1)

F1 (test AGC du micro webcam — 1 h), F2 (vérité terrain d'angle : AS5600 ou rapporteur de banc — 1 j), décision F8 (disponibilité d'une seconde personne — 0 j, logistique). Trois décisions d'achat/requalification à moins de 30 € au total, qui désamorcent les risques C5, C7 et C8 avant qu'ils ne coûtent des semaines.

### Étape 3 — J1 scindé avec échelle de baselines (2-3 semaines)

J1a : fusion Kalman commande+IMU, incertitude calibrée, validation contre la vérité terrain F2. J1b : prédiction de gyro_z/accel futurs, échelle persistance → linéaire → Kalman → GRU → (LNN si F4 le justifie), critères pré-enregistrés (3 graines, 3 sessions, marges), sélection de checkpoint par la métrique cible. Livrable : décision documentée LNN/GRU/Kalman — la première brique du schéma corporel, posée sur des fondations opposables.

---

## 12. Recommandation finale

**Option B : simplifier avant implémentation.**

Justification du choix contre les alternatives :

- **Pas A** (adopter telle quelle) : la spécification place encore JEPA et LNN sur le chemin critique alors que ses propres règles épistémiques, appliquées aux propres données du projet, les en excluent pour l'instant ; ses critères de jalons ne sont pas quantifiés ; J4 est probablement intestable tel qu'écrit ; J2.5 manque.
- **Pas C** (réviser profondément) : l'ossature est bonne — J0-first, contrat de données, sécurité, règles expérimentales, sommeil/éveil. Les corrections sont des rétrogradations et des durcissements, pas une refonte.
- **Pas D** (abandonner des hypothèses fondatrices) : aucune hypothèse fondatrice n'est falsifiée. L'approche développementale (contingences, habituation, familiarité, mémoire épisodique) reste un programme de recherche cohérent et le corps minimal est un bon instrument pour le tester. Ce qui est falsifié, c'est l'utilité *actuelle* de deux outils particuliers (latent JEPA comme représentation, injection directe dans le LNN) — et la spécification les a déjà partiellement encaissés.

Conditions attachées à B, sans lesquelles la recommandation devient C :

1. LNN, JEPA, motivation LP et LMM sont rétrogradés en branches expérimentales, hors chemin critique, chacune gated par sa sonde (F4, F6, F5, ablation J7).
2. Tous les critères J1-J7 sont réécrits avec graines, sessions et marges pré-enregistrées avant le premier entraînement.
3. J1 est scindé (estimation/prédiction), J2.5 est ajouté, J4 est requalifié si F8 échoue, l'infrastructure de promotion remonte à J1.
4. Les trois tests matériels F1-F3 sont exécutés avant tout investissement logiciel dans J3-J4.

Le principe directeur de cette revue est celui que la spécification énonce elle-même en §15.2 sans en tirer toutes les conséquences : toute architecture complexe est comparée à une baseline simple — *et perd sa place quand elle ne gagne pas*. L'analogie biologique (cervelet, cortex, sommeil) a une valeur heuristique réelle, mais aucun module ne doit rester dans le diagramme parce qu'il ressemble à un organe. Le banc actuel — un cou, quatre capteurs, une pièce, une personne — est petit ; c'est précisément ce qui le rend capable de produire des réponses nettes, à condition de ne pas l'écraser sous une cathédrale de modules avant qu'il ait parlé.

---

## 13. Addendum biomimétique — Ce que la neurologie du vivant impose et ce qu'elle ne justifie pas encore

*Revue complémentaire — Juin 2026*  
*Mandat : répondre à la question « quelles pistes biomimétiques seront impérativement nécessaires pour une intelligence générale, et lesquelles restent spéculatives ? », en appliquant les mêmes règles épistémiques que §12.*

---

### 13.1 Ce que la revue §1–12 implémente déjà sans le nommer

Avant d'ajouter quoi que ce soit, nommer ce qui existe. Plusieurs principes biologiques fondamentaux sont déjà présents dans l'ossature recommandée, sans être explicités :

| Principe biologique | Mécanisme naturel | Équivalent dans la revue |
|---|---|---|
| **Développement séquentiel** | Maturation neurologique : réflexes → motricité → perception → social | L'ordre J0→J1→J2→J2.5→J3→J4→J5→J6 |
| **Habitation neurale** | Décrément des réponses des neurones à stimulus répété | Ordonnanceur round-robin + compteur de décroissance (J5) |
| **Consolidation offline** | Replay hippocampique pendant le sommeil lent (SWS) | Cycle sommeil/éveil, checkpoints versionnés (J6) |
| **Mémoire épisodique → sémantique** | HPC encode les épisodes, néocortex extrait les régularités lentement | Épisodes parquet + prototypes de familiarité |
| **Plasticité contrôlée (Bcl-2, LTP/LTD bornés)** | Synapses ne se modifient pas librement pendant une tâche active | §9.1 : poids non modifiés pendant l'éveil |
| **Fiabilité avant vitesse** | Le développement priorise la précision sensorielle avant la vitesse motrice | J0 (instrumentation) bloquant pour J1 (moteur) |

Ces principes sont corrects et ne doivent pas être rouverts. L'addendum se limite à ce qui manque.

---

### 13.2 La question posée — Intelligence générale : définition opérationnelle

> *« L'intelligence n'est pas la capacité à répondre juste à une solution connue, mais la capacité à trouver des solutions à un problème jamais rencontré. »*

Traduit en critère testable sur ce banc : un agent est généralement intelligent si, placé dans une configuration sensorielle inédite (pièce réarrangée, nouvelle voix, obstacle imprévu), il produit une réponse *fonctionnellement adaptée* — non par mémorisation d'un stimulus similaire, mais par recomposition de mécanismes acquis.

Ce critère est différent de la performance à J4 (ré-identification) ou J5 (habituation). Il correspond à J2.5 généralisé : savoir ce qui vient de soi vs. ce qui vient du monde, et agir en conséquence dans une configuration non vue.

---

### 13.3 Trois principes biomimétiques impératifs — Classement opposable

Le classement suit la même logique que §3 : format **affirmation / pourquoi impératif / test le moins coûteux / confirmé si / abandonné si**.

#### B1 — Copie d'efférence / décharge corollaire (→ J2.5, J1b)

**Ce que c'est.** Quand un animal initie un mouvement, une copie de la commande motrice est envoyée simultanément aux aires sensorielles pour prédire les conséquences sensorielles attendues. Le résidu entre cette prédiction et l'observation réelle est appelé **réafférence** : c'est le signal « externe ». Sans ce mécanisme, un animal ne peut pas distinguer si le monde a bougé ou si c'est lui. Chez les téléostéens, ce circuit est littéralement codé dans le cervelet ; chez l'humain, c'est le modèle interne du cervelet de Wolpert (MOSAIC, 1998) et la décharge corollaire du cortex moteur.

**Pourquoi impératif.** J2.5 (jalon manquant ajouté par §6) exige précisément cette capacité : « le résidu pendant un mouvement propre doit rester bas ; un changement externe doit produire un résidu élevé *y compris pendant un mouvement propre simultané* ». Ce critère est inatteignable sans un module de prédiction des conséquences sensorimotrices. Le Kalman estimateur de J1a est une condition nécessaire mais pas suffisante : il estime l'état courant, il ne prédit pas l'état futur *conditionné à une commande donnée*.

**Pourquoi pas les autres approches biologiques d'abord.** La computation dendritique, les réseaux gliaux, la bioélectricité léviniène — aucune ne répond à la question « est-ce moi ou le monde ? » que J2.5 pose. La copie d'efférence est le seul mécanisme qui le résout, et c'est le plus ancien de l'évolution (présent chez les poissons osseux, ~400 Ma).

**Test le moins coûteux.** Sur replay J1b : entraîner un prédicteur linéaire `commande → Δgyro_z prédit(t+100ms)`. Pendant les sessions de test : le résidu `|Δgyro_z observé − prédit|` doit être faible lors des mouvements propres (erreur ≤ modèle de persistance) et élevé lors d'un perturbateur externe (complice qui tape sur le banc). AUROC de détection d'événement externe cible > 0.85, sur au moins 3 sessions.

**Confirmé si** le résidu distingue mouvement propre et perturbation externe avec AUROC > 0.85 pour le modèle linéaire (baseline copie d'efférence). La présence d'un GRU ou d'un LNN n'est alors justifiée que s'il améliore ce critère au-delà de la dispersion inter-graines.

**Abandonné (réformé) si** le Kalman seul atteint le critère B1 sans modèle de prédiction conditionnel explicite : dans ce cas, la copie d'efférence est implicitement couverte par l'estimateur, et le module séparé est superflu — mais J2.5 reste un jalon.

**Implémentation minimale dans le dépôt.** Un seul fichier, dérivé du Kalman J1a :

```python
# learning/efference_copy.py
class EfferenceCopy:
    """
    Prédit les conséquences proprioceptives d'une commande servo.
    Baseline linéaire : commande -> delta_gyro_z prédit.
    Conforme à la règle §15.6 : la commande appliquée, pas demandée.
    """
    def __init__(self):
        self.gain = 0.0   # appris par régression linéaire sur J1b
        self.bias = 0.0

    def predict(self, applied_command_delta_deg: float) -> float:
        return self.gain * applied_command_delta_deg + self.bias

    def residual(self, predicted: float, observed: float) -> float:
        return abs(observed - predicted)

    def fit(self, commands: np.ndarray, gyro_deltas: np.ndarray):
        # Régression OLS, aucun GPU requis
        A = np.column_stack([commands, np.ones_like(commands)])
        result = np.linalg.lstsq(A, gyro_deltas, rcond=None)
        self.gain, self.bias = result[0]
```

Aucun réseau de neurones, aucune dépendance GPU, compatible avec la contrainte §5.1 de causalité (commande appliquée, pas demandée).

---

#### B2 — Inférence active comme cadre de curiosité (→ J5, alternative à la formule à 7 termes)

**Ce que c'est.** L'inférence active (Friston, 2010) formalise le comportement d'un agent comme minimisation de l'*énergie libre espérée future*, qui se décompose en deux termes : (a) **valeur épistémique** = réduction attendue d'incertitude sur des variables non encore observées (= curiosité vers ce qu'on ne sait pas encore) ; (b) **valeur pragmatique** = atteindre des états préférés (= survie, homéostasie). La clé est que la curiosité n'est pas définie par la surprise actuelle mais par la *réduction d'incertitude attendue si on agissait*. Un canal bruité (télévision) a une surprise haute mais une valeur épistémique nulle car aucune action ne réduirait son incertitude.

**Pourquoi impératif.** La revue §3 (C10) identifie exactement ce problème : « la même chose que les ticks autocorrélés d'E1, en pire ». La formule à 7 termes tente d'approximer ce que l'inférence active formalise avec 2 termes. Elle évite aussi le piège de la « télévision bruyante » que la revue mentionne explicitement.

**Pourquoi maintenant et pas plus tard.** J5 est le jalon de la curiosité. Si la baseline round-robin+habituation y suffit, tant mieux. Mais le risque C10 (estimateur de progrès plus bruité que le signal) est réel sur un seul DDL dans une pièce statique. L'inférence active fournit le cadre le moins complexe qui réponde *théoriquement* au problème avant qu'il apparaisse empiriquement.

**Version opérationnelle minimale.** Remplacer la formule à 7 termes par :

```text
intérêt(primitive, contexte) =
    gain_contrôlabilité(primitive, contexte)     # B ← mesurable par permutation d'actions
  × progrès_prédiction_récent(primitive)         # simplification de C10 : fenêtre glissante
  - habituation(primitive)                       # compteur de décroissance, déjà prévu
  - risque_matériel(contexte)                    # seuil fixe, §11.1
```

`gain_contrôlabilité` = différence entre l'erreur de prédiction *avec* l'action et l'erreur *avec une action permutée aléatoire* sur les 10 dernières exécutions. Zéro si le bruit domine, positif si l'action fait une différence mesurable.

**Test le moins coûteux.** F5 de la revue, avec une extension : injecter un canal de bruit pur *et* un canal apprenable *et* un canal maîtrisé (sinus connu). L'ordonnanceur doit : saturer rapidement le canal maîtrisé (habituation), ignorer le bruit (contrôlabilité nulle), persister sur l'apprenable. Baseline : round-robin+habituation seul. Confirmé si la formule réduite (2 termes actifs + habituation + risque) bat le round-robin sur ces trois signatures en < 20 min de replay. Abandonné si round-robin est indistinguable : adopter round-robin définitivement pour la première génération, la formule réduite en branche expérimentale.

**Ce qui reste spéculatif de l'inférence active.** La version complète de Friston suppose un générateur de modèle bayésien hiérarchique — incompatible avec la recommandation B. Seul le principe de *contrôlabilité comme filtre de curiosité* est extrait ici. Le reste (POMDP, distributions conjuguées, minimisation de l'énergie libre en temps continu) est différé à J5+ si et seulement si la version minimale prouve un gain.

---

#### B3 — Décomposition ventrale/dorsale de la vision (→ J2, J4)

**Ce que c'est.** Le système visuel biologique sépare systématiquement deux voies :
- **Voie dorsale** (« où / comment ») : mouvement, flux optique, relations spatiales, guidage moteur. Rapide, peu invariante à l'identité.
- **Voie ventrale** (« quoi ») : forme, couleur, texture, identité de l'objet ou de la personne. Plus lente, invariante aux transformations.

Ces deux voies ont des buts différents, des fréquences différentes, et alimentent des jalons différents.

**Pourquoi impératif.** La revue recommande « encodeur pré-entraîné gelé + flux optique » pour la vision, ce qui est juste, mais sans distincter à quoi chaque voie sert. Si les deux flux sont mélangés dans un vecteur unique, J2 (contingences visuelles — *comment* ma rotation change la scène) est contaminé par J4 (familiarité — *qui* est là). Les deux tâches ont des propriétés opposées : J2 bénéficie de la vitesse et de la sensibilité au mouvement, J4 bénéficie de l'invariance et de la stabilité sur des jours.

**Version opérationnelle minimale.** Deux encodeurs gelés, deux canaux séparés dans le bus d'événements :

| Canal | Encodeur recommandé | Fréquence | Alimente |
|---|---|---|---|
| **Dorsal** | Flux optique (Farnebäck, déterministe, 0 GPU) | 10–30 Hz | J2, J2.5 (résidu d'efférence visuel) |
| **Ventral** | DINOv2-Small ViT (gelé, patch features ou CLS token) | 5–10 Hz | J3 (association audio-vidéo), J4 (familiarité) |

Le flux optique est une baseline déterministe (aucun entraînement). DINOv2 est un encodeur gelé — conforme à §7.2 (« encodeurs pré-entraînés gelés acceptés comme priors »). Aucun réseau à entraîner pour implémenter B3.

**Règle d'or.** Les deux canaux ne sont *jamais* concaténés avant J4. La question ouverte 16.2 de la spécification (« espaces par modalité + prédiction croisée vs espace unifié ») est résolue par défaut par la séparation — l'espace unifié n'est introduit que si une sonde spécifique le justifie (voir règle §13.5).

**Test le moins coûteux.** J2 baseline géométrique (déjà requise par §6 de la revue) : un prédicteur de flux optique pur (homographie commande → décalage image) vs. un modèle qui utilise le flux optique calculé. Le modèle appris doit battre la géométrie ; le canal DINOv2 ne doit pas améliorer J2 (sinon il encode du mouvement résiduel, ce qui invalide la séparation).

**Abandonné si** DINOv2 améliore significativement J2 : la séparation fonctionnelle n'est pas réalisée par ces encodeurs sur ce matériel, et il faut trouver un encodeur dorsal plus pur ou accepter l'espace mixte.

---

### 13.4 Classement complet des pistes biomimétiques

Format : **Impérative / Conditionnelle / Spéculative / Hors périmètre actuel**.

| Piste | Statut | Jalon | Condition d'entrée |
|---|---|---|---|
| Copie d'efférence (B1) | **Impérative** | J1b / J2.5 | Aucune — implémentation linéaire gratuite |
| Inférence active minimale (B2) | **Impérative** | J5 | F5 : confirme le gain sur round-robin |
| Décomposition ventrale/dorsale (B3) | **Impérative** | J2 / J4 | Aucune — encodeurs gelés déterministes |
| GRU comme belief state (B4) | **Conditionnelle** | J1b | F4 : bat Kalman + linéaire au-delà dispersion |
| Prototypes à décroissance exponentielle (B5) | **Conditionnelle** | J4 | Bat kNN gelé sur J4 avec ≥2 personnes, ≥10 sessions |
| JEPA multimodal (branche expérimentale) | **Conditionnelle** | Post-J2 | F6 : bat contexte brut sur ≥2 sondes |
| LNN (branche expérimentale) | **Conditionnelle** | Post-J1b | F4 : bat GRU ET Kalman |
| Computation dendritique | **Spéculative** | J8+ | Seulement si GRU plafonné et J8 l'exige |
| Inférence active complète (POMDP/FEP) | **Spéculative** | Post-J5 | Si version minimale B2 prouve un gain et atteint ses limites |
| Réseaux gliaux | **Hors périmètre** | — | Mécanisme non traduisible en ingénierie |
| Cognition céphalopode | **Hors périmètre** | J8 (second effecteur) | Pertinent si bras ajouté ; rediscuter à J8 |
| Bioélectricité (Levin) | **Hors périmètre** | — | Aucune implémentation disponible |

---

### 13.5 Plan d'intégration dans les jalons existants

Aucun jalon n'est modifié. B1–B3 s'intègrent comme livrables supplémentaires dans les jalons existants.

#### J1b — Ajouter l'expérience de copie d'efférence (B1)

Livrable additionnel : entraîner `EfferenceCopy` (régression linéaire, voir §13.3) sur les données J1b, mesurer le résidu, pré-enregistrer le critère AUROC J2.5 avant toute autre utilisation des données.

L'infrastructure est gratuite : les logs J1b contiennent déjà commandes appliquées et gyro_z ; une régression OLS suffit.

#### J2 — Ajouter les deux canaux visuels séparés (B3)

Livrables additionnels dans le bus d'événements :
- `OpticalFlowSample` (Farnebäck sur frames consécutives, magnitude + direction moyennée par région)
- `VisualAppearanceSample` (DINOv2-Small CLS token, 5 Hz)

Ces deux types de messages sont distincts, horodatés séparément, et ne sont jamais concaténés à ce stade.

Baseline J2 obligatoire (déjà requise par §6) : prédicteur homographie seul. Confirmé si le modèle utilisant `OpticalFlowSample` le bat. Le `VisualAppearanceSample` ne doit *pas* améliorer J2.

#### J2.5 — Le jalon manquant gagne un critère précis grâce à B1

Reformulation du critère J2.5 (§6 de la revue) avec la copie d'efférence explicite :

*Critère pré-enregistré :* sur ≥3 sessions (tête immobile + tête en mouvement propre + complice introduisant un perturbateur), le résidu `EfferenceCopy.residual()` distingue mouvement propre et événement externe avec **AUROC ≥ 0.80** dans les deux conditions. Baseline : seuil fixe sur l'énergie gyroscopique brute.

Ce critère est falsifiable, ne nécessite pas de réseau entraîné, et peut être validé en replay.

#### J4 — Introduire les prototypes à décroissance exponentielle (B5, conditionnelle)

Seulement si le kNN gelé de §5 (architecture minimale recommandée) ne satisfait pas le critère J4. Si la baseline kNN gelé passe J4, B5 entre en branche expérimentale et mesure un gain marginal, pas une nécessité.

Formule d'update online (O(1) par étape) :
```python
prototype = (1 - alpha) * prototype + alpha * new_embedding
# alpha = 0.01 : ~100 observations pour 63% de mise à jour
# Pas de GPU requis ; tourne en temps réel sur CPU
```

#### J5 — Remplacer la formule à 7 termes par la version B2

Ordre d'essai :
1. Round-robin + habituation par compteur (baseline §7.7)
2. + contrôlabilité estimée (2 termes actifs + habituation + risque, version B2)
3. LN si et seulement si F5 justifie un terme de plus

---

### 13.6 Ce que cette revue ne recommande pas — et pourquoi

**Mémoire sémantique FAISS au-delà de J4.** La revue §3 (C12) identifie correctement que les prototypes dépendent de l'espace de l'encodeur versionné. Ajouter FAISS avant que l'encodeur DINOv2 ne soit validé (J4) crée exactement le problème C12 : une invalidation silencieuse à chaque promotion d'encodeur. FAISS entre seulement après que les prototypes d'encodeur gelé ont démontré leur utilité et que la politique de rétention brute est opérationnelle.

**Belief states récurrents avant J1b.** La revue §3 (C2) montre que le LNN n'a pas encore battu les alternatives simples. Un GRU récurrent (B4) ne doit pas non plus être introduit avant que son utilité soit démontrée sur les données J1b réelles. La copie d'efférence linéaire (B1) fournit une capacité de belief state partielle gratuite.

**Inférence active complète.** La version Friston complète assume un modèle génératif bayésien — incompatible avec la recommandation B. La version B2 extrait le seul terme utile (contrôlabilité) sans l'appareillage mathématique complet.

---

### 13.7 Réponse synthétique à la question initiale

> *Quelles pistes biomimétiques seront impérativement implémentées dans les futurs modèles qui permettront l'émergence d'une vraie intelligence générale ?*

Réponse opérationnelle, filtrée par les règles de ce projet :

**Trois principes sont nécessaires et présentement implémentables :**

1. **La copie d'efférence** — distinguer ce qu'on cause de ce qui arrive. Sans elle, J2.5 est indéfinissable, et toute représentation du monde mélange l'agent et l'environnement. C'est le mécanisme le plus ancien de l'évolution et le plus ignoré par le deep learning actuel. Il s'implémente avec une régression linéaire.

2. **La contrôlabilité comme filtre de curiosité** — chercher l'apprenable, pas le surprenant. Sans ce filtre, la curiosité optimise le bruit. C'est le principe que l'inférence active formalise et que la revue §3 (C10) identifie comme risque sans en nommer le remède.

3. **La séparation ventrale/dorsale de la perception** — distinguer ce qui bouge de ce qui identifie. Sans elle, les jalons J2 (contingences) et J4 (familiarité) se contaminent mutuellement. Deux encodeurs gelés suffisent.

**Ce qui ne sera impératif que plus tard, conditionné à une sonde gagnée :**
- Belief states récurrents (GRU/LNN) — si le Kalman + efférence sature avant J5
- JEPA multimodal — si les encodeurs gelés plafonnent pour la familiarité
- Mémoire sémantique FAISS — si les prototypes par encodeur gelé saturent à J6

**Ce qui restera spéculatif dans la durée du projet :**
- Computation dendritique, réseaux gliaux, bioélectricité — aucun mécanisme traduisible. Ces pistes ont une valeur heuristique réelle pour *comprendre* pourquoi certaines propriétés émergent, pas pour les ingénier dans l'immédiat.

La biologie est utile à ce projet comme *source de contraintes* (développement séquentiel, habituation, sommeil) et de *mécanismes précis* (copie d'efférence, contrôlabilité). Elle n'est pas utile comme *liste de modules à implémenter* — exactement le piège que la revue §12 désigne sous le nom de « cathédrale de modules ».
