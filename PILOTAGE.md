# Émergence - Tableau de pilotage

Dernière mise à jour: 2026-07-20

Ce fichier est le point d'entrée humain du projet. Il indique qui doit agir maintenant et quelle demande envoyer sans avoir à interpréter la roadmap technique.

## Situation actuelle

| Élément | État |
|---|---|
| Jalon actif | Porte de décision après TV-001, avant étape 2/J6 |
| État logiciel | TV-001 complète et interprétable: calibration passée, 24 runs achevés; TV-H1 rejetée (`-2,80 %`), TV-H2 rejetée (`28,28 %` de TV contre `25,19 %`); tous les garde-fous passent; `regional_lp_gain` non promu sous D-009 |
| Responsable de l'action courante | Claude pour la revue contradictoire des résultats; Anthony transmet le dossier préparé |
| Action attendue d'Anthony maintenant | Transmettre à Claude le nouveau prompt exact de `CLAUDE_REVIEW_REQUEST.md`; aucune décision technique, manipulation, achat ou flash |
| Action attendue de Claude maintenant | Trancher l'ordre expérimental: J6 d'abord, diagnostic invariance/bruit d'abord, ou arrêt nécessitant arbitrage d'objectif |
| Blocage actuel | Porte de revue de résultats avant nouvelle campagne; aucun blocage technique ou matériel |

## Prochaine action exacte

**Prochaine action:** Anthony transmet à Claude le prompt de revue de résultats préparé
dans `CLAUDE_REVIEW_REQUEST.md`. Codex appliquera ensuite le verdict technique sous
D-004: soit pré-enregistrer J6 avec motivation gelée, soit pré-enregistrer le diagnostic
minimal demandé. Anthony ne tranche que si Claude conclut qu'un choix d'objectif général
est réellement nécessaire.

**Anthony n'a aucune action physique à effectuer.** Le banc v1.0, le flash et les achats
sont différés sous D-008. Les interdictions de sécurité de D-005 restent applicables au
matériel existant.

## Ce qu'Anthony doit demander

Pour effectuer la porte actuelle, transmettre à Claude:

```text
Effectue la revue de résultats demandée dans CLAUDE_REVIEW_REQUEST.md. Lis les fichiers
indiqués, maintiens la non-promotion TV-001 acquise, puis tranche uniquement l'ordre de
la suite: J6 d'abord, diagnostic d'abord, ou arrêt/arbitrage objectif. Écris ton verdict
dans docs/research/tv_real_jepa_001_results_review.md. Ne lance aucun calcul et ne
modifie aucun autre fichier.
```

Après dépôt de la revue, pour reprendre avec Codex:

```text
Continue le projet Emergence. Intègre la revue de résultats TV-001 et exécute la voie
qu'elle autorise jusqu'à la prochaine porte réelle. Mets à jour les documents de reprise.
```

Une version encore plus courte est acceptable:

```text
Continue le projet Emergence jusqu'à ce que tu aies réellement besoin de moi.
```

Codex ne doit pas répondre uniquement par un plan si les tâches peuvent être réalisées dans le dépôt. Il doit les exécuter, les vérifier et documenter la suite.

## Quand utiliser Claude

Anthony n'a pas à déterminer seul si Claude doit intervenir. Codex signale la nécessité d'une revue et prépare un fichier `CLAUDE_REVIEW_REQUEST.md` contenant le contexte et le prompt exact.

Lorsque ce fichier existe et que ce tableau indique `Action attendue de Claude: revue prête`, Anthony peut transmettre à Claude:

```text
Effectue la revue demandée dans CLAUDE_REVIEW_REQUEST.md. Lis uniquement les
fichiers qui y sont indiqués et écris ta conclusion dans le fichier demandé.
```

En l'absence de demande préparée, Claude n'est pas nécessaire pour faire avancer le travail courant.

## Rôle permanent d'Anthony

Anthony intervient principalement comme:

- technicien du banc d'essai: montage, câblage, manipulation et observation physique;
- garant de la sécurité matérielle et des limites mécaniques;
- exécutant des procédures physiques préparées précisément par Codex;
- validateur des achats et modifications de composants;
- responsable du consentement des personnes et des contraintes personnelles du projet;
- propriétaire de l'objectif général et des priorités personnelles.

Anthony ne prend pas en charge les choix logiciels, l'architecture technique, les hyperparamètres, les baselines, les métriques ou l'interprétation scientifique courante. Codex décide et implémente ces éléments; Claude les challenge aux portes importantes.

## Format obligatoire des prochaines étapes

À la fin de chaque session substantielle, Codex doit écrire explicitement:

```text
Action Codex: ce que Codex peut faire seul et doit exécuter ensuite.
Action Anthony: manipulation, observation ou achat précis; sinon « aucune ».
Action Claude: revue préparée avec fichier et prompt; sinon « aucune ».
Blocage: condition réelle empêchant la suite; sinon « aucun ».
```

Une formulation vague comme « il faut préparer J0 » est insuffisante. Elle doit préciser qui s'en charge et si Anthony doit faire quelque chose.
