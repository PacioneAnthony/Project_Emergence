# Émergence - Tableau de pilotage

Dernière mise à jour: 2026-06-12

Ce fichier est le point d'entrée humain du projet. Il indique qui doit agir maintenant et quelle demande envoyer sans avoir à interpréter la roadmap technique.

## Situation actuelle

| Élément | État |
|---|---|
| Jalon actif | J0 - Instrumentation fiable |
| État logiciel | Qualification courte J0 réussie; firmware passif v2 prêt; dépôt nettoyé et suite active validée |
| Responsable de l'action courante | Anthony et Claude pour le banc v1.0; aucune nouvelle manipulation J0 immédiate |
| Action attendue d'Anthony maintenant | Continuer la conception/mesure/impression du banc selon `BENCH_DESIGN.md`; ne plus tester le servo sur v0.1 |
| Action attendue de Claude maintenant | Poursuivre la conception mécanique déjà engagée avec Anthony |
| Blocage actuel | Banc v1.0 non construit; la session J0 de 30 minutes attend sa qualification mécanique |

## Prochaine action exacte

**Anthony doit maintenant:**

1. poursuivre avec Claude les mesures réelles et la modélisation du banc de `BENCH_DESIGN.md`;
2. imprimer d'abord le coupon de tolérances prévu par le dossier, puis les pièces après ajustement;
3. ne lancer aucun nouvel essai moteur sur le montage v0.1;
4. signaler simplement à Codex lorsque le banc v1.0 est assemblé, avec les éventuels écarts apportés au dossier.

**Codex fera ensuite automatiquement:** revue des écarts de montage, flash du firmware passif v2, qualification mécanique comparative, puis autorisation ou correction avant la session de 30 minutes.

Décision parallèle: répondre à ANT-008 dans `ANTHONY_INBOX.md` concernant le kit AS5600, prévu par le banc pour la vérité terrain d'angle.

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
