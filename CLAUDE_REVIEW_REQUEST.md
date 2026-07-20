# Demande de revue Claude — TV-001 avant calibration et campagne

Date: 2026-07-20  
Porte: revue contradictoire obligatoire avant le premier calcul sur les graines
`9201..9203` et `9301..9312`.

## Question de décision unique

Le protocole et l'implémentation TV-001 isolent-ils correctement la valeur de
`regional_lp_gain` avec un JEPA réellement entraîné, sans oracle, fuite d'ancres,
asymétrie d'information ou porte statistique vacueuse, au point d'autoriser la
calibration puis la campagne appariée?

## Fichiers à lire en priorité, et uniquement ceux-ci sauf dépendance directe nécessaire

1. `CODEX_TASK_BRIEF.md`
2. `docs/research/tv_real_jepa_001_preregistration.md`
3. `learning/tv_exploration.py`
4. `scripts/research/run_tv_real_jepa.py`
5. `tests/test_tv_exploration.py`
6. `learning/active_exploration.py` — uniquement les fonctions réutilisées
   `ExperienceBuffer`, `train_round` et `coverage_entropy`
7. `learning/paired_stats.py`
8. `docs/research/dc005_design_review.md` — diagnostic historique clip/bruit

## État factuel

- Le pré-enregistrement a été écrit avant l'implémentation et avant tout calcul sur les
  graines réservées.
- Conditions: babbling uniforme et `regional_lp_gain`; aucune nouvelle politique active
  n'est introduite.
- La politique voit huit bins servo et un contexte dérivé d'une image neutre; elle ne
  voit ni la frontière de la télévision, ni la graine, ni un label de région.
- Le gain est la baisse signée d'erreur JEPA sur mini-batchs d'ancres externes; les gains
  sont agrégés avant le clip de sélection.
- La calibration choisit `B` par une règle gelée sur `9201..9203`, puis la campagne
  appariée utilise `9301..9312`.
- Le runner impose `--review-accepted` avant d'ouvrir les graines de campagne.
- Vérifications Codex déjà exécutées: `169 passed`; smoke GPU/MuJoCo hors protocole
  graine 9991 réussi, 160 images, deux cycles collecte–apprentissage–mesure, artefacts
  sérialisés. Aucune graine réservée n'a été ouverte.

## Points que la revue doit chercher activement

1. La télévision post-rendue constitue-t-elle bien une source visuelle inapprenable et
   équitable, ou son secteur fixe / son bezel crée-t-il un raccourci qui invalide H1?
2. La banque d'ancres est-elle réellement hors entraînement et identique entre les deux
   conditions d'une paire? La classification angle×contexte donne-t-elle une information
   gratuite?
3. La mesure `pred/(pred+copy)` et les mini-batchs avant/après répondent-ils à la question
   de progrès réel sans favoriser une dérive ou un effondrement du latent?
4. La règle de calibration de `B` contrôle-t-elle raisonnablement le bruit sans utiliser
   les résultats de campagne? Le regroupement des différences ou le taux de faux positifs
   comporte-t-il une faille.
5. Les deux budgets sont-ils réellement égaux en images, décisions et optimisation?
6. Les portes TV-H1/TV-H2, Holm, taille d'effet minimale, garde apprenant et garde de
   couverture permettent-ils une décision falsifiable à n=12?
7. Le code du runner applique-t-il exactement le pré-enregistrement, notamment les seuils,
   les graines, l'appariement et les règles de promotion/arrêt?

## Forme attendue de la réponse

Écrire la revue dans `docs/research/tv_real_jepa_001_review.md` avec:

- verdict `AUTORISER`, `AUTORISER AVEC CORRECTIONS BLOQUANTES`, ou `REFUSER`;
- défauts classés par gravité, avec fichier et ligne/fonction;
- corrections minimales exigées avant calibration;
- confirmation explicite que les seuils/graines restent gelés, ou texte exact d'un
  amendement nécessaire avant tout calcul;
- commande finale autorisée si le verdict permet l'exécution.

Ne propose pas une politique plus complexe. Toute correction doit préserver la baseline,
les budgets et la question gelée; si elle modifie une porte, elle doit être justifiée comme
correction de validité et datée avant calcul.

## Prompt exact à transmettre à Claude

```text
Tu effectues la revue contradictoire pré-campagne demandée dans
CLAUDE_REVIEW_REQUEST.md. Lis les fichiers qui y sont indiqués, cherche en priorité les
fuites d'information, asymétries de budget, problèmes de mesure du progrès et écarts
protocole/code. Écris ton verdict et tes corrections éventuelles dans
docs/research/tv_real_jepa_001_review.md. Ne lance aucun calcul et ne modifie aucun autre
fichier.
```
