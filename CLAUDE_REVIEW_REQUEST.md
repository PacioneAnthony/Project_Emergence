# Demande de revue contradictoire Claude — pré-enregistrement J6-AR001

Date: 2026-07-20

## Contexte

J6-R001 est clos. La revue contradictoire des résultats a rendu **AUTORISER** et confirmé
qu'aucun ordonnanceur ne peut être promu: le replay uniforme a une valeur de rétention
réelle sur B, la priorité par erreur n'ajoute rien et ne sur-rejoue pas la télévision,
mais H3 échoue parce que le ratio fixe 50/50 dégrade excessivement la plasticité courante.

D-010 consigne la non-promotion. Sous D-004, Codex a choisi l'option A et consigné D-011:
tester une unique fraction de replay adaptative avant de passer à la réafférence. Les
mondes A/B/C et les graines 10301..10312 restent gelés. Aucun code J6-AR001, smoke ou
calcul sur les nouvelles graines n'a été exécuté.

## Fichiers à lire intégralement

- `docs/research/j6_replay_001_results_review.md`
- `DECISIONS.md` — D-010 et D-011
- `docs/research/j6_adaptive_replay_001_preregistration.md`
- `learning/paired_stats.py`

## Sortie attendue

Écris uniquement la revue dans:

`docs/research/j6_adaptive_replay_001_review.md`

Ne modifie aucun autre fichier et ne lance aucun calcul, smoke ou graine réservée.

## Prompt exact

```text
Tu es le relecteur contradictoire pré-calcul de J6-AR001. Lis intégralement
docs/research/j6_replay_001_results_review.md, les décisions D-010/D-011 de DECISIONS.md,
docs/research/j6_adaptive_replay_001_preregistration.md et learning/paired_stats.py.

Vérifie d'abord que la campagne est réellement nouvelle: aucun retuning ou réemploi des
mondes A/B/C ou graines 10301..10312, graines 11301..11316 vierges, smoke 11991 hors
protocole. Audite ensuite:

1. si les mondes D/E/F et leur ceinture physique ont une chance crédible d'induire un
   oubli mesurable sur D et E sans permettre de calibrer B1 sur le smoke;
2. l'équité d'information et de calcul entre naive, uniform_50 et adaptive_replay,
   notamment le coût identique des banques de suivi et l'absence de fuite depuis les
   banques finales;
3. la formule d_old/d_current/q/rho, sa causalité, ses références d'acquisition, sa
   quantification par blocs de 100 pas et l'absence de priorité d'épisode cachée;
4. la séparation corpus / banque de suivi / banque finale, B3, l'activation effective,
   les budgets, le plafond et la reprise;
5. les hypothèses B1, H1, H2, H3a/H3b, B2 et TV, les directions des différences, les
   marges 0,02 / 0,05 / 10 %, les familles Holm, la puissance n=16 et la compatibilité
   exacte avec learning/paired_stats.py;
6. si les règles de promotion empêchent bien de « résoudre » H3 en abandonnant la
   rétention, de masquer une région défaillante ou de promouvoir un calendrier qui ne
   s'est pas activé;
7. si la complexité du candidat est payée face aux baselines simples recevant la même
   information.

Recherche activement les degrés de liberté post hoc, incohérences d'unités, fuites,
portes insuffisantes et ambiguïtés d'implémentation. Les corrections nécessaires à la
validité doivent être formulées comme amendements pré-calcul précis sans proposer de
valeur réglée sur J6-R001.

Réponds par un verdict unique: AUTORISER, AUTORISER AVEC CORRECTIONS BLOQUANTES, ou NE
PAS AUTORISER. Liste séparément corrections bloquantes et recommandations non
bloquantes. Termine par une phrase explicite disant si l'implémentation, puis le smoke
11991, peuvent commencer; les graines 11301..11316 doivent rester interdites jusqu'à un
smoke vert et un manifeste concordant.
```
