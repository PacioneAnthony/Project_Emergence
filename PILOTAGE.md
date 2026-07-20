# Émergence - Tableau de pilotage

Dernière mise à jour: 2026-07-20

Ce fichier est le point d'entrée humain du projet. Il indique qui doit agir maintenant et quelle demande envoyer sans avoir à interpréter la roadmap technique.

## Situation actuelle

| Élément | État |
|---|---|
| Jalon actif | TV-001, étape 1 du brief: test de la télévision avec JEPA réel et `regional_lp_gain` |
| État logiciel | Pré-enregistrement gelé avant calcul; monde hétérogène, ancres tenues à part, calibration du bruit, ordonnanceur régional, analyse appariée et runner résumable implémentés; 169 tests passent et le smoke GPU/MuJoCo hors protocole réussit |
| Responsable de l'action courante | Claude pour la revue contradictoire pré-campagne; Anthony transmet le dossier préparé |
| Action attendue d'Anthony maintenant | Transmettre à Claude le prompt exact de `CLAUDE_REVIEW_REQUEST.md`; aucune manipulation, aucun achat, aucun flash |
| Action attendue de Claude maintenant | Auditer le protocole et le code TV-001, puis écrire `docs/research/tv_real_jepa_001_review.md` avec le verdict demandé |
| Blocage actuel | Porte de protocole: calibration `9201..9203` et campagne `9301..9312` interdites avant la revue; aucun blocage technique ou matériel |

## Prochaine action exacte

**Prochaine action:** Anthony transmet à Claude le prompt préparé dans
`CLAUDE_REVIEW_REQUEST.md`. Après un verdict favorable, Codex intègre les éventuelles
corrections bloquantes sans ouvrir les graines, exécute la calibration gelée, puis lance
la campagne appariée si la calibration passe. Le runner refuse les graines de campagne
sans confirmation explicite de cette revue.

**Anthony n'a aucune action physique à effectuer.** Le banc v1.0, le flash et les achats
sont différés sous D-008. Les interdictions de sécurité de D-005 restent applicables au
matériel existant.

## Ce qu'Anthony doit demander

Pour effectuer la porte actuelle, transmettre à Claude:

```text
Tu effectues la revue contradictoire pré-campagne demandée dans
CLAUDE_REVIEW_REQUEST.md. Lis les fichiers qui y sont indiqués, cherche en priorité les
fuites d'information, asymétries de budget, problèmes de mesure du progrès et écarts
protocole/code. Écris ton verdict et tes corrections éventuelles dans
docs/research/tv_real_jepa_001_review.md. Ne lance aucun calcul et ne modifie aucun autre
fichier.
```

Après dépôt de la revue, pour reprendre avec Codex:

```text
Continue le projet Emergence. Intègre la revue TV-001, puis exécute la calibration et la
campagne autorisées selon le pré-enregistrement. Mets à jour les documents de reprise.
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
