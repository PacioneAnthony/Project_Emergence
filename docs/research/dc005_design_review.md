# Revue de conception de l'ordonnanceur après DC-004

Date: 2026-07-20. Déclencheur: décision pré-enregistrée DC-004 (« retour en conception,
pas de simulation visuelle »). Périmètre: le seul mécanisme d'échec mesuré; aucune
retouche des autres composantes (frontière, habituation, couverture, coefficients).

## Diagnostic ancré dans le code

1. **Clip par observation.** `InterventionalCuriosity.observe`
   (`learning/developmental_curiosity.py:317`) stocke `gain = max(before − after, 0)` et
   `FractionalInterventionalCuriosity.score_components` (`:454`) recalcule
   `max(before − after, 0) / max(before, 1e-8)` **par observation**, avant tout
   moyennage. Sous bruit d'ancre symétrique de variance 2σ², chaque observation clippée
   a une espérance strictement positive (≈ 0.8·σ·√2 en zone inapprenable) — le bruit
   d'évaluation devient un signal d'apprenabilité fantôme. C'est le biais prédit par la
   revue DC-003 (section B) et mesuré par DC-004: gain clippé moyen en zone bruit
   `0.0102 → 0.0198 → 0.0279` pour σ = 0 → 0.02 → 0.05.
2. **Normalisation par un dénominateur bruité.** La division par `before` fait exploser
   le gain fractionnel fantôme là où l'erreur vraie est faible: en zone base
   (erreurs 0.04-0.24 face à σ = 0.05), le rapport bruit/signal du dénominateur est
   maximal. Conséquence comportementale observée en DC-004: la politique reste collée à
   la base (fraction bruit `1.82%`, erreur structurée `0.386`) — la base paraît
   éternellement productive.
3. **Contre-preuve interne.** `regional_lp_gain` reçoit exactement la même information
   bruitée mais moyenne ~40 gains **signés** par bin avant d'en faire un score: le bruit
   s'annule en moyenne et la politique reste robuste (`0.1105` à σ = 0.05). La
   défaillance est donc bien dans l'ordre des opérations clip/moyenne, pas dans la
   mesure interventionnelle.

## Correctif proposé: agréger puis clipper (`PooledFractionalCuriosity`)

Variante minimale de `FractionalInterventionalCuriosity`, nouvelle classe dans
`learning/pooled_curiosity.py`, qui ne change que l'estimateur de gain:

- gains **signés** par observation: `raw = before − after` (aucun clip au stockage);
- agrégation par région (mêmes noyaux, mêmes poids de récence):
  `mean_raw = Σ w·raw / Σ w` et `mean_before = Σ w·before / Σ w`;
- gain fractionnel **régional**: `ratio = mean_raw / max(mean_before, 1e-8)` — le
  dénominateur agrégé casse la corrélation observation-par-observation avec le bruit;
- clip **après** agrégation et pénalité d'incertitude inchangée:
  `confirmed = max(ratio − 0.5·stderr_ratio, 0)`, avec
  `stderr_ratio = stderr(raw) / max(mean_before, 1e-8)`.

Le biais résiduel décroît en 1/√(évidence effective) au lieu d'être constant. Tout le
reste est copié à l'identique du gel DC-003: pression de couverture `√(1 + evidence/8)`,
familiarité, habituation (`low_gain` évalué sur `max(ratio, 0)`), imprévisibilité
persistante, frontière, coefficients 2.0/0.08/0.05/0.30/0.50, ε = 0.05.

## Prédictions falsifiables (avant DC-005)

1. En zone inapprenable bruitée, le gain confirmé de la variante tend vers 0 avec
   l'évidence (test unitaire synthétique: ancres constantes + bruit symétrique);
2. à σ = 0.05 la variante retrouve un comportement proche de son régime σ = 0;
3. l'ancien `fractional`, inclus comme condition témoin dans DC-005, reproduit son
   effondrement (contrôle positif du banc);
4. à σ = 0, la variante ne régresse pas face à `fractional` (les moyennes signées et
   clippées coïncident quand aucun gain n'est négatif — seuls les mondes sans bruit
   d'ancre ont cette propriété).

## Ce qui reste hors périmètre

Pas de nouveau descripteur, pas de retuning des coefficients, pas d'oubli/interférence
dans le monde (objection connue, traitée après qu'un ordonnanceur survit au bruit).
Toute évaluation passe par le pré-enregistrement DC-005 sur graines vierges
(`dc005_preregistration.md`); les mondes 7301..7340 de DC-004 ne servent à aucun
réglage.
