# Émergence - Tableau de pilotage

Dernière mise à jour: 2026-07-20

Ce fichier est le point d'entrée humain du projet. Il indique qui doit agir maintenant et quelle demande envoyer sans avoir à interpréter la roadmap technique.

## Situation actuelle

| Élément | État |
|---|---|
| Jalon actif | DC-004 (durcissement) après réplication DC-003R réussie |
| État logiciel | DC-003R validée intégralement: R-H1 20/20 (p 9.5e-07, Holm, IC BCa positifs), non-infériorité vs regional_lp, bruit 4.97%, signatures 20/20 — promotion pré-enregistrée vers DC-004 |
| Responsable de l'action courante | Session Claude du 2026-07-20 (implémentation et campagne DC-004 selon `docs/research/dc004_preregistration.md`) |
| Action attendue d'Anthony maintenant | Aucune action matérielle (D-008); laisser les campagnes de simulation s'exécuter |
| Action attendue de Claude maintenant | Exécuter DC-004: geler le pré-enregistrement, implémenter les nouveaux fichiers, lancer les 40 mondes |
| Blocage actuel | Aucun |

## Prochaine action exacte

**Prochaine action:** exécuter DC-004 tel que pré-enregistré dans
`docs/research/dc004_preregistration.md` (ancres bruitées, layout permuté, contrôle
informationnel `regional_lp_gain`), sans toucher à l'algorithme gelé. La revue
contradictoire DC-003 (`docs/research/dc003_statistical_review.md`) et la réplication
DC-003R (`data/processed/experiments/developmental_curiosity_003R/`) sont terminées.

**Anthony n'a aucune action physique à effectuer.** Le banc v1.0, le flash et les achats
sont différés sous D-008. Les interdictions de sécurité de D-005 restent applicables au
matériel existant.

## Ce qu'Anthony doit demander

Pour faire avancer normalement le projet dans une nouvelle conversation Codex, ce message suffit:

```text
Continue le projet Emergence. Lis PILOTAGE.md et SESSION_HANDOFF.md, puis exécute
la prochaine action Codex jusqu'au prochain besoin réel d'intervention matérielle
ou de validation d'achat. Mets à jour les documents de reprise avant de terminer.
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
