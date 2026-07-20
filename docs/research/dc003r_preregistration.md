# Pré-enregistrement DC-003R — réplication appariée du gain fractionnel

Date de gel: 2026-07-20, avant toute implémentation du script d'analyse et avant tout
calcul sur les graines de réplication. Découle de la section E de
`dc003_statistical_review.md`. Aucun seuil de ce document ne peut être modifié après
observation des résultats.

## Périmètre

Réplication strictement inchangée de DC-003: mêmes mondes (`make_world`), mêmes quatre
conditions (`fractional`, `babbling`, `round_robin_habituation`, `regional_lp`), mêmes
budgets, mêmes coefficients. `learning/developmental_curiosity.py` et
`learning/fractional_curiosity_benchmark.py` sont gelés — seul le script d'analyse change.

- **Graines**: 6301..6320 inclus (20 mondes), jamais utilisées auparavant.
- **Budget**: 1 200 échantillons = 300 interventions × 4 échantillons, par condition.
- **Sortie**: `data/processed/experiments/developmental_curiosity_003R/`
  (`metrics.json`, `summary.md`), sans modification des artefacts DC-003.

## Hypothèses et portes gelées

### R-H1 — efficacité (primaire)

Réduction relative appariée moyenne de l'erreur structurée finale ≥ 10 % face à
`babbling` **et** face à `round_robin_habituation`.

- Test: permutation exacte par retournement de signe sur les 20 différences appariées
  (2²⁰ = 1 048 576 affectations, énumération exhaustive), unilatéral, correction de Holm
  sur les deux comparaisons, α famille = 0.05.
- Exigence additionnelle: borne inférieure de l'IC bootstrap BCa à 95 %
  (10 000 rééchantillons de mondes, graine bootstrap fixée à 20260720) de la réduction
  relative moyenne > 0, pour chacune des deux comparaisons.
- La réduction relative par monde est `(erreur_contrôle − erreur_fractional) / erreur_contrôle`.

### R-H1b — non-infériorité face à `regional_lp`

Moyenne appariée `(erreur_fractional − erreur_regional_lp)` ≤ 5 % relatif de l'erreur
moyenne de `regional_lp` sur les 20 mondes. Marge fixée maintenant comme la moitié de
l'effet minimal de R-H1, en connaissance des données de développement — la protection est
l'application à des graines vierges.

- Test: même permutation exacte par signes, en cadre de non-infériorité (hypothèse nulle:
  différence moyenne ≥ marge; les différences sont décalées de la marge avant
  retournement de signe), unilatéral, α = 0.05.

### R-H2 — évitement du bruit

Fraction bruit de `fractional` au moins 50 % sous `babbling` et inférieure aux deux autres
contrôles (inchangé de DC-003), **plus** test de permutation exacte apparié par signes sur
la fraction bruit face à `babbling`, unilatéral, α = 0.05.

### R-H3 — progression développementale

Sur au moins 16/20 graines: distance médiane à la base plus faible dans le premier
quintile que dans les 40 % centraux, plus de 50 % de structuré dans les 40 % centraux, et
moins de 15 % de bruit dans le dernier quintile (signature inchangée de DC-003).

### Garde-fous

- **Couverture**: entropie moyenne de `fractional` ≥ 0.65.
- **Stabilité**: écart-type de l'erreur structurée de `fractional` ≤ celui de `babbling`.

### Rapport obligatoire

- Comptage explicite et automatisé des signes appariés (x/20) face à chacun des trois
  contrôles — la revendication 20/20 de DC-003 n'était produite par aucun code.
- dz et corrélation rank-bisériale rapportés à titre descriptif, sans rôle de porte.
- p-values exactes de permutation, IC BCa complets, marge de non-infériorité en absolu.

## Décision pré-enregistrée

- **Toutes les portes passent** → promotion vers DC-004 (durcissement), qui devra être
  pré-enregistré à son tour avant exécution, conformément à la section E de la revue.
- **R-H1 échoue face aux deux baselines** → arrêt de la famille d'ordonnanceurs à gain
  fractionnel, revue conceptuelle.
- **R-H1b seul échoue** → pas de promotion: la valeur ajoutée face au LP régional n'est
  pas démontrée; la piste honnête devient « LP régional + garde anti-bruit ».
- Tout autre échec partiel (R-H2, R-H3, garde-fous) → pas de promotion, consignation, et
  décision de suite laissée à une revue dédiée.

## Contraintes d'implémentation

- Nouveau module `learning/paired_stats.py` (permutation exacte, BCa, Holm,
  non-infériorité, comptage de signes) avec tests unitaires dédiés contre des cas de
  référence calculables à la main.
- Nouveau runner `scripts/research/run_fractional_replication.py` réutilisant
  `run_condition` de `fractional_curiosity_benchmark.py` sans le modifier.
- Le verdict historique de DC-003 n'est pas réécrit; ses artefacts restent intacts.
