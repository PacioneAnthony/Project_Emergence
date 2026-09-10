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

## D-014 - Autorisation amendée de REF-001

Date: 2026-07-26
Décision: accepter le verdict contradictoire « AUTORISER AVEC CORRECTIONS BLOQUANTES »
et intégrer C1–C5 au pré-enregistrement avant code ou calcul.
Statut: porte pré-calcul franchie sous réserve d'un smoke 12991 entièrement vert.
Motif: la revue confirme la clôture intègre de J6-AR001 et la validité du contraste de
réafférence, mais exige une baseline pixel action-consciente, des gardes calculables,
l'exclusion des paires propres dégénérées, des preuves d'équité/recomputabilité et une
porte de faisabilité temporelle.
Données utilisées: documents pré-calcul uniquement; aucune graine 12301..12316, aucun
smoke et aucune donnée scientifique REF-001.
Baseline: `no_action_jepa`, `pixel_change` et `pixel_change_action`, chacune comparée
séparément à `action_jepa` selon les amendements gelés.
Avis Codex: accepter les cinq corrections; elles ferment des ambiguïtés réelles sans
changer l'hypothèse après observation de résultats.
Avis Claude: autoriser l'implémentation et le smoke après intégration additive de C1–C5.
Arbitrage Anthony: non requis; application de la délégation D-004.
Conséquences: implémentation et smoke 12991 autorisés; graines 12301..12316 toujours
interdites avant smoke vert, projection temporelle concordante et manifeste gelé.
Toute promotion reste interdite avant revue contradictoire des résultats.
Condition de réouverture: smoke rouge, projection/plafond non concordants, ou violation
d'une garde; aucune correction n'est alors permise sur les graines réservées.

## D-015 - Clôture expérimentale de REF-001 sans promotion

Date: 2026-07-26
Décision: clore la variante REF-001 après la campagne complète 12301..12316, sans
promotion du résidu `action_jepa` comme détecteur de réafférence.
Statut: verdict mécanique négatif, interprétable, soumis à revue contradictoire des
résultats pour audit; aucune reprise ou correction sur ces graines.
Motif: les 32 runs sont complets sous le plafond, mais H1–H4 échouent. L'avantage
d'erreur propre `no_action − action` vaut `−0,00182` au lieu de `≥0,05`; la TPR action
vaut `0,37077` en externe pur et `0,14266` en mixte au lieu de `0,75` et `0,70`.
Les deux comparaisons pixel qui passent en externe pur sont non informatives:
`pixel_change` y a une TPR exactement nulle par décalage de domaine (seuil calibré tête
mobile, banque tête tenue; AUC `0,063`). Dans le régime mixte, où la baseline reste
dans son domaine, `pixel_change=0,13924` et `action_jepa=0,14266` sont statistiquement
indiscernables. La FPR globale `0,06372` respecte le plafond, mais un bin atteint
`0,11865 > 0,10`; `5/16` graines dépassent `0,07` et `16/96` cellules graine×bin
dépassent `0,10` (maximum `0,5234`).
Données utilisées: smoke 12991, 16 paires / 32 runs 12301..12316, cinq banques de
128 paires par bin et exports complets `reafference_001_analysis.json` /
`reafference_001_evaluations.json`.
Baseline: `no_action_jepa`, `pixel_change` et `pixel_change_action`, correction Holm
commune aux six comparaisons.
Avis Codex: résultat négatif mais informatif; l'action conditionnée n'explique pas
mieux l'ego-motion dans ce contraste et ne justifie pas sa complexité face au contrôle
de même capacité. Aucun retuning de REF-001.
Avis Claude: `AUTORISER AVEC CORRECTIONS` documentaires. Le recalcul indépendant est
identique au chiffre près; REF-001 ne peut pas être promu.
Arbitrage Anthony: non requis pour appliquer les portes gelées.
Conséquences: aucune promotion; REF-001 est close. Toute nouvelle tentative de
réafférence exige une hypothèse, un pré-enregistrement, un monde et des graines neufs.
La direction scientifique suivante ne sera ouverte qu'après audit contradictoire de la
clôture.
Condition de réouverture: aucune pour REF-001; seules une erreur d'intégrité démontrée
par la revue ou une nouvelle hypothèse séparée peuvent justifier un nouveau dossier.

## D-016 - Intégration de la revue des résultats REF-001

Date: 2026-07-26
Décision: accepter le verdict contradictoire et intégrer ses cinq corrections
documentaires sans rouvrir REF-001.
Statut: clôture auditée et définitive sous D-004.
Motif: la revue indépendante reproduit au chiffre près H1–H4, les six tests sous Holm,
les 384 seuils et les temps; elle confirme l'intégrité et le verdict négatif.
Données utilisées: exports gelés et artefacts d'audit existants uniquement; aucun
nouvel entraînement ni calcul décisionnel.
Corrections intégrées:

1. les succès pixel en externe pur sont déclarés non informatifs à cause du décalage
   de domaine; le régime mixte montre une égalité avec la baseline pixel;
2. l'échec H4 est attribué au plafond par bin et à son instabilité inter-graines,
   malgré une FPR globale conforme;
3. une collision d'image unique `external_only` / `learner_validation` sur 12312 est
   consignée; corpus et banques restent parfaitement disjoints;
4. la garde « action utile » est satisfaite structurellement mais non exportée
   numériquement; dette de traçabilité imposée aux protocoles suivants;
5. C5 n'a pas amendé le plafond et les 31,80 minutes consignées excluent l'évaluation.

Avis Codex: accepter sans réserve; aucune correction ne change une porte ou une
conclusion. La prochaine hypothèse doit être neuve et ne peut citer les comparaisons
pixel externes comme soutien partiel.
Avis Claude: `AUTORISER AVEC CORRECTIONS`; aucune promotion, aucun retuning.
Arbitrage Anthony: non requis.
Conséquences: REF-001 est définitivement close et la porte vers la conception d'une
hypothèse neuve est rouverte. Aucune graine 12301..12316 ne peut être réutilisée.
Condition de réouverture: aucune.

## D-017 - Passage à REF-002, transport sensorimoteur spatial

Date: 2026-07-26
Décision: rester sur l'étape 3 et pré-enregistrer REF-002 avant tout code ou calcul.
Statut: hypothèse neuve soumise à revue contradictoire pré-calcul.
Motif: REF-001 exclut l'idée qu'une commande absolue concaténée à un latent global
suffise. REF-002 teste un mécanisme distinct: transport explicite d'une carte spatiale
par une commande relative, avec contrôle de même information sans biais de transport
et baseline géométrique `yaw_warp`.
Données utilisées: conclusion qualitative auditée de REF-001 uniquement; aucune valeur
12301..12316 ne règle un seuil, budget ou hyperparamètre REF-002.
Baseline: `concat_relative_jepa`, `no_command_jepa`, `pixel_change` et `yaw_warp`, avec
calibration appariée par strate de mouvement.
Avis Codex: ne pas avancer au jalon développemental suivant tant que la séparation
auto-produit/externe n'est pas acquise; tester d'abord l'inductive bias spatial et
l'utilisation causale de la commande.
Avis Claude: à obtenir sur `reafference_002_preregistration.md` avant code.
Arbitrage Anthony: non requis sous D-004.
Conséquences: smoke 13991 et graines 13301..13316 interdits avant revue favorable et
intégration des corrections bloquantes. REF-001 demeure close.
Condition de réouverture: revue défavorable, baseline géométrique inéquitable,
appariement de domaine non démontrable ou budget temporel non faisable.

## D-018 - Mise en place de KERNEL-001

Date: 2026-07-26
Décision: ajouter un noyau cognitif persistant minimal, indépendant des modèles appris,
pour relier événements, croyances, épisodes, compétences et propositions d'expérience.
Statut: infrastructure implémentée et vérifiée; aucune revendication scientifique.
Motif: J0 garantit une excellente mémoire brute append-only, mais le projet ne possédait
aucun état cognitif dérivé persistant entre sessions. Continuer à multiplier les
modèles isolés ne suffisait pas à construire l'organisme développemental visé.
Données utilisées: contrats J0 existants, architecture développementale et invariants
de sécurité D-005/D-008; aucun résultat REF-002 et aucune graine réservée.
Architecture: `BeliefState`, `EpisodicMemory`, `CausalBoundaryPolicy`,
`SafeExperimentCatalog` et `CognitiveKernel`. SQLite conserve uniquement références,
digests, états et snapshots; les données sensorielles restent dans J0.
Sécurité: aucune méthode d'actionnement; les propositions sont bloquées par arrêt
d'urgence, santé matérielle, mise à jour de modèle, quota, primitive, croyances, risque,
coût, cadence et quota de session.
Vérification: 22 tests dédiés couvrent reprise après crash, causalité, retard, domaines
d'horloge, idempotence du replay, version de schéma, compétences, modèles et gardes. Un
smoke LIFE-001 traverse deux sessions MuJoCo/J0 et valide une primitive analytique avec
digest. Les 215 tests complets du dépôt sont verts dans `.venv`.
Avis Codex: cette couche manquait pour transformer les acquis scientifiques futurs en
développement cumulatif, réversible et auditable. Elle reste volontairement neutre
vis-à-vis de JEPA, LNN et LLM.
Avis Claude: non requis pour l'implémentation infrastructurelle initiale; une revue
architecturale contradictoire sera utile avant toute délégation d'action ou politique
apprise.
Arbitrage Anthony: accord explicite donné pour commencer la mise en place.
Conséquences: LIFE-001 peut être préparé en simulation avec estimateurs simples. La
porte pré-calcul REF-002 demeure entièrement inchangée.
Condition de réouverture: test d'injection de panne révélant une incohérence,
duplication de données brutes, proposition contournant une garde ou besoin démontré
d'un changement de schéma.

## D-019 - Autorisation amendée de REF-002

Date: 2026-07-26
Décision: accepter le verdict Claude Opus 5 `AUTORISER AVEC CORRECTIONS BLOQUANTES` et
intégrer C1–C8 ainsi que R1–R6 avant tout code ou calcul REF-002.
Statut: implémentation et smoke 13991 autorisés; graines 13301..13316 toujours fermées.
Motif: la revue confirme la nouveauté et la pertinence du contraste `mixed`, mais
démontre que le score normalisé sur images strictement statiques force le seuil JEPA à
1, H2 à zéro et une moitié de H4 à passer à vide.
Corrections structurantes: contrôles statiques remplacés par micro-mouvements non nuls;
H2 rétrogradée en SANITY-EXTERNAL descriptive; H3 devient l'unique porte de détection;
prédicteur `yaw_warp` analytique gelé sans mesure future; équité mesurée sur paramètres
effectivement actifs; entrée motrice recalculable sans fuite; unicité intra/inter-banque;
H5 renommée garde de non-dégénérescence; temps H5 inclus dans la projection.
Données utilisées: documents pré-calcul et contrats logiciels uniquement. Aucun smoke,
rendu, entraînement, résultat réservé ou graine 13301..13316.
Avis Codex: retenir la variante micro-mouvement et réduire la revendication plutôt que
conserver une porte mathématiquement vide. Cette correction rend un échec futur
attribuable.
Avis Claude: autorisation après intégration complète de C1–C8; H3 est le cœur valide du
protocole.
Arbitrage Anthony: non requis sous D-004.
Conséquences: code et tests REF-002 puis smoke 13991 autorisés. La campagne reste
interdite avant smoke entièrement vert, projection concordante et manifeste portant le
digest du protocole amendé.
Condition de réouverture: échec d'une garde, inégalité de capacité effective, fuite
motrice, calibration avec `MSE(copie)=0` ou projection non gelée avant 13301.

## D-020 - Clôture technique sans résultat de REF-002

Date: 2026-07-27
Décision: clore REF-002 sans analyse scientifique, sans promotion et sans reprise après
l'arrêt d'intégrité sur la préparation de 13313.
Statut: non-résultat technique; 13301..13312 interdits d'analyse.
Motif: une trame finale de `moving_self_calibration[201]` collisionne bit à bit avec
`mixed[244]` sur 13313, malgré des provenances et états objet distincts. C6 imposait
zéro collision de trame inter-banques; modifier cette garde après 12 triplets serait
post hoc.
Données utilisées: manifestes, compte de runs, hashes et métadonnées physiques
nécessaires au diagnostic uniquement. Aucun score, aucune porte et aucune agrégation
scientifique des 12 triplets complets.
État: 36 runs complets sur 13301..13312; 13313 préparée sans entraînement;
13314..13316 non ouvertes; `35,15402` minutes consignées.
Avis Codex au moment de l'arrêt: la garde semblait confondre égalité fortuite
d'observation et fuite. Rectification du 2026-07-27 après revue REF-003: l'égalité
révélait une manipulation `mixed` visuellement nulle parce que l'objet pouvait sortir
du champ (`≈3,06 %` des paires entièrement hors champ). La garde était mal ciblée mais
l'arrêt a évité un résultat inattribuable.
Avis Claude: revue pré-calcul favorable après C1–C8; aucune revue de résultats possible
faute de campagne complète.
Arbitrage Anthony: non requis; application mécanique du protocole gelé.
Conséquences: aucune reprise REF-002, aucune analyse partielle, aucune promotion. Une
nouvelle tentative exige protocole, monde et graines neufs.
Condition de réouverture: aucune pour REF-002.

## D-021 - Pré-enregistrement de REF-003

Date: 2026-07-27
Décision: retester l'hypothèse REF-002 restée non testée avec REF-003, monde et graines
neufs, en remplaçant la collision de trame bloquante par des gardes de provenance/paires
et une visibilité contrefactuelle par paire.
Statut: pré-enregistrement soumis à revue contradictoire avant code ou calcul.
Motif: l'arrêt 13313 ne révèle ni fuite ni résultat modèle. La revue REF-003 a corrigé
le diagnostic: une observation pouvait être identique parce que l'objet externe sortait
du champ. Les propriétés requises sont donc l'absence de réutilisation des mêmes
paires/provenances et une visibilité garantie sur toute l'enveloppe, puis vérifiée par
paire.
Données utilisées: hash et métadonnées physiques de la collision uniquement; aucun
score ou résultat 13301..13312.
Baseline et portes: identiques à REF-002 amendé. Seules l'intégrité, la visibilité, le
monde, les graines et le plafond lié aux rendus supplémentaires changent.
Avis Codex: une nouvelle campagne est justifiée car l'hypothèse n'a pas été testée. La
correction ne favorise aucun modèle et rend H3 plus attribuable.
Avis Claude: à obtenir avant implémentation sur
`docs/research/reafference_003_preregistration.md`.
Arbitrage Anthony: non requis sous D-004.
Conséquences: smoke 14991 et graines 14301..14316 interdits avant revue favorable et
intégration de ses corrections.
Condition de réouverture: revue défavorable, visibilité par paire non réalisable sans
oracle modèle, ou garde de provenance insuffisante.

## D-023 - Autorisation amendée de REF-003

Date: 2026-07-27
Décision: accepter le verdict Claude Opus 5 `AUTORISER AVEC CORRECTIONS BLOQUANTES` et
intégrer C1–C8 ainsi que R1–R6 avant tout code ou calcul REF-003.
Statut: implémentation et smoke 14991 autorisés; graines 14301..14316 toujours fermées.
Motif: la revue confirme le retest et l'absence de retuning, mais démontre que la
géométrie initiale REF3 aurait encore produit des paires `mixed` sans objet visible.
Corrections structurantes: visibilité prouvée sur l'enveloppe avec marge `3°`; rail
`0,36 m`, demi-largeur objet `0,32 m`, bearing par paire `U(−3°, +3°)`; collisions
corpus↔banques bloquantes; garde paire+moteur non vacuoue; SANITY-EXTERNAL `≥0,70`;
digests hérités; diagnostics objet/tête; difficulté du monde explicitée.
Données utilisées: documents, code hérité, géométrie et métadonnées physiques
uniquement. Aucun score 13301..13312, rendu REF3 ou graine 14301..14316.
Avis Codex: retenir une garantie analytique primaire et une mesure par paire comme filet
de non-régression. Le seuil SANITY `0,70` reprend le plancher H3 sans créer une
supériorité supplémentaire.
Avis Claude: autorisation après intégration complète de C1–C8; la version initiale de
REF3 aurait très probablement fini en second non-résultat technique.
Arbitrage Anthony: non requis sous D-004.
Conséquences: code/tests REF-003 puis smoke 14991 autorisés. La campagne reste interdite
avant smoke entièrement vert, digests concordants, preuve géométrique recalculée,
visibilité complète et projection gelée.
Condition de réouverture: paire sous visibilité, divergence d'héritage, fuite
contrefactuelle, collision corpus↔banque ou impossibilité d'implémenter le bearing par
paire sans asymétrie.

## D-024 - Correction d'ingénierie du smoke REF-003

Date: 2026-07-27
Décision: après l'arrêt du premier smoke 14991 sur l'appariement exact des masques
`yaw_warp`, rendre l'état physique pré-transition déterministe dans les sept banques.
Statut: correction I1 intégrée avant toute graine 14301..14316; second smoke autorisé.
Motif: les plans moteurs étaient appariés, mais vingt pas de stabilisation depuis des
historiques servo différents produisaient une différence d'une paire dans le bin 0
(`0,76953125` contre `0,78466796875`). La garde a correctement tiré.
Correction: avant chaque paire, poser la tête à l'angle de départ planifié avec vitesse
nulle et contrôle cohérent, puis `mj_forward`. La transition, la commande, l'horizon,
les modèles, seuils et budgets ne changent pas.
Données utilisées: fractions de masque et métadonnées de plan nécessaires au diagnostic
uniquement. Aucun score modèle, aucune TPR, aucune porte et aucune graine réservée.
Vérification: trois banques mobiles complètes sur graine non réservée 14990 ont des
multiensembles de masques identiques dans les six bins; 11 tests REF-003 et 247 tests
complets verts.
Avis Codex: l'état exact rend exécutable une exigence déjà gelée et retire une dépendance
à l'ordre de génération; il ne favorise aucune méthode.
Avis Claude: non requis pour cette correction d'implémentation mécanique couverte par
la garde pré-enregistrée.
Arbitrage Anthony: non requis sous D-004.
Conséquences: premier smoke archivé sous `tmp/ref3_smoke_attempt1_mask_mismatch`; second
smoke 14991 permis. Campagne toujours fermée.
Condition de réouverture: nouvelle divergence de masque, écart de tenseur moteur ou
effet de l'état direct sur une information accessible à une seule méthode.

## D-025 - Instrumentation temporelle intercalée REF-003

Date: 2026-07-27
Décision: remplacer l'ordonnancement en trois blocs du benchmark temporel par un ordre
tournant intercalé et des synchronisations CUDA encadrant chaque mesure.
Statut: correction I2 intégrée avant données smoke et avant toute graine réservée.
Motif: la seconde tentative smoke s'est arrêtée avant génération sur un ratio
`1,275399 > 1,25`. Des blocs successifs confondaient coût conditionnel et dérive GPU.
Invariants: seuil `1,25`, modèles, opérations, batchs, optimisateurs, 20 pas
d'échauffement et 100 mesures par condition inchangés. Aucun retry interne.
Données utilisées: durées du benchmark seulement; aucun corpus, entraînement, score,
TPR, porte ou graine 14301..14316.
Vérification: sur graine d'ingénierie non réservée 14990, ratio intercalé `1,10978`,
avec synchronisation avant/après et 100 mesures par condition.
Avis Codex: l'intercalage transforme le temps en comparaison locale équitable sans
assouplir la garde. Un ratio futur supérieur à `1,25` restera un arrêt.
Avis Claude: non requis; instrumentation de la garde C4 inchangée dans son seuil et son
objet.
Arbitrage Anthony: non requis sous D-004.
Conséquences: tentative 2 archivée sous `tmp/ref3_smoke_attempt2_timing_ratio`; nouvelle
tentative 14991 autorisée, campagne toujours fermée.
Condition de réouverture: ratio intercalé >1,25, synchronisation absente ou nombre de
mesures divergent.

## D-026 - Smoke REF-003 vert et ouverture de la campagne

Date: 2026-07-27
Décision: accepter la troisième tentative smoke 14991 et autoriser mécaniquement la
campagne 14301..14316 sous le plafond initial inchangé de 90 minutes.
Statut: smoke entièrement vert; campagne autorisée, aucune promotion autorisée.
Intégrité: preuve de champ `26,72758° ≤ 28,94922°`, marge résiduelle `2,22165°`;
zéro collision corpus↔banques, zéro collision de paire et zéro collision inter-banque
sur le smoke; digests hérités et d'implémentation concordants.
Visibilité: minimum `0,15308` en `external_only`, `0,05794` en `mixed`; toutes les
moyennes par bin `≥0,15968`, au-dessus des gardes `0,01` et `0,05`.
Équité: ratio temporel intercalé `1,10334`; paramètres, initialisation, gradients,
batchs et tenseurs à commande nulle conformes.
Temps: smoke `153,97167 s`; projection `2395,64465 s`, soit `39,92741 min`; plafond
initial `90 min` non amendé; contrefactuels `2,70849 s`.
Avis Codex: toutes les conditions pré-enregistrées d'ouverture sont satisfaites. La
campagne peut commencer sans autre choix.
Avis Claude: autorisation pré-calcul acquise sous D-023; revue des résultats encore
obligatoire avant promotion.
Arbitrage Anthony: non requis sous D-004.
Conséquences: 14301..14316 peuvent être ouvertes dans l'ordre par le runner protégé.
Toute garde échouée arrête sans remplacement ni analyse partielle.
Condition de réouverture: divergence de digest, dépassement du plafond, garde rouge ou
campagne incomplète.

## D-027 - Clôture technique sans résultat de REF-003

Date: 2026-07-27
Décision: clore REF-003 sans analyse scientifique, promotion ou reprise après l'arrêt de
visibilité pendant la préparation de 14303.
Statut: non-résultat technique; scores 14301..14302 interdits d'analyse.
Motif: deux paires `external_only` ont des effets contrefactuels `0,004453` et
`0,006999`, sous la garde individuelle `0,01`, malgré un objet géométriquement dans le
champ. La preuve angulaire ne borne ni occlusion ni contraste photométrique local.
État: 14301..14302 complets; 14303 préparée sans entraînement; 14304..14316 non ouvertes.
Données utilisées: manifeste d'échec et audits physiques/photométriques des banques de
14303 uniquement. Aucun score, TPR, seuil appris ou agrégation des graines complètes.
Avis Codex: la garde a tiré pour la propriété exacte qu'elle devait protéger. Une suite
doit rendre l'objet non occlusible et borner son effet local par construction, pas
réessayer jusqu'à obtenir des paires favorables.
Avis Claude: revue pré-calcul favorable après C1–C8; aucune revue de résultats possible
faute de campagne complète.
Arbitrage Anthony: non requis; application mécanique du protocole.
Conséquences: aucune reprise REF-003, aucune analyse partielle. Une nouvelle tentative
exige protocole, monde, graines et revue neufs.
Condition de réouverture: aucune pour REF-003.

## D-022 - Deuxième tranche LIFE-001

Date: 2026-07-27
Décision: ajouter au noyau un évaluateur de compétence à hystérésis et une sélection
auditée entre expériences éligibles, puis vérifier le cycle
validation→régression→récupération en simulation multi-session.
Statut: implémenté et vérifié; aucune action physique ni revendication scientifique.
Motif: KERNEL-001 persistait déjà les transitions et propositions, mais la démonstration
LIFE-001 ne couvrait ni détection de régression, ni récupération, ni arbitrage entre
plusieurs expériences sûres.
Implémentation: `cognitive/competence.py` produit résultats et digests sans modifier
l'état; `SafeExperimentCatalog.propose_best` applique toutes les gardes à chaque
candidate, classe uniquement les candidates éligibles et persiste l'audit complet de
la candidate retenue.
Vérification: six graines MuJoCo 17101..17106 hors espaces REF; deux validations
nominales, deux régressions sous vitesse servo injectée à 10°/s, choix de
`recalibrate-servo`, redémarrage, puis deux validations de récupération tenues à part.
26 tests KERNEL/LIFE et 236 tests complets verts.
Avis Codex: cette tranche transforme les états déjà persistés en boucle vérifiable sans
introduire de politique apprise ou d'actionnement. L'hystérésis réduit le risque de
flapping et l'audit des candidates empêche qu'une option bloquée gagne par son score.
Avis Claude: non requis pour cette validation d'infrastructure; requis avant toute
politique apprise, tout diagnostic causal revendiqué ou toute délégation d'action.
Arbitrage Anthony: carte blanche donnée pour poursuivre les éléments sûrs du projet.
Conséquences: LIFE-001 couvre désormais persistance, validation, régression,
récupération et choix sûr à signaux externes. L'étape suivante doit porter sur des
signaux acquis plutôt que scénarisés, toujours en simulation.
Condition de réouverture: sélection non déterministe, perte d'une raison de blocage,
transition sans preuve, flapping au voisinage des seuils ou contournement d'une garde.

## D-028 - LIFE-002 fondé sur les observations J0

Date: 2026-07-27
Décision: calculer les signaux du sélecteur depuis des résumés déterministes d'essais
`servo_state` J0 et persister, pour chaque candidate, la preuve et les digests sources.
Statut: implémenté et vérifié en simulation; aucune politique apprise ni action physique.
Motif: LIFE-001 choisissait correctement entre plusieurs expériences sûres, mais ses
six signaux étaient encore écrits comme valeurs de scénario. Une boucle
développementale doit pouvoir reconstruire son arbitrage depuis son histoire mesurée.
Implémentation: `cognitive/observed_signals.py` valide et résume les observations
publiques `requested_deg`/`as5600_deg`, sans payload brut dans SQLite. Il dérive erreur,
incertitude, progression, nouveauté, contrôlabilité, exposition aux butées et coût
moteur. `propose_best` exige une preuve exactement alignée sur les candidates lorsqu'une
table de preuves est fournie et conserve aussi la preuve des candidates bloquées.
Vérification: quatre sessions MuJoCo/J0 sur les graines 17201..17204, deux histoires
candidates, choix de `diagnose-servo`, crash simulé avec session ouverte, replay des
journaux et égalité stricte des résumés, signaux et SHA-256 après redémarrage. Les
33 tests KERNEL/LIFE ciblés et les 254 tests complets passent dans `.venv`.
Limite: `predicted_risk` est un proxy conservateur d'exposition historique aux butées,
pas une prédiction causale; les coefficients transparents ne constituent pas une
curiosité validée.
Avis Codex: LIFE-002 ferme le premier raccord manquant entre sensation enregistrée et
choix persistant. La prochaine lacune est l'attribution durable
proposition→exécution→résultat, nécessaire pour que l'histoire se construise sans
assemblage manuel par l'appelant.
Avis Claude: non requis pour ce câblage d'infrastructure en simulation; requis avant
toute revendication causale, politique apprise ou délégation d'action.
Arbitrage Anthony: carte blanche donnée pour poursuivre les éléments sûrs du projet.
Conséquences: LIFE-002 est close comme succès d'ingénierie. LIFE-003 peut ajouter le
cycle de résultat d'expérience et reconstruire automatiquement les historiques depuis
les références J0, toujours sans actionnement autonome.
Condition de réouverture: digest non reproductible, payload brut en SQLite, preuve
désalignée des candidates, score contournant une garde ou commande dans une proposition.

## D-029 - LIFE-003 et chaîne d'attribution durable

Date: 2026-07-27
Décision: ajouter au noyau une exécution d'expérience persistante reliant une proposition
unique, une session J0 unique et un résumé observationnel vérifiable.
Statut: implémenté et vérifié en simulation; schéma mémoire v2.
Motif: LIFE-002 recalculait correctement les signaux, mais l'appelant devait encore
assembler manuellement les journaux appartenant à chaque candidat. Cette attribution
est une mémoire causale minimale de l'intention, pas encore une preuve de causalité.
Implémentation: table additive `experiment_executions`; transitions atomiques
`running→complete/aborted`; proposition `accepted→executed/cancelled`; migration v1→v2;
reconstruction par `CognitiveKernel.recompute_observed_history`. Le statut `executed`
ne peut plus être posé directement.
Intégrité: une proposition et une session J0 ne peuvent être attribuées qu'une fois. Un
journal doit être clos, non tronqué et cohérent avec son manifeste. Le résumé recalculé,
son digest, son candidat et sa session doivent correspondre à SQLite. Une session
cognitive avec exécution active ne peut pas être close.
Vérification: quatre essais MuJoCo/J0 17311..17314; perte de processus pendant le premier
essai; reprise et complétion; deux histoires reconstruites automatiquement; choix de
`diagnose-servo`; second redémarrage bit-identique; altération J0 détectée; migration v1
représentative sans perte. 37 tests KERNEL/LIFE ciblés et 258 tests complets verts.
Avis Codex: le noyau possède maintenant une boucle de provenance durable de l'intention
au résultat mesuré. La prochaine intégration utile est un exécuteur de simulation
extérieur au noyau, limité à des primitives symboliques autorisées, afin d'éprouver la
boucle complète sans délégation physique.
Avis Claude: non requis pour ce câblage transactionnel en simulation; requis avant une
politique apprise, une revendication causale ou toute délégation d'action physique.
Arbitrage Anthony: carte blanche donnée pour poursuivre les éléments sûrs du projet.
Conséquences: LIFE-003 est close comme succès d'ingénierie. LIFE-004 peut automatiser
l'exécution MuJoCo des propositions autorisées tout en gardant le noyau sans actionneur.
Condition de réouverture: attribution multiple, source partielle acceptée, statut
`executed` sans résultat, migration destructive, payload brut en SQLite ou histoire non
reproductible.

## D-030 - LIFE-004 et boucle MuJoCo bornée

Date: 2026-07-27
Décision: autoriser un adaptateur exclusivement MuJoCo, extérieur au noyau, à exécuter
un registre fermé de primitives symboliques bornées et à remettre leurs journaux au
cycle LIFE-003.
Statut: implémenté et vérifié en simulation; aucun backend physique.
Motif: LIFE-003 reconstruisait l'histoire mais l'appelant devait encore traduire puis
exécuter la primitive. Une boucle développementale minimale exige que la proposition
sûre puisse produire sa propre nouvelle observation sans transformer le noyau en
actionneur.
Implémentation: `sim3d/life_executor.py`; primitives initiales
`diagnose_bounded_servo` (12 pas à 40°) et `scan_bounded_servo` (12 pas alternés
40°/140°); cibles non paramétrables par la proposition; bornes `[10°,170°]`; maximum
64 pas; digest canonique du plan dans le manifeste J0.
Sécurité: identité SQLite de la proposition, session active et statut `proposed`
revérifiés; arrêt d'urgence, santé, mise à jour, quota et primitive autorisée réévalués
au lancement. Primitive inconnue ou identité falsifiée refusée avant journal. Toute
panne après attribution annule atomiquement exécution et proposition et marque le
journal `aborted`.
Vérification: quatre essais bootstrap 17421..17424, signaux exclusivement
observationnels, choix de `diagnose-servo`, cinquième essai automatique 17425 et
reconstruction 3/2 après redémarrage. Gardes 17401..17403 et panne injectée 17411
vertes. 41 tests KERNEL/LIFE ciblés et 262 tests complets verts.
Avis Codex: le projet possède désormais une boucle raccordée
observation→choix→exécution simulée→mémoire. La limite principale n'est plus le
câblage, mais la sémantique: plans écrits par l'ingénieur, score heuristique et absence
d'acquisition automatique d'une compétence depuis les résultats.
Avis Claude: non requis pour cet exécuteur déterministe limité à MuJoCo. Une revue
Claude Opus 5 devient requise avant d'introduire une politique apprise, une génération
ouverte de primitives ou une revendication de curiosité/causalité.
Arbitrage Anthony: autorisation explicite de procéder.
Conséquences: LIFE-004 est close comme succès d'ingénierie. La prochaine tranche peut
relier les résultats exécutés à l'évaluation et aux transitions de compétence, sans
encore apprendre une politique.
Condition de réouverture: cible libre injectée, backend physique accessible, garde
fraîche contournée, proposition falsifiée acceptée, panne laissant `running`, ou cible
silencieusement clampée.

## D-031 - LIFE-005 et compétence issue des résultats

Date: 2026-07-27
Décision: évaluer `bounded_servo_tracking` depuis une fenêtre explicite des résultats
`diagnose-servo` vérifiés, puis appliquer acquisition, régression et récupération dans
une transaction idempotente.
Statut: implémenté et vérifié en simulation; schéma mémoire v3.
Métrique: `mean_absolute_tracking_error_deg`, soit l'erreur normalisée LIFE-002
multipliée par le span servo `160°`, transitoires du plan inclus. Fenêtre courante:
deux derniers essais complets.
Critère: validation `≤9°`, régression `>15°`. Le seuil initial d'ingénierie `8°` a été
rectifié avant clôture du smoke: la primitive nominale de douze pas vaut exactement
`8,1884765625°`. Le seuil `9°` laisse 9,9 % de marge nominale et reste séparé de 6° du
seuil de régression; aucune primitive, graine, fenêtre ou donnée n'a été modifiée.
Implémentation: `assess_executed_servo_tracking` produit une preuve liée aux sessions et
digests LIFE-003; `evaluate_and_apply_executed_competence` reconstruit d'abord toutes
les sources. `competence_assessments` déduplique par
`(competence_name, assessment_digest)` et les chemins multi-transition sont atomiques.
Une preuve ancienne ou une compétence `suspended` ne peut pas modifier l'état.
Vérification: nominal 17501/17502 `8,1884765625°`; lent 17503/17504
`47,59765625°`; reprise nominale 17505/17506 `8,1884765625°`. Historique final:
`learning,candidate,validated,regressed,learning,candidate,validated`. Replay sans
nouvelle ligne, migrations v1/v2→v3 vertes. 45 tests ciblés et 266 tests complets verts.
Avis Codex: le projet possède désormais un retour vérifiable de l'expérience vers
l'état cognitif. La prochaine lacune est l'amont du choix: la liste de candidates reste
fournie par l'appelant au lieu d'être activée par les compétences inconnues ou
régressées.
Avis Claude: non requis pour ce critère analytique et cette machine d'état
transactionnelle. Revue requise avant seuil appris, politique de curriculum apprise ou
revendication métacognitive.
Arbitrage Anthony: autorisation explicite de poursuivre.
Conséquences: LIFE-005 est close comme succès d'ingénierie. LIFE-006 peut construire
des besoins persistants et activer les candidates depuis l'état des compétences, sans
encore apprendre leur politique de priorité.
Condition de réouverture: replay non idempotent, source non vérifiée, évaluation hors
ordre acceptée, réactivation automatique d'un état suspendu, promotion sans digest ou
migration destructive.

## D-032 - LIFE-006 et activation par besoins persistants

Date: 2026-07-27
Décision: construire automatiquement les candidates depuis un registre déclaratif
compétence→état→expériences et l'état persistant des compétences.
Statut: implémenté et vérifié en simulation; aucune priorité apprise.
Politique: sélectionner toutes les routes non vides à l'urgence maximale:
`regressed=4`, `unknown=3`, `learning=2`, `candidate=1`, `validated=0`;
`suspended` est toujours exclu. Les routes de priorité inférieure sont différées, pas
transformées en faux signaux.
Démarrage à froid: chaque expérience routable possède un `ExperimentSignals` déclaratif
audité comme `cold_start_prior`. Dès qu'un résultat LIFE-003 existe, LIFE-002 recalcule
les signaux et la preuve devient `observed_history`. Des priors contradictoires pour une
même expérience sont refusés.
Sécurité: l'activation filtre seulement les candidates; toutes les gardes du catalogue
restent appliquées ensuite. Une candidate urgente bloquée ne provoque pas un repli
silencieux vers un besoin moins urgent.
Vérification: à froid, `diagnose-servo` et `wide-scan` activées; 17601 remplace
uniquement le prior diagnose par une preuve observée, identique après redémarrage.
Validation servo laisse seulement le besoin visuel inconnu actif; 17602 l'exécute.
Régression servo préempte ensuite le visuel; suspension servo exclut sa route. Aucun
besoin actif signifie aucune proposition. 50 tests ciblés et 271 tests complets verts.
Avis Codex: l'état cognitif pilote désormais l'amont du choix sans intervention de
l'appelant sur la liste courante. Le dernier câblage manuel majeur est l'enchaînement
des étapes activate→select→execute→assess et sa reprise après crash.
Avis Claude: non requis pour ce curriculum déclaratif. Revue requise avant apprentissage
des priorités, découverte autonome de besoins ou génération d'expériences.
Arbitrage Anthony: autorisation explicite de continuer.
Conséquences: LIFE-006 est close comme succès d'ingénierie. LIFE-007 peut ajouter un
superviseur de cycle persistant et reprenable, sans modifier les politiques.
Condition de réouverture: compétence suspendue activée, urgence encodée dans les
`ExperimentSignals`, prior froid présenté comme observation, historique disponible
ignoré, repli silencieux vers une urgence inférieure ou proposition sans besoin actif.

## D-033 - LIFE-007 et supervision persistante du cycle

Date: 2026-07-27
Décision: persister et reprendre le cycle
`activate→select→execute→assess→complete` sans introduire de nouvelle politique.
Statut: implémenté et vérifié en simulation; schéma mémoire v4.
Phases: `selected`, `executed`, `complete`, `aborted`. Proposition et cycle sont créés
dans une transaction. Identités de cycle, proposition, exécution, session J0 et graine
sont uniques et vérifiées à chaque reprise.
Reprise: après sélection, LIFE-004 est lancé sans nouvelle proposition; après exécution
complète, LIFE-005 est appliqué sans nouvelle exécution; après application LIFE-005, le
même digest est rejoué sans transition supplémentaire avant commit terminal.
Limite physique: un journal encore `recording` après perte de processus implique un
état MuJoCo perdu. Il est marqué `aborted`, ainsi que l'exécution et le cycle; aucune
continuation ou nouvelle graine automatique n'est permise dans ce cycle.
Sécurité: une garde devenue rouge laisse le cycle `selected` et reprenable; une
sélection déjà bloquée ne crée ni proposition ni cycle. Une session cognitive ne peut
être close proprement avec cycle `selected/executed`.
Vérification: 17701 reprend après sélection; 17702 reprend après exécution puis après
évaluation; exactement deux propositions, deux exécutions, une application. 17711
reprend après arrêt d'urgence levé; 17721 est abandonné en plein essai; 17731 ne crée
rien. Migration v3→v4 et chaînes antérieures vertes. 55 tests ciblés et 276 tests
complets verts.
Avis Codex: les briques LIFE forment maintenant un processus autonome minimal,
explicable et reprenable en simulation. Avant toute politique apprise, la prochaine
étape utile est une campagne d'endurance et d'injection de pannes multi-cycle pour
tester quotas, répétitions, interruptions et croissance de la mémoire.
Avis Claude: non requis pour ce superviseur déterministe. Revue obligatoire avant
apprentissage des besoins, priorités, plans ou seuils.
Arbitrage Anthony: autorisation explicite de continuer.
Conséquences: LIFE-007 est close comme succès d'ingénierie. LIFE-008 peut qualifier la
robustesse temporelle et transactionnelle de la boucle sur une campagne bornée.
Condition de réouverture: proposition orpheline, duplication après reprise, cycle
terminé deux fois, exécution partielle continuée, fermeture de session avec cycle actif
ou identité de requête modifiable.

## D-034 - LIFE-008 et qualification d'endurance

Date: 2026-07-27
Décision: qualifier la boucle LIFE-007 sur 64 cycles déterministes et une matrice
périodique de reprises avant toute introduction de politique apprise.
Statut: campagne complète; toutes portes vertes.
Protocole: `life008-endurance-v1`, graines 17801..17864; cinq régimes répétés:
direct, reprise après sélection, reprise après exécution, reprise après assessment et
arrêt d'urgence temporaire après sélection.
Résultats: 64 cycles/propositions/exécutions/sessions J0 uniques et complets;
63 assessments; 51 redémarrages; 12 refus d'urgence; zéro résidu actif ou running;
historique `learning,candidate,validated`; intégrité SQLite `ok`.
Stockage: SQLite+WAL `1 609 856` octets, J0 `356 910`, moyenne combinée
`30 730,71875` octets/cycle, sous les portes respectives 4 MiB/4 MiB/128 KiB.
Idempotence: seconde invocation, 64 cycles sautés, zéro nouvel effet, mêmes comptes et
digest logique
`3cab7044228bb20ec512f67e32d3de44cac7a292c51d03311c7b815d3ccf2616`.
Quota: saturation réelle refuse LIFE-004 après sélection; même cycle et même proposition
terminent lorsque la politique saine est restaurée.
Vérification: 57 tests KERNEL/LIFE ciblés et 278 tests complets verts. Rapport local:
`data/processed/experiments/life_008_endurance/report.json`.
Avis Codex: l'infrastructure déterministe est suffisamment raccordée, auditée et
endurante pour cesser d'ajouter des couches de plomberie. L'étape utile suivante doit
tester une capacité apprise: estimer quelle expérience améliore quelle compétence, au
lieu d'utiliser uniquement priorités et priors écrits.
Avis Claude: revue contradictoire désormais requise avant implémentation ou calcul d'une
politique adaptative de curriculum, conformément aux limites D-030 à D-033.
Arbitrage Anthony: autorisation explicite de poursuivre LIFE-008.
Conséquences: LIFE-008 est close. Codex peut rédiger LIFE-009 et sa demande de revue;
aucun code appris, entraînement ou campagne LIFE-009 avant verdict Claude Opus 5.
Condition de réouverture: digest non idempotent, porte d'endurance rouge, cycle résiduel,
croissance hors budget, duplication ou corruption SQLite/J0.

## D-035 - Pré-enregistrement LIFE-009 avant politique apprise

Date: 2026-07-27
Décision: proposer LIFE-009 comme première épreuve de curriculum appris, couplée à une
compétence réellement plastique de prédiction sensorimotrice à un pas.
Statut: protocole rédigé; revue contradictoire Claude Opus 5 bloquante avant tout code
appris, smoke, génération de banque, entraînement ou calcul.
Motif: apprendre une priorité sur la boucle LIFE-008 immobile créerait un résultat
circulaire: répéter une épreuve nominale suffirait à faire progresser le statut sans que
l'organisme apprenne mieux les conséquences de ses actions. LIFE-009 mesure donc la
réduction d'erreur d'un modèle propre à chaque organisme sur 48 transitions privées.
Conception: trois expériences bornées fine/medium/wide alimentent un modèle de compétence
ridge. Une seconde ridge, entraînée sur 32 organismes et vérifiée sur 8, prédit le
progrès de chaque candidate depuis des features disponibles à l'inférence. L'évaluation
appariée utilise 24 organismes neufs et quatre baselines, dont une politique analytique
d'incertitude désignée comme comparaison principale.
Étanchéité: paramètres MuJoCo cachés, banques privées, labels futurs et métriques test
sont interdits aux features. Les poids sont gelés avant le test; toute fuite, resampling
ou lecture précoce arrête l'expérience.
Promotion: toutes les portes d'apprentissage, AUC, baselines, absence de raccourci,
sécurité et reproductibilité doivent passer. Un succès n'autorise qu'un sélecteur
optionnel en simulation; D-008 et toutes les gardes déterministes restent inchangées.
Avis Claude: requis sur `docs/research/life_009_preregistration.md` via
`docs/research/life_009_review_request.md`.
Arbitrage Anthony: non requis pour la rédaction sous D-004; Claude doit maintenant
produire la revue avant continuation scientifique.
Conséquences: Codex n'implémente ni n'exécute LIFE-009 avant verdict. Les graines
17901..17940, 17991 et 18001..18024 sont réservées et interdites de calcul.
Condition de réouverture: corrections Claude, changement de l'objectif général, fuite
entre banques, définition non implémentable ou puissance jugée insuffisante.

## D-036 - Intégration de la revue pré-calcul LIFE-009

Date: 2026-07-27
Décision: accepter le verdict Claude Opus 5
`AUTORISER AVEC CORRECTIONS BLOQUANTES` et intégrer B1–B7 comme amendement additif au
pré-enregistrement avant toute implémentation.
Statut: corrections intégrées; implémentation et smoke 17991 autorisés. Banques
17901..17940 et 18001..18024 toujours fermées.
Corrections: portes restreintes aux amplitudes atteignables 15/40/70; extrapolation
0/110/160 descriptive; marge oracle `>=10 %` et progrès 12→24 obligatoires au smoke;
Monte-Carlo des signes gelé à 200 000 rééchantillonnages; magasins contrefactuels
isolés; copie d'état et RNG exhaustive; projection temporelle couvrant professeur,
test, évaluations et analyse; conventions numériques/coût/tri fixées; validation P0
obligatoire avant toute ouverture du test.
Motif: la version initiale pouvait rendre P1 inatteignable par construction parce que
68 % de la masse d'erreur portait sur des amplitudes non explorables et que la baseline
principale approchait le tourniquet sous une garde moteur étroite. Le smoke doit
maintenant établir qu'une marge réelle existe avant de consommer les banques.
Remarques intégrées: redondance greedy/round-robin explicitée, colonnes constantes
standardisées avec échelle 1, allocations détaillées exportées, oracle présenté comme
plafond privilégié et suite de tests courante exigée.
Avis Claude: une fois B1–B7 intégrées, l'implémentation puis le smoke sont autorisés.
Une revue contradictoire des résultats reste obligatoire avant toute promotion.
Arbitrage Anthony: non requis sous D-004.
Conséquences: Codex peut coder LIFE-009 et lancer 17991. Les banques réservées ne
s'ouvrent que si smoke, marge et projection sont verts; le test exige en plus P0
validation vert.
Condition de réouverture: smoke sans marge, projection >60 minutes, fuite de branche,
validation rouge, contradiction d'implémentation ou correction scientifique nouvelle.

## D-037 - Arrêt LIFE-009 pour marge oracle insuffisante

Date: 2026-07-27
Décision: appliquer la porte B2 et clore LIFE-009 comme non-résultat de conception avant
toute ouverture des banques réservées.
Statut: arrêt définitif sous cet identifiant; aucune campagne scientifique LIFE-009.
Smoke: seule graine 17991; banque 48, professeur 72, replay bit-identique, comptes 24/24,
poids reproductibles et projection `696,2451677 s` sont verts. Round-robin progresse de
`12,3110770766°` à `12,2867277806°` entre les cycles 12 et 24.
Porte rouge: oracle AUC `1,510406` contre greedy `1,547281`, soit seulement
`2,3832203646 %` d'amélioration, sous les `10 %` exigés.
Digest:
`26610a6678f5af92aefc7d708256ba8069d5a2d3d1f7621689e2a9b2f52fa7f1`.
Interprétation: même l'oracle privilégié ne possède pas la marge nécessaire pour que
l'épreuve puisse attribuer un échec à la politique apprise. Les AUC >1 indiquent aussi
que le modèle ajusté dégrade le prior sur ce protocole; ce constat smoke ne teste pas
la généralisation.
Intégrité: graines 17901..17940 et 18001..18024 jamais ouvertes; aucun P0–P4 de campagne,
retuning, remplacement ou seconde lecture adaptative. Les 61 tests KERNEL/LIFE ciblés
et les 282 tests complets sont verts.
Avis Claude: la correction B2 pré-enregistrée impose mécaniquement cet arrêt; nouvelle
revue de résultats non requise puisqu'aucune campagne n'a été autorisée.
Arbitrage Anthony: non requis sous D-004.
Conséquences: une tentative ultérieure exige LIFE-010, de nouvelles graines et une
nouvelle revue pré-calcul. Elle doit démontrer la plasticité utile et la marge oracle
avant de réserver ou consommer une banque.
Condition de réouverture: aucune sous LIFE-009.

## D-038 - Pré-enregistrement LIFE-010 après l'arrêt de conception

Date: 2026-07-27
Décision: proposer LIFE-010 comme nouvelle tentative de curriculum appris, sans rouvrir
ou retuner LIFE-009.
Statut: protocole et demande de revue rédigés; aucun code, smoke ou calcul autorisé avant
verdict Claude Opus 5.
Compétence: prédire le résidu d'un prior physique à `12°/pas` plutôt que l'angle complet.
Chaque essai sépare indices pairs d'ajustement et impairs de validation publique; une
mise à jour ne peut dégrader cette validation au-delà de `1e-12`.
Expériences: `step_hold`, `reversal` et `micro` comportent chacune 32 pas, coûtent
exactement `560°` commandés et reviennent à `90°`, avec 5, 14 et 28 changements. Elles
varient donc la structure temporelle sans confondre choix et budget moteur.
Organismes: trois régimes cachés speed/settling/friction. La banque privée exécute deux
fois chaque plan, soit 192 transitions, exclusivement pour professeur et évaluation.
Marge précoce: six graines smoke neuves 18191..18196 doivent toutes améliorer le prior
d'au moins 20 % sous round-robin; l'oracle doit battre la baseline résiduelle de 15 %
en médiane et 5 % dans chaque régime avant toute banque.
Banques réservées: développement 18201..18232, validation 18241..18248, test
18301..18324. Leur ouverture reste interdite avant les portes précédentes et la
projection complète sous 90 minutes.
Avis Claude: revue contradictoire pré-calcul obligatoire via
`docs/research/life_010_review_request.md`.
Arbitrage Anthony: non requis pour la conception sous D-004.
Conséquences: Codex s'arrête avant implémentation. Après verdict, seules les opérations
explicitement autorisées pourront commencer; une revue des résultats restera obligatoire
avant promotion.
Condition de réouverture: corrections Claude, définition non implémentable, tâche
artificiellement favorable, baseline insuffisante ou changement d'objectif général.

## D-039 - Intégration de la revue pré-calcul LIFE-010

Date: 2026-07-27
Décision: accepter le verdict Claude Opus 5
`AUTORISER AVEC CORRECTIONS BLOQUANTES` et intégrer B1–B7 avant code ou calcul.
Statut: implémentation et smoke 18191..18196 autorisés; banques 18201..18248 et
18301..18324 toujours fermées.
Corrections: round-robin devient co-principale si greedy residual est moins bonne au
smoke; plancher 3 % face à round-robin; sens des portes MAE explicite; validation
publique déclarée autocorrélée et acceptations/refus exportés; smoke étendu aux six
politiques et oracle; prior aligné sur la rampe interne, pas l'AS5600; limites
mono-facteur/même distribution déclarées; P3 convertie en tests appariés de
non-infériorité corrigés par Holm.
Motif: empêcher une promotion facile contre une baseline greedy verrouillée et éviter
de présenter des assertions structurelles comme preuves scientifiques.
Avis Claude: implémentation puis smoke autorisés après intégration; aucune banque avant
sept portes smoke vertes, ancrage B1 écrit, comptes de protection exportés et projection
complète sous 90 minutes.
Arbitrage Anthony: non requis sous D-004.
Conséquences: Codex peut implémenter puis exécuter uniquement les six smokes. Toute
promotion nécessitera une revue contradictoire des résultats.
Condition de réouverture: porte smoke rouge, contradiction de code, fuite, projection
hors budget ou correction scientifique nouvelle.

## D-040 - Arrêt LIFE-010 sur incompatibilité plan–garde

Date: 2026-07-27
Décision: clore LIFE-010 comme non-résultat technique sans reprendre le smoke.
Statut: arrêt définitif sous cet identifiant; aucune métrique scientifique.
Événement: sur le début de 18191, l'historique de `probe_step_hold` produit
`boundary_exposure=predicted_risk=0.75`. La limite catalogue `0.50` bloque ensuite ce
plan; le sélecteur choisit `probe_micro`, en contradiction avec le carré latin demandé.
Interprétation: la garde fonctionne correctement. Les maintiens à `20°/160°` rendent le
plan structurellement trop exposé selon LIFE-002. Relever le seuil ou écraser le risque
après observation serait post hoc.
Intégrité: 18192..18196, développement 18201..18232, validation 18241..18248 et test
18301..18324 jamais ouverts. Aucune AUC, marge oracle, projection ou porte P0–P4.
Vérification avant lancement: 18 tests ciblés et 287 tests complets verts.
Avis Claude: non requis pour appliquer une garde préexistante; une nouvelle revue
pré-calcul est requise pour le successeur.
Arbitrage Anthony: non requis sous D-004.
Conséquences: LIFE-010 reste close. Un nouvel identifiant doit éloigner les cibles des
frontières et geler une porte d'éligibilité après historique propre.
Condition de réouverture: aucune sous LIFE-010.

## D-041 - Pré-enregistrement LIFE-011 à éligibilité persistante

Date: 2026-07-27
Décision: proposer LIFE-011 comme nouvel essai, sans modifier ou reprendre LIFE-010.
Statut: protocole et demande de revue prêts; aucun code, smoke ou calcul LIFE-011.
Plans: step_hold v2 utilise 30°/150°, reversal v2 50°/130°, micro v2 70°/110°.
Ils font exactement 32 pas, 480° commandés, retour 90°, avec 5/12/24 changements.
Sécurité: limites catalogue gelées `predicted_risk<=0.50`, `motor_cost<=0.80`. Un
préflight temporaire exécute chaque plan une fois et exige qu'il reste éligible à une
seconde proposition après reconstruction de son propre historique.
Science: compétence, protection, régimes, professeur, politiques, ancrage dynamique,
marges, statistiques et limites de LIFE-010 amendée sont conservés. Nouvelles graines:
18491..18496, 18501..18532, 18541..18548, 18601..18624; statistique 2026072704.
Motif: corriger le contrat plan–garde sans abaisser la garde. Recentrer les cibles
supprime l'exposition structurelle aux zones de 10° autour des bornes tout en conservant
trois structures temporelles et un budget identique.
Avis Claude: nouvelle revue pré-calcul obligatoire via
`docs/research/life_011_review_request.md`.
Arbitrage Anthony: non requis pour la rédaction sous D-004.
Conséquences: Codex s'arrête avant code. Toute autorisation future dépend du verdict;
promotion toujours soumise à revue de résultats.
Condition de réouverture: corrections Claude, plan encore inéligible, perte de
complémentarité, baseline insuffisante ou changement d'objectif général.

## D-042 - Intégration de la revue pré-calcul LIFE-011

Date: 2026-07-27
Décision: accepter `AUTORISER AVEC CORRECTIONS BLOQUANTES` et intégrer B1–B6 avant
toute exécution LIFE-011.
Motif: les plans v2 corrigeaient la garde mais perdaient leur complémentarité réalisée
sous le limiteur. Le triplet v3 conserve 32 pas, 480°, retour 90° et bornes 30°..150°,
tout en séparant pas mobiles et renversements. La revue impose aussi la plaque de marge
avant le professeur, l'invariant par essai, la décomposition mobile/inerte et une
comptabilité statistique non ambiguë.
Avis Claude: implémentation puis smoke `18491..18496` autorisés après intégration.
Arbitrage Anthony: non requis sous D-004.
Conséquences: les banques `18501..18532`, `18541..18548` et `18601..18624` restent
interdites tant que les dix portes smoke et tous les exports obligatoires ne sont pas
verts.
Condition de réouverture: aucune métrique réservée avant manifeste smoke vert; aucune
promotion avant revue contradictoire des résultats.

## D-043 - Arrêt LIFE-011 sur la marge minimale settling

Date: 2026-07-27
Décision: clore LIFE-011 au terme de sa plaque de marge, sans professeur ni reprise.
Statut: non-résultat de qualification; aucune banque réservée ouverte.
Résultat: porte 5 verte; ancrage greedy seule principale; porte 7 verte. La porte 6
échoue parce que la marge oracle minimale de `settling_dominant` vaut `4,4039 %`,
contre `5 %` exigés, malgré une médiane globale de `16,8853 %`.
Intégrité: 18/18 préflights verts, risque `0,0`, coût `0,09375`, complémentarité v3
verte, aucune violation de garde. Digest de plaque:
`dd3ce54c7b5380f4fb5d2952e986a5e7869e993259580eabcf9dfc288484bb7d`.
Avis Claude: le protocole B2 impose l'arrêt avant professeur sur porte 6 rouge.
Arbitrage Anthony: non requis sous D-004.
Conséquences: 18501..18624 restent vierges. LIFE-011 n'évalue pas la politique apprise.
Un successeur doit expliquer comment il augmente l'opportunité de sélection dans le
régime settling sans relâcher post hoc le seuil observé.
Condition de réouverture: aucune sous LIFE-011.

## D-044 - Pré-enregistrement LIFE-012 avec plateaux réalisés

Date: 2026-07-27
Décision: proposer un nouvel essai sans relâcher les portes LIFE-011.
Statut: protocole et demande de revue prêts; aucun code ou calcul LIFE-012.
Plans: coût commun réduit de 480° à 240° pour permettre des cibles atteintes et des
maintiens réalisés. Au nominal, step-settle/reversal/micro séparent 20/24/32 pas mobiles,
2/4/8 renversements et 6/4/0 maintiens hors neutre.
Motif: 18496 montre que l'oracle reconnaît l'utilité de step-hold mais que son avantage
reste 4,4039 %. Le plan v3 ne contient que deux maintiens hors neutre. LIFE-012 teste
si une excitation d'établissement réelle crée une opportunité uniforme, sans transformer
le seuil observé en succès.
Graines proposées: 18791..18796, 18801..18832, 18841..18848, 18901..18924;
statistique 2026072705.
Avis Claude: revue contradictoire pré-calcul obligatoire.
Arbitrage Anthony: non requis pour la rédaction sous D-004.
Conséquences: code et graines LIFE-012 interdits avant verdict.
Condition de réouverture: correction Claude, complémentarité invalide, dilution
excessive ou mécanisme settling non plausible.

## D-045 - Intégration de la revue LIFE-012 et choix de la voie B

Date: 2026-07-27
Décision: intégrer B1–B5 et conserver les plans v4 à 240° selon la voie B.
Motif: les plateaux ciblent correctement settling/friction à vitesse nominale. La
dégénérescence sous 375°/s est déclarée pour 28,125 % de speed_dominant et ne donnera
lieu à aucun filtrage. La voie B conserve en outre la taxonomie gelée `k=3` avec
`temps_mort=0`; les segments longs de la voie A proposée auraient créé des maintiens
au-delà de trois pas.
Corrections: diagnostics vides à `null`, cadence/plateau exportés, taxonomie
rampe/plateau/temps_mort, masses d'erreur, résidus de plateau, historique de la porte et
portée causale limitée.
Avis Claude: implémentation puis plaque de marge 18791..18796 autorisées après intégration.
Arbitrage Anthony: non requis sous D-004.
Conséquences: banques 18801..18924 interdites avant six portes de marge puis dix portes
finales vertes.
Condition de réouverture: porte rouge, temps_mort non nul, garde violée ou correction
scientifique nouvelle.

## D-046 - Arrêt LIFE-012 et retour au jalon J1

Date: 2026-07-27
Décision: clore LIFE-012 à la plaque et arrêter la famille de triplets LIFE-009..012.
Statut: non-résultat de qualification; aucune banque réservée ouverte.
Résultat: portes d'intégrité 1–3 vertes; portes scientifiques 4–6 rouges. Round-robin
ne progresse pas sur 18793 (`24/24` mises à jour refusées). Marge oracle médiane face à
greedy `4,9404 %`; round-robin devient co-principale et l'oracle myope perd jusqu'à
`−6,4459 %` face à elle.
Interprétation: le verrou n'est plus le dessin des plans. La compétence n'est pas
plastique sur tout l'espace et l'oracle à un pas n'est pas une borne séquentielle.
Avis Claude: le protocole impose l'arrêt avant professeur sur une porte de marge rouge.
Arbitrage Anthony: non requis sous D-004 et CODEX_TASK_BRIEF.
Conséquences: 18801..18924 restent vierges. La suite revient à J1 pour qualifier un
schéma corporel robuste et incertain avant toute nouvelle tentative J5.
Condition de réouverture: aucune sous LIFE-012; J5 exige une compétence J1 qualifiée.

## D-047 - Pré-enregistrement BODY-SCHEMA-001

Date: 2026-07-27
Décision: suspendre J5 et qualifier d'abord un schéma corporel probabiliste J1.
Statut: protocole et demande de revue prêts; aucun code ou calcul.
Modèle proposé: ensemble de 16 ridges résiduelles ARX, bootstrap de trials entiers,
variance inter-membres + MAD public et calibration conformelle. Excitation fixe commune,
aucune allocation ni oracle de curriculum.
Baselines: persistance, prior physique et ridge LIFE. Portes distinctes pour MAE,
plasticité, calibration et détection d'un actionneur bloqué.
Motif: 18793 refuse 24/24 mises à jour sous toutes les allocations; l'architecture manque
d'un schéma corporel plastique avec incertitude calibrée, en amont du sélecteur.
Graines proposées: smoke 19091..19096, test 19201..19224; statistique 2026072706.
Avis Claude: revue contradictoire pré-calcul obligatoire.
Arbitrage Anthony: non requis; retour conforme à l'ordre J1→J5 de l'architecture.
Conséquences: aucun nouveau LIFE/J5 avant qualification BODY-SCHEMA-001.
Condition de réouverture: corrections Claude, défaut d'équité, incertitude invalide ou
banque faute non attribuable.

## D-048 - Intégration de la revue BODY-SCHEMA-001

Date: 2026-07-27
Décision: intégrer B1–B6 avant toute graine.
Constat majeur: l'AS5600 simulé est déterministe; les banques LIFE de plans répétés
mesuraient une erreur d'ajustement et non une généralisation tenue à part.
Corrections: 36 instances temporelles distinctes, protection/calibration séparées,
comparateur B2' équitable, H0 angle/vitesse, fautes blocked/degraded, plancher privilégié
P, plasticité conditionnée par la marge et incertitude numérique entièrement gelée.
Avis Claude: implémentation puis smoke 19091..19096 autorisés après intégration.
Arbitrage Anthony: non requis sous D-004.
Conséquences: 19201..19224 interdits avant dix portes smoke vertes.
Condition de réouverture: collision de contenu, calibration invalide, absence de marge,
porte smoke rouge ou décision scientifique nouvelle.

## D-049 - Arrêt BODY-SCHEMA-001 aux portes d'incertitude et de faute

Date: 2026-07-27
Décision: clore BODY-SCHEMA-001 après le smoke `19091..19096`, sans ouvrir
`19201..19224`.
Statut: résultat smoke négatif; portes 7 et 8 rouges, huit autres portes vertes.
Résultat: M apprend sur les six organismes, réduit la MAE du prior de `53,2 %` à
`92,6 %` et corrige le refus historique de 18793. La couverture globale et les largeurs
sont valides, mais quatre organismes échouent à au moins une petite cellule
conditionnelle. Le détecteur par transition franchit `0,75` sur `degraded` mais ne bat
pas toujours la quantité de mouvement triviale; sur `blocked`, le trivial atteint
`0,948..1,000`.
Diagnostic: l'agrégation par trial rend M et le trivial parfaits sur les deux fautes.
Le défaut porte donc sur l'unité temporelle de décision et sur des interventions
résolubles sans relation commande→effet. B2' simple égale ou bat M sur cinq organismes.
Avis Claude: non requis pour appliquer la règle d'arrêt pré-enregistrée.
Arbitrage Anthony: non requis sous D-004.
Conséquences: BODY-SCHEMA-001 ne qualifie pas J1; aucune reprise ni modification post
hoc. Le rapport est `docs/research/body_schema_001_technical_stop.md`.
Condition de réouverture: aucune sous BODY-SCHEMA-001.

## D-050 - Pré-enregistrement BODY-SCHEMA-002

Date: 2026-07-27
Décision: proposer un successeur J1 qui sépare prévision moyenne, incertitude et
surveillance d'agence.
Statut: protocole et demande de revue prêts; aucun code ni calcul `19391+`.
Modèles: F reprend la ridge protégée simple B2'; E est un bootstrap de la même base,
chargé seulement de l'incertitude; A accumule causalement quatre innovations
consécutives.
Hypothèse nouvelle: une faute `mirrored` conserve la magnitude marginale des cibles
mais inverse leur direction effective. A doit la détecter et battre un détecteur fondé
sur la seule quantité de mouvement. `blocked` reste le contrôle J1 de commande sans
effet.
Statistique: unité faute = trial, couverture conditionnelle agrégée sur organismes avec
effectifs publiés, baseline de commande désalignée B-action, familles Holm séparées.
Graines proposées: smoke `19391..19396`, test `19501..19524`, statistique
`2026072707`.
Avis Claude: revue contradictoire obligatoire via
`docs/research/body_schema_002_review_request.md`.
Arbitrage Anthony: non requis pour la rédaction sous D-004.
Conséquences: code, smoke, test et toute reprise J5 interdits avant verdict.
Condition de réouverture: corrections Claude, faute mirrored trivialement séparable,
baseline B-action invalide, calibration encore sous-puissante ou composant J1 manquant.

## D-051 — Contrat BODY-SCHEMA-002 révisé après diagnostic

Date : 2026-09-09.
Décision : préparer la révision prospective du contrat et la prévision persistante,
conformément à la demande d'Anthony d'effectuer les étapes proposées après l'audit.
Statut : préparation documentaire achevée ; revue r2 requise avant code ou calcul.

Constats vérifiés par lecture : métrique angle/delta dupliquée, sigma dépendante de
ramp_class postérieure, porte d'absence de fuite constante. Le registre de modèles,
la promotion et les reprises existent mais ne démontrent pas encore la restauration
d'une capacité apprise. Aucun nouveau test, entraînement ou résultat de simulation.

Proposition : entrée causale dédiée et invariance, calibration globale, comparateur
entraîné sans commandes, déroulement libre, diversité du contenu des trajectoires,
candidat indépendant de l'actif, promotion avec marge pratique et plafond cumulatif.
Qualifications séparées : prévision, persistance, calibration et détection. F seul ne
qualifie pas J1 intégralement et ne rouvre pas J5.

Méthode proposée : développement borné sur provenance neuve, validation de configuration
séparée, puis manifeste confirmatoire complet et revu. Budget de première itération
proposé : 15 minutes par invocation, 60 minutes cumulées, génération/évaluation incluses.
Seuils d'usage à fixer sur développement avant validation ; aucune ancienne porte
n'est assouplie rétroactivement et aucune campagne close n'est reprise.

Artefacts :
- docs/research/body_schema_002_preregistration.md : contrat r2 ;
- docs/research/body_schema_002_persistence_plan.md : interfaces, réception et suite cumulative ;
- docs/research/body_schema_002_review_request.md : revue ciblée actualisée ;
- docs/research/body_schema_002_proposal_20260727.md : copie exacte de la proposition v1.

SHA-256 de l'archive v1 :
20f95a967d07da65eaae3a7c4b37a2f7df441cd996efcc7543aee5493d4225c3.

Avis Claude : non reçu ; aucun verdict n'est présumé. La revue demandée porte sur
l'implémentation r2 et son développement, pas sur le smoke v1 ni la confirmation.
Action Anthony : transmission du dossier préparé, ANT-010.
Action Codex : intégrer ensuite le verdict et poursuivre le plan selon son périmètre.
Conséquences : les réserves 19201..19224, 19391..19396 et 19501..19524 restent fermées ;
confirmation et J5 non autorisés. Aucun achat, mouvement physique ou collecte humaine.
Condition de suite : verdict r2 explicite, corrections intégrées et manifeste de
développement fixé avant premier calcul. La confirmation requiert un gel ultérieur.


## D-052 — Intégration de la revue BODY-SCHEMA-002 r2

Date : 2026-09-09. Verdict : AUTORISER AVEC CORRECTIONS BLOQUANTES.
Auteur de la revue : Codex, à la demande d’Anthony en remplacement de Claude ;
aucune indépendance ni attribution à Claude revendiquée.
C1–C6 intégrées textuellement dans le contrat et le plan de persistance : gel
temporel, équité B, validation, dépendances des preuves, atomicité et budget durable.
Autorisation : manifeste puis code, tests, développement MuJoCo borné et intégration
persistante après réception. Validation seulement après gel. Confirmation, réserves
historiques, J5 et A→B→A→C restent fermés.
Action Codex : fixer le manifeste puis exécuter les contrôles et le développement.
Action Anthony : aucune transmission supplémentaire requise.


## D-053 — Prévision corporelle persistante et validation de recette

Date : 2026-09-09. Statut : livrable F persistant réalisé, portée développement et
validation de configuration. Aucun J1 intégral, aucune confirmation ni agence qualifiée.

C1–C6 implémentées pour la capacité F et ses comparateurs. Contrat causal et calibration
synthétique vérifiés ; entrée privilégiée refusée et contrôle négatif sensible à une
fuite volontaire. Candidat séparé, huit occasions de promotion, référence fixe et marge
pratique. Activation par paquet et preuves, écritures atomiques et registre complet de
rejeu. Reprise entre trials et prochaine mise à jour bit-identiques en nouveau processus.

Variante dev v1 : arrêt du vérificateur avant publication de performances, à cause d'un
snapshot restauré dont history restait partagée. Correctif et test d'immuabilité ; v2
relance les six organismes entiers avec même provenance de développement réutilisable.
Ancien manifeste/artefacts préservés, budget cumulé non réinitialisé.

Six organismes dev verts. B3 choisi explicitement avant validation comme témoin sans
action : moyenne 3,981° contre 4,091° pour B13. Manifeste de validation gelé et empreinte
97edbe58fdeed02c861614eb5d5147d0872dd20d89efba8d8d59b282165f9647
avant accès. Six nouveaux organismes, apprenants neufs, sans réglage sur leurs scores.

Résultat validation : F moyenne 0,435216° à un pas contre prior 1,433081° et B3 4,326102° ;
0,464152° à 0,1 s ; 0,579012° à 0,5 s. Six/six satisfont les seuils figés de prévision,
déroulement et persistance. Statut : validation de recette sur formes connues, deux
organismes par régime ; aucune précision confirmatoire revendiquée.

Activation : six F de développement dans leurs mémoires du noyau, références immuables
et preuves par paquet. Requêtes servies identiques après redémarrage. Calibration et
détection non qualifiées ; le succès de la recette multi-pas sur validation ne modifie
pas rétroactivement les statuts des paquets de développement.

Vérification : 24 tests de contrat, 3 tests de frontière de validation ; suite finale
327 tests verts en 25,52 s. Supervision extérieure des calculs/tests : environ 121 s
cumulées sur 3600 s, plafond individuel 900 s. Journal exact dans le budget SQLite.

Artefacts : docs/research/body_schema_002_results.md et .json ; manifestes et journal
liés au rapport. Les essais restent dans body_schema_002_r2_dev_v1, v2 et validation_v1.
Action Codex suivante : préparer un protocole cumulatif distinct ou un manifeste
confirmatoire à nouvelles formes, selon le jalon suivant ; revue avant leurs calculs.
Action Anthony : aucune intervention requise pour ce lot ; ANT-010 clos.
Restrictions : E/A MuJoCo non qualifiés, bootstrap E pas encore raccordé ; reprise
physique intra-trial non qualifiée ; confirmation, réserves historiques, J5,
A→B→A→C et matériel restent fermés.

## D-054 — Mandat de progression autonome et CUMULATIVE-001

Date : 2026-09-09. Anthony demande de poursuivre jusqu'à des avancées notables et
prometteuses, en utilisant la RTX 5080 disponible et en notant avancées et échecs.
Ce nouveau mandat autorise les nouveaux travaux cumulatifs en simulation préparés
sous CUMULATIVE-001. Il remplace l'attente procédurale sur leur ouverture ; les anciens
résultats et les réserves historiques ne sont pas réouverts. Pas de matériel ni achat.

GPU vérifié localement : NVIDIA GeForce RTX 5080, 16303 MiB, CUDA disponible,
PyTorch 2.11.0+cu128. Premier cycle borné à 90 minutes cumulées et 15 minutes par
invocation avec journal durable ; pas de service de calcul payant.

Pré-enregistrement : docs/research/cumulative_001_preregistration.md, fixé avant code.
Comparer mémoire cumulative ridge, mémoire courte et MLP CUDA avec/sans rejeu dans
A→B→A→C ; contrôler l'oubli avant de revendiquer la consolidation. Conserver F r2
inchangé. Nouvelle étape comportementale à spécifier avant ses calculs.
Auto-revue Codex explicitement non indépendante ; toutes variantes, y compris négatives,
seront consignées. Action Codex : exécuter le protocole et progresser selon les preuves.
Action Anthony : aucune intervention requise. Aucun verdict Claude présumé.

## D-055 — CUMULATIVE-001 : candidat persistant et choix utile validés sur ce banc

Date : 2026-09-09. Mandat D-054 accompli pour ce cycle : avancées notables avec
succès et échecs consignés, sans ouverture des anciennes réserves ni essai matériel.
Rapport : docs/research/cumulative_001_results.md, JSON, graphique et journal associés.

Six vies dev puis 12 vies neuves A→B→A→C ; recette neuronale figée. Réseau avec
rejeu, MAE finale A/B/C 0,079515°, −53,19 % contre réseau naïf et −77,92 % contre
ridge cumulative, 12/12 vies favorables. Acquisition/rétention/récupération/reprise
passent. Retour A : gain relatif moyen par vie 69,93 % face à une instance neuve.
Reprises CUDA exactes des deux réseaux sur les 18 vies, avec optimiseur et mémoire.

Usage v1 négatif : aucune amélioration des trajectoires, plus de variation de commande.
Non promu. V2 distincte : choisir la cible atteignable avant échéance. Dev positif,
puis validation préspécifiée sur 192 situations de 12 corps distincts : 190 réussites,
utilité 47,031° contre prior prudent 38,125° et ridge 41,667°. Portes vertes.
Échecs locaux et absence du naïf dans la comparaison comportementale déclarés.
Oubli naïf généralement faible : aucune preuve de correction d'oubli catastrophique.

Décision : conserver le réseau à rejeu comme candidat expérimental persistant et
la sélection avant échéance comme usage probant dans cette famille de simulations.
Pas d'activation neuronale dans CognitiveKernel à ce stade ; F r2 déjà actif conservé.
Pas de revendication de vie physique continue, de rupture détectée ou de confirmation
générale. Revue Codex non indépendante, nouveaux cas de la même famille.

Vérification : 336 tests verts en 24,29 s ; publication vérifie 141 empreintes et
recalcule les scores comportementaux bruts. Budget 496,812 s / 5400 s, 13 invocations
supervisées terminées, aucune réservation restante. RTX 5080 effectivement utilisée.
Les données locales sous data/ sont exclues de Git et doivent être conservées.

Action Codex suivante lors de la poursuite : intégration du candidat au noyau puis
rupture de dynamique observable et récupération dans une nouvelle variante ; ajouter
le naïf au contraste comportemental. Ne pas régler sur les banques déjà consommées.
Action Anthony : aucune intervention requise pour le lot livré.


## D-056 — Résilience et apprentissage intrinsèque comme direction prioritaire

2026-09-10. Anthony autorise la suite et précise le but : un noyau robuste et résilient,
capable d'apprendre dans des situations nouvelles, de comprendre environnement, présence
propre et interlocuteur humain, de former objectifs/sous-objectifs et d'incarner ensuite
un corps électromécanique. L'analogie nouveau-né porte sur le développement intrinsèque.
La précision motrice ne constitue pas l'objectif final.

Cadrage intégré dans DEVELOPMENTAL_ARCHITECTURE.md. RESILIENCE-001 commence : rupture
non annoncée, réponse interne à la surprise, mémoire d'acquis, récupération fonctionnelle
et intégration transactionnelle au noyau. Protocole avant calcul dans
`docs/research/resilience_001_preregistration.md`. Sous-objectifs de récupération codés
explicitement ; exploration intrinsèque ouverte et compréhension humaine non revendiquées.

Budget distinct 90 min, 15 min/invocation, RTX 5080 ; nouvelles banques, anciennes sources
gelées conservées. Auto-revue Codex non indépendante. Action Codex : implémenter,
vérifier, exécuter le développement puis validation neuve si justifiée par les preuves.
Action Anthony : aucune intervention requise. Simulation uniquement.

## D-057 — RESILIENCE-001 : récupération répliquée, fragilité fonctionnelle à traiter

2026-09-10. Le cadrage D-056 est inscrit dans l'architecture, le brief et le pilotage.
Un service neuronal expérimental est intégré à la mémoire du noyau : expériences
atomiques, checkpoints complets, archives immuables, détecteur et sous-objectifs de
récupération, reprise exacte et absence de double apprentissage après interruption.

V1 arrêtée après première vie pour alias d'état Adam ; test rouge puis correction,
sources conservées. V2 six vies complètes : quatre portes sur cinq, mais −9,78 %
d'utilité pendant récupération contre naïf ; non promue et validation non lancée.
V3 distincte préspécifiée : forte surprise immédiate et trois essais de plasticité
sans ancien rejeu, puis mémoire récente ; archives préservées. Six nouvelles vies dev,
puis 12 nouvelles vies de validation, toutes les portes fixées passent.

Validation v3 : 24 changements détectés dès le premier essai, aucune fausse alarme
initiale, 24 sous-objectifs ouverts/clos et 12 rappels. Utilité post-rupture 16,782°
contre naïf 16,100° (+4,24 %) et récente 11,354° (+47,81 %). Rejeu cumulatif 0,602°,
figé 0°. Réussite pendant récupération 93,52 %, finale 137/144 (95,14 %).
Retour : utilité +2,54 % contre naïf, sans domination sur toutes les métriques.
Douze reprises exactes sur validation ; état de plasticité et prochaine mise à jour inclus.

Décision : garder v3 comme base expérimentale de récupération, preuve bornée à cette
famille. Le registre reste en état candidat : le résultat de recette n'est pas une
qualification universelle de chaque paquet. Le modèle F actif antérieur est conservé.
La génération d'objectifs reste une règle explicite et les expériences d'apprentissage
sont fournies par le banc ; autonomie ouverte et compréhension humaine non établies.

Limite décisive : life-04 de validation atteint seulement 50 % de réussite finale
après ralentissement, utilité 5°/11,667° atteignables, malgré erreur prédictive 0,0815°.
La clôture du sous-objectif prédictif peut donc masquer une faiblesse fonctionnelle.
Pas de tuning sur ce cas. La priorité suivante est de relier besoin interne, choix
d'expériences et clôture sur compétence observée, avec une nouvelle variante et de
nouveaux cas ; élargir ensuite les perturbations et leurs instants.

Validation/audit : 345 tests en 24,95 s ; 234 empreintes et 1728 situations vérifiées
sur validation. Sources gelées, continuité mécanique et reprises contrôlées. Un reçu
documente le contrôle supplémentaire de collision de graines réalisé juste après
lancement suite à un échec d'enrichissement facultatif du manifeste ; zéro collision,
manifeste original inchangé, protocole fixé avant lancement. Auto-revue non indépendante.
Budget final 1022,517 s / 5400 s, 22 invocations ; aucune réservation inachevée.
RTX 5080 effectivement utilisée. Environ 339 Mo de données locales exclus de Git.

Rapport : docs/research/resilience_001_results.md ; journal et manifestes associés.
Action Codex suivante : nouvelle épreuve de besoin d'apprentissage fonctionnel et
choix d'expériences ; ne pas réouvrir les banques closes. Action Anthony : aucune.


## D-058 — Besoin fonctionnel et choix d'expériences, RESILIENCE-002

2026-09-10. Anthony autorise à enchaîner. Le nouveau cycle examine la clôture du
besoin d'apprentissage à partir des résultats vécus et une sélection intrinsèque
restreinte d'expériences, comparée au cycle fixe et au hasard. Prédiction directe
à l'échéance, marge estimée sur expériences réellement observées, aucune donnée
privée du juge dans le noyau. Capacité de suivi honnête et valeur propre du choix
actif seront jugées séparément, avec critère sur la pire vie.

Protocole fixé avant code/calcul : docs/research/resilience_002_preregistration.md.
Budget propre 5400 s, 900 s/invocation, sources et banques précédentes inchangées.
Nouvelles vies, instants de rupture variables non transmis à l'agent. Catalogue
et règles écrits explicitement ; aucune autonomie ouverte présumée. Auto-revue
Codex non indépendante. Action Codex : contrats, développement complet, validation
neuve uniquement pour une capacité étayée. Aucune action Anthony requise.

## D-059 — RESILIENCE-002 : persistance acquise, choix actif non répliqué

2026-09-10. Cycle D-058 complet : prédiction terminale, promesses avant action,
résultats vécus, besoin et sélection de catégorie persistés atomiquement dans le
noyau. V1 stoppée après deux commits : score NumPy non relisible de façon sécurisée ;
sources et vie partielle conservées. V2 convertit le score en float natif, sans
modifier les règles d'apprentissage. 358 tests passent ; 18 reprises exactes.

Six vies dev : gain actif +17,77 % contre cycle, 91,48 % de l'oracle. Douze nouvelles
vies de validation : effet inversé à −15,20 %, réussite finale 143/144, pire vie
91,67 %, mais seulement 71,18 % de l'oracle. Récupération active et sélection
échouent. Cycle fixe 100 %/80,56 %, uniforme 100 %/74,00 %. Ne pas promouvoir le
sélecteur actif ; garder le cycle comme référence sans qualification universelle.

Le code gelé restreignait l'honnêteté aux checkpoints 6/fin, sans exclusion explicite
de 0 dans le texte. Audit strict ajouté sans modifier l'analyse gelée : moniteur
actif 22/57 états clos contredits (38,60 %), dont quatre après apprentissage ; même
le taux restreint 4/39 (10,26 %) échoue. Couverture 54,17 %. Aucune qualification.

Life-03 montre le couplage fragile : alarme tardive sans nouveau changement physique,
marge globale 3,515° et repli vers 5°/23,333° disponibles, malgré 12/12 réussites.
La contribution relative des composants reste à isoler ; pas de réglage sur ces vies.

573 expériences du noyau auditées en validation, 73344 pas et 36672 updates par
politique ; 1296 situations, 3888 décisions corrélées. 431+885 empreintes nouvelles
et 375 anciennes vérifiées sans écart. Budget 618,561 s/5400 s, 19 invocations
terminées (une erreur technique v1), aucune en cours. Environ 112,9 Mo hors Git à
préserver. Sources de banc figées, registre candidat, aucune activation globale.
Auto-revue non indépendante, simulation uniquement.

Action Codex suivante : nouveau protocole distinguant compétence, preuves récentes,
lacunes locales et changement global avant de guider l'exploration. Nouvelles banques,
aucune réouverture des validations consommées. Cadrage D-056 prioritaire, aucune
action Anthony. Rapport : docs/research/resilience_002_results.md.

## D-060 — Changement de substrat : la vision dans la boucle, cou à deux axes

2026-09-10. Anthony retient l'option (a) de `PROPOSITION_SUBSTRAT.md`, préparée par
Claude Opus 5. Le banc à un axe observé par cinq scalaires cesse d'être le substrat des
travaux cognitifs. Cette décision porte sur le terrain d'expérimentation, pas sur les
mécanismes ni sur les résultats acquis.

Constat qui la motive. Sur les neuf campagnes de LIFE-009 à RESILIENCE-002, toutes menées
sur le même banc, tout ce qui relève de la régression réussit — jusqu'à 0,0795° d'erreur
d'angle — tandis que toute porte mesurant la connaissance de soi ou la qualité d'un choix
échoue ou ne se réplique pas : incertitude et calibration jamais qualifiées, détection de
faute battue par « il y a moins de mouvement », contrôleur d'orientation sans gain,
moniteur d'honnêteté contredit sur 22 clôtures sur 57, choix actif à +17,77 % en
développement puis −15,20 % en validation. Quatre campagnes sont mortes sur une porte de
faisabilité ou de marge avant de tourner. La marge est donc déjà correctement mesurée,
mais appliquée à la variante proposée et jamais au banc. C'est le banc qui est vide : sur
cinq scalaires et un axe, une ridge est presque optimale et aucun mécanisme cognitif n'a
de quoi se payer.

Décision. La vision entre dans la boucle : l'observation devient une image plus la
proprioception, et l'angle du cou cesse d'être l'état du monde pour devenir un pointeur
vers une portion du monde. Une articulation d'inclinaison est ajoutée au jumeau MuJoCo,
portant l'espace sensorimoteur d'environ 5,3 vues à une quinzaine de cellules et donnant
un schéma corporel bidimensionnel. L'écart assumé avec le montage physique à un servo est
sans conséquence sous D-008, le banc v1.0 (ANT-009) n'étant pas construit.

Trois capacités enchaînées, chacune opposée au témoin simple le plus fort disponible :
C1 retrouver un objet désigné par son apparence, contre le retour au dernier angle vu ;
C2 localiser un changement sous budget de mouvements, contre balayage uniforme et
différence de pixels par cellule ; C3 conserver C1 en apprenant C2. Les capacités sont
promues séparément et gardent chacune son niveau de preuve.

Règle nouvelle, contraignante. La sonde de marge s'applique désormais au banc avant toute
conception de mécanisme, et non à la seule variante. Avant tout pré-enregistrement, mesurer
l'écart entre le témoin trivial et une borne supérieure sur la tâche ; si l'écart n'est pas
exploitable, la tâche est rejetée avant qu'une ligne de mécanisme ne soit écrite. Critère
d'abandon fixé maintenant : si C1 ne montre pas cette marge, ce substrat est déclaré épuisé
à son tour et aucun mécanisme n'est conçu dessus.

Allègement documentaire. Un pré-enregistrement, un rapport et un journal par capacité.
RESILIENCE-002 a produit 21 fichiers dans docs/research pour dix minutes de calcul : ce
volume était calibré pour des campagnes de plusieurs heures. Le développement redevient
libre — déboguer, essayer et jeter sans rebaptiser chaque correction en hypothèse ni
consommer de banque confirmatoire. La confirmation est rare et réservée à une capacité
dont la marge est établie.

Budget, mesuré sur la machine le 10 septembre et non estimé : 9 242 pas/s en physique
seule, 1 878 pas/s avec rendu 128×128 (37,6× le temps réel), 18 720 images/s
d'entraînement VisualJEPA sur RTX 5080. Le goulot est le simulateur et non le GPU, d'un
facteur dix : agrandir le réseau ne coûte presque rien, collecter l'expérience coûte tout.
Une campagne complète avec vision tient dans l'heure ; la consigne « campagnes visuelles
~250 min » du brief de juillet ne décrit plus cette machine.

Ce qui ne change pas. Le cadrage D-056 reste la direction : noyau résilient, apprentissage
intrinsèque, développement incarné, précision motrice secondaire. D-008 tient, simulation
uniquement, aucun achat ni manipulation. Les banques closes ne sont pas réouvertes, les
sources gelées ne sont pas modifiées, les acquis conservent leur niveau de preuve et leurs
limites. Aucune promotion n'est accordée par cette décision. Le registre du noyau reste
candidat.

Action Codex : ajouter l'axe d'inclinaison et son contrat d'observation, construire la
tâche C1, exécuter la sonde de marge — témoin trivial contre borne supérieure, quelques
dizaines de vies, moins d'une heure de calcul — et publier ce seul chiffre. S'arrêter à la
première porte rouge. Aucun mécanisme cognitif, aucun pré-enregistrement et aucune banque
de confirmation avant que cette marge existe.
Action Anthony : aucune ; l'arbitrage demandé est rendu.
Blocage : aucun. Proposition et argumentaire : `PROPOSITION_SUBSTRAT.md`.
## D-061 — Les octets des sources sont l'unité d'audit : Git ne les normalise plus

2026-09-10. Incident et clôture, sans perte. Le dépôt déclarait `*.py text eol=lf` dans
`.gitattributes` depuis le 21 juin, alors que les manifestes gèlent des SHA-256 des octets
bruts des sources. Toute normalisation de fin de ligne casse donc une empreinte sans rien
signaler. Le défaut était latent et général — la machine a `core.autocrlf = true` et
n'importe quel `git clone` produisait le même effet — mais il a été déclenché par le commit
du travail de septembre, dû à Claude Opus 5, qui a réécrit en LF onze sources `.py` écrites
en CRLF : 566 références d'empreintes dans 113 manifestes, sur 1 477 références `.py`
vérifiables.

La causalité est établie et non supposée. `resilience_002_previous_integrity.json`, écrit
par Codex le matin même, enregistre zéro écart sur `cumulative_001_results.json` et
`resilience_001_validation_v3_results.json` ; ces deux mêmes fichiers ont échoué après le
commit.

Cause racine fermée. `.gitattributes` passe à `* -text` : Git ne transforme plus rien et
restitue les octets tels quels. `-text` l'emporte sur `core.autocrlf`, donc la protection
ne dépend pas de la configuration d'une machine. Vérifié par clone neuf depuis `origin` :
`source_frozen` 11/11 et `driver_sha256` valides.

Restauration intégrale, sans re-gel. Six sources ont été reprises depuis
`data/processed/experiments/resilience_002/source_v1`, que Git n'avait jamais touché. Les
cinq sources BODY-SCHEMA-002 antérieures à la convention d'archivage n'existaient nulle
part ailleurs et ont d'abord été déclarées perdues. Elles ne l'étaient pas : leurs fins de
ligne n'étaient pas mélangées arbitrairement mais en LF partout sauf le dernier
terminateur, en CRLF — les deux derniers pour `body_forecast.py`. Cette forme reproduit
exactement les empreintes gelées `bd4065f5`, `d2b35cb7`, `2765cad3`, `d9cf0fd7` et
`d854bc7f`. C'est donc le manifeste gelé lui-même qui certifie la restauration : aucune
empreinte n'a été réécrite et aucune garde assouplie.

Arbitrage Anthony : ne pas adapter la garde pour qu'elle compare un contenu normalisé. La
comparaison sur octets bruts est ce qui donne sa valeur au gel ; la rendre tolérante aux
fins de ligne aurait échangé une propriété d'audit contre un test vert.

État vérifié. 358 tests passent, aucun échec ; `run_validation()` de BODY-SCHEMA-002 refuse
de nouveau sur la garde « banque déjà exposée » et non sur « le code a changé depuis le
gel ». Balayage de 2 369 références fichier → SHA-256 dans tout l'arbre de travail : ne
subsistent que les entrées `dev_v1`, qui désignent des sources v1 abandonnées dont les
archives correspondent exactement, et une dérive antérieure sur un fichier de travail non
suivi de REAFFERENCE-003. Le contrôle de Codex rejoué rend ses compteurs exacts, 141 et
234 références, zéro écart. Aucun résultat n'est modifié et aucun niveau de preuve ne bouge.

Règles. Les octets bruts des sources sont l'unité d'audit du projet ; aucun attribut Git ne
doit les transformer. Une source gelée n'est jamais modifiée puis re-gelée sous couvert de
reprise. Toute source destinée au gel est archivée à côté de ses résultats, comme le fait
la convention `source_v1` : c'est elle qui a rendu six des onze fichiers récupérables sans
reconstruction. Enfin, `body_schema_002_validation.py` est audité par la clé
`driver_sha256` du manifeste et non par `source_frozen.files` — un contrôle d'intégrité
indexé par chemin seul le manque et rend un vert trompeur.

Action Codex : aucune ; D-060 reste la tâche en cours. Action Anthony : aucune.
Blocage : aucun.
