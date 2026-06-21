# S4 - JEPA MPC-lite

Date: 2026-06-11

## Hypothèse

Le contrôleur `lnn_zoh_scan05_medium_dagger_002.pth` reste le réflexe. Tous les cinq pas, le JEPA gelé déroule plusieurs actions candidates et utilise la distance ultrason décodée comme proxy de risque. Le wrapper ne remplace l'action du LNN que si une candidate améliore suffisamment la distance minimale prédite.

Deux profils ont été comparés:

- `slow_only`: action de base ou ralentissement, sans modifier le sens de rotation;
- `conservative`: action de base, ralentissement, correction gauche ou droite limitée.

## Contrôle d'identité

Le premier smoke test a révélé un bug dans le wrapper: le mode `base` bornait la vitesse linéaire dans `[0, vmax]` et supprimait donc les commandes de recul du LNN. La première divergence apparaissait exactement au pas 70 (`v=-0.0399` pour la référence, `v=0` dans le wrapper). Le mode `base` préserve maintenant toute la plage `[-vmax, vmax]` et un test unitaire couvre cette propriété.

## Protocole

- 3 graines nominales: 3101, 3102, 3103;
- 3 graines randomisées: 3201, 3202, 3203;
- 3000 pas par paire;
- même checkpoint, même graine et même environnement pour la référence et chaque variante;
- graines de diagnostic distinctes des graines finales 1001 et 2201.

Le runner reproductible est `python -m scripts.research.run_jepa_mpc_s4`. Les artefacts sont dans `data/processed/experiments/jepa_mpc_s4/`.

## Résultats

| famille | nominal | ev. nom. / 1000 | randomisé | ev. rand. / 1000 |
|---|---:|---:|---:|---:|
| baseline | 1.36% +/- 0.87% | 3.78 +/- 1.90 | 0.26% +/- 0.36% | 0.78 +/- 0.69 |
| slow_only | 1.70% +/- 1.01% | 5.11 +/- 3.89 | 0.26% +/- 0.36% | 0.78 +/- 0.69 |
| conservative | 2.56% +/- 1.83% | 6.33 +/- 4.84 | 0.39% +/- 0.46% | 0.78 +/- 0.69 |

Différences appariées de taux de collision:

- `slow_only` nominal: +0.34 point; 0 graine améliorée, 2 égales, 1 régresse;
- `slow_only` randomisé: +0.00 point; 3 graines égales;
- `conservative` nominal: +1.20 point; 3 graines régressées;
- `conservative` randomisé: +0.13 point; 0 améliorée, 1 égale, 2 régressées.

## Verdict

S4 est rejeté dans cette formulation. Le décompte des événements n'est jamais amélioré et aucune des douze comparaisons famille/protocole/graine ne réduit les ticks de collision. Les corrections directionnelles sont particulièrement nocives.

Le problème est un décalage d'objectif: le décodeur a été entraîné à prédire l'observation ultrason suivante, pas la probabilité de collision future sous une séquence d'actions. Son RMSE distance reste modeste et les rollouts latents récursifs permettent au sélecteur d'exploiter des erreurs optimistes. Un seuil plus strict ne peut qu'annuler les interventions et revenir à la baseline; il ne crée pas de signal de risque fiable.

## Décision

- ne pas évaluer S4 sur les graines finales;
- ne pas promouvoir le wrapper MPC;
- conserver `lnn_zoh_scan05_medium_dagger_002.pth` comme contrôleur actif;
- pour poursuivre une voie critique, entraîner une tête de risque explicitement supervisée sur `collision dans les H prochains pas`, avec validation de calibration et comparaison à un simple seuil ultrason avant tout retour dans la boucle fermée.
