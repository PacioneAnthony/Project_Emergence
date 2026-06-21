# E2 - Schedule cosine du poids auxiliaire

## Protocole

E2 applique un schedule cosine de `lambda=1.0` vers `0.1` sur 2500 epochs. La sélection utilise les mini-rollouts E3, avec des graines distinctes de l'évaluation finale et une contrainte de locomotion (`v moyen >= 0.05`).

## Résultats

| famille | nominal ticks | nominal événements / 1000 | randomisé ticks | randomisé événements / 1000 |
|---|---:|---:|---:|---:|
| E3 `lambda=0.3` constant | 1.67% +/- 0.16% | 3.61 +/- 0.30 | 1.46% +/- 0.72% | 3.70 +/- 0.96 |
| E2 `1.0 -> 0.1` | 1.96% +/- 1.10% | 5.92 +/- 4.19 | 1.03% +/- 0.37% | 2.72 +/- 1.47 |

Le schedule améliore le randomisé en temps de collision et en incidence des impacts. Il régresse cependant en nominal et augmente fortement la variance nominale. Les trois taux nominaux sont `2.46%`, `0.70%` et `2.73%`.

## Décision

E2 ne domine pas E3 et ne remplace aucun checkpoint actif. Le levier auxiliaire JEPA est maintenant caractérisé:

- `lambda=0.3` constant avec sélection E3 donne le meilleur compromis nominal stable;
- le schedule E2 favorise davantage la robustesse randomisée, au prix du nominal;
- aucun réglage n'améliore simultanément et de façon stable tous les taux et événements.

La prochaine étape est S4 MPC-lite. Le LNN réflexe reste observation-only et intact. Le JEPA sert uniquement à évaluer ou opposer un véto à quelques actions candidates lentes, ce qui exploite son modèle prédictif sans créer une nouvelle voie de commande latente directe.
