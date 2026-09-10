# Revue BODY-SCHEMA-002 — révision 2 du 9 septembre 2026

Date : 2026-09-09. Auteur : Codex, à la demande d’Anthony, en remplacement de Claude indisponible. Cet avis n’est pas attribué à Claude et ne constitue pas une réplication indépendante des travaux de Codex.

**Verdict : AUTORISER AVEC CORRECTIONS BLOQUANTES.**

La r2 fournit une voie raisonnable vers une prévision corporelle causale et persistante. La ridge simple suffit comme premier candidat ; aucun manque mesuré ne justifie ici un modèle plus complexe. Les corrections ci-dessous précisent le contrat avant implémentation. Leurs essais de réception sont à réaliser pendant le développement, avant toute interprétation des résultats concernés ou activation persistante. Les valeurs qui dépendent des données restent à établir sur développement, puis à geler avant validation.

## Périmètre et preuves consultées

Revue du [contrat r2](body_schema_002_preregistration.md), du [plan de persistance](body_schema_002_persistence_plan.md), du [diagnostic](../../DIAGNOSTIC_ET_PLAN_DE_DEBLOCAGE.md), §3–4 et étapes 0–1 du §7, et de [D-049 à D-051](../../DECISIONS.md). La [proposition v1](body_schema_002_proposal_20260727.md) et l’[arrêt BODY-SCHEMA-001](body_schema_001_technical_stop.md) ont été lus pour la traçabilité et les définitions reprises explicitement par la r2.

Vérifications statiques effectuées :

- Dans [`execute_plan` et `calibration`](../../learning/body_schema_001.py), l’ancienne classe de rampe est construite après `env.step`, puis choisit une dispersion résiduelle. La r2 corrige ce chemin dans sa spécification ; elle ne l’a pas encore remplacé dans le code.
- Dans [`_metrics` et `_smoke_gates`](../../learning/body_schema_001_campaign.py), angle et delta retranchent le même angle courant, et `3_no_privileged_leak` vaut littéralement `True`. Les constats de l’audit sont confirmés par lecture, sans recalcul des résultats.
- [`ProtectedFullRidge`](../../learning/body_schema_001.py) ajuste le candidat sur les données fournies et ne conserve que les coefficients acceptés. La marge `1e-12` est bien présente. Cette classe, à elle seule, ne définit ni un candidat persistant indépendant ni le cycle complet d’accumulation.
- Le [prior et la base historique](../../learning/life_010.py) dépendent des commandes ; les sorties sont bornées à `[10°,170°]`. Leur réutilisation directe dans B-sans-action réintroduirait l’information interdite.
- [`register_model`](../../cognitive/memory.py) stocke référence et digest sans charger ni vérifier les paramètres. `promote_model` et `apply_competence_assessment` ont chacun leur transaction. `transaction()` ouvre explicitement `BEGIN IMMEDIATE` : entourer naïvement ces méthodes d’une transaction supplémentaire n’est pas une composition valide.
- [`PersistentDevelopmentSupervisor.advance`](../../cognitive/supervisor.py) reprend des étapes d’exécution et d’évaluation, mais ne restaure pas de ridge apprise. Une exécution physique partielle est actuellement abandonnée. La route d’évaluation existante porte sur le suivi servo.

Aucun test, entraînement, calcul statistique ou simulation n’a été exécuté pour cette revue. Aucune banque réservée ni donnée de campagne close n’a été ouverte. Les chiffres historiques, dont les 300 tests verts, ne sont pas des résultats nouveaux ni une preuve de conformité r2.

## Corrections nécessaires avant développement

Les textes normatifs C1–C6 sont à intégrer au contrat et au plan avant le code r2. Une vérification documentaire de cette intégration suffit pour lever ce préalable ; une nouvelle attente de Claude n’est pas requise. Les critères ci-dessous décrivent ensuite les preuves à produire par l’implémentation.

### C1 — Fermer le contrat temporel de calibration et d’évaluation

**Défaut et portée.** Le gel pendant A est explicite, mais la r2 ne définit pas aussi précisément le cycle de calibration de E, le traitement d’une promotion et le moment auquel les prédictions tenues à part sont émises. « Ne pas ajuster avec l’exemple avant son score » ne suffit pas à exclure l’adaptation sur les exemples précédents d’une banque d’évaluation. Le contrôle d’invariance doit également couvrir l’ajustement de la calibration, pas seulement l’appel final à sigma.

**Texte normatif intégrable :**

> Pour chaque version évaluée, achever l’apprentissage et la sélection sur leurs rôles autorisés, figer les coefficients, ajuster la calibration sur son rôle dédié, puis figer le paquet de prédiction avant l’évaluation. Les exemples d’évaluation ne modifient aucun coefficient, normaliseur, dispersion, quantile, seuil ou choix de version, même après leur score. L’historique observable et la fenêtre d’innovations peuvent évoluer causalement. Chaque prédiction enregistre avant exécution la moyenne, sigma et l’intervalle lorsqu’ils existent, ainsi que les versions nécessaires au score ultérieur. Une promotion de E exige une calibration liée à cette nouvelle moyenne avant utilisation de ses intervalles ; aucun recyclage silencieux d’une calibration antérieure. Le modèle, la calibration et le seuil sont fixes sur tout le lot évalué pour A ; seule sa fenêtre évolue et se réinitialise au début de chaque trial.
>
> Le contrôle d’invariance reconstruit également la calibration à résidus observés, rôles d’accès et état aléatoire identiques, en modifiant les annotations privilégiées. Il vérifie ensuite les sorties et décisions avant et après restauration. Les graines du juge ne sont pas des entrées de prédiction ; changer volontairement la graine de l’apprenant et donc ses paramètres constitue une autre expérience, pas le test d’invariance.

**Critère vérifiable.** Une mutation des seules annotations laisse inchangés la calibration reconstruite et les sorties ; une variante dépendant de `ramp_class` échoue. Une modification des cibles d’évaluation laisse inchangé le paquet figé, mais change l’erreur du juge. Les traces prouvent l’émission avant observation et le rattachement exact de l’innovation à sa prédiction, y compris après reprise. Les branches de déroulement libre ne modifient pas l’instance vivante.

### C2 — Rendre le comparateur sans action équitable jusque dans l’ajustement

**Défaut et portée.** Les treize monômes proposés sont distincts, mais constituent une base cubique enrichie de trois interactions de degré quatre, pas une base quartique complète. Leur nombre ne rend pas la régularisation ni l’expressivité équivalentes à F. En particulier, diviser la variation observée par 12 ne la borne pas à `[-1,1]` ; les puissances peuvent avoir des échelles très différentes. Cela ne démontre pas que cette base échouera et ne justifie pas de la rejeter a priori. Le risque concret est de comparer F à un témoin mal ajusté ou de réutiliser le prior dépendant de la commande dans une fonction commune.

**Texte normatif intégrable :**

> B-sans-action est ajusté sur `angle_suivant - angle_courant`, avec prior de persistance, y compris à poids d’apprentissage total nul. Ses features et tous leurs prétraitements excluent commandes et dérivées de commande. La base initiale à treize termes est autorisée comme variante de développement. Publier les échelles des colonnes, les diagnostics numériques et la fréquence de saturation des sorties ; toute normalisation apprise utilise exclusivement l’apprentissage, reste figée à l’évaluation et est sérialisée. La pénalisation et l’intercept sont définis après cette normalisation. F et B utilisent le même domaine de sortie `[10°,170°]` ; aucun bornage propre à B n’est ajouté après lecture de ses erreurs.
>
> Comparer sur développement cette base à l’ablation minimale des termes de commande de F, soit `1, x, v`, avec prior de persistance. Cette ablation diagnostique ne remplace pas automatiquement le témoin principal. Choisir le témoin sans action avant validation, avec un accès comparable au développement. Documenter pour F et B les mêmes données d’apprentissage, ancres, occasions de sélection, budget d’interaction et règle de choix de la version évaluée. Ne pas opposer un actif sélectionné à un candidat choisi arbitrairement à un autre stade. Le coût de calcul réel de chaque méthode est rapporté séparément.

**Critère vérifiable.** Changer toutes les commandes à angles observés identiques laisse features, cible résiduelle, coefficients, prior et prévisions de B inchangés, y compris en rechargement et déroulement libre. Les rapports de développement contiennent les diagnostics numériques et les deux bases sans action. Aucun gain de F n’est attribué à la commande si le comparateur est invalide ; sa performance absolue reste rapportable. L’avantage éventuel de F établit une valeur prédictive de l’information de commande dans ce dispositif, pas une causalité générale.

### C3 — Définir ce que la validation peut apprendre et ce qu’elle ne peut décider

**Défaut et portée.** « Une lecture » et « si la validation conduit à une modification » sont de bons principes, mais les critères de passage et l’état initial de l’apprenant sur les nouveaux organismes ne sont pas explicités. La validation pourrait sinon servir à choisir un checkpoint ou à transporter des paramètres d’un organisme de développement sans que cela soit annoncé.

**Texte normatif intégrable :**

> Avant d’ouvrir la validation, figer la recette, les seuils de passage, les critères techniques d’arrêt et l’état initial des apprenants. Pour le présent essai d’apprentissage individuel, chaque nouvel organisme démarre avec un apprenant neuf selon la recette fixée ; ses propres rôles d’apprentissage, sélection et calibration restent utilisables selon cette recette, tandis que son évaluation reste sans adaptation. Le seuil global de A provient exclusivement du développement. Une initialisation apprise entre organismes serait une autre variante, à déclarer avant exposition.
>
> Toute utilisation des résultats de validation pour choisir un modèle, un horizon, un seuil, une promotion ou un sous-ensemble de résultats transforme l’ensemble de cette banque en développement. Une nouvelle validation complète prend une provenance neuve, sans remplacement sélectif ni réinitialisation du journal des variantes. Une validation insuffisante reste insuffisante ; la réussite des seules capacités F et persistance peut être retenue si cette décision par capacité a été fixée avant lecture.

**Critère vérifiable.** Un manifeste daté et son empreinte précèdent l’accès à la validation. Les journaux distinguent apprentissage local prévu et changement de recette. Une modification après lecture entraîne le reclassement intégral de la banque ; les réserves historiques restent refusées par le lanceur.

### C4 — Lier preuves, capacités et versions réellement actives

**Défaut et portée.** Conserver les résultats propres des autres capacités est correct historiquement, mais ne permet pas de conserver automatiquement leur statut courant sur une nouvelle version. Une nouvelle moyenne peut invalider une calibration ou un moniteur sans effacer la preuve concernant l’ancien paquet. Le registre ne représente pas encore cette dépendance.

**Texte normatif intégrable :**

> Toute preuve identifie la capacité, le paquet de paramètres évalué, ses dépendances et son niveau développement/validation/confirmation. Les preuves historiques restent consultables. À l’activation d’une autre version, une capacité dépendante non réévaluée porte un statut explicite non qualifié pour cette version, ou continue à utiliser son ancien paquet complet clairement identifié. La promotion de F n’hérite ni des intervalles de E ni du seuil de A par simple association de noms. L’activation d’une version techniquement `validated` ne qualifie pas scientifiquement J1.

**Critère vérifiable.** Promouvoir F seul ne donne aucun statut de calibration ou de détection à son nouveau paquet. Une régression de E ne détruit pas la preuve de F inchangé. Une requête de prévision retrouve les paramètres correspondant exactement à la version active et à la preuve affichée.

### C5 — Étendre l’atomicité à l’apprentissage et rendre la reprise réalisable

**Défaut et portée.** Le plan exige déjà une activation transactionnelle, mais la relation entre mise à jour du candidat, consommation du trial et progression du superviseur reste à préciser. Une simple séquence « apprendre, incrémenter, promouvoir » pourrait doubler l’apprentissage à la reprise. De plus, le superviseur actuel abandonne l’exécution partielle au lieu de la rejouer.

**Texte normatif intégrable :**

> Après publication et vérification d’un artefact immuable, une transaction de mémoire rend cohérents sa référence, l’application du trial, l’état du candidat et le curseur d’apprentissage. Lorsqu’une promotion est due, la même unité atomique de décision associe version active, preuve, états de capacité et identité de promotion. Les opérations composées utilisent une seule transaction effective, sans imbrication des méthodes ouvrant elles-mêmes `BEGIN IMMEDIATE`. Un pointeur de cycle en retard est réconcilié depuis ces écritures idempotentes.
>
> L’identité logique d’un trial comprend sa variante, son organisme et sa position prévue ; elle est distincte de l’identité de tentative physique. Son contenu inclut les observations et commandes pertinentes. Même identité logique et contenu différent : erreur ; même contenu légitimement répété à deux positions prévues : deux trials. Un compteur et la seule dernière clé ne suffisent pas : conserver le registre des applications ou un mécanisme équivalent vérifiant tout rejeu.
>
> Le premier livrable garantit la reprise entre trials. Pour une interruption au milieu d’un trial, rejouer dans une nouvelle tentative depuis l’état initial sauvegardé et éliminer toute écriture partielle de l’apprenant. Si cet état physique exact n’est pas restaurable, déclarer un arrêt technique ; ne pas présenter l’abandon actuel du superviseur comme une reprise exacte. Un artefact orphelin n’est jamais activé automatiquement.

**Critère vérifiable.** Des interruptions injectées avant/après publication, application du trial, promotion et progression donnent toujours un ancien ou nouveau paquet complet. Rejouer également un trial ancien, après plusieurs autres mises à jour, n’ajoute aucun apprentissage. Dans un nouveau processus et le même environnement, prévisions puis prochaine mise à jour correspondent bit à bit à l’exécution continue. Toute divergence physique non résolue ferme la revendication de reprise correspondante.

### C6 — Faire du budget un plafond effectif malgré les interruptions

**Défaut et portée.** Les 15/60 minutes sont adaptées comme limites de première exploration, mais une sauvegarde du coût uniquement aux frontières de trials perdrait le temps consommé par un processus interrompu. Vérifier le plafond seulement après un trial long pourrait également le dépasser.

**Texte normatif intégrable :**

> Les plafonds portent sur le temps écoulé des invocations de calcul : génération, apprentissage, évaluation, écritures et tentatives perdues. Une supervision extérieure au calcul impose au plus 15 minutes par invocation et 60 minutes cumulées pour l’itération, ou le reliquat inférieur disponible. Un journal durable des tentatives permet de conserver ou de majorer prudemment le coût après interruption ; le compteur ne revient jamais à zéro lors d’une reprise. Au plafond, arrêter sans exposer de banque supplémentaire et publier les travaux incomplets. Toute nouvelle itération reçoit un budget et une configuration explicites avant calcul.

**Critère vérifiable.** Une interruption avant checkpoint laisse le coût de la tentative comptabilisé ; un redémarrage ne dépasse pas le reliquat. La supervision coupe une opération bloquée. Le manifeste précise séparément le coût des tests techniques, et inclut toute simulation qu’ils exécutent dans le budget de calcul concerné, sans détour par un lanceur de tests.

## Champs à fixer par Codex dans le manifeste de développement

Ces décisions sont nécessaires avant le premier calcul correspondant. Elles ne nécessitent pas d’inventer dès maintenant des seuils confirmatoires ni d’attendre un nouveau modèle.

| Champ | Prescription et critère de vérification |
|---|---|
| Provenance et accès | Recette SHA-256 canonique, largeur des graines, sous-espaces, valeurs exportées et inventaire des collisions. Vérifier avant génération l’exclusion de `19201..19224`, `19391..19396`, `19501..19524` et des banques closes. |
| Historique et pas | Définir les indices de cible/variation, l’observation initiale et la remise à zéro. Le nominal est `control_dt=0.02` dans `sim3d/bench_model.py`. Soit refuser les autres pas, soit spécifier l’adaptation causale du prior et des normalisations ; enregistrer seulement dt sans l’utiliser ne suffit pas pour changer de fréquence. |
| F et B | Bases exactes, prior, bornes, solveur, normalisation et sélection selon C2. Les essais d’invariance précèdent les comparaisons MuJoCo interprétables. |
| Promotion | Identifier les ancres et leurs digests, l’agrégation globale/par motif, la référence cumulative immuable, les huit occasions initiales aux trials 3 à 24 et les règles en cas d’égalité. Déclarer les marges initiales avant la variante, puis fixer les marges finales sur développement avant validation. |
| Dérive cumulative | Définir explicitement le plafond par rapport à la référence fixe, en plus de la marge par rapport à l’actif et du plafond absolu. Un scénario synthétique de petites régressions successives doit être arrêté avant de franchir le plafond cumulatif. Un candidat refusé continue d’apprendre sans altérer l’actif. |
| Sélection | i0 peut servir de banque de sélection/protection pour la même capacité, comme le permet la r2. En cas de capacité nouvelle distincte, définir des ancres appropriées avant calcul. Toute réutilisation répétée de ces ancres est une sélection, jamais une preuve indépendante. |
| Diversité | Canonicaliser et hacher séparément la suite entière des commandes et celle des angles, sans métadonnées ; fixer représentation numérique et traitement de l’angle initial. Comparer entre rôles normaux pour un même organisme. Les commandes communes entre organismes et les préfixes normaux appariés ne sont pas des erreurs de partition. Rapporter aussi les distances et quasi-doublons ; un hash distinct n’établit pas l’indépendance. |
| Validité de mirrored | Définir les traces appariées normales/faute, la première transition affectée après huit pas, les déplacements absolus et signés, amplitudes, maintiens et inversions observés. Examiner séparément le début de faute et la suite. Changer la cible en `180°-a` ne garantit pas une magnitude observée conservée. |
| Contrôles de A | Définir le moniteur sans action, sa propre normalisation et son seuil sur développement, ainsi que le détecteur de magnitude. Comparer à FPR visée comparable avec seuils figés ; ne pas choisir l’orientation AUROC sur validation. Préciser la première alarme, les fenêtres, les égalités au seuil et le traitement des alarmes précoces. Une alarme précoce ne peut devenir une réussite par une seconde alarme après faute. |
| E | Définir MAD global, facteur d’échelle, plancher, convention de variance, quantile `higher`, bornage de l’intervalle, bootstrap par trial logique et comportement à poids total nul. L’emploi de la même calibration pour dispersion et quantile reste une recette empirique ; ses scores d’ajustement ne prouvent pas la couverture tenue à part. |
| Horizons | À 50 Hz, 0,1 s et 0,5 s correspondent à 5 et 25 transitions. Avec 32 transitions et l’origine initiale disponible, il existe 8 origines complètes à 25 pas. Définir explicitement erreur terminale à horizon h ou erreur moyenne du chemin ; retenir l’erreur terminale comme lecture initiale simple. |
| Origines et agrégation | Toutes les méthodes partagent les origines d’un horizon. Rapporter la MAE à un pas sur toutes ses origines et, pour comparer les horizons, sur le sous-ensemble commun approprié. Exporter effectifs ; ne pas ajouter les fenêtres chevauchantes comme réplications. |
| Réception et arrêt | Vérifications causales, numériques et de persistance d’abord ; premier organisme, puis six si l’intégrité est verte. Couvrir temps, compte des opérations et arrêt selon C6. Aucun engagement que F, E et A seront tous tranchés en 60 minutes. |

La vérification de mirrored doit chercher un raccourci de mouvement observé, sans imposer artificiellement une égalité point par point de deux trajectoires différentes. Si le témoin de magnitude suffit, la manipulation n’établit pas la contingence recherchée. Corriger le générateur sur développement et relancer la variante entière est alors approprié ; les résultats de F peuvent rester distincts. Les critères numériques de validité retenus après cette exploration doivent être fixés avant validation.

## Exigences du gel avant validation et du futur gel confirmatoire

**Avant validation**, figer les choix issus du développement : bases et hyperparamètres, normalisation, règles de promotion, seuils d’usage en degrés et gains relatifs, horizons, comparateurs, seuils et orientations de A, calibration de E selon la recette, diagnostics de validité, critères par capacité et traitement des incidents. Mesurer les constantes de temps et le coût avant de décider si 25 pas apportent une information utile. Les six organismes de développement et les six de validation donnent une première épreuve de recette ; deux organismes par régime ne suffisent pas à promettre une précision fine des résultats par régime.

**Avant confirmation**, soumettre un manifeste complet à une nouvelle revue. Il doit fixer :

- Organismes indépendants, formes de commande tenues à part de la conception, effectifs justifiés par la précision recherchée et coût mesuré. Prévalider le générateur sur développement ; tout contrôle technique sur les réserves doit être prédéfini, sans adaptation de recette à leur contenu ni exposition de leurs scores.
- Estimands, pondération égale des motifs et des organismes, traitement des régimes, erreurs absolues et relatives, données manquantes, échecs techniques et arrêts. Les fautes appariées et les fenêtres d’un organisme ne créent pas de nouveaux organismes indépendants. Les futures vies seront l’unité de réplication du protocole cumulatif distinct.
- Famille primaire F de trois contrastes à un pas contre B0, B1 et B-sans-action, sans doublon angle/delta. Pour une marge absolue utile m, le contraste peut être `MAE_B - MAE_F - m` ; pour une réduction relative r, `(1-r)*MAE_B - MAE_F`. Choisir les marges et le traitement des baselines quasi nulles avant les résultats. Déclarer si les deux exigences sont conjointes et comment elles sont testées.
- Rôle confirmatoire ou secondaire des horizons, multiplicité entre revendications, non-infériorité de E et ses marges, couverture et largeur attendues, FPR/TPR/délai de A avec non-détections. Un intervalle autour de E ne qualifie pas un intervalle autour de F. Les échecs de E ou A ne suppriment pas une preuve F distincte, mais ne permettent pas de rebaptiser après coup une campagne ratée en succès global.
- Méthode d’incertitude au niveau organisme et justification de ses hypothèses. Réutiliser [`paired_stats.py`](../../learning/paired_stats.py) : son test par changements de signes porte sur les amplitudes des différences sous une hypothèse de symétrie, pas sur le seul compte de signes favorables. La fonction exacte y est limitée à 20 unités ; fixer le choix exact/Monte-Carlo, les tirages et les graines selon l’effectif. Pour la non-infériorité, définir le sens du contraste et le décalage de marge, sans interpréter une absence de différence significative comme équivalence.
- Code, dépendances, artefacts, restauration, coûts complets et arrêt technique gelés. Une précision insuffisante doit rester une conclusion possible ; elle ne justifie pas d’ajouter sélectivement des organismes après lecture.

## Réponse aux neuf points et décision d’exécution

1. **Causalité :** bonne séparation proposée ; C1 ferme la calibration, le gel d’évaluation et les versions. Les essais couvrent moyenne, sigma, intervalle, score, décision et restauration.
2. **Comparateur :** proposition recevable en développement ; C2 exige un ajustement réellement sans action et contrôle les différences de représentation sans prétendre égaliser l’expressivité par treize coefficients.
3. **Partitions :** développement réutilisable approprié ; C3 ferme la sélection sur validation. Les anciennes réserves restent fermées et la confirmation exige une revue distincte.
4. **Diversité et mirrored :** hashes de contenu et diagnostics cinématiques nécessaires ; leur validité reste à mesurer. Ni un tick commun ni un préfixe apparié ne constitue une collision de trial normal entre rôles.
5. **Promotion :** candidat indépendant et fenêtres réduisent le verrou, sans garantir une promotion. Référence fixe et plafond cumulatif évitent la dérive prévue ; la sélection répétée reste exploratoire.
6. **Horizon et statistiques :** 5/25 pas sont cohérents au nominal, les huit origines à 25 pas sont correctes avec la convention indiquée. Durées finales, effectifs, marges et familles restent à fixer aux étapes prescrites.
7. **Qualifications :** conserver les acquis séparés est approuvé, avec dépendances par version selon C4. F seul n’est ni agence, ni incertitude calibrée, ni validation intégrale de J1.
8. **Persistance :** plan crédible, mais le code historique ne réalise pas encore cette continuité. C5 précise l’application exactement une fois et la limite entre reprise des paramètres et reprise physique.
9. **Budget :** 15 minutes par invocation et 60 minutes cumulées bornent raisonnablement la première itération si C6 est effectif. Ils ne garantissent ni sa terminaison complète ni une qualification statistique.

**Autorisation explicite :** après intégration documentaire de C1–C6 et fixation du manifeste de développement, j’autorise le code r2, les tests synthétiques et de contrat, puis le développement MuJoCo borné sur les nouvelles provenances de développement. Les contrôles d’intégrité doivent être verts avant interprétation des performances. J’autorise également l’implémentation de l’intégration persistante au noyau ; son activation exige les essais de réception de C4–C5, une preuve F conforme aux critères d’usage fixés et des statuts portant explicitement leur niveau de preuve. La suite de tests ciblés puis la suite complète doivent être exécutées pour les modifications de code, dans le cadre budgétaire déclaré. La validation de configuration devient permise uniquement après le gel décrit ci-dessus ; elle n’ouvre aucune confirmation automatique.

**Interdictions maintenues :** aucun smoke v1, aucune confirmation, aucune ouverture de `19201..19224`, `19391..19396` ou `19501..19524`, aucune reprise de campagne close et aucun J5. Cette revue ne qualifie pas J1 intégralement, n’autorise pas de mouvement matériel et n’ouvre pas le futur essai cumulatif A→B→A→C.
