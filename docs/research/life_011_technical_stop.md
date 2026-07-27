# LIFE-011 — arrêt au smoke sur la marge minimale settling

Date: 2026-07-27
Statut: close comme non-résultat de qualification; aucune banque réservée ouverte

## Autorisation et assiette exécutée

La revue `docs/research/life_011_review.md` a autorisé, après B1–B6, l'implémentation
puis le smoke `18491..18496`, avec plaque de marge obligatoire avant professeur.
Les amendements ont été gelés sous D-042. Avant lancement:

- 10 tests LIFE-010/LIFE-011 verts;
- suite complète: 292 tests verts;
- complémentarité v3 vérifiée aux cadences `4,8`, `12,0` et `14,4°/pas`.

Le smoke a exécuté uniquement:

- les 18 essais de préflight;
- les six banques privées smoke;
- `round_robin`, `greedy_public_residual` et l'oracle sur les six graines.

Il n'a exécuté ni professeur, ni politique apprise, ni plaque de chronométrage.

## Intégrité

Les 18 préflights sont verts:

```text
predicted_risk = 0,0
motor_cost = 0,09375
```

pour chaque plan et chaque graine. Les plans restent éligibles après leur propre
historique. L'invariant par essai n'a jamais été violé. Le triplet v3 satisfait la
complémentarité réalisée et toutes les banques contiennent 192 transitions avec leur
décomposition mobile/inerte.

Les graines réservées suivantes n'ont jamais été ouvertes:

- développement `18501..18532`;
- validation `18541..18548`;
- test `18601..18624`.

## Résultat de la plaque de marge

La porte 5 est verte: le ratio MAE finale/initiale de round-robin vaut, par graine,
`0,54899`, `0,49568`, `0,41371`, `0,46350`, `0,15316`, `0,53435`, donc toujours
`<=0,80`.

L'ancrage reste `greedy_public_residual` seule principale:

```text
AUC moyenne greedy      = 0,4676907855
AUC moyenne round-robin = 0,4727366770
```

L'AUC basse étant meilleure, la condition de promotion de round-robin n'est pas
satisfaite. La porte 7 est donc verte sans co-principale.

La porte 6 est rouge:

```text
marge oracle médiane face à greedy = 16,8853 %  >= 15 %  (vert)
minimum friction_dominant          = 18,6897 %  >= 5 %   (vert)
minimum speed_dominant             = 13,1349 %  >= 5 %   (vert)
minimum settling_dominant          =  4,4039 %  <  5 %   (rouge)
```

L'échec est porté par 18496. L'autre organisme settling, 18493, donne `19,8871 %`.
Sur 18496, greedy choisit `micro` 22 fois, tandis que l'oracle choisit `step_hold`
20 fois, mais l'avantage AUC de cette réallocation reste seulement `4,4039 %`.

Le digest logique de la plaque est:

```text
dd3ce54c7b5380f4fb5d2952e986a5e7869e993259580eabcf9dfc288484bb7d
```

Le manifeste complet est conservé dans
`data/processed/experiments/life_011_smoke/margin_plate_report.json`.

## Décision

LIFE-011 est close. Le seuil de 5 %, les plans, l'organisme 18496 et la graine ne sont
ni modifiés, filtrés, remplacés ou rejoués. La plaque de chronométrage ne doit pas être
lancée. Le résultat n'évalue pas la politique apprise: il établit seulement que
l'opportunité oracle gelée n'est pas assez uniforme dans le régime settling.

Toute suite exige un nouvel identifiant, de nouvelles graines, une justification
scientifique qui ne transforme pas `4,4039 %` en succès post hoc, et une nouvelle revue
pré-calcul.
