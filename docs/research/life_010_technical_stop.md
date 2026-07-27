# LIFE-010 — arrêt technique sur incompatibilité de garde

Date: 2026-07-27
Statut: close comme non-résultat technique; aucune métrique scientifique calculée

## Contexte

Claude Opus 5 a autorisé LIFE-010 avec B1–B7. Les corrections ont été intégrées sous
D-039. L'implémentation et les seuls smokes `18191..18196` étaient autorisés; toutes les
banques `18201..18248` et `18301..18324` restaient fermées.

Les 18 tests ciblés et les 287 tests complets étaient verts avant lancement.

## Arrêt observé

Le smoke a commencé sur `18191`, régime `friction_dominant`, et s'est arrêté pendant la
construction du professeur principal avant de terminer un organisme.

Après la première exécution de `probe_step_hold`, LIFE-002 a reconstruit:

```text
boundary_exposure = 0.75
predicted_risk = 0.75
```

La spécification catalogue active utilisait:

```text
max_predicted_risk = 0.50
```

Au cycle où le carré latin demandait de nouveau `probe_step_hold`, le catalogue a donc
correctement bloqué cette candidate avec la raison `predicted_risk`. Les deux autres
candidates restaient éligibles; le sélecteur transparent a choisi `probe_micro`.
L'assertion d'identité professeur a immédiatement arrêté le runner:

```text
AssertionError: LIFE-010 cycle did not complete with its selected plan
```

## Diagnostic

Ce n'est ni une panne du catalogue, ni un résultat de politique:

- les cibles `20°/160°` restent dans les bornes absolues `[10°,170°]`;
- mais 24 des 32 pas de `step_hold` maintiennent une cible à 10° d'une borne;
- le proxy observationnel de LIFE-002 représente donc légitimement ce plan comme très
  exposé aux frontières;
- le choix curriculum ne peut pas contourner la garde fraîche;
- la branche professeur ne peut pas imposer une candidate devenue inéligible.

Le pré-enregistrement gelait les plans mais pas une exception à la garde de risque.
Relever `max_predicted_risk` après cette observation ou écraser le risque par le choix
appris serait un ajustement post-smoke et un contournement de sécurité.

## Portée des données

- seul le début de `18191` a été ouvert;
- aucune trajectoire smoke complète;
- aucune AUC, marge oracle, projection complète ou porte scientifique;
- `18192..18196` jamais ouverts;
- développement `18201..18232` jamais ouvert;
- validation `18241..18248` jamais ouverte;
- test `18301..18324` jamais ouvert.

Les magasins temporaires de branches ont été détruits normalement. Le magasin principal
partiel de `18191` est conservé sous
`data/processed/experiments/life_010_smoke/teacher/18191/main`.

## Décision

LIFE-010 est close comme non-résultat technique. Aucun seuil, plan, risque ou catalogue
n'est modifié sous cet identifiant, et le smoke n'est pas repris.

Une nouvelle tentative doit:

- utiliser de nouvelles graines;
- geler explicitement la compatibilité plan→proxy de risque;
- vérifier qu'une candidate reste éligible après son propre historique;
- éloigner les maintiens des zones qui déclenchent `boundary_exposure`;
- conserver longueur et coût égaux;
- recevoir une nouvelle revue pré-calcul.

