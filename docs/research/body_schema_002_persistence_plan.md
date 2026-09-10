# BODY-SCHEMA-002 — intégration de la prévision persistante

> État courant D-053 : corrections intégrées, implémentation et essais réalisés.
> Voir [le rapport](body_schema_002_results.md). Les formulations « proposé » et
> « à implémenter » ci-dessous décrivent le contrat préalable conservé pour traçabilité.
> Aucune confirmation ni qualification E/A ne découle du résultat F.


Date : 2026-09-09. Statut : spécification proposée, non implémentée.  
Contrat applicable : [révision 2](body_schema_002_preregistration.md), D-051.

## Livrable et limites

Une même instance apprend une prévision du cou, l'évalue sur des commandes distinctes,
la sauvegarde et la retrouve après fermeture du processus. La prévision produit une
conséquence attendue et son erreur mesurable ; elle ne devient pas automatiquement un
contrôleur moteur. Les primitives et gardes MuJoCo existantes restent le cadre d'action.

La moyenne F est le premier livrable. Persistance, prévision multi-pas, calibration
et détection ont leurs propres preuves. Les étapes cumulatives ci-dessous sont une
conception à pré-enregistrer ensuite, pas une campagne déjà autorisée.

## Points de raccordement vérifiés dans le code

| Composant existant | Usage prévu | Travail manquant |
|---|---|---|
| `learning/body_schema_001.py`, `ProtectedFullRidge` | Référence de la ridge simple | Implémentation r2 avec entrée causale et candidat indépendant ; préserver 001 historique. |
| `cognitive/memory.py`, `register_model` | Référence, digest et métadonnées d'artefact | Sérialiser effectivement le modèle et vérifier son contenu au chargement. |
| `promote_model`, `validated_model` | Une version active par module | Associer promotion, preuve et état de compétence dans une opération cohérente et idempotente. |
| `apply_competence_assessment` | Historique des évaluations et transitions | Route d'évaluation propre à la prédiction, distincte du suivi de cible actuel. |
| `cognitive/supervisor.py`, `PersistentDevelopmentSupervisor` | Reprises après sélection, exécution et évaluation | Raccorder apprentissage et activation sans doubler une mise à jour à la reprise. |
| `learning/paired_stats.py` | Analyse appariée | Réutiliser les fonctions existantes ; ne pas créer un second moteur statistique. |

Ces interfaces existent ; leur simple présence ne prouve pas encore la restauration
de coefficients appris. La métrique actuelle de suivi servo ne mesure pas une erreur
de prédiction : ne pas réutiliser son nom ni ses seuils de validation.

## Artefact versionné à produire

Prévoir un manifeste JSON et des tableaux numériques dans un format sans exécution
de code au chargement. Leur ensemble est immuable, référencé par empreinte de contenu.
Inclure :

- version du format, contrat causal, ordre des features, unités, pas temporel ;
- coefficients F, prior nominal, hyperparamètres et règles de normalisation ;
- candidat et actif séparés, trials accumulés ou statistiques suffisantes permettant
  de reproduire exactement la prochaine mise à jour ;
- références et digests des ancres, provenance des données et rôle de chaque banque ;
- membres E et calibration lorsqu'ils existent, avec versions liées à leur moyenne ;
- état des fenêtres A s'il existe, historique causal, curseur et RNG de l'apprenant ;
- preuves de capacité, portée développement/validation/confirmation et versions de code
  et dépendances ;
- compteur des trials appliqués, coût cumulé et identité de la dernière promotion.

L'état complet du simulateur nécessaire à une reprise physique exacte est un checkpoint
d'exécution séparé. Restaurer des coefficients n'implique pas restaurer une trajectoire
MuJoCo interrompue. Le premier livrable peut fermer entre trials, avec un état physique
initial explicitement identique des deux côtés.

## Écriture et activation

Écrire l'artefact dans un emplacement temporaire, fermer, vérifier le digest puis
publier son chemin immuable. Enregistrer ensuite le candidat dans la mémoire. Une
transaction doit rendre cohérents preuve, version active et compétence ; les méthodes
actuelles séparées ne constituent pas, seules, cette transaction composée.

La clé d'application d'un trial est fondée sur son identité et son contenu. Une reprise
avec la même clé retrouve son résultat sans réappliquer l'apprentissage. Même identité
avec contenu différent : erreur explicite. Un artefact incomplet ou corrompu n'est
jamais actif ; un fichier orphelin après interruption n'est pas promu au redémarrage.
Conserver l'ancien artefact pour retour à la version précédente.

Enregistrer des noms de compétence explicites : `body_forecast_one_step`,
`body_forecast_rollout`, `body_forecast_persistence`, puis calibration et détection
si elles sont qualifiées. Ces noms sont proposés, pas déjà ajoutés au registre.

## Vérifications et critères de réception

| Essai | Condition de réussite |
|---|---|
| Apprentissage synthétique causal | Erreur mesurée diminue sur exemples distincts ; aucune annotation privilégiée utilisée. |
| Développement MuJoCo | F comparé à B0/B1/B-sans-action sur les mêmes trials ; résultats en degrés et par organisme. |
| Rechargement dans un nouveau processus | Mêmes tableaux, état et prévisions bit à bit dans le même environnement numérique. |
| Continuation après rechargement | Le prochain trial produit les mêmes coefficients et décision que sans interruption. |
| Refus du candidat | Actif inchangé ; candidat et données conservés pour les mises à jour suivantes. |
| Interruption avant/après publication et transaction | Ancien ou nouveau paquet complet actif, jamais un état mélangé. |
| Rejeu d'une mise à jour et d'une promotion | Aucun doublon, même version et même preuve finale. |
| Artefact altéré ou version incompatible | Refus explicite ; aucune promotion ou restauration silencieuse. |
| Régression d'une capacité | Son statut évolue avec preuve ; les autres capacités conservent leurs résultats propres. |

La comparaison bit à bit vise un même logiciel et une même plateforme ; une migration
numérique demande son propre contrat de tolérance. Ces essais ne sont pas encore
exécutés. Après implémentation, lancer les tests ciblés puis la suite complète.

## Ordre de réalisation après revue

1. Codex fixe le manifeste de développement : bases exactes, ancres, budget, provenance.
2. Codex implémente les entrées causales et leurs contrôles synthétiques.
3. Codex développe F et les comparateurs, puis effectue les essais MuJoCo bornés.
4. Codex ajoute artefacts, chargement et continuation dans un nouveau processus.
5. Codex raccorde activation et évaluations au noyau ; vérifie les interruptions.
6. Codex mesure le développement, fige la configuration et effectue la validation.
7. Codex prépare le manifeste confirmatoire complet et sa revue.

Les diagnostics de E/A peuvent continuer sans annuler un livrable F valide. Aucun
statut de développement n'ouvre automatiquement J5 ou un essai physique.

## Suite cumulative à pré-enregistrer après ce livrable

Commencer sur le cou, sans dépendance à une nouvelle branche visuelle. Définir des
vies A→B→A→C avec une seule mémoire et des paramètres appris persistants. Choisir A/B/C
sur développement avec une véritable marge d'apprentissage et un risque d'interférence
mesuré. Ne pas exiger deux conséquences incompatibles pour exactement le même
historique observable sans possibilité d'identifier le contexte.

Comparer adaptation naïve, replay uniforme et instance neuve au retour à A. Même
initialisation, mêmes données visitées pour l'ablation d'apprentissage, mêmes nombres
d'interactions et de mises à jour ; compter les répétitions du replay dans ces mises
à jour. Séparer la politique de collecte, qui demeure fixe à ce stade.

Mesurer à chaque phase : acquisition du contexte courant, performance tenue à part
sur A, récupération au retour, capacité comportementale si une orientation a été
ajoutée, mémoire et calcul. Les évaluations sur A pendant B sont des branches de juge
sans apprentissage, sans modification de l'instance vivante ni retour de données.

Les vies sont les réplications. Les réinitialisations physiques sont identiques entre
conditions et n'effacent pas l'apprenant. Choisir et figer fraction de replay,
contextes, budgets, effectifs et marges avant confirmation. Un modèle entraîné sur
toutes les phases, incluant le futur, peut servir de référence privilégiée déclarée.

Si aucun oubli mesurable n'apparaît, conserver ce résultat et ne pas revendiquer un
gain de consolidation. Si B est appris mais A perdu, distinguer capacité insuffisante,
oubli, ambiguïté de contexte et refus de promotion avant de changer d'architecture.


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
