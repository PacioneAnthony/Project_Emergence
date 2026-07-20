# Émergence - Registre des décisions

## D-001 - Pivot développemental

Date: 2026-06-11  
Décision: la navigation 2D n'est plus l'objectif principal; le projet se recentre sur les contingences sensorimotrices, la familiarité, l'habituation et l'apprentissage cumulatif.  
Statut: acceptée  
Motif: divergence entre l'optimisation du contrôleur de navigation et l'objectif final du robot.  
Données utilisées: campagnes JEPA-LNN, E1-E3, S4 et critique de collision.  
Avis Codex: pivot recommandé.  
Avis Claude: spécification cohérente mais à simplifier avant implémentation.  
Arbitrage Anthony: pivot demandé et spécification lancée.  
Conséquences: la navigation devient une branche historique et une future compétence possible.  
Condition de réouverture: ajout de la locomotion au jalon J8.

## D-002 - Architecture minimale avant modules biologiquement inspirés

Date: 2026-06-11  
Décision: LNN, JEPA multimodal, motivation par learning progress et LMM sortent du chemin critique de première génération.  
Statut: acceptée  
Motif: absence de gain démontré face aux baselines simples et recommandation de la revue contradictoire.  
Données utilisées: `DEVELOPMENTAL_ARCHITECTURE_REVIEW.md`, `docs/research/collision_risk_results.md`, résultats E1 et S4.  
Baseline: Kalman/complémentaire, modèles linéaires, GRU, contexte brut, embeddings gelés+kNN, round-robin+habituation.  
Avis Codex: accord; les modules complexes doivent regagner leur place par des sondes.  
Avis Claude: recommandation B, simplifier avant implémentation.  
Arbitrage Anthony: avis Codex et Claude validé le 2026-06-11.  
Conséquences: J0 puis J1a/J1b avec échelle de baselines; ajout de J2.5.  
Condition de réouverture: succès des expériences F4, F5, F6 ou ablation J7 correspondantes.

## D-003 - Gouvernance du projet

Date: 2026-06-11  
Décision: Anthony gère le hardware et arbitre; Codex assure l'implémentation et les expériences; Claude fournit des revues ponctuelles aux portes de décision.  
Statut: acceptée  
Motif: conserver une boucle d'ingénierie rapide tout en réservant les analyses Claude coûteuses aux décisions structurantes.  
Données utilisées: besoins exprimés par Anthony et historique du projet.  
Avis Codex: protocole formalisé dans `COLLABORATION_PROTOCOL.md`.  
Avis Claude: non consulté sur la gouvernance.  
Arbitrage Anthony: organisation demandée.  
Conséquences: les documents versionnés deviennent la mémoire partagée; chaque session substantielle produit un handoff.  
Condition de réouverture: inefficacité constatée du protocole pendant deux jalons consécutifs.

## D-004 - Délégation des décisions techniques

Date: 2026-06-11  
Décision: Anthony intervient principalement comme technicien du banc d'essai et validateur des achats ou modifications matérielles. Codex reçoit l'autonomie sur les choix logiciels, l'architecture technique, les protocoles expérimentaux, les baselines et l'implémentation. Claude intervient comme revue contradictoire aux portes techniques importantes préparées par Codex.  
Statut: acceptée; remplace la répartition d'autorité technique de D-003.  
Motif: Anthony ne souhaite pas devoir traduire les étapes techniques ni arbitrer des choix logiciels ou architecturaux hors de son rôle matériel.  
Données utilisées: demande explicite d'Anthony du 2026-06-11.  
Baseline: fonctionnement antérieur où Anthony devait arbitrer des décisions techniques et deviner quelle instruction donner pour poursuivre.  
Avis Codex: recommandé; la responsabilité technique doit appartenir aux agents qui produisent et évaluent les preuves.  
Avis Claude: non consulté; il s'agit d'une règle de gouvernance fixée par Anthony.  
Arbitrage Anthony: délégation explicite des choix logiciels et architecturaux à Codex et Claude.  
Conséquences: Codex poursuit le jalon actif sans attendre une validation technique d'Anthony. Il ne sollicite Anthony que pour une action physique, un achat, une question de sécurité, des données humaines, une contrainte personnelle ou un changement de l'objectif général. Les promotions et abandons techniques suivent les critères pré-enregistrés, avec revue Claude lorsqu'elle est prévue.  
Condition de réouverture: Anthony souhaite reprendre une catégorie de décisions ou constate que l'autonomie technique éloigne le projet de son objectif général.

## D-005 - Servo passif et remplacement du banc v0.1

Date: 2026-06-12  
Décision: le servo reste détaché au démarrage et se détache immédiatement en cas d'arrêt d'urgence ou de perte de communication. Aucun nouvel essai moteur n'est exécuté sur le montage v0.1; la qualification mécanique et la session J0 de 30 minutes attendent le banc v1.0 décrit dans `BENCH_DESIGN.md`.  
Statut: acceptée sous l'autorité technique déléguée par D-004.  
Motif: Anthony signale un assemblage direct sur l'axe, fragile et tremblant. Le rapport mécanique de la session `j0-20260612T123848.687322Z-afac9e86` mesure des ratios de stabilisation gyroscopique de 5,22 à 13,45 par rapport au repos, au-dessus de la limite provisoire de 3,0.  
Données utilisées: observation d'Anthony, IMU de la session servo, conception mécanique `BENCH_DESIGN.md`.  
Avis Codex: le v0.1 suffit pour valider l'acquisition mais pas pour une collecte longue ni pour étudier le contrôle moteur.  
Avis Claude: conception proposée où le servo entraîne et la structure porte, avec piste circulaire, jupe de centrage et gestion du faisceau.  
Arbitrage Anthony: remplacement mécanique déjà engagé avec Claude et impression 3D prévue.  
Conséquences: firmware patch 2 à flasher sur le nouveau banc; qualification comparative par `j0 mechanics`; session longue différée sans bloquer la préparation logicielle.  
Condition de réouverture: preuve qu'un mouvement vers le neutre est matériellement plus sûr que le détachement immédiat sur une future plateforme.

## D-006 - Backend de simulation 3D MuJoCo en piste parallèle

Date: 2026-07-15  
Décision: création du paquet `sim3d/`, backend MuJoCo exposant exactement le contrat observation/action de `sim2d`, comme piste parallèle pendant la conception mécanique du banc v1.0. Phase A (robot mobile, viewer, validation par rollout) livrée; Phase B (jumeau numérique de la tête du banc avec rendu caméra) et Phase C (vectorisation massive) restent conditionnelles.  
Statut: acceptée.  
Motif: la modélisation Onshape du banc bloque temporairement Anthony; un environnement 3D visualisable prépare la vision (le banc est une tête caméra rotative), accélère les futures campagnes d'évaluation et pourra pré-valider la mécanique du banc. Ceci ne rouvre pas D-001: la navigation 2D/3D reste une branche historique et outillage de recherche.  
Données utilisées: `docs/research/SIMULATION.md` (section sim3d), rollouts `lnn_dagger_002_sim3d_rollout_001` (1,20% de ticks en nominal contre 1,21% re-mesuré en 2D) et `lnn_dagger_002_sim3d_rollout_randomized_001` (0,98%).  
Baseline: `sim2d` conservé comme banc rapide de référence; MuJoCo retenu contre Isaac Lab (trop lourd), Genesis (immature) et Unity/Godot (intégration PyTorch coûteuse).  
Avis Codex: non consulté sur cette session; le code suit les conventions existantes (contrat `common/types.py`, logger CSV, protocoles de rollout).  
Avis Claude: recommandation MuJoCo et implémentation Phase A réalisées en session Claude Code du 2026-07-15.  
Arbitrage Anthony: piste parallèle et Phase A validées le 2026-07-15.  
Conséquences: `requirements/research.txt` ajoute la dépendance `mujoco`; `learning/rollout_lnn.py` gagne l'option `--backend sim3d`; les tests `tests/test_sim3d.py` se désactivent proprement sans MuJoCo.  
Condition de réouverture: la maintenance du double backend coûte plus que sa valeur, ou la Phase B démontre qu'un autre moteur est nécessaire pour le rendu caméra.

## D-007 - Curiosité graduelle sans niveaux annotés

Date: 2026-07-17
Décision: conserver le learning progress régional rejeté uniquement comme baseline
reproductible et développer, en branche expérimentale, un ordonnanceur continu où la
difficulté est relative aux compétences courantes. Les niveaux de difficulté conçus par
l'expérimentateur ne peuvent servir que d'oracle caché dans un test contrôlé, jamais
d'entrée de la politique.
Statut: acceptée sous l'autorité technique de D-004; ne modifie pas la rétrogradation D-002.
Motif: `active_exploration_001` montre qu'une partition arbitraire de huit angles concentre
les données sans gain dans un monde homogène. L'analogie développementale pertinente est
un refuge initial puis une frontière apprenable qui se déplace avec la maîtrise, pas une
recherche de surprise maximale.
Données utilisées: `docs/research/active_exploration_probe.md`, ratios finaux `0.747`
contre `0.732`, MAE angle `22.8°` contre `20.8°`, entropies `0.794` contre `0.994`.
Baseline: babbling uniforme et round-robin+habituation; learning progress régional comme
ablation historique.
Implémentation: `learning/developmental_curiosity.py`, intégration conditionnelle dans
`learning/active_exploration.py`, tests synthétiques et protocole
`docs/research/developmental_curiosity_probe.md`.
Conséquences: aucun run GPU long n'est lancé avant pré-enregistrement du banc discriminant;
aucune promotion dans le chemin critique sans gain tenu à part, évitement du bruit,
couverture suffisante et réplication sur au moins trois graines.
Condition de réouverture: la variante continue ne bat pas round-robin+habituation, son
incertitude bootstrap est mal calibrée, ou son coût excède son gain mesuré.

Résultat de réouverture (2026-07-17): DC-001 déclenche la condition. La variante continue
évite le bruit (`4.66%` du budget contre `22.74%` pour le babbling) mais perd fortement sur
l'apprentissage structuré (`0.253` contre `0.113`) et ne satisfait la progression graduelle
que sur 11/20 graines. Le bootstrap de la surface d'erreur confond connaissance d'une
erreur élevée et preuve qu'elle est irréductible. D-007 reste le principe de recherche,
mais son implémentation DC-001 est rejetée et demeure hors chemin critique sous D-002.

## D-008 - Simulation probante avant reprise du banc physique

Date: 2026-07-20
Décision: suspendre le chemin critique matériel J0/J1 et faire de la validation en
simulation la priorité active. Le banc physique n'est réintroduit qu'après émergence de
comportements robustes, prometteurs et répliqués dans des environnements simulés de
réalisme croissant.
Statut: accepté par arbitrage explicite d'Anthony; remplace l'ordre opérationnel de D-005
sans lever ses règles de sécurité.
Motif: un mécanisme qui n'émerge pas dans un environnement simplifié et contrôlable a peu
de chances d'apparaître sur un banc réel plus bruité, coûteux et difficile à diagnostiquer.
Baseline de preuve: protocoles pré-enregistrés, baselines simples, plusieurs graines,
environnements tenus à part, robustesse au bruit et réplication indépendante.
Conséquences: aucune action physique, achat, flash ou essai servo n'est attendu. La
progression active devient abstraction contrôlée, monde continu non annoté, jumeau visuel,
domain randomization, puis seulement transfert physique. Le matériel existant est conservé
mais ne bloque plus l'avancement logiciel.
Condition de réouverture: au moins un comportement développemental central bat ses
baselines, généralise hors distribution et se réplique sur une seconde série de graines;
la décision de retour au matériel reste à Anthony.

## D-009 - Non-promotion de regional_lp_gain sur apprenant visuel réel

Date: 2026-07-20
Décision: ne pas promouvoir `regional_lp_gain` comme ordonnanceur développemental du
JEPA visuel après TV-001; geler l'implémentation et les graines, sans retouche post hoc.
Statut: acceptée par application des règles pré-enregistrées de TV-001 sous D-004.
Motif: TV-H1 et TV-H2 sont rejetées dans une campagne appariée interprétable. L'actif
dégrade l'erreur structurée de 2,80 % en moyenne et alloue 28,28 % du budget à la
télévision contre 25,19 % pour babbling.
Données utilisées: `docs/research/tv_real_jepa_001_results.md`, 12 paires 9301..9312,
calibration 9201..9203, statistiques exactes/BCa/Holm et garde-fous tous passés.
Baseline: babbling uniforme avec mêmes modèles, pièces, ancres, images, décisions et
pas d'optimisation.
Avis Codex: non-promotion obligatoire; la baisse initiale d'erreur dans les cellules TV
peut représenter l'apprentissage légitime d'une invariance au bruit, ce qui rend le
diagnostic causal ambigu sans invalider le verdict pré-enregistré.
Avis Claude: revue de résultats demandée avant choix de la suite.
Arbitrage Anthony: aucun arbitrage technique demandé; D-004 s'applique. Une décision
d'objectif général ne sera demandée que si la revue oppose durablement J6 à un nouveau
diagnostic de motivation.
Conséquences: `regional_lp_gain` reste une baseline historique, pas un mécanisme par
défaut. Aucun réglage sur TV-001. Étape 2/J6 non lancée avant revue du diagnostic et de
l'ordre expérimental.
Condition de réouverture: hypothèse nouvelle pré-enregistrée distinguant progrès
d'invariance et attraction pour l'aléatoire, sur graines vierges, ou preuve que la
question mémoire J6 peut avancer indépendamment sans réintroduire l'ordonnanceur.

Résultat de revue (2026-07-20): Claude confirme « J6 D'ABORD ». TV-001 est décisive
sur la non-promotion et indécise sur la cause; cette cause ne conditionne ni les
baselines ni les métriques J6 puisque les trois conditions collectent par babbling.
La sonde encodeur gelé/plastique reste dormante. Codex gèle J6-R001 avant implémentation
et soumet son pré-enregistrement à revue contradictoire.

## D-010 - Non-promotion des ordonnanceurs de consolidation J6-R001

Date: 2026-07-20
Décision: ne promouvoir ni `uniform_replay` ni `error_prioritized_replay` après J6-R001;
geler les mondes A/B/C, les graines 10301..10312, les seuils et les artefacts, sans
retuning post hoc.
Statut: acceptée par application des règles pré-enregistrées sous D-004; revue Claude
des résultats: **AUTORISER**, aucune correction bloquante et aucune promotion.
Motif: le replay uniforme démontre une valeur de rétention réelle sur B, où la garde
d'oubli passe (réduction relative `0,1506`, `6/6` bins, p Holm `0,000488`), mais H3
échoue. À ratio 50/50 et calcul fixe, uniform et priorisé dégradent le pire bin courant
C de `14,25 %` et `13,47 %`, au-dessus de la limite régionale de `10 %`; leur
non-infériorité face à naïf n'est pas établie après Holm. A est non interprétable sous
B1, pas un rejet du replay. H2 ne démontre aucune valeur ajoutée de la priorité et la
garde TV confirme que le piège TV-001 ne s'est pas reproduit.
Données utilisées: `docs/research/j6_replay_001_results.md`,
`docs/research/j6_replay_001_analysis.json`, 36 runs appariés 10301..10312 et
`docs/research/j6_replay_001_results_review.md`.
Baseline: adaptation naïve; uniform 50/50 comme référence de rétention; priorité par
erreur comme mécanisme candidat.
Avis Codex: non-promotion obligatoire; le blocage décisif est la plasticité H3, non
l'absence de valeur de la mémoire.
Avis Claude: campagne intègre, calculs concordants, verdict AUTORISER et aucune
promotion.
Arbitrage Anthony: aucun arbitrage technique demandé; D-004 s'applique.
Conséquences: toute reprise utilise une hypothèse, un pré-enregistrement, des mondes et
des graines nouveaux. Les résultats J6-R001 restent des historiques probants.
Condition de réouverture: aucune pour J6-R001. Seule une nouvelle campagne indépendante
peut tester un autre compromis rétention/plasticité.

## D-011 - Résoudre le compromis rétention/plasticité avant la réafférence

Date: 2026-07-20
Décision: poursuivre l'option A avec J6-AR001, une nouvelle campagne sur mondes D/E/F et
graines vierges, avant de passer à l'étape 3 de réafférence. Le candidat est un replay
uniforme à fraction adaptative, commandé par une banque de suivi séparée; il est comparé
à naïf et au replay uniforme 50/50 exact.
Statut: pré-enregistrement soumis à revue contradictoire avant implémentation ou calcul.
Motif: J6-R001 a déjà établi que la répétition protège un acquis qui s'oublie et que le
coût décisif est H3. Résoudre ce compromis directement est une progression plus
informatrice que changer de question maintenant. Le mécanisme reste minimal: il ne
priorise aucun épisode et ne reçoit aucune information refusée aux baselines.
Données utilisées: acquis gelés de D-010 et recommandations de
`docs/research/j6_replay_001_results_review.md`.
Baseline: adaptation naïve et uniform 50/50, mêmes corpus, modèles, banques de suivi,
évaluations et nombre de gradients.
Avis Codex: option A recommandée; elle teste le problème exact exposé par H3 sans
ressusciter la priorité par erreur rejetée ni la famille motivationnelle fractionnelle.
Avis Claude: à obtenir sur le pré-enregistrement J6-AR001 avant toute implémentation.
Arbitrage Anthony: non requis; choix technique sous D-004, sans changement de l'objectif
général.
Conséquences: l'étape 3 reste la suite par défaut après clôture de J6-AR001, quel que
soit son verdict, sauf nouvelle preuve exigeant une réplication de consolidation.
Condition de réouverture: revue préalable défavorable, impossibilité de garantir
l'absence de fuite entre suivi et décision, ou campagne non interprétable sur les deux
domaines anciens.

## D-012 - Clôture technique sans résultat de J6-AR001

Date: 2026-07-20
Décision: clore J6-AR001 sans analyse scientifique, sans promotion et sans reprise sur
11301..11316 après l'arrêt automatique au plafond gelé de 75 minutes.
Statut: arrêt technique pré-enregistré sous D-004.
Motif: le runner a atteint la limite pendant `adaptive_replay` de 11313. Douze triplets
11301..11312 sont complets; 11313 contient seulement `naive` et `uniform_50`; 11314 à
11316 sont restées fermées. Le plan exige n=16/48 runs: toute analyse à n=12 ou toute
extension du plafond après ouverture des graines serait post hoc.
Données utilisées: métadonnées locales résumables de
`data/processed/experiments/j6_adaptive_replay_001/`, 38 runs complets, 73,22 minutes
enregistrées plus le fragment interrompu, et `j6_adaptive_replay_001_technical_stop.md`.
Baseline: protocole J6-AR001 amendé C1–C4; aucune comparaison de résultats n'est faite.
Avis Codex: préserver l'arrêt est plus important que récupérer une campagne incomplète;
l'hypothèse adaptative reste non testée, ni confirmée ni rejetée.
Avis Claude: revue pré-calcul favorable après C1–C4; aucune revue de résultats possible
faute de campagne complète.
Arbitrage Anthony: non requis; application mécanique du plafond sous D-004.
Conséquences: aucun run supplémentaire, aucune analyse des portes et aucune promotion.
Les artefacts partiels sont conservés localement comme audit technique. La règle de
clôture J6-AR001 rend la réafférence étape 3 active.
Condition de réouverture: aucune pour J6-AR001; une reprise de consolidation exigerait
une hypothèse, des graines et un pré-enregistrement nouveaux.

## D-013 - Passage à la réafférence visuelle

Date: 2026-07-20
Décision: après la clôture J6-AR001, passer à l'étape 3 du brief avec REF-001: tester si
le résidu d'un JEPA conditionné par l'action détecte les changements externes tout en
expliquant les changements auto-produits.
Statut: pré-enregistrement soumis à revue contradictoire avant implémentation ou calcul.
Motif: le point 2 de la définition du succès exige de séparer changement auto-produit et
externe. L'action-JEPA existe déjà, mais cette propriété n'a jamais été testée avec un
objet mobile indépendant et un critère tenu à part.
Baseline: JEPA de même capacité sans action et score de changement pixel analytique;
mêmes images, actions, budgets et banques d'évaluation, labels physiques invisibles aux
modèles.
Avis Codex: voie la plus informative après la clôture explicite de la variante de
consolidation; elle teste une capacité développementale nouvelle sans recycler J6.
Avis Claude: à obtenir sur `reafference_001_preregistration.md` avant code.
Arbitrage Anthony: non requis; choix scientifique dans le brief sous D-004.
Conséquences: graines 12301..12316 et smoke 12991 interdits avant revue favorable; toute
promotion exige une seconde revue des résultats.
Condition de réouverture: critère tenu à part non identifiable sans oracle d'entraînement,
baseline simple inadéquate ou revue pré-calcul défavorable.
