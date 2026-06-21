# Stratégie de couplage JEPA-LNN : analyse de l'échec direct et plan de relance

Date : 2026-06-10
Références : `data/processed/experiments/jepa_lnn_coupling_comparison.md`, `data/processed/experiments/lnn_dagger_comparison.md`, `learning/jepa_lnn_features.py`, `learning/rollout_jepa_lnn.py`, `jepa_lnn_robot_math.md`

Rappel des faits :

| contrôleur | entrée | RMSE validation | collisions déterministes |
|---|---|---:|---:|
| `lnn_zoh_scan05_medium_dagger_002` | obs brute | 0.3489 | 362 (1.21%) |
| `lnn_jepa_..._dagger_001` | obs + latent JEPA | 0.3063 | 2 319 (7.73%) |
| `lnn_jepa_..._dagger_002` | obs + latent JEPA, + DAgger couplé | 0.3670 | 3 908 (13.03%) |

---

## 1. Diagnostic : pourquoi la RMSE offline ment

### M1 — Le couplage introduit une seconde boucle de rétroaction non entraînée

Le LNN brut n'a qu'une mémoire : son état interne `x(t)`, dont la distribution en boucle fermée a été corrigée par DAgger. Le couplage direct ajoute un second système récurrent dans la boucle : le buffer de contexte (8 pas d'observations + 7 actions) → encodeur JEPA gelé → latent 128-d → action → nouvelles observations/actions → contexte. Dès que le contrôleur dévie, le vecteur de contexte sort de la variété d'entraînement. L'encodeur est un MLP : son extrapolation hors distribution est non contrôlée dans R^128. Le latent devient erratique, le LNN sur-réagit, la déviation s'amplifie. C'est une rétroaction positive structurellement absente du contrôleur brut.

### M2 — Confusion causale : le latent contient l'historique d'actions

Le contexte JEPA encode les 7 dernières actions. Offline, ce sont des actions expertes : lisses, tenues par le ZOH 50 Hz, fortement autocorrélées. Prédire l'action experte suivante à partir des actions expertes passées est un raccourci facile. Le gain de RMSE (0.306 vs 0.349) mesure donc vraisemblablement surtout ce raccourci, pas une meilleure perception. En boucle fermée, les actions passées sont celles de l'élève : le raccourci devient de l'auto-imitation, qui recopie et lisse les propres erreurs du contrôleur. C'est le phénomène de causal confusion en imitation learning (de Haan et al., 2019) : la feature la plus informative offline est précisément celle dont la sémantique change en boucle fermée.

Corollaire important : la meilleure RMSE offline n'était pas un succès mais un signal d'alarme. Elle mesure la dépendance du LNN à une entrée dont la distribution en boucle fermée n'est pas contrôlée.

### M3 — Pourquoi le DAgger couplé a aggravé (7.73% → 13.03%)

DAgger corrige la distribution d'états visités par la politique, mais ne peut pas corriger la distribution d'entrée d'un encodeur gelé. Les états relabellisés portent des contextes student-visited, pour lesquels le JEPA gelé produit des latents quasi-bruités ou aliasés (deux situations physiques proches donnent des latents éloignés selon l'historique). Entraîner le LNN à mapper ces latents incohérents vers des labels experts crée des conflits de labels : la RMSE de validation remonte (0.367) et le rollout empire. L'échec est structurel, pas un défaut d'estimation : plus de DAgger ou plus d'epochs (dagger_001 couplé a convergé à l'epoch 2 400/2 500 sans early stop) ne peuvent rien y changer.

### M4 — Violation de la séparation des échelles de temps

`jepa_lnn_robot_math.md` (§9) impose ||dc/dt|| << ||dr_fast/dt|| : le latent doit être un contexte lent qui module, pas une commande rapide. Ici le latent est recalculé à chaque pas de 20 ms, concaténé à l'observation, et domine dimensionnellement l'entrée (128 vs 3). L'implémentation contredit l'architecture théorique du projet : c'est une injection directe, pas une modulation.

---

## 2. Phase 0 — Diagnostics falsifiables (avant toute correction)

Quatre expériences bon marché, sans réentraînement, pour confirmer ou réfuter M1–M4 :

| id | expérience | résultat attendu si l'hypothèse est vraie |
|---|---|---|
| D1 | Rollout de `lnn_jepa_dagger_001` avec latent figé (moyenne d'entraînement, et zéro) | Collisions retombent vers le niveau dagger_002 → le chemin latent est bien le déstabilisateur |
| D2 | Rollout avec latent remplacé par bruit gaussien calibré | Effondrement → sensibilité excessive au latent |
| D3 | Ajuster une gaussienne sur les latents d'entraînement ; logger la distance de Mahalanobis du latent pendant (a) replay expert, (b) rollout couplé | Dérive marquée en (b), corrélée temporellement aux collisions |
| D4 | Mesurer ‖∂a/∂latent‖ vs ‖∂a/∂obs‖ sur le LNN couplé | Gradient latent dominant malgré 3 dims d'obs seulement |

D3 est le test central : il transforme l'hypothèse « distribution shift du contexte » en courbe mesurable, réutilisable comme métrique de monitoring pour toute la suite.

---

## 3. Stratégies, par ordre de priorité

### S1 — Hygiène du latent (chemin direct contraint)

Si le chemin direct est conservé, le contraindre : normalisation du latent par les statistiques d'entraînement (LayerNorm figée), dropout du latent complet p ≈ 0.3 à l'entraînement (le LNN doit savoir agir sans), projection apprise 128 → 16 pour rééquilibrer les dimensions, et rafraîchissement du latent tous les K = 5–10 pas avec maintien ZOH pour restaurer la séparation des échelles (§9 du doc math). Optionnel : porte scalaire apprise g ∈ [0,1] avec régularisation L1 vers 0, pour mesurer combien le LNN « veut » du latent.

### S2 — JEPA comme perte auxiliaire sur l'état caché du LNN (pari principal)

Entraîner un LNN identique à la recette dagger_002 (entrée : obs brute uniquement), avec une tête auxiliaire `H : x_t → ŝ_{t+1}` entraînée à prédire le latent cible JEPA gelé de `o_{t+1}` :

L = L_imitation + λ · ‖H(x_t) − sg(E_target(contexte_{t+1}))‖²

À l'inférence, la tête est supprimée : l'entrée de la politique est strictement celle de dagger_002, donc la distribution d'entrée en boucle fermée est inchangée et le risque M1/M2 disparaît par construction. Le JEPA façonne la représentation interne sans jamais entrer dans la boucle. Causalité : on prédit une cible future depuis l'état présent ; le futur n'est utilisé que comme cible d'entraînement, jamais comme entrée. C'est exactement le rôle des pertes auxiliaires prévu pour x̄_k dans le doc math (§3, §8).

### S3 — Adapter le JEPA aux trajectoires student-visited

Réentraîner (ou fine-tuner) le JEPA sur les logs mixtes expert + DAgger, en utilisant `student_actuator_action_*` comme actions de contexte (déjà supporté par `load_context_action_array`). Critère de validation : la dérive D3 sur un rollout couplé doit chuter d'au moins 50%. Ce JEPA v2 sert ensuite de cible pour S2 et, le cas échéant, d'encodeur pour S1. Note : cela réduit M1 mais ne supprime pas la boucle de rétroaction ; c'est un complément, pas une solution seule.

### S4 — JEPA comme critique / évaluateur d'actions (MPC-lite)

Garder dagger_002 comme réflexe rapide intact. Tous les K pas, générer quelques séquences d'actions candidates (action du réflexe ± perturbations structurées), les dérouler dans l'espace latent via le prédicteur JEPA, scorer par risque (distance ultrason décodée prédite, proxy de collision), et utiliser le score uniquement comme veto ou biais sur l'action réflexe. Le JEPA ne commande jamais directement ; le prédicteur n'utilise que le contexte passé et les actions candidates, donc la causalité est préservée. Premier usage du JEPA comme modèle du monde plutôt que comme feature.

### S5 — Refonte modulation (architecture cible du doc math)

Le latent ne s'ajoute plus à l'entrée : il module les paramètres du LNN (constantes de temps τ, gains — conditionnement type FiLM sur `tau_net`/`dyn_net`), avec un pont `c(t)` interpolé lentement entre mises à jour JEPA (interpolation euclidienne d'abord, §5.1), et une porte régularisée vers une modulation faible. Fine-tuning en boucle fermée sur horizons courts. C'est la voie lente/voie rapide du doc math (§6.1, §9) implémentée littéralement.

### Orthogonal — Safety/reflex override

Couche réflexe codée en dur près des obstacles (ex. : d_ultra < seuil → manœuvre d'évitement prioritaire), implémentée comme wrapper de politique. Règle stricte d'évaluation : chaque contrôleur est mesuré avec et sans override, en colonnes séparées. L'override borne le risque matériel ; il ne doit jamais masquer la qualité d'imitation dans les comparaisons.

---

## 4. Plan en trois niveaux

### Niveau 1 — Correction minimale (quelques jours)

1. Phase 0 complète (D1–D4) ; décision documentée dans `jepa_lnn_coupling_comparison.md`.
2. S1 : réentraîner le LNN couplé avec normalisation + dropout latent + projection 16-d + latent ZOH tous les 5 pas.
3. Safety override implémenté et évalué séparément (toutes politiques, avec/sans).

Succès : déterministe ≤ 1.21% ET randomisé ≤ 2.52% ET RMSE validation ≤ 0.349 — le couplage ne doit plus coûter quoi que ce soit. Stop-loss : si > 3% en déterministe après S1, abandonner définitivement l'entrée directe et passer au niveau 2.

### Niveau 2 — Expérience intermédiaire (1–2 semaines)

1. S2 : balayage λ ∈ {0.1, 0.3, 1.0}. Succès : collisions ≤ dagger_002 sur les deux protocoles, et au moins un signe de transfert (RMSE < 0.349 ou amélioration d'une sonde linéaire `x_t → distance min future` vs l'état caché de dagger_002).
2. S3 : JEPA v2 sur logs mixtes ; succès : dérive D3 réduite ≥ 50%. Puis rejouer S2 (et S1 si encore vivant) avec JEPA v2.

### Niveau 3 — Refonte ambitieuse (plusieurs semaines)

1. S4 critique MPC-lite au-dessus de dagger_002. Succès : randomisé < 2.13% (meilleur que dagger_003) sans régression déterministe au-delà de 1.5%.
2. S5 modulation FiLM + pont c(t) + fine-tuning boucle fermée courte. Succès final du projet de couplage : un contrôleur couplé strictement meilleur que dagger_002 en déterministe ET en randomisé simultanément — ce qu'aucun checkpoint actuel ne fait — avec dérive D3 bornée.

---

## 5. Protocole d'évaluation commun

Même protocole que les comparatifs existants : 30 000 pas, mêmes seeds, rollouts déterministe et randomisé. Métriques rapportées pour chaque candidat : collisions et taux, RMSE validation, dérive latente D3 (p95 de la distance de Mahalanobis), taux de near-miss (fraction de pas avec d_ultra sous un seuil — plus granulaire que la collision binaire), lissage des actions ; chaque ligne avec et sans safety override.

Règle de promotion : un checkpoint ne remplace `lnn_zoh_scan05_medium_dagger_002.pth` que s'il le bat sur les deux protocoles, sans override.

Tests : les 31 tests existants restent verts ; ajouter des tests unitaires pour la projection/gating du latent (S1), la tête auxiliaire (S2) et le wrapper override.

---

## 6. Ce qu'on ne fera pas, et pourquoi

Plus d'epochs : le LNN couplé a convergé (best epoch 2 400/2 500, pas d'early stop) ; le problème n'est pas l'optimisation. Plus de DAgger sur l'architecture directe : le passage 7.73% → 13.03% montre que l'agrégation amplifie le problème tant que l'encodeur est gelé, car elle injecte des latents incohérents dans le dataset. Le mode d'échec est structurel : il se corrige en changeant le rôle du latent (cible auxiliaire, critique, modulation), pas en accumulant des données dessus.

---

## 7. Mise à jour 2026-06-10 — résultats Phase 0 et S2

Sources : `jepa_lnn_phase0_results.md`, `jepa_lnn_s2_results.md`.

### 7.1 Diagnostic révisé

Phase 0 réfute le mécanisme M1 tel que formulé : D3 ne montre aucune dérive de Mahalanobis du latent en rollout couplé (p95 : 7.27 vs 7.69 en replay expert), et les pas de collision ont une distance *plus faible* que les autres. Les collisions surviennent dans des régions de contexte bien couvertes — près des obstacles, là où le DAgger a concentré les données. Réserve méthodologique : une gaussienne unimodale en 128-d est un détecteur OOD grossier (un latent peut être hors variété à distance de Mahalanobis normale), mais D1 corrobore indépendamment la conclusion.

D1 est le résultat le plus instructif : latent gelé à zéro ≈ latent dynamique (7.75% vs 7.73%), latent moyen catastrophique (56%). Le latent agit donc comme un *sélecteur de régime d'action* — son point de fonctionnement fixe le comportement global — et son contenu dynamique n'apporte aucun bénéfice mesurable en boucle fermée. Combiné à D4 (norme de gradient agrégée du bloc latent 4.77× celle de l'observation), le mécanisme dominant est le déséquilibre structurel M4 : une voie de contrôle 128-d très conséquente, sans repli obs-only. M2 (raccourci sur l'historique d'actions) reste plausible pour expliquer le gain de RMSE offline mais n'a pas été testé directement ; un test à coût faible existe si besoin (réentraîner le couplé avec actions du contexte mises à zéro et vérifier que l'avantage offline disparaît). Verdict inchangé : l'injection directe est close.

### 7.2 Lecture S2

S2 valide le mécanisme visé : la perte auxiliaire change le comportement fermé à RMSE d'action offline quasi constante (0.350–0.355 partout), donc elle agit bien sur la dynamique interne, pas sur l'imitation teacher-forced. Et `lambda=0.3` produit le meilleur résultat randomisé du projet (0.59%).

Mais le résultat le plus important de S2 est méthodologique : le contrôle ré-entraîné à recette identique (graine 4202) fait 3.14% nominal là où `dagger_002` fait 1.21%. **La variance inter-graines en boucle fermée est du même ordre que les effets qu'on cherche à mesurer.** Conséquences : toutes les comparaisons mono-graine du projet — y compris le 1.21% de référence — portent une incertitude non quantifiée ; le 0.59% randomisé de `lambda=0.3` peut être en partie de la chance de graine ; et la non-monotonie en lambda peut être du bruit. S'ajoute un problème de comptage : les ticks de collision sont autocorrélés (une collision dure plusieurs pas), donc l'échantillon effectif est bien plus petit que 30 000 ; les écarts d'un facteur < 2 sont fragiles.

### 7.3 Prochaines expériences

E1 — Réplication multi-graines (bloquant, avant tout réglage). Contrôle, `lambda=0.3`, `lambda=1.0` × 3 graines d'entraînement chacun ; plus 2 graines additionnelles de la recette `dagger_002` pour borner l'incertitude de la référence elle-même. Rapporter moyenne et min–max par protocole, et compter les *événements* de collision (entrées en collision) en plus des ticks. Critère de lecture : si l'écart inter-graines dépasse l'écart inter-lambda, le levier prioritaire devient la réduction de variance (EMA des poids, moyennage de checkpoints, sélection par rollout), pas le réglage de lambda.

E2 — Lambda programmé (l'essai proposé dans `jepa_lnn_s2_results.md`, légitime). Décroissance cosine de 1.0 vers 0.1 sur les epochs : représentation formée tôt, contrôle nominal optimisé tard. Variante : stop-gradient de la perte auxiliaire vers le tronc en fin d'entraînement. À lancer seulement après E1, sur le nombre de graines que E1 aura montré nécessaire.

E3 — Sélection de modèle par rollout. La RMSE offline est démontrée non prédictive du comportement fermé. Ajouter une validation périodique par mini-rollout (par ex. 5 × 2 000 pas, nominal + randomisé) pendant l'entraînement, et sélectionner le checkpoint sur le pire des deux taux. Coût : quelques rollouts courts par entraînement ; gain : la métrique de sélection mesure enfin la bonne chose.

### 7.4 Règle de promotion amendée

Un checkpoint ne remplace `dagger_002` que s'il le domine sur les deux protocoles *en moyenne sur ≥ 3 graines d'entraînement*, avec un chevauchement min–max faible ou nul face aux réplications de la référence. La règle mono-graine du §5 est caduque.
