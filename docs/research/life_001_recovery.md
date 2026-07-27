# LIFE-001 — régression, récupération et choix d'expérience

Date: 2026-07-27. Validation d'ingénierie en simulation uniquement sous D-008 et D-022.
Aucune revendication d'apprentissage autonome ou de performance scientifique.

## Objectif

Compléter le premier smoke LIFE-001 par les deux capacités qui manquaient au noyau:

1. qualifier une compétence avec une zone d'hystérésis entre validation et régression;
2. choisir une expérience parmi plusieurs candidates sans contourner les gardes.

Le noyau demeure un orchestrateur. Les métriques et signaux sont fournis par des
évaluateurs externes; aucune primitive n'est exécutée par `cognitive/`.

## Évaluateur de compétence

`cognitive/competence.py` ajoute un critère générique pour les métriques bornées
supérieurement:

- seuil de validation;
- seuil de régression, nécessairement moins strict;
- nombre minimal d'échantillons;
- résultat `validated`, `inconclusive` ou `regressed`;
- maximum, moyenne, digest des valeurs et digest de la preuve.

La zone intermédiaire évite qu'un faible bruit fasse alterner automatiquement les
états. Les observations insuffisantes, non finies ou non auditables sont refusées.
L'évaluateur produit une preuve; le graphe transactionnel de `EpisodicMemory` reste
seul responsable des transitions.

## Sélection d'expérience

`SafeExperimentCatalog.propose_best` évalue chaque candidate avec les mêmes gardes que
la proposition nominale:

- sécurité et santé;
- primitive autorisée;
- risque et coût;
- croyances requises;
- cadence et quota persistants.

Les candidates bloquées ne participent pas au classement. La meilleure candidate
éligible est choisie par score, puis par identifiant en cas d'égalité. La proposition
persiste l'état `eligible` ou `blocked`, les raisons et les scores de toutes les
candidates. Si toutes sont bloquées, aucune proposition n'est écrite et l'exception
conserve les raisons par candidate.

## Smoke de cycle de vie

Le test d'intégration utilise la primitive analytique `bounded_head_orientation` dans
le jumeau MuJoCo:

| Phase | Graines | Configuration | Erreurs absolues |
|---|---|---|---|
| validation | 17101, 17102 | servo nominal, cibles 75°/105° | 0,02930° / 0,02930° |
| régression injectée | 17103, 17104 | vitesse limitée à 10°/s | 11,13281° / 11,13281° |
| récupération tenue à part | 17105, 17106 | servo nominal, cibles 70°/110° | 0,03906° / 0,03906° |

Critère gelé dans le test: validation `≤2°`, régression `>4°`, au moins deux
observations. Le cycle persistant obtenu est:

```text
unknown → learning → candidate → validated → regressed
        → learning → candidate → validated
```

Après détection de la régression, le catalogue compare `explore-room` et
`recalibrate-servo`; les signaux externes rendent la seconde plus informative. Le noyau
la sélectionne, persiste la justification, ferme la session, redémarre puis récupère
l'état `regressed` avant la phase de récupération.

La limitation de vitesse est une panne injectée connue, pas une découverte. Le smoke
prouve le câblage, la persistance, l'hystérésis et le respect des gardes; il ne prouve
ni diagnostic causal autonome, ni apprentissage d'une stratégie de réparation.

## Vérification

- 26 tests KERNEL/LIFE verts;
- sélection déterministe et audit complet testés;
- toutes candidates bloquées testées;
- quota consommé uniquement par la candidate retenue;
- régression, redémarrage, récupération et historique complet testés;
- suite complète du dépôt requise avant clôture de D-022.

