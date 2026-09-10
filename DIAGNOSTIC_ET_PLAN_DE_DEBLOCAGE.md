# Émergence — diagnostic scientifique et plan de déblocage

**Date : 9 septembre 2026.** Audit commencé le 8 septembre, terminé le 9, heure de Paris.

**Périmètre :** état local du dépôt, code actif, rapports et artefacts d'expériences disponibles, tests exécutés pendant cet audit et littérature scientifique consultée sur Internet. Dernier commit observé : `6a30837`, daté du 27 juillet 2026 ; plusieurs travaux BODY-SCHEMA et documents de pilotage étaient déjà modifiés ou non suivis par Git. Ils font partie de l'état audité.

**Statut :** diagnostic et recommandations. Ce document ne modifie pas les décisions expérimentales antérieures, ne promeut aucun modèle et ne lance aucune nouvelle campagne. Les conclusions nouvelles de lecture de code sont distinguées des résultats historiques. La recherche bibliographique est ciblée sur les verrous du projet ; elle ne prétend pas être une revue systématique exhaustive.

## 1. Le diagnostic essentiel

**Émergence dispose désormais d'une infrastructure sérieuse et de plusieurs apprentissages locaux réels, mais pas encore d'une démonstration intégrée de développement cumulatif.** La stagnation s'explique principalement par trois écarts :

1. **Entre ce qui est mesuré et la capacité recherchée.** Une baisse d'erreur latente, une absence de collision ou une couverture statistique ne prouvent pas, seules, une meilleure compréhension sensorimotrice.
2. **Entre une expérience valide et une expérience seulement bien encadrée.** Plusieurs campagnes ont des protocoles détaillés, des digests et des tests verts, mais une manipulation insuffisamment observable, des données redondantes ou une marge de progression non établie.
3. **Entre les acquis des branches et ceux d'un même organisme.** La persistance du noyau, les prédicteurs, la mémoire visuelle et les expériences de consolidation existent ; leur composition en une capacité qui apprend, agit, redémarre et conserve ses progrès reste à démontrer.

**La décision structurante recommandée est de donner la priorité à une boucle cumulative observable, avec un modèle simple utilisable, un évaluateur stable et des apprentissages promus par capacité.** L'augmentation de taille du réseau, un nouveau score de curiosité ou une nouvelle variante de plans ne répondraient pas aux causes déjà identifiées.

Le projet ne repart pas de zéro. Sa meilleure prochaine preuve serait :

> Dans un monde simulé, la même tête apprend sa dynamique, anticipe l'effet d'une commande nouvelle, détecte une rupture de cette relation, conserve son modèle après redémarrage, puis apprend un changement sans effacer ce qu'elle savait déjà.

Cette démonstration respecte la vision développementale. Les tâches d'évaluation servent à vérifier ses capacités ; elles n'imposent pas une récompense externe unique à toute sa vie. Le projet ne fournit aujourd'hui aucune base pour promettre une intelligence générale ou une émergence ouverte. Il permet en revanche de construire une progression sensorimotrice vérifiable.

## 2. Ce qui a été testé et ce que cela établit

| Branche | Résultat documenté | Conclusion défendable |
|---|---|---|
| Navigation LNN / DAgger | Le checkpoint historique passe de 20,66 % de ticks de collision en imitation seule à 1,21 % après DAgger. Mais E1 retrouve 3,30 ± 0,47 % sur cinq réentraînements de la recette observation-only. | Corriger la distribution des données visitées est utile. Le checkpoint exceptionnel ne représente pas la performance moyenne d'un algorithme. |
| Couplage JEPA–LNN, S2, E1–E3, S4 | Latent dynamique : 7,73 % de collision ; latent zéro : 7,75 %. E3 améliore le nominal avec l'auxiliaire JEPA, sans domination sur les impacts randomisés. S4 n'améliore aucune des douze comparaisons de ticks. | Ni l'injection du latent ni le MPC fondé sur la distance décodée ne sont qualifiés. La sélection offline prédit mal le comportement fermé. |
| Critique de collision | AP contexte brut : 0,193 ; latent JEPA : 0,167 ; ultrason seul : 0,035. | Le contexte contient un signal prédictif ; le latent testé en perd une partie. Cela concerne ce JEPA et cette sonde, pas toute la famille JEPA. |
| Vision du banc, v1–v3 | En v3, ratio prédiction/copie à 0,5 s sur mouvements : 0,661 avec action, 0,716 sans. Pose décodable : 11,75° contre 24,90°. Objectifs pose <5° et profondeur non atteints. | La commande apporte de l'information dans ce protocole. La représentation reste insuffisante sur d'autres dimensions. Corpus et graines ont été réutilisés entre versions : les améliorations v1–v3 ne sont pas trois validations externes indépendantes. |
| Exploration active initiale | Ratio final : 0,747 en actif contre 0,732 en babbling ; pose également moins bonne. | Concentrer les observations n'améliore pas automatiquement l'apprentissage. |
| DC-001 à DC-005, dont DC-003R | DC-003R réplique un avantage sur babbling et round-robin dans un monde analytique. Le contrôle recevant la même information supprime la valeur ajoutée revendiquée ; DC-004/005 exposent une fragilité au bruit. | La mesure avant/après est utile dans ce banc. La supériorité du mécanisme développemental fractionnel n'est pas établie. Ces campagnes ne comportaient pas d'apprenant neural réel ni d'oubli. |
| TV-001, avec JEPA réel | 12 paires, 24 runs. Erreur structurée dégradée de 2,80 % en moyenne ; secteur TV : 28,28 % contre 25,19 %. L'apprenant progresse dans les deux conditions. | Résultat négatif interprétable pour cet ordonnanceur. Le bruit pixel peut devenir une invariance apprenable dans le latent ; le pourcentage de temps devant la TV n'est pas une mesure suffisante de gaspillage. |
| J6-R001, replay | 12 triplets, 36 runs. Sur B, réduction relative moyenne de 15,06 % selon la métrique pré-enregistrée ; borne basse de l'IC : 10,66 %. Sur A, oubli insuffisant pour interpréter H1. Plasticité sur C non qualifiée. | Le replay possède une valeur locale de rétention. Son dosage 50/50 ne satisfait pas le compromis demandé ; la priorité par erreur n'apporte pas de gain établi. |
| J6-AR001 | Arrêt au plafond de 75 min, avant les 16 triplets requis. | Non-résultat technique. L'hypothèse de replay adaptatif demeure non tranchée. |
| REF-001 | 16 paires complètes ; H1–H4 échouent. En mouvement mixte, TPR JEPA 0,14266 et pixel 0,13924. | La concaténation de commande au latent global ne qualifie pas la séparation propre/externe. |
| REF-002 / REF-003 | REF-002 : objets parfois hors champ. REF-003 : présence au champ mais effets photométriques trop faibles sur deux paires. | Deux arrêts de validité du dispositif. L'hypothèse de transport spatial n'est pas réfutée. |
| KERNEL / LIFE-001–008 | Mémoire, attribution, reprise, refus sûrs, compétences déclaratives ; 64 cycles, 51 redémarrages, 12 refus sûrs, zéro résidu actif dans LIFE-008. | Infrastructure persistante qualifiée sur ce scénario. Cette endurance ne prouve pas une acquisition neurale autonome. |
| LIFE-009–012 | Marge oracle insuffisante ; incompatibilité plan–garde ; minima non atteints ; 24/24 mises à jour refusées sur un organisme ; oracle myope parfois battu par round-robin. | Le curriculum a été étudié avant de disposer d'un problème d'apprentissage et d'un comparateur correctement qualifiés. La revue BODY-SCHEMA a ensuite montré que les banques d'angle LIFE prétendument distinctes répétaient les mêmes trajectoires. |
| BODY-SCHEMA-001 | Six organismes exploratoires : MAE de l'ensemble 0,348–0,691°, contre 0,977–4,720° pour le prior. La ridge simple est légèrement meilleure sur cinq cas sur six. Portes incertitude et faute rouges. | Progrès réel de prévision à un pas sur ces organismes ; test confirmatoire jamais ouvert. L'audit ci-dessous restreint encore la portée des résultats d'incertitude. |
| BODY-SCHEMA-002 | Pré-enregistrement F/E/A disponible, revue demandée, aucun code correspondant identifié. | Prochaine proposition du dépôt au 27 juillet. Elle demande une correction de contrat avant d'être considérée comme une sortie suffisante de l'impasse. |

Sources locales : [navigation DAgger][dagger], [réplication E1][e1], [couplage][phase0], [E3][e3], [S4][s4], [collision][collision], [vision][vision], [exploration][active], [DC][dc], [TV][tv], [replay][replay], [arrêt adaptatif][arstop], [pilotage][pilotage], [LIFE-012][lifestop], [revue corporelle][bodyreview], [résultats corporels][bodystop], [proposition BODY-SCHEMA-002][body2].

### Vérification réalisée pendant cet audit

Depuis la racine du projet :

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

**Résultat : 300 tests réussis en 64,48 secondes.** Environnement observé : Python 3.11.9, PyTorch 2.11.0+cu128, NumPy 2.4.4, MuJoCo 3.10.0 ; CUDA disponible. Les 48 fichiers de tests actifs couvrent notamment les contrats, les simulations, les entraînements, les statistiques et la persistance.

Les rapports JSON locaux [BODY-SCHEMA-001][bodysmoke] et [LIFE-012][lifesmoke] ont été lus et leurs portes rapprochées des comptes rendus. Les 270 points de courbes déjà publiés de BODY-SCHEMA-001 ont aussi été examinés pour le diagnostic de métriques ci-dessous. Aucun entraînement long ni aucune banque réservée n'a été ouvert. Les résultats historiques n'ont pas tous été recalculés : leur niveau de preuve reste celui de leurs rapports, revues et artefacts consultés.

## 3. Les blocages de fond

### 3.1. La mesure laisse parfois au modèle la possibilité de simplifier la question

Dans [VisualJEPA][visualcode], l'image devient un vecteur global de 128 dimensions après réduction spatiale. Le prédicteur MLP reçoit ce vecteur, les commandes et, selon la configuration, l'horizon. Dans [son entraînement][visualtrain], l'encodeur des cibles est le même réseau courant, utilisé avec arrêt du gradient sur la perte prédictive ; les régularisations de variance/covariance ne figent pas sa sémantique.

Le ratio prédiction/copie est utile pour comparer la prédiction à la persistance dans un espace donné. **Il ne garantit pas que deux encodeurs, ou deux dates d'un encodeur plastique, conservent les mêmes informations.** Un espace peut devenir plus prévisible en abandonnant des détails nécessaires à une future capacité. L'anti-effondrement statistique ne suffit pas à empêcher cet abandon sélectif.

Les traces locales sont cohérentes avec ce risque : sélection trop précoce en vision v1, contexte brut supérieur au latent pour les collisions, ambiguïté TV entre apprentissage du monde et apprentissage du filtrage. Ce n'est pas la preuve que tout progrès latent est artificiel ; c'est la raison de lui adjoindre un juge indépendant.

**Déblocage :** conserver l'apprentissage auto-supervisé, mais mesurer les progrès dans des coordonnées stables : angle observé, anticipation d'une conséquence mesurable, rappel d'un épisode, localisation d'un changement, réussite d'une orientation. Pour comparer les prédicteurs, commencer avec un encodeur commun gelé. La plasticité de l'encodeur devient ensuite une ablation séparée.

### 3.2. Les tâches ne présentent pas toujours le problème que le mécanisme est censé résoudre

Un ordonnanceur ne peut gagner beaucoup si presque toutes les expériences sont équivalentes. Un mécanisme de consolidation ne peut démontrer son intérêt si le monde n'induit pas d'oubli. Un détecteur de changement ne peut reconnaître un objet invisible. Un schéma corporel ne peut prouver sa spécificité si « il y a moins de mouvement » suffit à détecter toutes les fautes.

Le cas LIFE est particulièrement instructif : changer la graine d'exécution ne changeait pas l'angle AS5600 pour un même organisme et un même plan. La revue l'a découvert tardivement. **L'indépendance des graines n'est pas l'indépendance des observations.** BODY-SCHEMA-001 a amélioré cette situation en séparant effectivement les formes de commande.

Autre confusion : la politique privilégiée choisissant la meilleure mise à jour immédiate n'est pas un optimum séquentiel. Si elle perd contre round-robin, son échec ne prouve pas l'absence de curriculum utile. Inversement, un prédicteur privilégié ajusté en ridge n'est pas un plancher d'erreur théorique.

**Déblocage :** qualifier d'abord la faisabilité du dispositif sur des mondes de développement : observabilité, diversité des trajectoires réalisées, erreur irréductible, espace de progression. Utiliser un optimum exact seulement dans une version suffisamment petite pour l'énumérer ; ailleurs, nommer honnêtement une « référence privilégiée myope ».

### 3.3. La protection des acquis peut bloquer l'apprentissage lui-même

[ProtectedFullRidge et BootstrapEnsemble][bodycode] acceptent un candidat si sa MAE sur la protection ne dépasse pas celle du modèle courant de plus de `1e-12`. Cette règle est reproductible ; elle peut pourtant verrouiller un modèle sur un petit ensemble de trajectoires et refuser un compromis utile ailleurs.

Sur LIFE-012/18793, l'ancien couple représentation–protection refusait toutes les mises à jour. BODY-SCHEMA-001 a corrigé ce cas : la marge d'apprentissage existait. Il serait donc faux d'attribuer cet arrêt à une incapacité fondamentale de la descente de gradient ou à un manque de taille du modèle : il concernait ici une ridge et son contrat d'acceptation.

**Déblocage :** séparer le candidat qui apprend du modèle utilisé par le système. Le candidat peut accumuler plusieurs mises à jour dans un espace isolé ; la promotion porte sur une fenêtre et des capacités définies, avec une marge pratique de non-infériorité. Les contraintes physiques restent absolues. Le modèle actif conserve son état tant que le candidat ne satisfait pas le contrat.

### 3.4. La persistance des statuts n'est pas encore la continuité d'un apprenant

Le noyau enregistre des croyances, des expériences, des versions et des états de compétence. Dans [les signaux observés][signalscode], `epistemic_gain` vaut une erreur récente additionnée à sa dispersion ; `learning_progress` compare deux groupes d'essais. Le [catalogue][catalogcode] combine ces quantités avec des poids fixes. Ce sont des heuristiques documentées, pas une estimation acquise du gain d'information d'un modèle du monde.

LIFE-001–008 prouve que le système sait exécuter et reprendre ce processus. La campagne n'établit pas que les mots « croyance », « besoin » ou « compétence » correspondent déjà à une cognition générale apprise.

**Déblocage :** relier une seule compétence concrète au cycle persistant, avec ses paramètres appris, ses données, son état de calibration et son comportement avant/après. Exiger qu'un redémarrage restaure la capacité mesurée. La prochaine progression doit apparaître dans cette boucle, au lieu de rester uniquement dans un rapport de branche.

### 3.5. Le fonctionnement expérimental rend les petites itérations trop coûteuses

J6-AR001 s'arrête sur une limite de temps ; REF-002/003 sur des défauts de génération ; LIFE enchaîne des variantes qui ferment au smoke. Les arrêts ont souvent correctement empêché une conclusion injustifiée. **Le problème est d'avoir figé et engagé une campagne confirmatoire avant d'avoir suffisamment stabilisé son instrument.**

Le dépôt contient aussi des prescriptions plus souples que son chemin critique récent : le [protocole de collaboration][collaboration] prévoit une revue ponctuelle et l'autonomie technique pour les corrections locales. L'attente de revue BODY-SCHEMA-002 est un verrou procédural documenté ; elle ne constitue pas une démonstration d'impossibilité scientifique.

Pour les futurs travaux, Codex devrait séparer explicitement :

| Niveau | Usage des données et règle |
|---|---|
| Développement | Mondes dédiés réutilisables, débogage et comparaisons exploratoires autorisés, toutes les variantes consignées. |
| Validation | Choix limité du modèle et des seuils ; cette banque devient elle aussi une donnée de développement dès qu'elle oriente plusieurs décisions. |
| Confirmation | Hypothèse, configuration, budget et analyse figés ; mondes indépendants, aucune sélection après lecture des scores. |

Prévoir les reprises techniques identiques avant campagne, avec points de sauvegarde et durée totale budgétée. Prévalider le générateur entier sur les contraintes techniques, sans exposer les scores réservés. Ne pas récupérer sélectivement les campagnes déjà closes : cette méthode s'applique prospectivement.

Les critères doivent distinguer un effet absent, une incertitude trop large et une non-infériorité démontrée. Une absence de significativité ne démontre pas l'équivalence. Les intervalles sur différences appariées et l'unité indépendante organisme/session sont plus pertinents que les minima sur des ticks corrélés. Cela rejoint les recommandations d'[Agarwal et al., NeurIPS 2021](https://arxiv.org/abs/2108.13264).

## 4. Trois constats de code à traiter avant la prochaine qualification

### 4.1. « MAE angle » et « MAE variation » sont la même métrique

Dans [`_metrics`][metricscode], la variation prédite et la variation observée retranchent le même angle courant :

```text
erreur_delta = |(angle_prédit_suivant - angle_courant)
                - (angle_observé_suivant - angle_courant)|
             = |angle_prédit_suivant - angle_observé_suivant|
             = erreur_angle
```

**Vérification nouvelle :** sur les 270 points de courbes du rapport BODY-SCHEMA-001, l'écart absolu maximal entre ces deux MAE vaut exactement zéro. Le protocole BODY-SCHEMA-002 prévoit encore les deux.

Cela ne fausse pas la MAE, mais ne fournit pas deux preuves indépendantes de compréhension dynamique. La duplication alourdit artificiellement la famille de tests. Garder une MAE à un pas ; ajouter une mesure réellement différente : prédiction en déroulement libre à plusieurs pas, erreur de phase, ou classification du sens d'une conséquence avec cas immobiles traités séparément.

### 4.2. L'incertitude utilise une information interne et postérieure du simulateur

Dans [`execute_plan`][executecode], `ramp_class` est déterminée à partir de la variation de `env._limited_deg` **après** l'exécution du pas. Dans [`calibration`][calibrationcode], cette classe choisit ensuite la composante MAD de l'incertitude pour chaque exemple évalué. L'étiquette sert donc au calcul des intervalles et des scores de faute, et pas seulement au tableau de résultats.

Cette information n'est pas disponible à un prédicteur limité à l'historique observé avant le pas. Sous une panne, le limiteur est précisément modifié par l'intervention ; l'étiquette peut également révéler indirectement une conséquence de la condition testée.

**Vérification nouvelle, purement synthétique :** avec les mêmes observations autorisées et la même moyenne prédite de 90°, changer seulement `ramp_class` fait passer `sigma` de 1,4826 à 4,4478. Aucune simulation et aucune graine réservée n'ont été utilisées pour cette démonstration de dépendance.

**Portée :** la moyenne prédictive de la ridge n'utilise pas cette étiquette dans ses features. Son progrès de MAE ne disparaît donc pas. En revanche, les intervalles et scores actuels ne constituent pas une qualification de l'incertitude ou de l'agence sous le contrat d'observation annoncé. L'audit établit le chemin de dépendance, sans quantifier son effet sur une future campagne.

Correction recommandée : réserver les classes exactes à l'évaluateur. L'apprenant utilise une échelle globale, ou une classe estimée causalement depuis les observations autorisées. BODY-SCHEMA-002 conserve un MAD par rampe/plateau sans résoudre explicitement l'observabilité de cette classe : ce point doit être clarifié avant implémentation.

### 4.3. La porte « absence de fuite » est fixée à vrai

Dans [`_smoke_gates`][gatescode], la valeur `"3_no_privileged_leak": True` est inscrite directement. Ce champ ne résulte pas d'une vérification du chemin de données. Les tests existants passent donc malgré la dépendance précédente.

Correction recommandée : définir un objet d'entrée du modèle qui exclut les données du juge, puis vérifier une propriété précise : changer régime, labels de faute, états internes et métadonnées d'évaluation, à observations autorisées constantes, ne change ni prédiction ni incertitude ni décision. Le test doit couvrir tout le calcul, et pas uniquement les features de la moyenne.

Ces trois constats expliquent pourquoi **300 tests verts constituent une preuve de fonctionnement des contrats testés, sans garantir la validité scientifique de tous les contrats**.

## 5. Ce que la littérature apporte à la décision

### 5.1. Des représentations spatiales stables avant un grand modèle entraîné localement

[DINO-WM — Zhou et al., 2024/2025](https://arxiv.org/html/2411.04983v2) prédit des features de patches issues d'un DINOv2 gelé, puis optimise des actions pour atteindre une observation cible. L'intérêt transférable à Émergence est la séparation entre perception spatiale, dynamique apprise et mesure comportementale. Ses résultats ne garantissent pas le transfert aux images du banc.

[V-JEPA 2 — Assran et al., 2025](https://arxiv.org/abs/2506.09985) combine un préentraînement sur plus d'un million d'heures de vidéo et une adaptation conditionnée par l'action sur moins de 62 heures de données robotiques. Le faible volume robotique vient après un préentraînement massif : il ne justifie pas d'attendre les mêmes propriétés d'un petit CNN entraîné à partir de zéro sur quelques pièces.

La version récente [V-JEPA 2.1 — Mur-Labadia et al., 2026, v3 de juin](https://arxiv.org/abs/2603.14482v3) renforce notamment la supervision dense et hiérarchique des représentations. Cette piste conforte l'intérêt d'informations spatiales conservées. Ce résultat récent reste à distinguer d'une réplication indépendante dans Émergence.

**Recommandation :** comparer d'abord le CNN actuel à un encodeur compact préentraîné gelé, avec sorties spatiales et calcul des features mis en cache. Le choix du checkpoint dépendra de son empreinte mesurée et de ses sondes sur le banc. Documenter séparément les compétences héritées du préentraînement et les contingences apprises par l'organisme. La branche « tout apprendre de zéro » demeure une question scientifique distincte.

### 5.2. Un modèle du monde doit servir une décision et représenter l'histoire pertinente

[DreamerV3 — Hafner et al., Nature 2025](https://www.nature.com/articles/s41586-025-08744-2) articule un état récurrent, une dynamique conditionnée par les actions et l'apprentissage de comportements dans les trajectoires imaginées. [TD-MPC2 — Hansen et al., 2023/2024](https://arxiv.org/abs/2310.16828) optimise des trajectoires dans un modèle latent. Leurs évaluations portent sur des résultats de contrôle, avec des objectifs de tâche ; elles ne constituent pas une preuve de développement autonome sans objectif.

Pour Émergence, une image seule ne révèle pas toujours le mouvement d'un objet, et un angle instantané ne décrit pas tout l'état d'un actionneur avec inertie ou retard. Une mémoire temporelle devient utile lorsque ces ambiguïtés sont réellement présentes. Une GRU ou un modèle d'état sont alors des candidats justifiés, à comparer à une fenêtre d'observations et à un modèle classique.

Le résultat DAgger historique illustre déjà l'importance de la distribution induite par les actions. C'est précisément le problème étudié par [Ross, Gordon et Bagnell, AISTATS 2011](https://proceedings.mlr.press/v15/ross11a.html).

**Recommandation :** qualifier le classement des actions et les prédictions sur plusieurs pas, puis une orientation réalisée. Un faible score de prédiction offline ne doit plus suffire à choisir le checkpoint de contrôle. Ne pas intégrer immédiatement toute la pile Dreamer : importer d'abord le principe de validation.

### 5.3. La curiosité doit rechercher une information réductible

Le progrès d'apprentissage constitue une hypothèse pertinente depuis [Oudeyer, Kaplan et Hafner, 2007](https://www.pyoudeyer.com/ims.pdf). Il ne découle pas automatiquement de la surprise. [Pathak et al., ICML 2019](https://proceedings.mlr.press/v97/pathak19a.html) utilisent le désaccord entre prédicteurs ; [Plan2Explore — Sekar et al., ICML 2020](https://proceedings.mlr.press/v119/sekar20a.html) planifie l'exploration à partir d'un modèle du monde et d'un désaccord anticipé.

Ces travaux proposent des approximations de l'incertitude réductible. Un ensemble peut rester biaisé, partager les mêmes erreurs ou réagir à un déplacement de distribution : son désaccord ne devient pas automatiquement un gain d'information calibré.

Pour une future expérience, distinguer :

```text
erreur prédictive : ce qui était mal anticipé ;
dispersion résiduelle : mélange possible de bruit, quantification et biais du modèle ;
désaccord : variation des prédictions entre modèles ;
progrès utile : diminution d'une erreur tenue à part, dans un espace d'évaluation stable.
```

Sur le canal d'angle déterministe actuel, appeler le MAD résiduel « bruit aléatoire » serait excessif. Il inclut des erreurs de modélisation. Ne pas les confondre avec du bruit physique irréductible.

**Recommandation :** lorsqu'une boucle d'apprentissage cumulative est qualifiée, comparer couverture uniforme, progrès sur ancres stables et désaccord prospectif à budget égal. Pour une ridge, une baseline de conception d'expériences maximisant l'information de ses features est particulièrement pertinente ; voir la conception D-optimale chez [Boyd et Vandenberghe, §7.5](https://stanford.edu/~boyd/cvxbook/bv_cvxbook.pdf). Les conséquences candidates doivent être estimées depuis l'information accessible à l'agent. La version utilisant le simulateur caché reste un diagnostic privilégié.

Le critère décisif est une capacité apprise plus vite ou mieux conservée. Un comportement qui ressemble à de la curiosité ne suffit pas. Une politique uniforme qui permet le développement recherché constitue un résultat positif pour le système.

### 5.4. Conserver les acquis et rester capable d'apprendre sont deux problèmes

J6-R001 montre déjà qu'un replay uniforme peut aider la rétention tout en ralentissant l'adaptation. De plus, [Dohare et al., Nature 2024](https://www.nature.com/articles/s41586-024-07711-7) montrent une perte de plasticité des réseaux dans plusieurs contextes continus et étudient la réinitialisation sélective d'unités peu utiles. Cette perte de capacité à apprendre de nouvelles tâches est distincte de l'oubli d'anciennes tâches.

**Recommandation :** mesurer les deux avant de choisir une solution. D'abord un replay simple et un compromis explicite ; ensuite seulement, si une perte de plasticité neurale est observée, étudier régularisation ou renouvellement limité d'unités. Le blocage d'acceptation d'une ridge ne justifie pas, à lui seul, cette machinerie.

### 5.5. Un intervalle conforme ne résout pas à lui seul la calibration temporelle

[Barber et al., The limits of distribution-free conditional predictive inference](https://arxiv.org/abs/1903.04684) distinguent couverture marginale et garanties conditionnelles, ces dernières ne pouvant être obtenues en toute généralité sans hypothèses supplémentaires. Leur travail sur [la prédiction conforme hors échangeabilité](https://arxiv.org/abs/2202.13415) traite notamment la dérive de distribution.

Cela ne rend pas impossibles les objectifs finis par régime du projet. Cela interdit de présenter un quantile empirique comme une garantie universelle sur de petites cellules temporelles corrélées.

**Recommandation :** calibrer et évaluer sur des essais séparés, rapporter effectifs et incertitude des couvertures par organisme, fixer la tolérance à partir d'un usage. Pour le moniteur séquentiel, mesurer les faux déclenchements par épisode ou par durée normale, le délai de détection et la TPR au seuil fixé. Une AUROC seule ne décrit pas un détecteur utilisable.

## 6. L'architecture à viser maintenant

Conserver le noyau existant et raccorder une chaîne minimale :

```text
Observations horodatées + historique des commandes
        |
        +--> Prévision corporelle simple : ridge / modèle d'état
        |
        +--> Features visuelles spatiales, initialement gelées
        |
        +--> Mémoire temporelle si une ambiguïté mesurée la justifie
                         |
            Prédictions de conséquences d'actions
                         |
          Compétence bornée : anticiper / orienter / retrouver
                         |
                Exécution MuJoCo et résultat
                         |
           Épisodes persistants + apprentissage candidat
                         |
       Évaluateur indépendant --> promotion par capacité
```

L'incertitude et le moniteur d'agence accompagnent cette chaîne avec des entrées exclusivement causales. Les annotations privilégiées appartiennent au juge. Le modèle actif, le candidat et leurs versions de représentation sont distincts ; un changement d'encodeur entraîne le re-encodage contrôlé des souvenirs concernés.

Cette architecture vise à combiner les acquis déjà disponibles. Elle n'exige ni un latent multimodal unique ni une nouvelle théorie de la motivation. Une représentation partagée pourra être étudiée quand le partage améliore effectivement deux capacités, sans en dégrader une autre.

## 7. Plan d'exécution priorisé

Les étapes ci-dessous sont des propositions pour de **nouveaux** travaux. Les seuils illustratifs doivent être fixés après développement et avant confirmation ; ils ne réinterprètent aucune ancienne porte. Le calendrier dépend du temps disponible et du débit mesuré : l'unité de pilotage proposée est une capacité livrée, pas un nombre d'epochs.

### Étape 0 — rendre l'instrument fiable

**Responsable : Codex.** Préparer un amendement prospectif de BODY-SCHEMA-002 intégrant les trois constats de code. Revue scientifique ciblée sur le contrat causal et l'analyse, sans relancer une campagne close.

Livrables :

- séparation explicite des entrées de l'apprenant et de celles du juge ;
- test d'invariance à la modification des champs privilégiés ;
- suppression de la pseudo-duplication angle/delta dans les hypothèses ;
- contrôle de diversité des trajectoires réalisées, et pas seulement des graines ;
- séparation développement/validation/confirmation et politique de reprise préétablie.

**Sortie :** les métriques et les contrôles correspondent aux informations réellement disponibles en ligne. Si ce contrat échoue, le défaut est corrigé dans le développement ; aucune comparaison de modèles n'est interprétée.

### Étape 1 — livrer une prévision corporelle persistante

**Responsable : Codex.** Utiliser la ridge simple comme candidate de référence. La comparer à persistance et prior physique sur des organismes et formes de commande indépendants. Ajouter un modèle entraîné sans commandes, de capacité comparable, en retirant aussi leur information du prior et des variables dérivées. Décaler les actions uniquement à l'inférence reste un test de sensibilité, pas un contrôle équitable d'apprentissage.

Évaluer une prévision à un pas, puis à 0,1 et 0,5 seconde. Dans les déroulements libres, les observations intermédiaires futures ne sont pas rendues au prédicteur. Les horizons de cette proposition doivent être alignés sur les constantes de temps mesurées du banc.

Le critère actuel d'un gain d'au moins 15 % face au prior peut servir de point de départ à la conception. La marge finale doit aussi avoir un sens en degrés et dans l'usage. **Une ridge qui satisfait la capacité demandée peut devenir la solution ; la complexité du candidat n'est pas une condition de réussite.**

Enregistrer ses coefficients, ses données utiles, sa calibration et son état dans le cycle persistant. Vérifier les mêmes prédictions avant/après redémarrage.

Le contrôle de faute commence par une version séquentielle observable. Pour `mirrored`, vérifier que la cinématique réalisée n'offre pas un simple raccourci d'amplitude : conserver les amplitudes demandées ne garantit pas les mêmes mouvements observés, notamment à l'instant d'intervention. Mesurer le bénéfice de l'alignement commande–conséquence avec des témoins appariés.

**Sortie :** un artefact rechargeable qui anticipe une conséquence inconnue lors de son entraînement. La qualification de la moyenne peut être conservée comme acquis distinct pendant que l'incertitude ou le moniteur restent en développement ; aucune revendication d'agence n'est alors attachée à la seule moyenne.

### Étape 2 — faire gagner la vision sur une capacité locale

**Responsable : Codex.** Construire un monde simple où un événement externe reste visible et contrasté, puis élargir les variations. Vérifier la manipulation dans les images rendues avant entraînement.

Comparer trois voies sur les mêmes données : compensation visuelle simple du mouvement propre, VisualJEPA actuel, prédiction de features spatiales gelées. Pour isoler l'effet de l'action, comparer aussi des prédicteurs avec/sans action sur le même encodeur.

Choisir une seule capacité principale : localiser un changement externe pendant une rotation, ou orienter la tête vers une observation mémorisée. Mesurer la réussite et son coût d'action ; utiliser la perte latente comme diagnostic secondaire. Les objets hors champ constituent un régime séparé avec abstention ou recherche, pas des exemples positifs arbitrairement impossibles.

**Sortie :** une amélioration observable attribuable à un modèle, ou une baseline simple suffisamment bonne pour poursuivre la construction de l'organisme. Si aucun prédicteur ne bat une compensation analytique, conserver cette dernière et identifier l'information manquante avant d'agrandir le réseau.

### Étape 3 — démontrer un apprentissage cumulatif

**Responsable : Codex.** Exécuter des vies simulées de type A → B → A → C. Au sein d'une vie, les paramètres appris et la mémoire persistent ; les éventuelles réinitialisations physiques de l'environnement sont identiques entre conditions et consignées. Les vies indépendantes constituent les réplications.

Comparer apprentissage naïf, replay uniforme et, si utile, modèle perceptif gelé avec seuls prédicteurs adaptatifs. Choisir la fraction de replay sur le développement, puis la figer. Un entraînement joint sur toutes les données peut fournir une référence diagnostique avec son accès aux données futures clairement déclaré.

À chaque phase, mesurer :

- apprentissage du nouveau contexte ;
- rétention et rapidité de récupération de l'ancien ;
- réussite de la capacité comportementale ;
- mémoire, interactions et coût total d'apprentissage.

Comparer à budget identique d'interactions et de mises à jour, et publier séparément les secondes de calcul. Ne pas ralentir artificiellement une baseline simplement pour égaliser son temps : distinguer l'ablation à architecture appariée de la comparaison pratique coût–performance.

**Sortie décisive :** une même instance acquiert B tout en restant capable sur A dans une marge utile, puis retrouve A plus efficacement qu'une instance neuve. Si le compromis échoue, séparer manque de capacité, oubli, changement de représentation et refus de promotion ; chacun conduit à une intervention différente.

### Étape 4 — donner enfin un problème réel à l'exploration active

**Responsable : Codex.** Après les étapes précédentes, comparer couverture uniforme, progrès mesuré sur juge stable, puis désaccord ou conception d'expériences. Fixer modèle, buffer, budgets et distributions d'évaluation ; seule la politique de collecte varie.

Mesurer la quantité d'interactions nécessaire pour atteindre une capacité, l'aire sous sa courbe d'apprentissage et la rétention. L'allocation à une région n'est qu'un diagnostic. Ne jamais alimenter la politique avec la banque finale ; les ancres de sélection font partie de ses ressources de développement.

**Sortie :** conserver une politique adaptative seulement si elle améliore la capacité ou son coût. Sinon, la couverture simple reste active, et les autres capacités continuent à progresser.

### L'étape suivante, au-delà du cou

Une fois cette boucle démontrée, étendre le même contrat à la récurrence d'objets et de situations, puis aux associations entre modalités. La familiarité peut commencer par des voisins proches sur features stables, avec des tests séparant même instance, même catégorie et simple similarité de décor. La vision sociale n'a pas besoin d'attendre l'invention d'un ordonnanceur supérieur.

Les données humaines et le retour au banc restent soumis au périmètre d'Anthony. L'ajout d'un LLM ne devient pertinent pour la cognition du système qu'après l'existence d'épisodes correctement attribués et de capacités mesurées ; son éloquence ne pourra pas servir de preuve de leur acquisition.

## 8. Ce que je recommande de décider

| Priorité | Décision proposée | Conséquence concrète |
|---|---|---|
| Immédiate | Corriger le contrat de mesure BODY-SCHEMA avant toute nouvelle qualification. | Éviter une nouvelle campagne soigneusement exécutée mais non concluante. |
| Immédiate | Conserver des acquis distincts : prédiction, calibration, agence, rétention. | Un échec local ne remet plus toute la construction à zéro ; chaque capacité garde son niveau de preuve. |
| Haute | Faire d'un organisme persistant le support commun des prochaines démonstrations. | Les résultats des branches deviennent des comportements cumulés dans le même système. |
| Haute | Tester une perception spatiale gelée avant un nouvel entraînement visuel massif. | Stabiliser le juge et concentrer le calcul local sur les contingences propres au corps. |
| Haute | Donner un espace explicite au développement itératif. | Déboguer sans consommer des banques confirmatoires ni rebaptiser chaque correction en nouvelle hypothèse. |
| Différée | Reprendre curiosité sophistiquée, nouveau LNN, grand JEPA ou LLM cognitif seulement face à un manque mesuré. | Chaque nouveau composant a une fonction et une expérience discriminante. |

Pour le calcul, commencer par les diagnostics CPU et la mise en cache des features ; mesurer le coût d'un prototype neural court avant de dimensionner une campagne. La présence de CUDA et les temps des derniers smokes ne montrent pas un besoin immédiat d'achat. Les préentraînements à l'échelle de V-JEPA restent hors de portée de ces petits budgets ; utiliser un checkpoint existant et entraîner un prédicteur sont deux engagements très différents.

**Action Codex :** prendre l'étape 0 comme prochain travail technique, puis livrer la compétence persistante de l'étape 1.

**Action Anthony :** aucune manipulation, aucun achat et aucune collecte nécessaires pour appliquer ces premières recommandations en simulation.

**Action Claude, selon le protocole actuel du dépôt :** relire le contrat corrigé de BODY-SCHEMA-002 et ses hypothèses discriminantes ; la demande existante doit intégrer les constats de cet audit.

**Blocage actuel :** BODY-SCHEMA-002 attend toujours sa revue dans le pilotage existant. À cela s'ajoute un défaut de contrat causal mis en évidence ici. Ce document prépare une décision concrète, sans se substituer à cette revue ni demander de réouvrir les expériences closes.

La progression recherchée doit désormais se voir dans ce que la même instance sait faire après une nouvelle expérience et conserve après la suivante. C'est le critère qui donnera aux améliorations du deep learning une valeur réelle dans Émergence.

## Références locales et traçabilité

Les liens ci-dessous pointent vers l'état local audité, qui comprend des modifications non commitées. Les articles scientifiques sont liés directement dans le texte avec leur apport et leurs limites. Les constats nouveaux sont vérifiables dans les fonctions citées ; leurs démonstrations synthétiques n'ont pas modifié le code.

[pilotage]: C:/Users/antho/Documents/Programmation/Emergence/Project_Emergence/PILOTAGE.md
[dagger]: C:/Users/antho/Documents/Programmation/Emergence/Project_Emergence/data/processed/experiments/lnn_dagger_comparison.md
[bodysmoke]: C:/Users/antho/Documents/Programmation/Emergence/Project_Emergence/data/processed/experiments/body_schema_001_smoke/smoke_report.json
[lifesmoke]: C:/Users/antho/Documents/Programmation/Emergence/Project_Emergence/data/processed/experiments/life_012_smoke/margin_plate_report.json
[visualtrain]: C:/Users/antho/Documents/Programmation/Emergence/Project_Emergence/learning/train_visual_jepa.py:305
[collaboration]: C:/Users/antho/Documents/Programmation/Emergence/Project_Emergence/COLLABORATION_PROTOCOL.md
[e1]: C:/Users/antho/Documents/Programmation/Emergence/Project_Emergence/docs/research/jepa_lnn_e1_results.md
[phase0]: C:/Users/antho/Documents/Programmation/Emergence/Project_Emergence/docs/research/jepa_lnn_phase0_results.md
[e3]: C:/Users/antho/Documents/Programmation/Emergence/Project_Emergence/docs/research/jepa_lnn_e3_results.md
[s4]: C:/Users/antho/Documents/Programmation/Emergence/Project_Emergence/docs/research/jepa_lnn_s4_results.md
[collision]: C:/Users/antho/Documents/Programmation/Emergence/Project_Emergence/docs/research/collision_risk_results.md
[vision]: C:/Users/antho/Documents/Programmation/Emergence/Project_Emergence/docs/research/visual_bench_probe.md
[active]: C:/Users/antho/Documents/Programmation/Emergence/Project_Emergence/docs/research/active_exploration_probe.md
[dc]: C:/Users/antho/Documents/Programmation/Emergence/Project_Emergence/docs/research/developmental_curiosity_probe.md
[tv]: C:/Users/antho/Documents/Programmation/Emergence/Project_Emergence/docs/research/tv_real_jepa_001_results.md
[replay]: C:/Users/antho/Documents/Programmation/Emergence/Project_Emergence/docs/research/j6_replay_001_results.md
[arstop]: C:/Users/antho/Documents/Programmation/Emergence/Project_Emergence/docs/research/j6_adaptive_replay_001_technical_stop.md
[lifestop]: C:/Users/antho/Documents/Programmation/Emergence/Project_Emergence/docs/research/life_012_technical_stop.md
[bodyreview]: C:/Users/antho/Documents/Programmation/Emergence/Project_Emergence/docs/research/body_schema_001_review.md
[bodystop]: C:/Users/antho/Documents/Programmation/Emergence/Project_Emergence/docs/research/body_schema_001_technical_stop.md
[body2]: C:/Users/antho/Documents/Programmation/Emergence/Project_Emergence/docs/research/body_schema_002_preregistration.md
[visualcode]: C:/Users/antho/Documents/Programmation/Emergence/Project_Emergence/learning/visual_jepa.py
[bodycode]: C:/Users/antho/Documents/Programmation/Emergence/Project_Emergence/learning/body_schema_001.py:391
[signalscode]: C:/Users/antho/Documents/Programmation/Emergence/Project_Emergence/cognitive/observed_signals.py:230
[catalogcode]: C:/Users/antho/Documents/Programmation/Emergence/Project_Emergence/cognitive/experiments.py:62
[metricscode]: C:/Users/antho/Documents/Programmation/Emergence/Project_Emergence/learning/body_schema_001_campaign.py:142
[executecode]: C:/Users/antho/Documents/Programmation/Emergence/Project_Emergence/learning/body_schema_001.py:203
[calibrationcode]: C:/Users/antho/Documents/Programmation/Emergence/Project_Emergence/learning/body_schema_001.py:495
[gatescode]: C:/Users/antho/Documents/Programmation/Emergence/Project_Emergence/learning/body_schema_001_campaign.py:440
