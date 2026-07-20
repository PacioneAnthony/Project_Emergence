# Clôture technique J6-AR001 — plafond atteint

Date: 2026-07-20

## Statut

**NON-RÉSULTAT TECHNIQUE.** Aucune porte B1/H1/H2/H3 n'est calculée, aucune comparaison
scientifique n'est interprétée et aucune condition n'est promue ou rejetée.

## Séquence vérifiée

- La revue pré-calcul a conclu **AUTORISER AVEC CORRECTIONS BLOQUANTES**.
- C1–C4 ont été intégrées additivement avant création du code et tout calcul.
- 181 tests ont réussi.
- Le smoke hors protocole 11991 a passé les constructions D/E/F, B3, budgets,
  séparation entraînement/suivi/décision, composition exacte, recomputabilité de `rho`,
  parité des évaluations et définition conditionnelle de la fraction TV.
- Les graines réservées n'ont été ouvertes qu'après ce smoke vert et un digest concordant.

## Arrêt

Le runner a levé `TimeoutError: J6-AR001 75-minute GPU wall-clock cap reached` pendant
la branche `adaptive_replay` de 11313.

État complet au moment de l'arrêt:

- 11301..11312: trois conditions complètes, soit 12 triplets / 36 runs;
- 11313: `naive` et `uniform_50` complets; `adaptive_replay` interrompu sans fichier de
  résultat complet;
- 11314..11316: non ouvertes;
- total valide: 38 runs complets;
- temps des artefacts complets: 73,22 minutes; le fragment interrompu porte le temps
  mural au plafond de 75 minutes.

Le protocole exige 16 triplets et 48 runs. Les 12 triplets complets ne sont donc pas un
échantillon décisionnel autorisé. Aucun export d'analyse ou rapport de résultats n'est
produit. Les artefacts locaux restent conservés pour audit technique, sans publication
de métriques partielles susceptible d'encourager une lecture post hoc.

## Décision

Le plafond n'est pas étendu et la campagne n'est pas reprise. J6-AR001 avait gelé la
clôture de cette variante unique quelle que soit son issue; D-012 applique cette règle.
L'hypothèse « adaptive_replay résout le compromis » demeure **non testée**, pas rejetée.

La suite active devient l'étape 3 du brief, réafférence, sous un pré-enregistrement et
des graines entièrement nouveaux.
