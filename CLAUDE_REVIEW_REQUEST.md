# Demande de revue Claude — résultats TV-001 et ordre de la suite

Date: 2026-07-20
Porte: revue contradictoire après rejet interprétable de TV-H1 et TV-H2, avant toute
nouvelle campagne ou étape J6.

## Question de décision unique

TV-001 démontre-t-elle suffisamment que `regional_lp_gain` échoue avec un apprenant
visuel réel pour passer directement à l'étape 2/J6 en gardant la motivation gelée, ou
l'ambiguïté « apprentissage légitime d'une invariance au bruit » contre « attraction
pour l'aléatoire » exige-t-elle d'abord une sonde diagnostique nouvelle?

La non-promotion TV-001 n'est pas à réinterpréter: elle est acquise par protocole. La
question porte uniquement sur l'ordre expérimental suivant et la cause à tester.

## Fichiers à lire en priorité

1. `CODEX_TASK_BRIEF.md`
2. `docs/research/tv_real_jepa_001_preregistration.md`
3. `docs/research/tv_real_jepa_001_review.md`
4. `docs/research/tv_real_jepa_001_results.md`
5. `learning/tv_exploration.py`
6. `scripts/research/run_tv_real_jepa.py`
7. `DEVELOPMENTAL_ARCHITECTURE.md`, sections 7.6 et 9
8. `DECISIONS.md`, D-009

Les métriques brutes locales ne sont pas nécessaires: le document de résultats contient
les 12 paires, statistiques, garde-fous et diagnostics agrégés requis.

## Résultats compacts

- Calibration: passée, `B=4`, σ nul `0,000205`, 0 % de faux positifs, corrélation TV
  maximale `0,000913`, aucune contamination du bin 5.
- TV-H1: réduction relative regional vs babbling `-2,80 %`, IC BCa 95 %
  `[-9,92 %, +1,31 %]`, 5/12 signes favorables, p exacte `0,8076`, Holm `1,0`.
- TV-H2: regional `28,28 %` de TV contre `25,19 %`, différence `-3,09 points`,
  5/12 signes favorables, p exacte `0,8354`, Holm `1,0`.
- Garde apprenant, couverture, construction et budgets: tous passés.
- Gains régionaux moyens: structuré `0,0780`, TV `0,0860`; au round 1, TV `0,498`
  contre structuré `0,341`.
- Allocation regional moyenne par round: `26,0, 25,1, 41,7, 25,7, 45,7, 34,7,
  26,6, 37,7, 8,8, 10,9 %`.

## Interprétation actuelle de Codex

La non-promotion est nette. Le diagnostic causal ne l'est pas: le contenu TV est
i.i.d. au niveau pixel, mais un encodeur plastique peut réduire son erreur tenue à part
en apprenant à ignorer ce contenu et à préserver le bezel/périphérie prédictible. Le
signal de gain positif initial peut donc être un vrai progrès d'invariance, alors que
TV-H2 qualifie toute visite de gaspillage. Les mises à jour une fois par round et le
retour uniforme lorsque tous les scores sont clippés à zéro amplifient ensuite les
oscillations.

Option technique préférée à challenger: **geler la motivation et passer à J6**, car la
question oubli/replay est falsifiable sans ordonnanceur actif. Conserver comme future
sonde diagnostique distincte une comparaison encodeur gelé/plastique ou une cible
externe irréductible; ne pas retarder J6 si cette sonde ne conditionne pas ses baselines.

## Mission de Claude

- vérifier que l'interprétation invariance vs bruit est compatible avec les métriques;
- dire si elle rend TV-001 non informatif au-delà de la non-promotion (sans rouvrir le
  verdict);
- recommander explicitement l'une des options:
  - `J6 D'ABORD`: motivation gelée, pré-enregistrement naïf vs replay uniforme vs
    replay priorisé;
  - `DIAGNOSTIC D'ABORD`: définir la manipulation minimale et la décision qu'elle
    change avant J6;
  - `ARRÊT/ARBITRAGE OBJECTIF`: seulement si aucune des deux voies ne répond encore au
    brief;
- si un diagnostic est exigé, donner hypothèse, baseline simple, métrique, coût maximal
  et règle d'arrêt — aucune retouche de TV-001;
- identifier tout écart entre le verdict documenté et les règles gelées.

## Forme attendue

Écrire `docs/research/tv_real_jepa_001_results_review.md` avec:

- verdict parmi les trois options ci-dessus;
- constats classés par gravité;
- justification causale;
- prochaine expérience minimale, si nécessaire;
- commande ou pré-enregistrement que Codex est autorisé à préparer ensuite.

Ne lance aucun calcul et ne modifie aucun autre fichier.

## Prompt exact à transmettre à Claude

```text
Effectue la revue de résultats demandée dans CLAUDE_REVIEW_REQUEST.md. Lis les fichiers
indiqués, maintiens la non-promotion TV-001 acquise, puis tranche uniquement l'ordre de
la suite: J6 d'abord, diagnostic d'abord, ou arrêt/arbitrage objectif. Écris ton verdict
dans docs/research/tv_real_jepa_001_results_review.md. Ne lance aucun calcul et ne
modifie aucun autre fichier.
```
