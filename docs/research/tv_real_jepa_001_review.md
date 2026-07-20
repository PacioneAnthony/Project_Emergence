# Revue contradictoire TV-001 — avant calibration et campagne

Date: 2026-07-20. Revue demandée par `CLAUDE_REVIEW_REQUEST.md`, portant sur
`docs/research/tv_real_jepa_001_preregistration.md`, `learning/tv_exploration.py`,
`scripts/research/run_tv_real_jepa.py`, `tests/test_tv_exploration.py`,
`learning/paired_stats.py` et les fonctions réutilisées de
`learning/active_exploration.py` (`ExperienceBuffer`, `train_round`,
`coverage_entropy`). Aucun calcul n'a été lancé; aucun fichier autre que la présente
revue n'a été modifié.

## Verdict

**AUTORISER AVEC CORRECTIONS BLOQUANTES.**

Le protocole isole correctement la valeur de `regional_lp_gain`: pas d'oracle, ancres
réellement tenues à part et identiques dans chaque paire, budgets symétriques,
agrégation avant clip conforme au diagnostic DC-005, portes statistiques non vacueuses
et exécutables à n=12. Deux défauts doivent être corrigés avant d'ouvrir les graines
`9201..9203`: une porte de revue mal placée dans le runner, et un amendement
documentaire daté sur deux écarts entre le texte gelé et le monde implémenté. Aucune
correction ne touche un seuil, une graine, un budget ou la question gelée.

## Défauts bloquants

### B1 — La porte `--review-accepted` ne protège pas la calibration

`scripts/research/run_tv_real_jepa.py:272-275` exécute `run_calibration` (graines
`9201..9203`) dès que ni `--summary-only` ni `--campaign-only` n'est passé; le
contrôle `--review-accepted` n'intervient qu'à la ligne 285, juste avant les graines
de campagne. Le pré-enregistrement (§Séquence, point 3) exige la revue **avant la
calibration et avant la campagne**. En l'état, `--calibration-only` — ou un lancement
sans drapeau — ouvre les graines de calibration sans que la porte de revue soit
vérifiée.

Correction minimale exigée: déplacer le contrôle `--review-accepted` avant
`run_calibration` (le mode `--smoke`, graine 9991 hors protocole, reste exempté;
`--summary-only` aussi, puisqu'il n'ouvre aucune graine). Aucun seuil ni graine ne
change.

### B2 — Amendement documentaire daté requis: surface d'écran et alignement des bins

Deux affirmations du pré-enregistrement ne décrivent pas exactement le monde
implémenté. Ni l'une ni l'autre n'invalide le test, mais le texte gelé doit être
amendé, avec date, avant tout calcul — sinon le premier écart constaté après coup
ressemblera à une retouche post hoc.

1. **Surface de l'écran.** Le texte dit « un écran central bordé remplace 75 %
   environ des pixels ». `television_rectangle`
   (`learning/tv_exploration.py:71-73`) couvre les fractions `[1/8, 7/8]` de chaque
   dimension, soit 75 % **par dimension** mais **56,25 % des pixels**. La
   revendication d'inapprenabilité repose sur la porte de corrélation `|r| ≤ 0.02`,
   qui ne dépend pas de la surface; je recommande donc d'amender le texte plutôt que
   d'agrandir le rectangle (modifier le monde après gel serait pire).

2. **Alignement secteur/bins.** Le texte dit « Les frontières d'angle sont celles du
   servo, pas celles de la télévision ». Or les huit bins de 20° sur `[10°, 170°]`
   placent une frontière exactement à 130°: le secteur télévision `[130°, 170°]`
   coïncide **exactement** avec les bins 6 et 7 (`angle_bin(130.0) == 6`, vérifié
   par `tests/test_tv_exploration.py:20`). La phrase est vraie quant à l'origine des
   frontières mais fausse quant à leur non-coïncidence. C'est le cas le plus
   favorable pour `regional_lp_gain` (aucune cellule mixte structuré/bruit); la
   politique ne reçoit toujours aucun oracle, mais la portée de TV-H2 doit être
   déclarée limitée au cas aligné.

Texte exact de l'amendement à ajouter en fin de pré-enregistrement:

> **Amendement du 2026-07-20, avant calibration et avant tout calcul sur graines
> réservées (revue contradictoire, correction de description sans changement de
> seuil ni de code du monde):** (1) l'écran couvre les fractions `[1/8, 7/8]` de
> chaque dimension de l'image, soit 56,25 % des pixels (75 % par dimension); la
> périphérie et le bezel restent visibles et prédictibles, seul le contenu central
> est du bruit indépendant soumis à la porte de corrélation. (2) Le secteur
> `[130°, 170°]` coïncide exactement avec les bins servo 6 et 7; les frontières des
> bins sont définies par le servo mais l'une d'elles tombe sur la frontière de la
> télévision. La conclusion TV-H2 vaut pour ce cas aligné; la généralisation à un
> secteur chevauchant plusieurs bins partiels n'est pas revendiquée.

## Défauts non bloquants, par gravité décroissante

- **M1 — Contamination marginale possible des ancres du bin 5.**
  `generate_anchor_bank` (`learning/tv_exploration.py:194-218`) étiquette la cellule
  par le bin **visé** mais applique la télévision selon l'angle **réel**
  (`obs_end.as5600_deg`); la marge de tirage n'est que de 0,25° sous 130°. Un
  dépassement de servo ferait entrer une image bruitée dans les ancres de la cellule
  (5, ·). Les métriques finales utilisent l'angle réel (`target_deg < 130`), donc
  TV-H1 n'est pas affectée; seul le signal de gain de cette cellule serait
  légèrement bruité. Vérification recommandée, sans modification de code: après
  génération des banques, compter les ancres de bin visé ≤ 5 dont
  `target_deg ≥ 130` et consigner ce comptage (attendu: 0 ou quasi nul).
- **M2 — Bruit calibré sur modèle non entraîné.** La calibration mesure `s` et `m`
  sur un JEPA à poids aléatoires (pré-enregistré ainsi). Le niveau de bruit d'un
  modèle entraîné peut différer; l'erreur bornée `pred/(pred+copy)` limite la dérive
  d'échelle, et les gains par round sont consignés (`regional_gains`), ce qui
  permettra de vérifier a posteriori que `B` restait adapté. Limite d'interprétation
  à mentionner dans le rapport final, rien à corriger.
- **M3 — Comportement à saturation.** Quand tous les gains agrégés deviennent ≤ 0,
  tous les scores valent 0 (`RegionalGainTelevisionPolicy.score`,
  `learning/tv_exploration.py:321-325`) et le bris d'égalité uniforme inclut les
  cellules télévision, en plus du plancher ε = 0,10. `regional_lp_gain` tend donc
  vers l'uniforme en fin de budget. C'est un comportement honnête du mécanisme testé
  — un risque pour TV-H2, pas un défaut de validité.
- **M4 — Tension garde de couverture / plancher ε.** Le plancher ε donne en
  espérance 1,25 % des décisions par cellule, sous le seuil de 2 % par bin structuré
  exigé par la garde. La garde ne peut passer que si l'optimisme initial et la phase
  gloutonne visitent réellement chaque bin: un échec « non interprétable » est un
  résultat plausible par construction. Pré-enregistré, assumé, rien à changer.
- **M5 — Lectures à figer avant données.** (a) TV-H2 « moins de 15 % » est
  implémenté comme **moyenne sur les 12 graines** (`run_tv_real_jepa.py:197`), pas
  par graine: cette lecture est raisonnable et doit être déclarée maintenant.
  (b) Le test de retournement de signes sur la réduction **relative** (un ratio)
  suppose la symétrie sous H0 de façon approchée; les comptages de signes
  obligatoires servent de contrôle. Les deux points sont conformes au texte gelé;
  il s'agit seulement de fermer l'ambiguïté avant tout calcul.
- **M6 — Partage des réalisations télévision.** Les deux conditions partagent la
  graine `tv_rng` par pièce, mais la consommation du générateur diverge dès que les
  politiques visitent différemment le secteur: les réalisations ne sont identiques
  qu'au sens de la graine, pas image par image. Sans conséquence statistique (bruit
  i.i.d.); reformulation possible dans le rapport final.
- **M7 — Validation faible au rechargement des banques.** `AnchorBank.load` via
  `generate_anchor_bank` (`learning/tv_exploration.py:159-164`) ne vérifie que le
  nombre d'ancres, ni la graine ni la taille d'image. Risque limité à une erreur
  d'opérateur; amélioration facultative.

## Vérifications positives explicites

- **Pas d'oracle.** La politique ne reçoit que les gains agrégés des cellules
  visitées (`run_condition`, `learning/tv_exploration.py:577-593`); ni frontière, ni
  drapeau, ni graine, ni erreur télévision. Le contexte est un bit de hachage de
  pixels observés (`visual_context_id`), sans corrélation avec la télévision
  (présente dans toutes les pièces au même secteur).
- **Ancres hors entraînement et partagées.** Pièces d'ancrage `41_000_000 + …`
  disjointes des pièces d'entraînement `51_000_000 + …`; les ancres n'entrent jamais
  dans `ExperienceBuffer`; le test final utilise la banque entière
  (`full_anchor_metrics`). Même fichier de banque, même initialisation de modèle
  (`torch.manual_seed(args.seed)`), mêmes pièces et même calendrier de mini-batchs
  (graines de sonde dérivées de `args.seed`/round/cellule) pour les deux conditions
  d'une paire.
- **Budgets symétriques.** 8 000 images et 1 600 décisions vérifiés numériquement
  dans `summarize`; les pas d'optimisation ne dépendent que de la taille du buffer
  (identique par construction); les sondes avant/après sont sans gradient et
  n'entraînent rien, dans les deux conditions.
- **Agréger puis clipper.** Historiques signés (`update`), clip uniquement dans
  `score` après moyenne des mini-batchs et de l'historique — conforme au diagnostic
  `dc005_design_review.md`. La règle de calibration du code applique exactement le
  texte gelé (`1.96·s/√B ≤ 0.02·m`, taux de faux positifs ≤ 0,05, grille
  `{4, 8, 16, 32}`, arrêt si aucun candidat); les agrégats sont alignés dans les
  cellules (64 divisible par chaque `B`), et la variance de l'agrégat de campagne
  correspond bien à `s²/B` mesuré.
- **Statistiques.** Retournement de signes exact (n = 12 ≤ 20), Holm sur deux
  hypothèses, BCa graine `20260720`, comptages de signes, `dz` et rank-bisériale
  descriptifs: conformes à `learning/paired_stats.py` et au texte gelé. Les portes
  ne sont pas vacueuses: babbling attend ~25 % de décisions télévision, le seuil
  TV-H2 de 15 % et l'effet minimal TV-H1 de 5 % sont exigeants.
- **Runner.** Graines `9201..9203` et `9301..9312` figées en constantes, ordre des
  conditions alterné par parité, reprise par runs complets, `--smoke` confiné à la
  graine 9991 et à des répertoires séparés. Tous les seuils du code
  (5 %, 15 %, 0,75, 2 %, 10 %, α = 0,05, `|r| ≤ 0,02`) correspondent au texte gelé.

## Confirmation de gel

Les seuils, graines, budgets, conditions et règles de décision du pré-enregistrement
restent **gelés et inchangés**. Les deux corrections bloquantes sont: un déplacement
de porte dans le runner (B1, sans effet sur aucun seuil) et l'amendement documentaire
daté dont le texte exact figure en B2 (correction de description, pas de porte).
Aucun calcul sur `9201..9203` ou `9301..9312` avant l'application des deux.

## Commande autorisée

Après application de B1 et insertion de l'amendement B2 dans le pré-enregistrement:

```bash
python scripts/research/run_tv_real_jepa.py --review-accepted
```

qui exécute la calibration, applique sa porte gelée, puis enchaîne la campagne
appariée et le résumé. L'exécution en deux temps
(`--calibration-only --review-accepted`, puis `--campaign-only --review-accepted`)
est également autorisée.
