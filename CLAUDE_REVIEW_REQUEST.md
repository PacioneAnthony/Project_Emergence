# Demande de revue Claude — pré-enregistrement J6-R001

Date: 2026-07-20
Porte: revue contradictoire avant implémentation, smoke et calcul sur graines J6.

## Question unique

Le pré-enregistrement J6-R001 permet-il de conclure proprement sur la valeur du replay
uniforme puis du replay priorisé par erreur pour la rétention d'un JEPA visuel, sans
confondre budget, plasticité courante, non-stationnarité, difficulté des domaines ou
sur-échantillonnage de la télévision?

## Fichiers à lire en priorité

1. `CODEX_TASK_BRIEF.md`, étape 2
2. `docs/research/tv_real_jepa_001_results_review.md`
3. `docs/research/j6_replay_001_preregistration.md`
4. `learning/tv_exploration.py` — substrat réutilisable, sans modification prévue de
   l'ordonnanceur
5. `learning/train_visual_jepa.py`
6. `learning/paired_stats.py`
7. `DEVELOPMENTAL_ARCHITECTURE.md`, section 9
8. `DECISIONS.md`, D-009

## Choix techniques déjà tranchés sous D-004

- Collecte babbling bit-identique entre `naive`, `uniform_replay` et
  `error_prioritized_replay`; motivation totalement gelée.
- Trois domaines physiques A/B/C: landmark réellement déplacé dans le MJCF et lumière
  modifiée, pas d'overlay simulant l'objet.
- 12 triplets 10301..10312, 4 500 pas d'optimisation par condition, plafond 90 min.
- Replay fixe à 50 % du batch pour les deux conditions replay; seule la distribution
  des anciens épisodes change.
- Priorité primaire unique: erreur normalisée d'épisode mesurée une fois au début du
  sommeil, puis gelée. Pas de condition nouveauté.
- Métriques séparées par domaine et six bins structurés; télévision uniquement comme
  diagnostic/garde du priorisé.
- Sonde encodeur gelé/plastique dormante, non planifiée avant J6.

## Points d'audit demandés

1. Les domaines A/B/C et leurs ancres permettent-ils de distinguer oubli et simple
   différence de difficulté?
2. La définition signée de la régression et les références après acquisition A/B sont-
   elles causales et comparables?
3. Le ratio 50/50 et les 1 500 pas égaux rendent-ils naïf/uniform/priorisé équitables,
   ou faut-il un contrôle de quantité de données distinct?
4. La priorité d'épisode `p_i ∝ error_i+1e-3` est-elle calculable sans fuite de test et
   isole-t-elle bien la valeur du prioritizing?
5. Les portes H1/H2/H3, Holm, BCa, marges et règles régionales sont-elles cohérentes,
   suffisamment puissantes à n=12 et non vacueuses?
6. La garde télévision à +5 points est-elle une vraie protection de promotion ou une
   hypothèse ajoutée après TV-001 qui devrait rester seulement descriptive?
7. Le plafond de calcul et le smoke suffisent-ils sans pilote sur graines de campagne?
8. Quel écart texte/code devra être explicitement testé avant calcul lors de
   l'implémentation?

## Forme attendue

Écrire `docs/research/j6_replay_001_review.md` avec:

- verdict `AUTORISER`, `AUTORISER AVEC CORRECTIONS BLOQUANTES`, ou `REFUSER`;
- défauts classés par gravité et texte exact des corrections pré-calcul;
- confirmation ou correction des graines, budgets, priorité, portes et décisions;
- architecture d'implémentation minimale autorisée, sans ajouter une quatrième
  condition;
- commande ou séquence que Codex pourra exécuter après intégration.

Ne lance aucun calcul et ne modifie aucun autre fichier.

## Prompt exact à transmettre

```text
Effectue la revue pré-campagne demandée dans CLAUDE_REVIEW_REQUEST.md. Audite le
pré-enregistrement J6-R001, en particulier l'équité des budgets, la mesure de l'oubli,
les portes régionales et la priorité par erreur. Écris ton verdict dans
docs/research/j6_replay_001_review.md. Ne lance aucun calcul et ne modifie aucun autre
fichier.
```
