# Émergence - Tableau de pilotage

Dernière mise à jour: 2026-07-20

Ce fichier est le point d'entrée humain du projet. Il indique qui doit agir maintenant et quelle demande envoyer sans avoir à interpréter la roadmap technique.

## Situation actuelle

| Élément | État |
|---|---|
| Jalon actif | Arbitrage d'Anthony après DC-005: `regional_lp_gain` promu ordonnanceur de référence |
| État logiciel | DC-003R validée, DC-004 rejetée (bruit d'ancre), DC-005 rejetée (le correctif agréger-puis-clipper ne régresse pas mais ne rattrape ni babbling ni le contrôle sous bruit): arrêt pré-enregistré de la famille à gain fractionnel; `regional_lp_gain` seul robuste sur les trois campagnes durcies |
| Responsable de l'action courante | Anthony pour l'arbitrage de la suite; Codex/Claude préparent le pré-enregistrement correspondant |
| Action attendue d'Anthony maintenant | Arbitrer: (a) promouvoir `regional_lp_gain` vers la conception de la simulation visuelle via un pré-enregistrement dédié, ou (b) exiger une hypothèse nouvelle avant tout ordonnanceur développemental |
| Action attendue de Claude maintenant | Revue contradictoire du prochain pré-enregistrement, quel que soit l'arbitrage |
| Blocage actuel | Arbitrage humain requis: la décision DC-005 clôt la famille en cours, la direction suivante est un choix de priorités |

## Prochaine action exacte

**Prochaine action (Anthony):** arbitrer la suite après l'arrêt pré-enregistré de la
famille à gain fractionnel (DC-005). Les faits pour trancher: la mesure
interventionnelle avant/après est validée et robuste; `regional_lp_gain` (LP régional
fenêtré nourri de cette mesure) est le seul ordonnanceur stable sous bruit d'ancre sur
DC-004 et DC-005 (`0.109` à σ=0.05 contre `0.115` babbling et `0.142` pour la meilleure
variante développementale); la machinerie développementale continue n'a pas démontré de
valeur ajoutée. Les deux options sont détaillées dans le tableau ci-dessus; dans les
deux cas, le protocole suivant est pré-enregistré et passe par une revue contradictoire
Claude avant exécution.

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
