# LIFE-012 — arrêt à la plaque de marge

Date: 2026-07-27
Statut: close; trois portes scientifiques rouges; aucune banque réservée ouverte

## Assiette exécutée

Après intégration de B1–B5 sous D-045, LIFE-012 a exécuté uniquement:

- le manifeste voie B et son digest;
- les 18 préflights de 18791..18796;
- six banques privées smoke;
- round-robin, greedy public residual et l'oracle myope.

Avant lancement, 14 tests LIFE ciblés et 296 tests complets étaient verts. Aucun
professeur, politique apprise, plaque de chronométrage ou organisme 18801+ n'a été
exécuté.

## Intégrité

Les portes 1 à 3 sont vertes:

- plans v4 exacts et complémentaires selon le contrat;
- 18/18 préflights éligibles, invariant par essai intact;
- six organismes valides, 2/2/2, sans remplacement;
- `temps_mort=0` pour chaque organisme;
- diagnostics vides définis sans exception.

Les deux organismes speed tirés valent `624,60` et `599,25°/s`, tous deux au-dessus de
la cadence critique `375°/s`. L'échec n'est donc pas imputable à la dégénérescence
déclarée en B1.

Digest protocole:

```text
b68be6b547d7fbfc6b310a00a568313c8f73cce5110bebba29fb7735f23eee9e
```

Digest logique de plaque:

```text
9bf81d8249481aa4d63ab176c0f309730e35757aa111bfc13a94efcf0fbfd812
```

## Portes scientifiques

### Porte 4 — progrès round-robin: rouge

Les ratios MAE finale/initiale sont:

```text
18791  0,43206
18792  0,42098
18793  1,00000  rouge
18794  0,43950
18795  0,42511
18796  0,49513
```

Sur 18793, les 24 mises à jour sont refusées sous round-robin, greedy et oracle. La
compétence reste exactement au prior (`AUC=1`, MAE initiale=finale `0,887939`).

### Porte 5 — marge oracle face à greedy: rouge

```text
médiane globale       4,9404 % < 15 %
minimum friction      0,0000 % < 5 %
minimum settling      0,0000 % < 5 %
minimum speed         3,2692 % < 5 %
```

### Porte 6 — marge oracle face à round-robin co-principale: rouge

Greedy est moins bon en moyenne que round-robin:

```text
AUC greedy moyenne       0,6058176831
AUC round-robin moyenne  0,5872427598
```

Round-robin devient donc co-principale. La marge oracle médiane face à elle ne vaut que
`1,2233 %`; son minimum friction vaut `−6,4459 %`. L'« oracle » sélectionne le meilleur
progrès contrefactuel immédiat, pas la meilleure séquence globale: il peut donc perdre
contre round-robin. Ce résultat interdit de le traiter comme une borne supérieure
universelle.

## Décision

LIFE-012 est close sans reprise, retuning ou changement de seuil. Les graines
`18801..18832`, `18841..18848` et `18901..18924` restent vierges.

Après LIFE-009, LIFE-011 et LIFE-012, fabriquer un nouveau triplet de plans ne constitue
plus une hypothèse suffisamment nouvelle. Le verrou se situe en amont:

1. la compétence résiduelle n'est pas plastique sur tous les organismes;
2. la protection pair/impair peut refuser 24/24 mises à jour;
3. le modèle n'exprime pas d'incertitude calibrée sur son schéma corporel;
4. l'oracle myope n'est pas une borne supérieure séquentielle.

La suite doit revenir au jalon J1 et qualifier un schéma corporel prédictif robuste avant
de reprendre J5, plutôt que poursuivre l'optimisation d'un curriculum pour une compétence
non encore stable.
