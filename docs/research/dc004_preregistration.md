# Pré-enregistrement DC-004 — durcissement du gain fractionnel

Statut: brouillon rédigé le 2026-07-20 avant exécution de DC-003R; **gelé le 2026-07-20
après la promotion DC-003R (toutes portes passées) et avant toute implémentation ou
exécution DC-004**. Découle de la section E de `dc003_statistical_review.md`. Aucun
seuil ne peut être modifié après observation des résultats.

Précision de gel (avant exécution): avec 40 mondes, l'énumération exacte 2⁴⁰ est
impossible. Les tests appariés sur les 40 mondes utilisent la permutation par signes
Monte-Carlo: 200 000 tirages, graine 20260721, estimateur add-one
`(1 + succès) / (1 + tirages)`. Le test D4-H3, restreint aux 20 mondes permutés, reste
en énumération exacte 2²⁰. Le bruit d'ancre s'applique à toutes les valeurs d'ancre
visibles des politiques (before/after pour fractional et regional_lp_gain, after pour
regional_lp); les métriques oracle restent calculées sans bruit.

Amendements d'implémentation (2026-07-20, consignés avant toute exécution de campagne,
découverts par les tests unitaires, aucun résultat DC-004 observé):

1. **Troncature à zéro des ancres bruitées**: l'algorithme gelé rejette les erreurs
   d'ancre négatives (contrainte de domaine de
   `FractionalInterventionalCuriosity.observe`). Les valeurs bruitées sont donc
   `max(valeur + σ·ξ, 0)`, identiquement pour toutes les politiques consommant des
   ancres. La troncature ne concerne en pratique que la zone base (erreurs ~0.04-0.24).
2. **Fuite structurée résiduelle dans la bande de bruit permutée**: les transitions
   sigmoïdes (mêmes raideurs que le monde original) laissent jusqu'à ~9 % de poids
   structuré au centre des bandes de bruit les plus étroites — le layout original
   présente la même fuite en bordure de sa zone bruit. Le gain d'ancre en zone bruit à
   σ = 0 est donc quasi nul et non exactement nul; le rapport de biais s'interprète
   comme la croissance du gain clippé avec σ au-dessus de ce niveau de fuite.

## Motivation

DC-003R, même réussi, ne lève pas les trois objections de construction de la revue:
oracle de gain sans bruit, géométrie monotone favorable, absence de contrôle
informationnel. DC-004 les attaque frontalement, algorithme strictement gelé
(`learning/developmental_curiosity.py` inchangé, coefficients compris).

## Périmètre

- **Mondes**: 40, graines 7301..7340, mêmes familles de paramètres cachés que DC-003.
- **Budget**: identique (1 200 échantillons = 300 interventions × 4) par condition.
- **Sortie**: `data/processed/experiments/developmental_curiosity_004/`.

## Manipulations

1. **Ancres bruitées**: les valeurs before/after fournies aux politiques qui en
   consomment sont perturbées par un bruit gaussien indépendant d'écart-type σ = 0.02
   puis σ = 0.05 (deux passes complètes). Les métriques oracle restent calculées sur les
   valeurs non bruitées. Teste le biais du clip `max(gain, 0)` en régime stochastique.
2. **Layout permuté**: sur 20 des 40 mondes (graines paires), la bande de bruit est
   placée entre la base et le structuré; home = 0.10 reste dans la base. Teste la
   capacité à franchir une région inapprenable au lieu de bénéficier de la géométrie
   monotone. Les 20 autres mondes gardent le layout DC-003.
3. **Contrôle informationnel**: baseline `regional_lp_gain` — le LP régional recevant
   before−after comme signal d'apprentissage, même information que fractional. Sépare la
   valeur de l'information interventionnelle de celle du mécanisme d'ordonnancement.

Conditions: `fractional`, `babbling`, `regional_lp`, `regional_lp_gain` (round-robin
abandonné: dominé deux fois, le contrôle informationnel le remplace à budget constant).

## Portes gelées (évaluées à σ = 0.05, appariées, mêmes tests que DC-003R)

- **D4-H1**: erreur structurée de fractional sous celle de babbling (permutation exacte
  par signes, unilatéral, α = 0.05) et fraction bruit < 15 % en moyenne.
- **D4-H2 (contrôle informationnel)**: face à `regional_lp_gain`, non-infériorité en
  erreur structurée (marge 5 % relatif, cadre identique à R-H1b) **et** fraction bruit
  strictement inférieure (permutation appariée, unilatéral, α = 0.05).
- **D4-H3 (géométrie)**: sur les 20 mondes à layout permuté pris seuls, l'erreur
  structurée de fractional reste sous celle de babbling (permutation appariée sur les 20
  différences, unilatéral, α = 0.05) — la politique doit traverser le bruit, pas en être
  protégée par la géométrie.
- **Rapport σ = 0.02**: résultats complets rapportés à titre descriptif, sans porte.
- **Rapport de biais**: gain fractionnel moyen mesuré en zone bruit par σ (0, 0.02,
  0.05); une croissance monotone avec σ documente le biais du clip prédit par la revue.

## Décision pré-enregistrée

- Toutes les portes passent → promotion vers la conception d'une simulation visuelle
  plus riche (conditions de la section E de la revue remplies).
- D4-H1 échoue à σ = 0.05 → la robustesse au bruit d'évaluation n'est pas acquise:
  retour en conception (le clip et la normalisation du gain sont les premiers suspects),
  pas de simulation visuelle.
- D4-H2 échoue → la valeur ajoutée du mécanisme n'est pas démontrée face à un LP recevant
  la même information: la piste honnête devient « LP régional + information
  interventionnelle », consignation et revue conceptuelle.
- D4-H3 seul échoue → le bénéfice dépend de la géométrie: consignation explicite et
  revue de conception du descripteur de frontière avant toute suite.

## Contraintes d'implémentation

- Nouveaux fichiers uniquement; `fractional_curiosity_benchmark.py`,
  `curiosity_benchmark.py` et `developmental_curiosity.py` restent intacts (extension par
  sous-classe ou composition pour le monde permuté et le bruit d'ancre).
- Réutilisation de `learning/paired_stats.py` (DC-003R) pour toutes les portes.
- Tests unitaires: déterminisme, budget exact, géométrie permutée correcte (frontières),
  bruit d'ancre reproductible par graine, absence de fuite des frontières vers les
  politiques.
