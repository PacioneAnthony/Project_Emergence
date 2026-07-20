# Pré-enregistrement DC-005 — gain fractionnel agrégé sous bruit d'ancre

Date de gel: 2026-07-20, avant toute implémentation de `PooledFractionalCuriosity` et
avant tout calcul sur les graines de campagne. Découle de `dc005_design_review.md`
(correctif agréger-puis-clipper) et reprend le banc durci DC-004 à l'identique
(`learning/hardened_curiosity_benchmark.py`: ancres bruitées tronquées à zéro, layout
permuté sur graines paires, mêmes familles de paramètres cachés). Aucun seuil modifiable
après observation des résultats. Les mondes DC-004 (7301..7340) n'ont servi à aucun
réglage de la variante.

## Périmètre

- **Graines**: 8301..8340 inclus (40 mondes vierges, 20 permutés — graines paires).
- **Budget**: 1 200 échantillons = 300 interventions × 4, par condition et par σ.
- **σ**: passes complètes à 0, 0.02 et 0.05; portes évaluées à σ = 0.05 sauf D5-H3.
- **Conditions**: `pooled` (variante), `fractional` (témoin d'effondrement),
  `babbling`, `regional_lp_gain` (contrôle informationnel robuste).
- **Sortie**: `data/processed/experiments/developmental_curiosity_005/`.
- **Tests**: permutation par signes Monte-Carlo 200 000 tirages, graine 20260722,
  estimateur add-one (n = 40 interdit l'énumération exacte), α = 0.05, unilatéral;
  non-infériorité par décalage de marge comme en DC-003R.

## Portes gelées

### D5-H1 — efficacité sous bruit (primaire)

À σ = 0.05: erreur structurée de `pooled` sous celle de `babbling` (permutation MC
appariée, unilatéral) **et** fraction bruit moyenne de `pooled` < 15 %.

### D5-H2 — valeur ajoutée face au contrôle informationnel

À σ = 0.05, face à `regional_lp_gain`: non-infériorité en erreur structurée (marge 5 %
relatif de l'erreur moyenne du contrôle, permutation MC en cadre de non-infériorité)
**et** fraction bruit de `pooled` strictement inférieure (permutation MC appariée,
unilatéral).

### D5-H3 — absence de régression sans bruit

À σ = 0: non-infériorité de `pooled` face à `fractional` en erreur structurée (marge
5 % relatif de l'erreur moyenne de `fractional`, permutation MC).

### Rapports obligatoires (sans rôle de porte)

- Contrôle positif: l'effondrement de `fractional` à σ = 0.05 doit être rapporté; s'il
  ne se reproduit pas, le banc lui-même est suspect et la campagne est consignée comme
  non interprétable;
- rapport de biais en zone bruit par σ pour `pooled` et `fractional`;
- comptages de signes, dz descriptifs, décomposition permuté/standard.

## Décision pré-enregistrée

- **Toutes les portes passent** → l'ordonnanceur survit au bruit d'ancre: le blocage
  DC-004 sur la simulation visuelle est levé, sous réserve d'une revue contradictoire
  du présent protocole et des résultats avant conception de la simulation.
- **D5-H1 échoue** → arrêt de la famille d'ordonnanceurs développementaux à gain
  fractionnel; `regional_lp_gain` devient l'ordonnanceur de référence du projet.
- **D5-H2 échoue (volet bruit seulement)** → la machinerie développementale n'apporte
  rien de mesurable au-delà du LP informé: piste honnête = `regional_lp_gain` + garde
  anti-bruit, consignation.
- **D5-H3 échoue** → la variante est une régression en régime propre: rejet de
  `pooled`, la revue de conception reprend (le correctif suivant devra être
  pré-enregistré à son tour, graines vierges).

## Contraintes d'implémentation

- Nouvelle classe dans `learning/pooled_curiosity.py`; aucun fichier gelé modifié
  (`developmental_curiosity.py` intact); ajout additif de la condition `pooled` au
  banc durci et nouveau runner `scripts/research/run_pooled_curiosity.py`.
- Tests unitaires exigés avant campagne: biais nul asymptotique en zone inapprenable
  bruitée (contraste direct avec `fractional` sur les mêmes données synthétiques),
  détection d'un apprentissage réel, déterminisme.
