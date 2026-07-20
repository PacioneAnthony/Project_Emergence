# Brief Codex — réorientation de la branche développementale après DC-005

Date: 2026-07-20. Ce fichier est le prompt de référence de la phase qui suit l'arrêt de
la famille d'ordonnanceurs à gain fractionnel. Il vaut arbitrage d'Anthony sur la
question laissée ouverte dans `PILOTAGE.md` (promotion de `regional_lp_gain` plutôt
qu'une nouvelle variante développementale abstraite).

---

## Prompt à donner à Codex

```text
Continue le projet Emergence. Lis d'abord PILOTAGE.md, SESSION_HANDOFF.md,
DEVELOPMENTAL_ARCHITECTURE.md et CODEX_TASK_BRIEF.md, puis exécute la phase décrite
ci-dessous jusqu'au prochain besoin réel d'arbitrage humain. Tu décides des choix
logiciels et expérimentaux (D-004); tu ne demandes pas à Anthony de trancher des
questions d'implémentation. Mets à jour les documents de reprise avant de terminer.

CONTEXTE — pourquoi on change de direction

Cinq campagnes (DC-001 à DC-005, résultats dans docs/research/developmental_curiosity_probe.md,
revue dans docs/research/dc003_statistical_review.md et dc005_design_review.md) ont
établi:
- la mesure interventionnelle avant/après a de la valeur;
- aucun ordonnanceur développemental continu n'a battu un LP régional fenêtré recevant
  la même information, dans un protocole apparié et durci;
- le correctif du clip (DC-005) supprime le biais mais ne rattrape pas l'écart;
- décision pré-enregistrée exécutée: arrêt de la famille, `regional_lp_gain` devient
  l'ordonnanceur de référence.

Le diagnostic de fond, qui motive cette phase: le banc DC-001..005 n'avait NI apprenant
réel (l'erreur était une fonction analytique de l'exposition, pas l'erreur d'un modèle
qui apprend), NI oubli, NI interférence. Ce sont exactement les deux conditions sous
lesquelles un mécanisme de curiosité biologique n'a rien à faire de plus qu'un mécanisme
trivial. La suite corrige ces deux manques.

OBJECTIF DE LA PHASE

Rapprocher l'apprentissage du système de celui des systèmes nerveux du vivant, en
ancrant la motivation intrinsèque dans un apprenant réel placé dans la boucle
sensorimotrice, puis en confrontant le système au problème que la biologie résout
réellement: apprendre sans détruire les acquis dans un monde qui change.

ÉTAPE 1 (prioritaire) — « test de la télévision » avec un apprenant réel

Question gelée: une exploration active bat-elle le babbling QUAND L'APPRENANT EST RÉEL,
dans un environnement hétérogène contenant une région inapprenable?

- Substrat: le jumeau 3D de la tête du banc (sim3d/bench_env.py, bench_model.py,
  bench_corpus.py) et le JEPA visuel (learning/visual_jepa.py,
  learning/train_visual_jepa.py), tous deux déjà validés.
- Monde: une pièce contenant au moins une région visuellement structurée et apprenable
  ET une source de bruit visuel réellement inapprenable (la « télévision » de
  DEVELOPMENTAL_ARCHITECTURE.md §7.6). L'hétérogénéité est indispensable: le rejet de
  active_exploration_001 était dû à un environnement homogène (voir
  docs/research/active_exploration_probe.md).
- Signal de motivation: le progrès d'apprentissage estimé sur l'erreur TENUE À PART du
  JEPA par région de l'espace sensorimoteur (angle de cou x contexte visuel). Aucun
  oracle: la politique ne voit jamais les frontières des régions ni les paramètres
  cachés du monde, seulement l'erreur de son propre modèle.
- Conditions obligatoires: babbling (contrôle bas), `regional_lp_gain` (référence
  survivante, adaptée au signal réel), et la politique active proposée si elle diffère
  de la référence. Budgets d'interaction strictement identiques.
- Attendu explicite: l'estimation du progrès sera BRUITÉE (erreur sur mini-batchs tenus
  à part). C'est le régime qui a tué DC-003. Mesure d'abord empiriquement le niveau de
  bruit d'évaluation, consigne-le, et choisis l'estimateur en conséquence (le
  moyennage fenêtré est robuste, le clip par observation ne l'est pas — voir
  dc005_design_review.md). Le pré-enregistrement doit fixer ce choix AVANT la campagne.

ÉTAPE 2 — non-stationnarité, oubli et consolidation (jalon J6)

Une fois l'étape 1 conclue: rendre le monde non stationnaire entre les sessions (la
pièce change, un objet se déplace, l'éclairage varie) et mesurer la rétention des acquis.
Conditions à comparer à budget égal: adaptation naïve en continu (attendu: oubli
catastrophique), replay uniforme d'épisodes anciens, replay priorisé (par erreur de
prédiction ou nouveauté). C'est ici que la distinction éveil/sommeil de
DEVELOPMENTAL_ARCHITECTURE.md §9 devient falsifiable, et c'est ici seulement qu'un
ordonnanceur a un vrai problème à résoudre: décider quand revenir sur un acquis qui se
dégrade. Métriques de rétention et de régression par compétence, jamais une métrique
unique.

ÉTAPE 3 — distinguer les changements auto-produits des changements externes

Point 2 de la définition du succès (§2) et principe de réafférence. Un objet mobile
indépendant est introduit dans la pièce; le modèle doit séparer le flux visuel causé par
sa propre commande de celui causé par l'extérieur. La prédiction conditionnée par
l'action est déjà validée (campagne v3, docs/research/visual_bench_probe.md); il ne
manque que la manipulation et un critère tenu à part.

SONDE PARALLÈLE À FAIBLE COÛT (optionnelle, si une fenêtre de calcul se libère)

Maturation sensorielle: entraîner le JEPA visuel selon un calendrier d'acuité croissante
(basse résolution d'abord, puis fine) contre un contrôle à pleine acuité constante, à
budget de calcul égal, sur le pipeline v3 existant. Hypothèse: le calendrier grossier
vers fin améliore la qualité du latent ou sa robustesse.

DISCIPLINE EXPÉRIMENTALE — non négociable

1. Pré-enregistrement AVANT implémentation et avant tout calcul: hypothèses, graines
   vierges, budgets, baselines, métriques, test statistique, taille d'effet minimale,
   règles de promotion ET d'arrêt. Un fichier par campagne dans docs/research/.
2. Toute architecture ou mécanisme est comparé à une baseline simple recevant la même
   information. C'est cette règle qui a permis de conclure honnêtement sur DC-001..005.
3. Réutilise learning/paired_stats.py pour les portes (permutation par signes exacte ou
   Monte-Carlo, BCa, Holm, non-infériorité). N'écris pas un second module statistique.
4. Aucun réglage sur les mondes d'une campagne passée; graines vierges à chaque fois.
5. Ne ressuscite pas la famille fractionnelle: developmental_curiosity.py,
   fractional_curiosity_benchmark.py, pooled_curiosity.py et leurs artefacts sont gelés
   comme historique. Une reprise exigerait une hypothèse nouvelle, pas un réglage.
6. Simulation uniquement (D-008): aucune action matérielle, aucun flash, aucun achat.
7. Les campagnes visuelles sont longues (v2 et v3: ~250 min). Utilise le motif de runner
   résumable et keep-awake de scripts/research/run_visual_night.py.
8. Signale une revue Claude en préparant CLAUDE_REVIEW_REQUEST.md à chaque porte de
   promotion, avec le contexte et le prompt exact, comme prévu par PILOTAGE.md.
9. Attention au biomimétisme infalsifiable: un mécanisme inspiré du vivant qui ne bat pas
   une baseline bête n'est pas un progrès, c'est une complexité non payée.

LIVRABLE DE FIN DE SESSION

Termine par le format obligatoire de PILOTAGE.md:

Action Codex: ce que tu peux faire seul et dois exécuter ensuite.
Action Anthony: manipulation, observation ou achat précis; sinon « aucune ».
Action Claude: revue préparée avec fichier et prompt; sinon « aucune ».
Blocage: condition réelle empêchant la suite; sinon « aucun ».

Commence par l'étape 1: rédige et gèle son pré-enregistrement, implémente, vérifie par
tests, lance la campagne, consigne les résultats selon les portes gelées, et mets à jour
PILOTAGE.md et SESSION_HANDOFF.md. N'enchaîne sur l'étape 2 qu'une fois l'étape 1
consignée.
```

---

## Note pour Anthony

Ce brief tranche l'arbitrage laissé ouvert par DC-005 en faveur de l'option (a):
`regional_lp_gain` est promu comme référence et transféré vers le substrat embarqué,
plutôt que de relancer une variante développementale abstraite. Si tu préfères
l'option (b) — exiger une hypothèse développementale nouvelle avant tout nouvel
ordonnanceur — le brief doit être amendé avant envoi.
