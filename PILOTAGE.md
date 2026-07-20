# Émergence - Tableau de pilotage

Dernière mise à jour: 2026-07-20

Ce fichier est le point d'entrée humain du projet. Il indique qui doit agir maintenant et quelle demande envoyer sans avoir à interpréter la roadmap technique.

## Situation actuelle

| Élément | État |
|---|---|
| Jalon actif | Revue de conception de l'ordonnanceur après rejet DC-004 |
| État logiciel | DC-003R validée (20/20, portes appariées) puis DC-004 rejetée: l'ordonnanceur fractionnel s'effondre sous bruit d'ancre (0/40 à σ=0.05), biais du clip confirmé; la géométrie permutée seule est indolore; `regional_lp_gain` robuste |
| Responsable de l'action courante | Codex ou Claude pour la revue de conception (clip et normalisation du gain, moyennage fenêtré); aucune campagne avant nouveau pré-enregistrement |
| Action attendue d'Anthony maintenant | Aucune action matérielle (D-008); arbitrer la suite si la revue de conception propose plusieurs pistes |
| Action attendue de Claude maintenant | Aucune; la décision pré-enregistrée DC-004 (retour en conception) est exécutoire |
| Blocage actuel | Pas de simulation visuelle tant qu'un ordonnanceur n'a pas survécu à des ancres bruitées sur protocole pré-enregistré |

## Prochaine action exacte

**Prochaine action:** revue de conception de l'ordonnanceur, à partir des deux constats
gelés de DC-004: le clip `max(gain, 0)` transforme le bruit d'évaluation en signal
fantôme (biais mesuré croissant avec σ), et le moyennage fenêtré du gain
(`regional_lp_gain`) est robuste là où le gain fractionnel instantané s'effondre. Toute
nouvelle variante repart d'un pré-enregistrement neuf (graines vierges), sans retuning
sur les mondes 7301..7340. La lecture d'ensemble: DC-003/DC-003R valident la mesure
interventionnelle, pas l'ordonnanceur.

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
