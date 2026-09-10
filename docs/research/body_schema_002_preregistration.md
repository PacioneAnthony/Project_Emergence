# BODY-SCHEMA-002 — contrat révisé et prévision persistante

> État courant D-053 : corrections intégrées, implémentation et essais réalisés.
> Voir [le rapport](body_schema_002_results.md). Les formulations « proposé » et
> « à implémenter » ci-dessous décrivent le contrat préalable conservé pour traçabilité.
> Aucune confirmation ni qualification E/A ne découle du résultat F.


Date : 2026-09-09. Révision 2 proposée sous D-051.  
Statut : dossier prêt pour revue ; aucun code expérimental ni calcul nouveau exécuté.  
Portée : J1, simulation uniquement ; J5 reste suspendu.

## Décision demandée

Autoriser, après intégration des corrections de revue, le développement borné d'une
prévision corporelle causale et rechargeable dans le noyau existant. Qualifier
séparément prévision, persistance, incertitude et détection. La seule moyenne ne
qualifie pas tout J1 et ne permet aucune revendication d'agence.

Cette révision remplace la [proposition du 27 juillet](body_schema_002_proposal_20260727.md),
archivée à l'identique. Ses anciennes portes et graines ne sont plus un protocole
exécutable. Les clôtures BODY-SCHEMA-001, LIFE et REF restent inchangées.

Ce document fixe un contrat de développement, pas une campagne confirmatoire gelée.
Les seuils d'usage encore à établir sont explicités ci-dessous. La revue actuelle
porte sur le contrat et le développement ; un manifeste complet et sa revue seront
nécessaires avant confirmation. Aucun accès à une banque finale n'est autorisé ici.

## Corrections de l'audit

| Défaut | Correction prospective |
|---|---|
| MAE angle et variation identiques | Une MAE à un pas ; déroulements libres à plusieurs horizons. |
| `ramp_class` postérieure au pas sélectionne sigma | Calibration globale initiale ; annotations internes réservées au juge. |
| `3_no_privileged_leak` vaut littéralement `True` | Entrée dédiée et vérification d'invariance de toute la chaîne. |
| Commandes décalées seulement à l'inférence | Comparateur entraîné sans commandes ; décalage diagnostique secondaire. |
| Protection à `1e-12` après chaque trial | Candidat cumulatif séparé de l'actif ; promotion par fenêtre et marge pratique. |
| Échec de E ou A ferme toute qualification | Statuts distincts pour chaque capacité. |
| Smoke servant à régler et valider le seuil | Développement, validation de configuration et confirmation séparés. |

Les constats et leurs limites figurent dans le
[diagnostic du 9 septembre](../../DIAGNOSTIC_ET_PLAN_DE_DEBLOCAGE.md), §3–4.
La progression historique de la moyenne ridge reste exploratoire ; les anciens
scores d'incertitude ne deviennent pas une qualification causale.

## 1. Contrat causal et contrôles bloquants

L'entrée de prédiction contient seulement : angle courant observé, variation observée
précédente, cible précédente, cible demandée suivante, variation de commande précédente
et durée du pas connue. Un signal de début de trial initialise l'historique. Aucun
identifiant d'organisme, de plan ou index temporel de plan ne sert de feature.
Les commandes futures d'un déroulement sont un plan fourni au modèle.

Un objet séparé porte la cible d'apprentissage observée après prédiction. Un troisième
objet, réservé au juge, porte régime, état interne, condition de faute, limiteur,
graines, provenance et `ramp_class`. Ne pas passer les objets riches historiques
`BodySample` ou `DynamicsTransition` directement à la prédiction, à sigma ou au choix.

Ordre obligatoire : entrée au temps t → prédiction et version enregistrées → exécution
→ observation t+1 → innovation et décision du moniteur → apprentissage éventuel.
Ni calibration ni seuil ne sont ajustés avec l'exemple avant son score. Durant
l'évaluation de A, modèle, calibration et seuil restent figés.

Vérifier aussi après rechargement :

- modifier tous les champs du juge à observations et état autorisés constants laisse
  moyenne, sigma, intervalle, score et décision identiques ;
- modifier les observations futures laisse les prédictions en déroulement libre
  identiques, mais peut changer l'erreur calculée ensuite par le juge ;
- modifier les commandes cachées à B-sans-action laisse ses features, son prior et ses
  prédictions inchangés ;
- modifier une conséquence synthétique change effectivement l'erreur du juge ;
- une variante synthétique volontairement fautive utilisant `ramp_class` fait échouer
  le contrôle. La porte agrège les résultats effectifs, jamais une constante.

Pour A, l'invariance suppose les mêmes innovations observées. Une vraie modification
physique peut légitimement changer les observations puis le score.

## 2. Mondes, partitions et diversité

Les trois familles physiques de la v1 restent le point de départ : vitesse,
établissement et friction, avec les mêmes plages de paramètres. Excitation fixe et
commune : 32 pas, cibles [30°,150°], départ/retour 90°, coût demandé 240°.
Le pas nominal vaut 0,02 s (`sim3d/bench_model.py`) ; enregistrer sa valeur effective.

Les 16 formes par motif de la v1 servent initialement au développement : i0 protection,
i1–i2 calibration, i3–i10 apprentissage, i11–i15 évaluation. Elles ont un historique
connu de conception et ne prouvent pas une généralisation à des familles inédites.

| Banque | Usage | Provenance proposée |
|---|---|---|
| Développement | Débogage, comparaison, fixation de la configuration | Six organismes, deux par famille ; `body-schema-002-r2/dev/v1`. |
| Validation | Une lecture de la configuration choisie | Six autres organismes, deux par famille ; `body-schema-002-r2/validation/v1`. |
| Confirmation | Recette intégralement gelée | Effectif et provenance fixés après étude de précision et de coût. |

Les identifiants explicites sont famille × index ; dériver les graines par SHA-256
canonique, avec sous-espaces organisme, exécution, bootstrap et statistiques. Le
manifeste devra exporter leurs valeurs et contrôler les collisions avec l'inventaire
existant avant génération. Aucune graine de cette révision n'a encore été calculée.
Les anciennes réserves 19201..19224, 19391..19396 et 19501..19524 restent fermées.

La protection est une donnée de sélection, la calibration une donnée d'ajustement.
L'évaluation d'un organisme ne sert pas à adapter ses coefficients. Les scores de
développement peuvent guider la conception globale ; journaliser toutes les variantes.
Si la validation conduit à une modification, elle devient développement et une nouvelle
validation reçoit une provenance neuve. Aucun remplacement sélectif d'organisme.

Vérifier avant entraînement les empreintes des commandes seules et des angles seuls,
sans rôle, condition, graine ou plan ID dans le contenu haché. Les digests historiques
incluent des métadonnées et ne suffisent pas. Rapporter distances entre trajectoires,
amplitudes réalisées, maintiens et inversions. Un tick neutre commun n'est pas une
collision de trial ; les préfixes normaux des fautes appariées sont intentionnels.

Une collision complète entre rôles normaux ou une manipulation inobservable bloque
l'interprétation. En développement, corriger le générateur et relancer la variante
entière. En confirmation, appliquer l'arrêt technique gelé. Les formes d'évaluation
confirmatoires devront aussi être distinctes de celles retenues pour la conception.

## 3. F : prévision et promotion

F démarre avec B2' : ridge résiduelle à treize features, alpha=1, intercept non pénalisé
et prior nominal décrits dans la v1. Le prior n'utilise aucun paramètre caché de
l'organisme. L'ensemble historique M n'est pas le candidat principal.

Le candidat apprend sur les trials accumulés ; un refus de promotion ne supprime ni
ses données ni son état. L'actif reste disponible. Évaluer une promotion tous les trois
trials jusqu'à 24, cadence initiale à consigner si elle change en développement.

Comparer candidat et actif sur les mêmes ancres de protection, globalement et par
motif, avec marge en degrés. Exiger aussi un gain utile sur des ancres de sélection
pour la capacité nouvelle. Les rôles et le contenu de ces ancres doivent être fixés
dans le manifeste de développement avant le premier calcul ; ils ne proviennent
jamais de l'évaluation finale. Une même banque de sélection peut mesurer gain et
protection si les capacités sont identiques ; elle doit être nommée comme telle.

Les comparaisons répétées de promotion sont une règle d'ingénierie, pas une preuve
statistique indépendante. Fixer marge, gain utile et plafond d'erreur absolue à partir
de l'usage et du développement, avant validation. Conserver en plus une ancre de
référence et un plafond cumulatif pour éviter une dérive par petites régressions.
Les contraintes physiques ne sont jamais relâchées.

Baselines à données et budget d'interaction identiques :

- B0 : persistance ;
- B1 : prior physique nominal ;
- B-sans-action : ridge entraînée séparément, prior de persistance et treize termes
  d'angle/historique observé, sans cible ni dérivée de cible, hold ou reversal de
  commande, selon la base de départ ci-dessous ;
- F-action-décalée : décalage de sept pas des commandes à l'inférence, diagnostic
  secondaire sans hypothèse principale de supériorité.

Pour B-sans-action, poser `x=(angle_courant-90)/80` et
`v=variation_observée_précédente/12`. Base initiale proposée, alpha=1 et intercept
non pénalisé comme F :

```text
1, x, v, x², x*v, v², x³, x²*v, x*v², v³, x³*v, x²*v², x*v³
```

Sa cible est le résidu de l'angle suivant par rapport à la persistance. Appliquer
les mêmes bornes de sortie que F. En déroulement libre, x et v proviennent ensuite
de ses propres prédictions. Aucun apprentissage des coefficients n'utilise les ancres
de protection ou les évaluations. Cette base est une proposition de développement,
pas une affirmation de meilleur modèle sans action.

Même nombre de coefficients ne signifie pas expressivité identique. Publier les bases
et, si nécessaire, une ablation retirant simplement les termes de commande de F.
B-sans-action dispose du même accès au développement pour sa conception.

Mesurer une seule MAE à un pas, puis aux horizons 0,1 et 0,5 s : cinq et vingt-cinq
pas au nominal. En déroulement libre, remplacer récursivement angle et variation par
les prédictions ; aucune observation intermédiaire future n'est fournie. Toutes les
méthodes utilisent les mêmes origines disposant de l'horizon complet. Un trial de
32 pas ne fournit que huit origines à 25 pas : exporter les effectifs et mesurer les
constantes de temps avant de figer les horizons finaux.

Le gain historique de 15 % contre le prior est un repère de conception, pas une porte
active. Associer erreur absolue utile, gain relatif et généralisation sur organismes
et formes de commande distincts dans le futur contrat confirmatoire.

## 4. E et A : qualifications séparées

E démarre avec seize ridges de la base F, poids Poisson(1) par trial entier. Le MAD
global des résidus de calibration, avec plancher d'un pas AS5600, remplace les MAD
sélectionnés par rampe/plateau. Le nom est `sigma_residuelle` : il ne s'agit pas d'une
estimation démontrée du bruit physique irréductible sur ce canal déterministe.

Sigma combine variance inter-membres et dispersion résiduelle globale. Le quantile
empirique 0,90 des résidus normalisés, méthode `higher`, fournit l'intervalle initial.
Le juge peut stratifier les résultats par régime/rampe/plateau après prédiction, sans
que ces labels participent à l'intervalle. Rapporter couvertures, largeurs, effectifs
et incertitude au niveau organisme ; aucune garantie conforme universelle revendiquée.

Un échec de E ne retire pas les résultats de F. Un intervalle évalué autour de la
moyenne E ne qualifie pas automatiquement un intervalle centré sur F.

A conserve comme prototype la moyenne de quatre innovations normalisées et le maximum
par trial de la v1. Ajuster son seuil exclusivement sur des épisodes normaux de
développement et évaluer sur d'autres organismes. Le score sur les épisodes ayant
réglé le seuil ne mesure pas une FPR tenue à part.

Tester blocked, degraded et mirrored après huit pas normaux. A ignore l'instant et
la condition d'intervention. Publier FPR par épisode, alarmes avant intervention,
TPR au seuil fixé, délai, non-détections et AUROC secondaire. Une alarme précoce est
une fausse alarme, jamais une détection réussie ; l'épisode reste au dénominateur.
Le délai conditionnel aux détections est accompagné du taux de non-détection.

Pour mirrored, vérifier la cinématique OBSERVÉE, notamment au début de la faute.
Comparer au mouvement trivial et à un moniteur issu du prédicteur sans action ;
orientations et seuils choisis sur développement uniquement. Si la magnitude seule
sépare les conditions, aucune qualification de contingence commande–conséquence.

## 5. Premier livrable intégré

Le [plan d'intégration](body_schema_002_persistence_plan.md) fixe interfaces, artefacts
et essais de reprise. Cible : apprendre sur certaines commandes, anticiper des
commandes distinctes, fermer le processus et retrouver les mêmes prévisions au retour.

Conserver des statuts distincts : prévision à un pas, multi-pas, persistance,
calibration et détection. Marquer les preuves exploratoires. Le statut technique
`validated` du registre n'est pas, seul, une confirmation scientifique.

## 6. Budget et reprise prospective

Après revue : tests synthétiques et contrat, premier organisme de développement,
puis six organismes si l'intégrité est verte. Plafonds proposés : 15 minutes par
invocation et 60 minutes cumulées pour la première itération, génération, apprentissage
et évaluation inclus. Au plafond, arrêter et documenter les points non tranchés.
Toute itération suivante reçoit sa configuration et son budget avant calcul.

Sauvegarder aux frontières de trials : paramètres, données, versions, RNG, progression,
coût cumulé et configuration. Reprendre seulement sous code, environnement et manifeste
identiques, contenus vérifiés. Rejouer entièrement un trial interrompu depuis son état
initial sauvegardé, sans appliquer ses écritures partielles. Comptabiliser le coût
perdu. Vérifier l'équivalence avec une exécution ininterrompue. Changer le code crée
une nouvelle variante, pas une reprise.

Tests prévus : invariance, déroulement sans fuite future, baselines, contenu des
trajectoires, candidat conservé après refus, absence de dérive cumulative, artefacts
et reprise idempotente. Puis suite complète pour les modifications de code.
Les 300 tests du diagnostic restent historiques ; aucun test n'est relancé pour cette
préparation documentaire.

## 7. Gel avant confirmation

Codex produira un manifeste sans champ manquant : code, dépendances, bases exactes,
hyperparamètres, générateur, provenance, effectifs par régime, formes tenues à part,
horizons, origines, seuils absolus/relatifs, promotion, statistiques, budget et reprise.
Prévalider techniquement le générateur entier sans exposer les scores réservés.

Unité indépendante : organisme, puis vie pour l'essai cumulatif futur. Calculer la MAE
par trial, moyenner également par motif, puis par organisme et régime. Les fenêtres
chevauchantes ne sont pas des réplications indépendantes. Réutiliser
`learning/paired_stats.py` ; justifier les hypothèses du test par changements de signes,
qui n'est pas un simple test du nombre de signes favorables.

La famille primaire F comprend une comparaison par B0/B1/B-sans-action à un pas,
sans duplication angle/delta. Les marges entrent dans les contrastes testés. Figer le
rôle des horizons supplémentaires, la multiplicité et la non-infériorité de E avant
confirmation. Distinguer effet absent, précision insuffisante et non-infériorité établie.

Ouvrir la confirmation seulement après développement valide, validation de la
configuration, budget mesuré et revue du manifeste gelé. Les travaux cumulatifs
A→B→A→C auront leur propre protocole après qualification de la prévision persistante.

## Actions actuelles

Codex : contrat et plan d'intégration préparés ; intégrer le verdict avant code ou
calcul. Claude : examiner la [demande actualisée](body_schema_002_review_request.md).
Anthony : transmettre cette demande et rendre la revue disponible dans le dépôt.
Aucune manipulation ni acquisition matérielle requise. Vision et curiosité adaptative
ne sont pas des prérequis de la première capacité persistante.


## Corrections de revue intégrées — D-052

Date : 2026-09-09. C1–C6 ci-dessous font autorité sur les formulations antérieures.
La revue est attribuée à Codex, en remplacement de Claude à la demande d’Anthony.
Le code et le développement sont autorisés après le manifeste, sans nouvelle revue.

### C1 — Fermer le contrat temporel de calibration et d’évaluation

Pour chaque version évaluée, achever l’apprentissage et la sélection sur leurs rôles autorisés, figer les coefficients, ajuster la calibration sur son rôle dédié, puis figer le paquet de prédiction avant l’évaluation. Les exemples d’évaluation ne modifient aucun coefficient, normaliseur, dispersion, quantile, seuil ou choix de version, même après leur score. L’historique observable et la fenêtre d’innovations peuvent évoluer causalement. Chaque prédiction enregistre avant exécution la moyenne, sigma et l’intervalle lorsqu’ils existent, ainsi que les versions nécessaires au score ultérieur. Une promotion de E exige une calibration liée à cette nouvelle moyenne avant utilisation de ses intervalles ; aucun recyclage silencieux d’une calibration antérieure. Le modèle, la calibration et le seuil sont fixes sur tout le lot évalué pour A ; seule sa fenêtre évolue et se réinitialise au début de chaque trial.

Le contrôle d’invariance reconstruit également la calibration à résidus observés, rôles d’accès et état aléatoire identiques, en modifiant les annotations privilégiées. Il vérifie ensuite les sorties et décisions avant et après restauration. Les graines du juge ne sont pas des entrées de prédiction ; changer volontairement la graine de l’apprenant et donc ses paramètres constitue une autre expérience, pas le test d’invariance.

### C2 — Rendre le comparateur sans action équitable jusque dans l’ajustement

B-sans-action est ajusté sur `angle_suivant - angle_courant`, avec prior de persistance, y compris à poids d’apprentissage total nul. Ses features et tous leurs prétraitements excluent commandes et dérivées de commande. La base initiale à treize termes est autorisée comme variante de développement. Publier les échelles des colonnes, les diagnostics numériques et la fréquence de saturation des sorties ; toute normalisation apprise utilise exclusivement l’apprentissage, reste figée à l’évaluation et est sérialisée. La pénalisation et l’intercept sont définis après cette normalisation. F et B utilisent le même domaine de sortie `[10°,170°]` ; aucun bornage propre à B n’est ajouté après lecture de ses erreurs.

Comparer sur développement cette base à l’ablation minimale des termes de commande de F, soit `1, x, v`, avec prior de persistance. Cette ablation diagnostique ne remplace pas automatiquement le témoin principal. Choisir le témoin sans action avant validation, avec un accès comparable au développement. Documenter pour F et B les mêmes données d’apprentissage, ancres, occasions de sélection, budget d’interaction et règle de choix de la version évaluée. Ne pas opposer un actif sélectionné à un candidat choisi arbitrairement à un autre stade. Le coût de calcul réel de chaque méthode est rapporté séparément.

### C3 — Définir ce que la validation peut apprendre et ce qu’elle ne peut décider

Avant d’ouvrir la validation, figer la recette, les seuils de passage, les critères techniques d’arrêt et l’état initial des apprenants. Pour le présent essai d’apprentissage individuel, chaque nouvel organisme démarre avec un apprenant neuf selon la recette fixée ; ses propres rôles d’apprentissage, sélection et calibration restent utilisables selon cette recette, tandis que son évaluation reste sans adaptation. Le seuil global de A provient exclusivement du développement. Une initialisation apprise entre organismes serait une autre variante, à déclarer avant exposition.

Toute utilisation des résultats de validation pour choisir un modèle, un horizon, un seuil, une promotion ou un sous-ensemble de résultats transforme l’ensemble de cette banque en développement. Une nouvelle validation complète prend une provenance neuve, sans remplacement sélectif ni réinitialisation du journal des variantes. Une validation insuffisante reste insuffisante ; la réussite des seules capacités F et persistance peut être retenue si cette décision par capacité a été fixée avant lecture.

### C4 — Lier preuves, capacités et versions réellement actives

Toute preuve identifie la capacité, le paquet de paramètres évalué, ses dépendances et son niveau développement/validation/confirmation. Les preuves historiques restent consultables. À l’activation d’une autre version, une capacité dépendante non réévaluée porte un statut explicite non qualifié pour cette version, ou continue à utiliser son ancien paquet complet clairement identifié. La promotion de F n’hérite ni des intervalles de E ni du seuil de A par simple association de noms. L’activation d’une version techniquement `validated` ne qualifie pas scientifiquement J1.

### C5 — Étendre l’atomicité à l’apprentissage et rendre la reprise réalisable

Après publication et vérification d’un artefact immuable, une transaction de mémoire rend cohérents sa référence, l’application du trial, l’état du candidat et le curseur d’apprentissage. Lorsqu’une promotion est due, la même unité atomique de décision associe version active, preuve, états de capacité et identité de promotion. Les opérations composées utilisent une seule transaction effective, sans imbrication des méthodes ouvrant elles-mêmes `BEGIN IMMEDIATE`. Un pointeur de cycle en retard est réconcilié depuis ces écritures idempotentes.

L’identité logique d’un trial comprend sa variante, son organisme et sa position prévue ; elle est distincte de l’identité de tentative physique. Son contenu inclut les observations et commandes pertinentes. Même identité logique et contenu différent : erreur ; même contenu légitimement répété à deux positions prévues : deux trials. Un compteur et la seule dernière clé ne suffisent pas : conserver le registre des applications ou un mécanisme équivalent vérifiant tout rejeu.

Le premier livrable garantit la reprise entre trials. Pour une interruption au milieu d’un trial, rejouer dans une nouvelle tentative depuis l’état initial sauvegardé et éliminer toute écriture partielle de l’apprenant. Si cet état physique exact n’est pas restaurable, déclarer un arrêt technique ; ne pas présenter l’abandon actuel du superviseur comme une reprise exacte. Un artefact orphelin n’est jamais activé automatiquement.

### C6 — Faire du budget un plafond effectif malgré les interruptions

Les plafonds portent sur le temps écoulé des invocations de calcul : génération, apprentissage, évaluation, écritures et tentatives perdues. Une supervision extérieure au calcul impose au plus 15 minutes par invocation et 60 minutes cumulées pour l’itération, ou le reliquat inférieur disponible. Un journal durable des tentatives permet de conserver ou de majorer prudemment le coût après interruption ; le compteur ne revient jamais à zéro lors d’une reprise. Au plafond, arrêter sans exposer de banque supplémentaire et publier les travaux incomplets. Toute nouvelle itération reçoit un budget et une configuration explicites avant calcul.
