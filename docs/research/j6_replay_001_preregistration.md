# Pré-enregistrement J6-R001 — rétention visuelle en monde non stationnaire

Date de gel: 2026-07-20, avant implémentation et avant tout calcul sur les graines
réservées. Filiation: étape 2 de `CODEX_TASK_BRIEF.md`, verdict « J6 D'ABORD » de
`tv_real_jepa_001_results_review.md`, motivation gelée par D-009.

## Question

Dans une succession de pièces visuellement modifiées, un JEPA visuel conserve-t-il
mieux ses contingences anciennes avec replay d'épisodes qu'avec adaptation naïve, et
un replay priorisé par erreur de prédiction apporte-t-il une valeur mesurable face au
replay uniforme sans sur-échantillonner le secteur télévision?

Le test porte sur la consolidation, pas sur l'exploration. Les trois conditions
collectent exactement les mêmes épisodes par babbling; aucun ordonnanceur de motivation
n'intervient.

## Hypothèses gelées

- **J6-H1A et J6-H1B — valeur du replay uniforme:** après la troisième session, le
  replay uniforme réduit d'au moins `0,05` la régression relative moyenne des six
  compétences structurées de la session A, et séparément de la session B, face à
  l'adaptation naïve.
- **J6-H2 — valeur ajoutée de la priorité par erreur:** le replay priorisé réduit d'au
  moins `0,03` supplémentaire la régression relative sur **A et B** face au replay
  uniforme.
- **J6-H3 — plasticité courante:** sur la session C tenue à part, uniform et priorisé
  restent chacun non inférieurs à naïf dans une marge de `5 %` relatif d'erreur.

Les domaines A/B et les six régions d'angle structurées restent des métriques séparées.
Aucune moyenne globale unique ne peut masquer la perte d'une compétence.

## Graines et coût maximal

- Smoke d'intégration hors protocole: `10991`, aucun rôle de décision.
- Campagne appariée: graines vierges `10301..10312` (12 triplets).
- Trois conditions: `naive`, `uniform_replay`, `error_prioritized_replay`.
- Trois sessions séquentielles A→B→C par run.
- Collecte par session et par graine: 20 épisodes de 200 images à 10 Hz, soit 4 000
  images et 800 décisions babbling. Le corpus d'une graine est généré une fois et partagé
  bit à bit entre ses trois conditions.
- Total d'interaction par condition: 12 000 images et 2 400 décisions.
- Optimisation: exactement 1 500 pas AdamW par session, batch 256, soit 4 500 pas par
  condition. Plafond campagne: 36 runs et 90 minutes GPU murales; runner résumable au
  niveau run, keep-awake, arrêt technique si un budget ou un manifeste diverge.
- Sorties locales: `data/processed/experiments/j6_replay_001/`; checkpoints sous
  `models/`; rapport versionné sous `docs/research/`.

## Apprenant

JEPA v3 inchangé: images 64×64, encodeur convolutionnel largeur 32, latent 128,
prédicteur caché 512, action et horizon conditionnés, horizons 1..5, pertes stop-gradient
et variance/covariance existantes. AdamW `lr=3e-4`, weight decay `1e-4`, poids variance
`1.0`, covariance `0.1`. Même initialisation par graine dans les trois conditions.

Les sondes linéaires angle/distance existantes sont entraînées avec le JEPA comme
diagnostics mais n'entrent ni dans la priorité ni dans une porte de rétention.

## Non-stationnarité inter-sessions

Chaque domaine conserve le même corps, la même télévision `[130°, 170°]` et la même
distribution de babbling. Il modifie deux facteurs physiques explicites du jumeau:

| domaine | landmark physique | éclairage |
|---|---|---|
| A | panneau rouge à motif damier sur le mur gauche, secteur visible cible 30–50° | nominal |
| B | même panneau déplacé sur le mur frontal, secteur visible cible 90–110° | intensité des lumières ×0,70 |
| C | même panneau déplacé sur le mur droit, secteur visible cible 50–70° | lumière principale ×1,15, composante chaude documentée |

L'implémentation doit placer un véritable geom/asset dans le MJCF et modifier les
paramètres de lumière avant rendu; aucun rectangle écran-space ne simule le landmark.
Les objets de fond restent randomisés par épisode à l'intérieur de chaque domaine, selon
les mêmes graines pour les trois conditions. Les domaines sont des variables du monde,
jamais des entrées explicites du JEPA.

Contrôles de manipulation avant campagne, uniquement sur le smoke 10991:

- le centroïde ou secteur visible du landmark diffère selon A/B/C comme indiqué;
- la luminance médiane B est au moins 15 % sous A et la signature chromatique C diffère
  d'au moins 5 % de A;
- mêmes actions et même domaine donnent des images bit-identiques entre conditions;
- les trois domaines ont chacun au moins 64 ancres par compétence structurée.

Un échec exige une correction d'implémentation sans ouvrir 10301..10312; aucun seuil de
campagne n'est réglé sur le smoke.

## Données et compétences

Une compétence est le couple `(domaine, bin d'angle)`. Les huit bins servo de 20° sont
conservés; les bins 0..5 (`[10°,130°)`) sont structurés et constituent les compétences
de décision. Les bins 6..7 sont télévision et restent diagnostiques.

Chaque graine possède pour A, B et C une banque d'ancres tenue à part, équilibrée par
bin et contexte visuel, issue de pièces disjointes de la collecte. Les ancres ne sont
jamais entraînées ni utilisées pour calculer les priorités. L'erreur par ancre reste:

```text
e = MSE(prediction, cible) / max(MSE(prediction, cible) + MSE(copie, cible), 1e-8)
```

Évaluations complètes: avant toute session, après A, après B et après C, sur les trois
banques A/B/C. Les domaines futurs sont rapportés mais ne servent à aucune sélection.

## Conditions de consolidation

### Adaptation naïve

Après chaque collecte, les 1 500 pas utilisent uniquement des paires de la session
courante. Aucune donnée A pendant B/C, aucune donnée B pendant C.

### Replay uniforme

Session A identique à naïf. En B et C, chaque batch contient exactement 50 % de paires
de la session courante et 50 % d'anciennes paires. Les anciennes paires sont tirées en
sélectionnant uniformément un épisode parmi tous les épisodes A (en B) ou A+B (en C),
puis uniformément une paire valide dans cet épisode.

### Replay priorisé par erreur

Même ratio fixe 50/50, mêmes données et mêmes 1 500 pas. Au début du sommeil B puis C,
le modèle courant mesure une fois l'erreur normalisée moyenne de chaque **épisode ancien
d'entraînement**. Les probabilités d'épisode sont ensuite gelées pour toute la session:

```text
p_i = (error_i + 1e-3) / sum_j(error_j + 1e-3)
```

Pas d'exposant, de mélange uniforme additionnel, de mise à jour en ligne ou de correction
d'importance. L'erreur de prédiction est le critère primaire unique; la nouveauté n'est
pas une quatrième condition.

Pour uniform et priorisé, le runner consigne la masse de probabilité de replay et la
fraction effective de paires rejouées dont l'angle cible est dans la télévision. Cette
mesure n'entre pas dans le score du modèle.

## Métriques

Pour domaine ancien `d ∈ {A,B}` et bin structuré `r`:

```text
regression[d,r] = e_final_C[d,r] / max(e_acquisition[d,r], 1e-8) - 1
```

où `e_acquisition` est l'erreur juste après A pour A et juste après B pour B. La valeur
reste signée: une amélioration ultérieure n'est pas clippée à zéro.

Métriques obligatoires:

- les 12 régressions domaine×bin par condition et par graine;
- réduction de régression appariée uniform−naïf et priorisé−uniform, séparée pour A/B;
- erreur finale C par chacun des six bins, pour la plasticité courante;
- erreur initiale et après acquisition de chaque domaine;
- masse/fraction de replay télévision, séparée A/B au sommeil C;
- courbes après chaque session, pertes d'entraînement, budgets et temps mural;
- angle probe MAE et distance R² descriptifs.

## Statistiques et portes

Toutes les différences sont appariées par graine. Tests exacts par retournement de
signes via `learning/paired_stats.py`, unilatéraux, n=12. IC BCa 95 %, 10 000
rééchantillonnages, graine `20260720`; signes, `dz` et rank-bisériale rapportés.

### J6-H1A/B

Pour chaque graine et domaine, moyenne des six différences
`regression_naive - regression_uniform`. Porte:

- moyenne ≥ `0,05`;
- borne basse BCa > 0;
- p exacte après Holm ≤ 0,05 sur A/B;
- au moins 5 des 6 bins ont une différence moyenne favorable dans chaque domaine.

### J6-H2

Même analyse `regression_uniform - regression_prioritized`, Holm sur A/B. Les deux
domaines doivent chacun atteindre moyenne ≥ `0,03`, borne BCa > 0, p Holm ≤ 0,05 et
5/6 bins favorables.

Garde anti-télévision pour promotion du priorisé: sa fraction effective de replay TV ne
peut dépasser celle d'uniform de plus de `5 points` en moyenne à B ou C. Cette garde
n'affecte pas l'interprétation de H1.

### J6-H3

Non-infériorité séparée de uniform et priorisé face à naïf sur l'erreur C finale,
moyennée sur les six bins par graine. Marge = 5 % de l'erreur moyenne naïve, test exact
de non-infériorité, Holm sur les deux comparaisons, p ≤ 0,05. Exigence régionale:
aucun bin C ne régresse de plus de 10 % en moyenne face à naïf.

### Garde apprenant

Après acquisition de chaque domaine, l'erreur structurée moyenne de ce domaine doit
baisser d'au moins 20 % face à l'évaluation initiale correspondante dans chaque
condition. Budgets et corpus partagés doivent être exacts. Un échec rend la campagne
non interprétable pour la rétention, sans retuning.

## Décisions gelées

- **H1A, H1B et H3 passent:** replay uniforme promu comme mécanisme J6 minimal.
- **H1 échoue sur A ou B:** le replay uniforme ne démontre pas de rétention cumulative;
  aucune promotion, retour en conception après revue de résultats.
- **Uniform est promu et H2+H3+garde TV passent:** replay priorisé par erreur promu.
- **Uniform est promu mais priorité échoue:** uniform devient la référence; priorité par
  erreur rejetée. Une masse TV excessive est le diagnostic pré-enregistré du mode
  d'échec TV-001 dans la mémoire.
- **H3 échoue:** le replay achète la stabilité au prix d'une plasticité excessive;
  aucune condition concernée n'est promue.
- Aucun réglage post hoc sur A/B/C ou 10301..10312. Toute reprise utilise une hypothèse,
  un fichier et des graines nouveaux.

## Sonde motivation dormante

La sonde encodeur gelé/plastique décrite dans
`tv_real_jepa_001_results_review.md` reste la condition de réouverture de D-009. Elle
n'est ni implémentée ni exécutée avant J6-R001 et ne partage aucune graine avec lui.

## Séquence

1. Geler le présent fichier avant implémentation.
2. Soumettre protocole et architecture prévue à revue Claude; aucune graine réservée
   ni campagne avant verdict favorable.
3. Après corrections pré-calcul éventuelles: implémenter, tester, smoke 10991, puis
   exécuter le runner résumable sur 10301..10312.
4. Consigner les résultats selon les portes ci-dessus et préparer une revue de résultats
   avant toute promotion.

Simulation uniquement sous D-008; aucune action physique, aucun achat, aucun flash.

## Amendement pré-calcul du 2026-07-20 — corrections B1, B2 et B3

Les textes suivants sont intégrés avant toute implémentation de campagne, tout smoke et
tout calcul sur 10301..10312. Ils sont strictement additifs et ne changent aucune
graine, aucun budget, ratio, seuil ou règle de promotion.

### B1 — garde d'oubli

**Garde d'oubli (amendement pré-calcul du 2026-07-20).** J6-H1 n'est interprétée
que si l'adaptation naïve régresse de façon mesurable sur le domaine considéré:
pour A et pour B séparément, la régression relative moyenne de `naive` doit être
`≥ 0,05` avec borne basse BCa 95 % strictement positive. Si cette condition échoue
sur un domaine, la comparaison H1 de ce domaine est déclarée **non interprétable**
(le monde n'a pas induit d'oubli), et non un rejet du replay. La règle de décision
« H1 échoue → retour en conception » ne s'applique qu'à un domaine où la garde
d'oubli est passée.

Cette garde n'est jamais calibrée sur le smoke 10991.

### B2 — régression absolue co-primaire

**Amendement pré-calcul du 2026-07-20.** Pour A et B, la régression absolue
`regression_abs[d,r] = e_final_C[d,r] − e_acquisition[d,r]` est calculée et rapportée
à côté de la régression relative. La différence appariée absolue
(`naive − uniform`, puis `uniform − prioritized`) est reportée avec sa moyenne, son
IC BCa et ses signes. Une promotion fondée sur H1B ou sur la composante B de H2
n'est valide que si la différence absolue et la différence relative **s'accordent en
signe**; un désaccord signale un artefact de dénominateur et rend la revendication B
non interprétable. Le test statistique primaire reste la version relative gelée.

### B3 — identité de session A

Les trois conditions partagent la même initialisation de modèle par graine et sont
**bit à bit identiques jusqu'à la fin de la session A incluse** (mêmes données,
mêmes 1 500 pas, aucun replay avant B). L'implémentation asserte l'égalité des poids
et des évaluations post-A des trois conditions sur le smoke 10991 avant toute graine
de campagne.

### Clarifications de lecture gelées

Un H2 nul s'interprète « aucune valeur ajoutée démontrée à cette puissance », pas
« la priorité est inutile ». À 50/50 et calcul fixe, les conditions replay consacrent
la moitié de leurs gradients aux données anciennes; un gain de rétention signifie que
cette réallocation du calcul aide la stabilité, sous le contrôle de plasticité H3. La
garde télévision à +5 points reste une porte de promotion du priorisé, sans établir de
causalité entre télévision et éventuel gain H2. Aucune comparaison absolue de difficulté
entre A et B n'est revendiquée; toutes les décisions sont intra-domaine et appariées.
