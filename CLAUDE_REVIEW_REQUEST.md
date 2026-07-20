# Demande de revue contradictoire Claude — pré-enregistrement REF-001

Date: 2026-07-20

## Contexte

J6-AR001 a reçu une autorisation pré-calcul après intégration additive de C1–C4. Son
implémentation, ses 181 tests et le smoke 11991 ont réussi. La campagne réservée a
ensuite atteint son plafond gelé de 75 minutes pendant la troisième condition de 11313:
12 triplets sont complets, deux runs supplémentaires sont complets, un fragment est
interrompu et 11314..11316 n'ont pas été ouvertes. Le protocole exigeait 16 triplets.
D-012 clôt donc J6-AR001 comme **non-résultat technique**, sans calcul de porte, analyse
partielle, promotion, rejet scientifique, reprise ni extension post hoc du plafond.

Sous D-004, D-013 ouvre maintenant l'étape 3 du brief: tester une réafférence visuelle
minimale avec un objet physique MJCF mobile indépendamment de la tête. REF-001 est un
nouveau pré-enregistrement; aucun code, smoke ou calcul REF-001 n'a été lancé. Les
graines 12301..12316 et le smoke 12991 sont neufs et restent fermés jusqu'au verdict.

## Fichiers à lire intégralement

- `docs/research/j6_adaptive_replay_001_review.md`
- `docs/research/j6_adaptive_replay_001_technical_stop.md`
- `DECISIONS.md` — D-012 et D-013
- `DEVELOPMENTAL_ARCHITECTURE.md`
- `CODEX_TASK_BRIEF.md` — étape 3 / réafférence
- `docs/research/reafference_001_preregistration.md`
- `learning/paired_stats.py`

## Sortie attendue

Écris uniquement la revue dans:

`docs/research/reafference_001_review.md`

Ne modifie aucun autre fichier et ne lance aucun calcul, smoke ou graine réservée.

## Prompt exact

```text
Tu es le relecteur contradictoire pré-calcul de REF-001. Lis intégralement
docs/research/j6_adaptive_replay_001_review.md,
docs/research/j6_adaptive_replay_001_technical_stop.md, les décisions D-012/D-013 de
DECISIONS.md, DEVELOPMENTAL_ARCHITECTURE.md, l'étape 3 de CODEX_TASK_BRIEF.md,
docs/research/reafference_001_preregistration.md et learning/paired_stats.py.

Avant d'auditer REF-001, vérifie la clôture de J6-AR001: le plafond pré-enregistré a été
atteint avant 16 triplets; aucune analyse scientifique à n=12, extension du plafond,
reprise, promotion ou rejet de l'hypothèse adaptative ne doit être permis. Signale toute
formulation qui transformerait indûment cet arrêt en résultat scientifique.

Vérifie ensuite que REF-001 est réellement pré-calcul et nouveau: monde REF distinct,
objet mobile indépendant, smoke 12991 hors protocole, graines 12301..12316 vierges,
aucun réemploi décisionnel des mondes, seuils, résultats ou graines J6. Audite en détail:

1. si le contraste self_test / external_only / mixed opérationnalise effectivement la
   réafférence sans prétendre démontrer segmentation, agentivité ou causalité générale;
2. si le mouvement de l'objet est physiquement rendu par un vrai geom/joint MJCF,
   visible dans les six bins, statistiquement indépendant du babbling et impossible à
   inférer d'un label, état, trajectoire, RNG ou métadonnée fourni au modèle;
3. l'équité entre action_jepa et no_action_jepa: mêmes architecture, capacité,
   initialisation, images, actions disponibles, ordre de batchs, gradients, banques et
   évaluations, la seule différence étant l'utilisation ou la mise à zéro de l'action;
4. si pixel_change est une baseline simple adéquate et suffisamment forte, et si la
   règle anti-biomimétisme non payé interdit bien une promotion quand elle égale ou bat
   action_jepa;
5. la séparation stricte corpus / self_calibration / self_test / external_only / mixed /
   learner_validation, l'absence de fuite des labels physiques, et la définition exacte
   du seuil par méthode, graine et bin avec égalités non externes;
6. les scores JEPA pred/(pred+copy) et pixel, leurs unités et leurs comportements
   dégénérés possibles, notamment quand le mouvement propre ou externe est faible;
7. les directions et agrégations de REF-H1 à H4, les minima 0,05 / 0,10, TPR 0,75 /
   0,70, FPR 0,07 / 0,10, les portes 5/6 bins, la famille Holm commune de quatre tests,
   les IC BCa, l'exactitude des tests appariés à n=16 et la compatibilité avec
   learning/paired_stats.py;
8. la puissance et la cohérence arithmétique des 12 000 images, 2 400 décisions,
   4 500 pas, batch 256, 32 runs et plafond de 60 minutes, ainsi que la reprise sans
   dépassement silencieux;
9. si les gardes apprenant, action utile, objet visible, indépendance, aucune fuite,
   équité et budget ferment les issues post hoc et rendent chaque échec non ambigu;
10. si le smoke demandé peut prouver avant campagne la parité bit à bit, les budgets,
    la disjonction, l'indépendance action–objet, la visibilité contrefactuelle et
    l'absence d'état objet dans les tenseurs.

Recherche activement les degrés de liberté post hoc, confusions calibration/test,
fuites d'oracle, baselines artificiellement faibles, portes insuffisantes, incohérences
d'unités et ambiguïtés d'implémentation. Toute correction nécessaire à la validité doit
être formulée comme un amendement pré-calcul précis, sans choisir une valeur à partir de
données réservées ni lancer de calcul.

Écris uniquement ta revue dans docs/research/reafference_001_review.md et ne modifie
aucun autre fichier. Ne lance aucun test, smoke, rendu, entraînement ou graine.

Rends un verdict unique: AUTORISER, AUTORISER AVEC CORRECTIONS BLOQUANTES, ou NE PAS
AUTORISER. Sépare corrections bloquantes et recommandations non bloquantes. Termine par
une autorisation explicite ou une interdiction d'implémenter puis de lancer le smoke
12991. Les graines 12301..12316 doivent rester interdites jusqu'à intégration de toutes
les corrections bloquantes, smoke vert et manifeste concordant. Toute promotion future
reste interdite avant une seconde revue contradictoire des résultats.
```
