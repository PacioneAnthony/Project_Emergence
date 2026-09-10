# BODY-SCHEMA-001 — arrêt au smoke

Date: 2026-07-27  
Statut: clos; portes 7 et 8 rouges; aucune graine de test `19201+` ouverte

## Assiette exécutée

Après intégration de B1–B6 sous D-048, BODY-SCHEMA-001 a exécuté uniquement:

- les tests unitaires de l'implémentation;
- les six organismes smoke `19091..19096`, équilibrés `2/2/2` entre les régimes;
- le cas LIFE publié `18793`, hors portes comme prévu;
- une reproduction analytique complète des six smokes.

Les tests ciblés BODY-SCHEMA/LIFE-012 passent `8/8`; la suite complète passe
`300/300`. La campagne a duré `20,70713 s`, soit une projection de `82,82852 s`
pour les vingt-quatre organismes de test.

Le rapport brut est conservé dans
`data/processed/experiments/body_schema_001_smoke/smoke_report.json`.

Digest logique:

```text
197b7b682b18fa673e7b9a9d61cbf5c27ec8e5cd65ba6cf0ccd51c1cfc243db1
```

## Portes smoke

| Porte | Résultat |
|---|---|
| plans, comptes, gardes et replay | verte |
| disjonction réelle des contenus | verte |
| absence de fuite privilégiée | verte |
| plasticité conditionnée par la marge | verte |
| amélioration privée conditionnée par la marge | verte |
| prédictions et intervalles finis | verte |
| incertitude conditionnelle | **rouge** |
| détection `blocked` et `degraded` | **rouge** |
| reproduction analytique | verte |
| projection sous 90 minutes | verte |

Le contrat pré-enregistré dit qu'une seule porte rouge clôt sans ouvrir `19201+`.
Les banques `19201..19224` sont donc restées vierges.

## Ce qui a fonctionné

La prédiction immédiate est nettement meilleure que le prior physique sur chaque
organisme:

| Graine | MAE prior | MAE M | ratio M/prior | MAE B2' | mises à jour M |
|---:|---:|---:|---:|---:|---:|
| 19091 | 1,818756 | 0,690957 | 0,3799 | 0,679242 | 15/24 |
| 19092 | 4,241974 | 0,405296 | 0,0955 | 0,403423 | 14/24 |
| 19093 | 0,977112 | 0,457191 | 0,4679 | 0,449323 | 17/24 |
| 19094 | 1,535950 | 0,564026 | 0,3672 | 0,570268 | 14/24 |
| 19095 | 4,720032 | 0,347641 | 0,0737 | 0,347332 | 14/24 |
| 19096 | 1,109619 | 0,481521 | 0,4340 | 0,477997 | 17/24 |

Les marges privilégiées valent `0,569..0,931`; tous les organismes avaient donc une
vraie marge d'apprentissage. M accepte `14..17` mises à jour sur 24 et corrige le
verrou historique.

Sur le cas `18793`, hors portes:

```text
MAE prior                  0,919739°
MAE M finale               0,439047°
MAE privilégiée P          0,409633°
marge disponible           55,4621 %
mises à jour M             17 acceptées / 7 refusées
```

Le refus `24/24` de LIFE-012 provenait donc de l'ancien couple
représentation/protection, pas d'une absence de marge physique.

B2' atteint toutefois une MAE légèrement meilleure que M sur cinq organismes sur six.
Le bootstrap et les cinq features supplémentaires n'apportent pas de gain moyen
visible au smoke. Cette comparaison est descriptive puisque les graines de test n'ont
pas été ouvertes.

## Porte 7 — calibration conditionnelle rouge

La couverture globale est raisonnable sur les six organismes (`0,854..0,938`) et toutes
les largeurs médianes respectent `<6×MAE_M`. Les échecs portent uniquement sur les
cellules conditionnelles:

| Graine | globale | rampe | plateau | terciles du déplacement prédit |
|---:|---:|---:|---:|---|
| 19091 | 0,880 | 0,867 | 0,886 | 0,894 / 0,937 / 0,810 |
| 19092 | 0,906 | 0,890 | 1,000 | 0,969 / 0,750 / 1,000 |
| 19093 | 0,938 | 0,933 | 0,932 | 0,956 / 0,939 / 0,914 |
| 19094 | 0,854 | 0,881 | 0,727 | 0,829 / 0,966 / 0,778 |
| 19095 | 0,906 | 0,892 | 1,000 | 0,818 / 0,903 / 1,000 |
| 19096 | 0,865 | 0,874 | 0,795 | 0,859 / 0,943 / 0,776 |

Deux organismes sur six satisfont toutes les cellules `[0,80;0,98]`. Les banques
privées ne contiennent que `22..44` transitions plateau par organisme; le minimum par
petite cellule est instable, mais la règle avait été gelée précisément comme une porte
à minimum. Le résultat est donc une insuffisance de qualification de l'incertitude, pas
un motif pour agréger ou déplacer le seuil après observation.

## Porte 8 — détecteur de faute rouge

AUROC par transition:

| Graine | M `blocked` | trivial `blocked` | M `degraded` | trivial `degraded` |
|---:|---:|---:|---:|---:|
| 19091 | 0,752 | 0,964 | 0,818 | 0,741 |
| 19092 | 0,672 | 0,995 | 0,793 | 0,869 |
| 19093 | 0,754 | 0,956 | 0,863 | 0,727 |
| 19094 | 0,711 | 0,966 | 0,835 | 0,724 |
| 19095 | 0,680 | 1,000 | 0,819 | 0,883 |
| 19096 | 0,748 | 0,948 | 0,860 | 0,723 |

Sur `blocked`, le mouvement observé nul rend le détecteur trivial presque parfait;
M ne peut l'égaler par transition. Sur `degraded`, M franchit `0,75` partout mais perd
contre le trivial sur 19092 et 19095.

Un diagnostic post hoc, limité aux six smokes déjà publics et sans portée confirmatoire,
a agrégé les innovations par trial de 32 pas. La moyenne des résidus standardisés de M
et la moyenne du mouvement trivial atteignent toutes deux une AUROC `1,0` sur
`blocked` et `degraded`, pour les six organismes. Cela montre deux choses:

1. la décision de faute est naturellement séquentielle plutôt que transitionnelle;
2. `blocked` et la simple réduction de vitesse restent résolubles sans schéma corporel,
   même après agrégation.

La suite doit donc inclure une faute qui conserve la quantité de mouvement tout en
brisant la correspondance commande→conséquence.

## Décision

BODY-SCHEMA-001 est clos sans reprise, retuning, modification de seuil ou lecture des
graines `19201..19224`. Il ne qualifie pas J1.

Le résultat n'est pas un retour au point de départ:

- une ridge protégée simple apprend une prédiction tenue à part très supérieure à la
  persistance et au prior;
- le verrou `18793` est corrigé;
- la valeur ajoutée du bagging pour la moyenne n'est pas établie;
- un intervalle prédictif n'est pas, à lui seul, un moniteur d'agence;
- la détection doit accumuler des innovations sur une séquence et être testée sur une
  altération non résoluble par la seule amplitude du mouvement.

Le successeur recommandé sépare trois responsabilités: prévision moyenne simple,
incertitude calibrée et moniteur séquentiel d'agence. Il conserve J5 suspendu jusqu'à
qualification complète de J1.
