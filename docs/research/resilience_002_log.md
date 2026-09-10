# Journal RESILIENCE-002

2026-09-10 · D-058 · priorité résilience et apprentissage intrinsèque.

## Avant les données v1

Protocole fixé avant implémentation dans `resilience_002_preregistration.md`.
Nouvel agent terminal, mémoire de résultats vécus, marge issue des erreurs passées,
besoin fonctionnel et choix de catégorie depuis les seules lacunes observées.
Comparateurs cycle et uniforme : architecture et budgets identiques, expériences
propres dans trois simulations physiques continues du même corps. Les instants des
changements sont tirés et invisibles aux trois agents.

Le service `FunctionalStore` lie choix, annonces préalables, expérience et état
complet dans une transaction du noyau. Registre candidat, aucune activation globale.
Tests ciblés : 11 puis 12 réussis, avec interruptions aux trois frontières,
reprise du RNG de choix, état Adam sans alias, divergence de contenu et annonces
réécrites refusées ; conservation du corps et des 128 pas par essai vérifiée.
Budget propre : 5400 s, maximum 900 s par invocation, tests inclus.

Conventions d'analyse fixées avant accès : checkpoints après apprentissage = 6
et fin dans les trois phases ; utilité post-rupture = moyenne des checkpoints 6
et fin de la phase perturbée ; fraction oracle = ratio des utilités moyennes par
checkpoint. L'unité indépendante est la vie, pas chaque décision corrélée.
Le manifeste gèle aussi le code d'analyse et ces conventions avant lancement.

La sonde de reprise interprocessus vérifie l'état, le prochain choix et la prochaine
mise à jour sur une branche non engagée d'expériences déjà vécues. Les simulateurs
physiques restent en mémoire, sans reset ; leurs pas sont suspendus pendant la
sonde logicielle. Aucune continuité temps réel sur matériel n'est revendiquée.

## Arrêt technique v1, correction v2

Suite complète initiale : 357 tests réussis en 25,46 s. Le manifeste v1 a été gelé
avant la première simulation (SHA `6872d9e07cf890cd740f7a8ef0f2a69eb4b00c3804a910ba60c96ac3bb694b8e`).
Arrêt technique au troisième essai, après deux commits du service : un score de
choix calculé par NumPy restait `float64` dans l'historique. La relecture PyTorch
`weights_only=True` le refuse. Les tests initiaux couvraient la première écriture
uniforme et des reprises en mémoire, mais pas la relecture des scores non vides.

Tous les fichiers sources v1 sont copiés sous `data/processed/experiments/resilience_002/source_v1`.
La vie partielle et son noyau restent conservés. Correction v2 : conversion explicite
du score en `float` Python ; aucune modification de formule, seuil ou entraînement.
Un test supplémentaire enchaîne quatre décisions selon besoin et leur relecture
sécurisée depuis le disque. Repartir sur six nouvelles vies `dev/v2`, sans réutiliser
les graines de v1. Aucune conclusion fonctionnelle n'est tirée de la vie partielle.

## Six vies v2 complètes

358 tests réussis en 25,32 s avant simulation ; reçu versionné. 996 nouvelles graines,
zéro collision avec l'inventaire historique. 275 essais par politique, 35200 pas
physiques et 17600 updates chacune ; 648 situations indépendantes des données
d'apprentissage, 1944 décisions de politiques corrélées. Six reprises exactes.
SHA manifeste v2 `60d1e236d389302d4f6c5eb8517c519bbbdf8e2d7dccea3ac070f0e9781cdbee`.

Résultat prometteur de récupération : réussite finale `need` 100 % dans les six
vies ; utilité/oracle 91,48 %, contre 73,93 % cycle et 69,13 % uniforme. Utilité
post-rupture 8,056° contre cycle 6,840° (+17,77 %), uniforme 6,493°.
Les portes récupération et sélection passent en développement.

Échec distinct : la clôture globale n'est pas fiable immédiatement après un
changement caché. L'analyse gelée restreint l'honnêteté aux checkpoints 6/fin
(0/18 clôtures contredites, couverture 50 %). Le texte ne justifiait pas d'exclure
les checkpoints 0 : l'audit conservateur compte 10/28 contradictions (35,71 %).
Le moniteur n'est donc pas qualifié. Les deux calculs restent publiés ; aucune
modification du calcul gelé pour effacer la divergence. Validation neuve limitée
aux deux capacités passantes, selon `resilience_002_validation_v2.md`.

Les 375 artefacts historiques de CUMULATIVE-001 et RESILIENCE-001 vérifiés sont
inchangés. Budget consommé après développement et audit : 250,641 s.

## Validation v2 complète : avantage actif non répliqué

Douze nouvelles vies, sources inchangées, manifeste
`9592ebaeba28b2449c259735a38197abd6cbd93ae48188494593fec8e2c41444`.
Le reçu `resilience_002_validation_v2_contract.json` lie manifeste, protocole de
validation et audit avant lancement. 1992 graines distinctes de l'inventaire.
573 essais, 73344 pas et 36672 updates par politique. 1296 situations du juge,
3888 décisions corrélées ; douze reprises exactes du service.

L'effet s'inverse : utilité post-rupture `need` 7,847° contre cycle 9,253°,
soit **−15,20 %**. Actif meilleur dans trois vies, égal dans trois, pire dans six.
Réussite finale 143/144 (99,31 %), pire vie 11/12 (91,67 %), mais fraction oracle
71,18 % <80 % : récupération active et sélection échouent. Cycle 144/144,
80,56 % de l'oracle ; uniforme 144/144, 74,00 %. Le cycle passe sur validation
mais échouait à la porte d'utilité en développement : aucune robustesse générale.
Décision : conserver le cycle fixe comme référence, ne pas promouvoir l'heuristique
active et ne pas retoucher celle-ci sur ces vies consommées.

Le moniteur actif échoue aussi après apprentissage : 4/39 états clos contredits
(10,26 %), couverture 39/72 (54,17 %). Audit tous checkpoints : 22/57 contredits
(38,60 %), dont 18 immédiatement après changement et quatre après apprentissage.
La distinction des dénominateurs est explicitée dans le rapport et le graphique.

Trace diagnostique conservée : validation life-03, marge globale 3,515° après une
alarme tardive sans nouveau changement physique. Aucune cible ne peut satisfaire
la promesse ≤2° ; repli vers 5° sur 23,333° disponibles, malgré 12/12 réussites.
Cycle : 16,667°. Le choix des expériences, le détecteur qui vide le rejeu et la
marge commune interagissent mal dans ce cas. Leurs contributions causales ne
sont pas isolées ; les comptes globaux de catégories proches ne suffisent pas.
Prochaine question : distinguer lacune locale, preuve devenue ancienne et rupture
globale, avant de refaire dépendre l'exploration d'un tel signal. Nouveau protocole
et nouvelles banques nécessaires, avec le cadrage de résilience inchangé.

## Clôture technique D-059

358 tests réussis ; les modifications ultérieures concernent seulement les
lectures d'audit, diagnostics et publication, exécutées avec assertions et
vérification visuelle du graphique. 431 empreintes dev et 885 validation
vérifiées, aucun écart ; contrat pré-validation intact. 375 anciens artefacts
inchangés. Budget final : **618,561 s sur 5400 s**, 19 invocations terminées,
dont une erreur technique v1 ; aucune réservation ou simulation en cours.
Environ 112,9 Mo de données locales exclus de Git à préserver. Les noyaux et
histoires restent candidats expérimentaux, sans activation globale.

Rapport `resilience_002_results.md`, graphique `resilience_002_progress.png`,
reçus des tests, de publication et de clôture. Les échecs de validation restent
visibles ; aucun gain de développement n'est présenté comme une généralisation.
