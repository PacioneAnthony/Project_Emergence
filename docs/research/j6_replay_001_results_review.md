# Revue contradictoire des résultats J6-R001 — promotion

Date: 2026-07-20. Revue demandée après exécution de la campagne (commit `18f72ad` sur
main). Fichiers audités: `j6_replay_001_preregistration.md` (avec amendement B1/B2/B3),
`j6_replay_001_review.md`, `j6_replay_001_results.md`, `j6_replay_001_analysis.json`,
`j6_replay_001_runs.json`, `learning/j6_replay.py`, `scripts/research/run_j6_replay.py`,
`sim3d/j6_domains.py`. Aucun calcul de campagne relancé; recomputation statistique
indépendante depuis les données brutes. Aucun fichier autre que la présente revue
modifié. Aucun retuning proposé sur `10301..10312`.

## Verdict

**AUTORISER.** La campagne est intègre, ses portes gelées sont appliquées à la lettre,
et sa décision mécanique est correcte. **Ni `uniform_replay` ni
`error_prioritized_replay` ne peuvent être promus.** Le résultat n'est pas un simple
« échec »: il faut distinguer trois statuts, ci-dessous. La non-promotion est
pré-enregistrée et interprétable; elle ne déclenche pas la branche « retour en
conception » de H1, mais la branche **H3 (plasticité courante excessive)**.

## Intégrité vérifiée indépendamment

- 12 triplets, 36 runs complets, graines `10301..10312`, tous présents.
- `spec_digest` unique sur les 36 runs (`70f6f298…`); budgets exacts partout
  (12 000 images, 2 400 décisions, 4 500 pas, 1 500 pas/session).
- **B3** vérifié empiriquement: le digest d'état post-A *et* les évaluations post-A sont
  **identiques** entre les trois conditions de chaque graine; les `corpus_sha256` sont
  identiques entre conditions. L'identité bit à bit jusqu'à la fin de A tient réellement.
- Garde apprenant recalculée: aucune violation (baisse structurée ≥ 20 % dans les 36×3
  couples domaine×phase).
- Runner: les graines réservées sont durement bloquées derrière `--review-accepted`
  **et** un smoke 10991 vert au `spec_digest` concordant
  (`run_j6_replay.py:70-79`); le smoke asserte landmark vrai geom MJCF, secteur par
  domaine, luminance B/A ≤ 0,85, chroma C ≥ 5 %, corpus bit-identique, identité B3
  poids+évaluations, budgets, ≥ 64 ancres par compétence, non-fuite d'ancres, priorité
  sommant à 1, masse TV consignée, régressions absolue+relative produites. Les sept
  points texte/code exigés par ma revue pré-campagne sont implémentés.

Réserve honnête: cet environnement n'a ni GPU ni MuJoCo, donc je n'ai pas ré-exécuté le
smoke 10991. Mais chaque propriété qu'il asserte est indépendamment satisfaite dans les
artefacts de campagne versionnés (identité B3, budgets, sha corpus, priorité normalisée,
masses TV, régressions abs+rel), ce qui corrobore la porte du smoke.

## Recomputation des portes — concordance exacte avec l'analyse de Codex

Toutes les valeurs ci-dessous ont été recalculées depuis `runs.json` avec
`learning/paired_stats.py`; elles reproduisent `analysis.json` au chiffre près.

| Porte | A | B | Statut |
|---|---|---|---|
| Garde d'oubli B1 (naïf) | mean `0,0397`, BCa `[0,0007 ; 0,116]` → **échoue** | mean `0,1414`, BCa `[0,092 ; 0,179]` → **passe** | conforme |
| H1 (naïf−uniform), relatif | mean `0,0659`, p `0,0100`, 4/6 bins | mean `0,1506`, p `0,00024`, 6/6 bins | conforme |
| H1 absolu (B2) | mean `0,0298`, même signe | mean `0,0501`, même signe | accord |
| H2 (uniform−priorité) | mean `−0,0001`, p Holm `0,835` | mean `0,0039`, p Holm `0,835` | conforme |
| H3 non-infériorité (erreur C finale) | uniform: diff `0,0082`, p Holm `0,0820`, pire bin `+14,25 %` | priorité: diff `0,0099`, p Holm `0,0876`, pire bin `+13,47 %` | conforme |
| Garde TV (priorité−uniform) | B excès `≈0`, C excès `−0,10 pt` | — | passe |

Aucune erreur de calcul ni d'interprétation détectée. Les unités de la phrase garde-TV
du rapport mélangent fraction et « points » (B `0,001 point`, C `−0,104 point`), simple
imprécision de présentation; les nombres et la comparaison au seuil `+5 points` sont
justes.

## Distinction demandée: absence d'effet, non-interprétabilité, échec

- **H1A — NON INTERPRÉTABLE.** L'adaptation naïve ne régresse que de `0,0397` en moyenne
  sur A (< 0,05), sous le seuil de détection gelé de H1, même si la borne BCa basse
  (`0,0007`) est marginalement positive. Le monde n'a pas induit d'oubli d'ampleur
  mesurable sur A: on ne peut donc rien conclure sur la valeur du replay là-bas. C'est
  exactement le statut que la garde B1 devait produire, et non un rejet du replay
  (`j6_replay.py:694-695`). À noter, subsidiairement: H1A n'aurait de toute façon pas
  passé la porte 5/6 bins (4 favorables).
- **H1B — PASS, effet réel.** Sur B, l'oubli naïf est franc (`0,1414`, 11/12 signes) et
  le replay uniforme le réduit fortement: `0,1506` relatif (`6/6` bins, p Holm
  `0,00049`), avec accord de signe absolu (`0,0501`, `12/12` signes, B2). C'est une
  démonstration solide de valeur de rétention du replay uniforme — mais elle ne suffit
  pas seule à promouvoir (voir H3).
- **H2 — ABSENCE D'EFFET (pas un effondrement).** La priorité par erreur n'apporte
  aucune valeur mesurable face au replay uniforme (`−0,0001` / `0,0039`, signes 6/6,
  p Holm `0,835`). Point diagnostique important: le piège TV-001 **ne s'est pas
  reproduit** — la fraction effective de replay TV du priorisé égale celle d'uniform
  (excès `≈0`, masse TV attendue ~`0,11`/domaine, masse par domaine ~`0,50/0,50`). Le
  null H2 se lit « aucune valeur ajoutée démontrée à cette puissance », conformément à
  la clarification gelée, et non « la priorité s'effondre sur le bruit ».
- **H3 — ÉCHEC réel et interprétable.** Ni uniform ni priorité ne démontrent la
  non-infériorité de plasticité courante: après Holm, p `0,0820` et `0,0876` (> 0,05),
  et surtout le pire bin structuré de C régresse de `+14,25 %` et `+13,47 %`, au-dessus
  de la limite régionale gelée de 10 %. Les dénominateurs C sont sains (erreurs
  `0,23–0,44`), donc ce n'est pas un artefact de petit dénominateur. Le replay 50/50
  achète la rétention au prix d'une perte de plasticité sur la session courante — le
  résultat adverse exact prévu par la règle gelée « H3 échoue ».

Garde apprenant: PASS. Garde TV: PASS. B2: accord de signe sur B. B1: A échoue
(→ non interprétable), B passe.

## Promotion — décision confirmée

- **`uniform_replay`: NON PROMU.** Deux blocages indépendants: (1) H1A non
  interprétable, donc la valeur de rétention n'est pas établie sur A (elle l'est sur B);
  (2) **H3 échoue** — cause décisive et suffisante à elle seule, `aucune condition
  concernée n'est promue` selon la règle gelée. Le code exige B1+H1 passés sur A **et** B
  et H3 passé (`j6_replay.py:748`); tout est cohérent.
- **`error_prioritized_replay`: NON PROMU.** Bloqué en cascade: uniform non promu, H2
  nul, H3 échoue. La garde TV, elle, est respectée (le priorisé n'a pas sur-répliqué la
  télévision).

La décision mécanique `uniform_promoted=False`, `error_prioritized_promoted=False`
(`analysis.json`) est correcte.

## La campagne est informative (au-delà de la non-promotion)

Trois acquis interprétables:

1. Le replay uniforme **a une valeur de rétention réelle** là où l'oubli existe (B:
   réduction relative `15 %`, 6/6 bins) — la mémoire par répétition fonctionne quand le
   monde force l'oubli.
2. Cette valeur est **payée par une plasticité courante dégradée** (H3): à 50/50 et
   calcul fixe, réallouer la moitié des gradients à l'ancien coûte plus de 10 % d'erreur
   sur le pire bin de la session courante. C'est un compromis mesuré, non une opinion.
3. La priorité par erreur, dans ce dispositif, **n'ajoute rien et ne tombe pas dans le
   piège TV** — le mode d'échec TV-001 en mémoire ne s'est pas matérialisé; le null H2
   est propre.

## Corrections bloquantes

**Aucune.** Les portes sont appliquées littéralement, la décision est correcte, aucun
retuning n'a eu lieu.

## Recommandations non bloquantes (documentation seulement, aucun calcul)

- **R1.** Mettre en avant dans `results.md` que le blocage décisif de `uniform_replay`
  est **H3** (à lui seul suffisant), pas seulement la non-interprétabilité de A. Sans
  cela, la lecture rapide sous-estime le caractère informatif de la campagne (le replay
  marche pour la rétention mais coûte trop en plasticité).
- **R2.** Consigner explicitement dans le rapport que la fraction de replay TV du
  priorisé a égalé celle d'uniform (piège TV-001 non reproduit): c'est ce qui qualifie
  le null H2 d'« absence de valeur ajoutée » plutôt que d'« effondrement ».
- **R3.** Harmoniser les unités de la phrase garde-TV (fraction vs « points »).

Ces trois points sont éditoriaux; ils ne changent aucune donnée, aucune porte, aucune
décision, et ne conditionnent pas le verdict AUTORISER.

## Suite (sans retuning sur 10301..10312)

Le déclencheur gelé est « H3 échoue → aucune condition promue; le replay achète la
stabilité au prix d'une plasticité excessive ». Toute reprise (par exemple une fraction
de replay inférieure à 50 %, ou un critère de plasticité révisé) exige, conformément à
la discipline, une **hypothèse nouvelle, un nouveau fichier de pré-enregistrement et des
graines vierges** — jamais un réglage sur les mondes `10301..10312`. Je ne propose ici
aucune valeur de remplacement. La sonde motivation dormante (encodeur gelé/plastique)
reste la condition de réouverture de D-009 et n'est pas affectée par J6-R001.
