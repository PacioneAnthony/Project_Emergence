# BODY-SCHEMA-002 — prévision simple et moniteur séquentiel d'agence

Date: 2026-07-27  
Statut: proposé; revue Claude Opus 5 obligatoire avant code ou calcul  
Portée: jalon J1, simulation MuJoCo uniquement

## Motivation

BODY-SCHEMA-001 est clos au smoke sous D-049. Il établit trois faits de développement,
sans ouvrir ses graines de test:

1. une ridge protégée à treize features prédit l'angle tenu à part avec une MAE
   `0,35..0,69°`, très meilleure que persistance et prior;
2. l'ensemble enrichi M n'améliore pas cette ridge simple sur cinq organismes sur six;
3. l'incertitude conditionnelle par petite cellule et la détection de faute par
   transition échouent.

Le post-mortem montre qu'une moyenne de trial sépare parfaitement `blocked` et
`degraded`, mais que la quantité de mouvement seule les sépare aussi parfaitement.
Ces fautes ne démontrent donc pas que le système connaît la relation entre sa commande
et sa conséquence.

BODY-SCHEMA-002 sépare les responsabilités:

- **F**, prévision moyenne simple;
- **E**, incertitude épistémique et intervalle prédictif;
- **A**, moniteur d'agence qui accumule les innovations dans le temps.

Ce n'est pas un retuning de BODY-SCHEMA-001. Les graines sont nouvelles, M n'est pas
repris comme modèle principal, l'unité de détection devient le trial et une faute
`mirrored` conserve la structure d'amplitude tout en brisant le sens
commande→conséquence.

J5, toute allocation adaptative et tout curriculum restent interdits.

## Substrat et information autorisée

Le canal AS5600 simulé est déterministe pour un organisme et une suite de cibles. Sa
quantification vaut `0,087890625°`; la graine d'exécution ne crée aucun nouveau contenu
d'angle.

F, E et A peuvent utiliser seulement, au pas `t`:

- angle AS5600 courant;
- variation d'angle précédente;
- cible précédente et cible demandée suivante;
- variation de commande précédente;
- indice causal utilisé seulement pour remettre à zéro les fenêtres au début du trial.

Ils ne reçoivent jamais régime, paramètres MuJoCo, `_limited_deg`, vitesse articulaire
interne, condition de faute, graines, future observation ou banque privée.

Après observation de l'angle suivant, A peut calculer l'innovation causale de la
prédiction qui avait été émise avant cette observation.

## Organismes

Les trois régimes de BODY-SCHEMA-001 sont conservés pour comparabilité:

- `speed_dominant`: vitesse maximale uniforme dans `[240,720]°/s`;
- `settling_dominant`: gain uniforme `[7,13]`, damping `[0,08,0,24]`;
- `friction_dominant`: friction uniforme `[0,006,0,030]`, armature
  `[1e-4,4e-4]`.

Les autres paramètres restent nominaux. Aucun organisme n'est filtré, remplacé ou
resamplé après observation.

## Plans et partition réelle

Chaque motif possède seize instances temporelles de 32 pas, 240°, départ et retour à
90°, cibles dans `[30°,150°]`.

Les instances `i0..i11` reprennent exactement les cibles gelées de
`body_schema_001_preregistration.md`. Les quatre nouvelles instances sont:

```text
impulsion waypoints: 150,90,30,90
i12 [5,9,11,7]   i13 [11,7,5,9]
i14 [7,5,11,9]   i15 [9,11,7,5]

renversement waypoints: 60,90,120,90,60,90,120,90
i12 [1,3,5,7,7,5,3,1]
i13 [3,5,7,7,5,3,1,1]
i14 [5,7,7,5,3,1,1,3]
i15 [7,7,5,3,1,1,3,5]

micro waypoints: 75,90,105,90 répété quatre fois
i12: [2]×16, positions 0 et 8 à 3, positions 4 et 12 à 1
i13: [2]×16, positions 1 et 9 à 3, positions 5 et 13 à 1
i14: [2]×16, positions 2 et 10 à 3, positions 6 et 14 à 1
i15: [2]×16, positions 3 et 11 à 3, positions 7 et 15 à 1
```

Rôles identiques pour les trois motifs:

- i0: protection;
- i1..i2: calibration;
- i3..i10: apprentissage;
- i11..i15: banque privée normale;
- fautes: i11..i15 appariées.

Par organisme, cela donne 3 trials de protection, 6 de calibration, 24
d'apprentissage et 15 privés. Digests de plan, couples `(digest, step)`, provenances et
séquences AS5600 doivent être disjoints entre rôles normaux. Une collision de contenu
clôt avant métrique.

Le fait que les douze premières formes aient été vues sur les smokes BODY-SCHEMA-001 est
déclaré. Elles ne fournissent aucune donnée au modèle d'un nouvel organisme et aucun
hyperparamètre n'est appris entre organismes. Les cinq instances privées de chaque
motif restent distinctes des instances apprises pour ce même organisme.

## F — forecaster simple

F est la ridge résiduelle B2' qui a servi de comparateur équitable dans
BODY-SCHEMA-001:

- prior physique identique;
- `alpha=1,0`, intercept non pénalisé;
- ajustement sur les 32 transitions de chaque trial d'apprentissage accumulé;
- candidat accepté seulement si sa MAE sur les trois trials de protection ne dégrade
  pas le modèle courant au-delà de `1e-12`.

Sa base exhaustive est:

```text
1
error/160
clip(error,-12,12)/12
previous_angle_delta/12
command_delta/160
previous_command_delta/160
hold
reversal
abs(error)/160
error*abs(error)/160²
(current_angle-90)/80
hold*previous_angle_delta/12
reversal*previous_angle_delta/12
```

F est le candidat de prévision J1. Le modèle M à 18 features de BODY-SCHEMA-001 reste
historique et n'est pas relancé.

Baselines:

- B0: persistance;
- B1: prior physique;
- B-action: F évalué avec la suite de commandes circulairement décalée de sept pas dans
  chaque trial privé; angle, temps et observations restent inchangés, tandis que cible
  précédente, cible suivante et variations de commande sont recalculées depuis cette
  suite décalée.

B-action reçoit les mêmes valeurs marginales de commande mais détruit leur alignement
causal. Il n'est jamais entraîné séparément.

## E — incertitude séparée

E contient seize ridges de la même base à treize features que F. Chaque membre reçoit
des poids `Poisson(1)` déterministes par trial entier. Un membre de poids total nul rend
exactement le prior. La moyenne E n'a aucune prétention de battre F: elle doit seulement
lui être non inférieure dans la marge gelée ci-dessous.

À chaque mise à jour, l'ensemble candidat est accepté ou refusé sur la même protection
que F. Protection et calibration restent séparées.

Pour chaque organisme:

```text
sigma_bruit = 1,4826 × MAD(résidus E sur calibration)
sigma² = variance inter-membres + sigma_bruit²
score conforme = abs(résidu)/sigma
q = quantile empirique 0,90 "higher"
intervalle = moyenne E ± q×sigma
```

`sigma_bruit` est calculé séparément pour rampe et plateau; `q` reste unique. Le
plancher AS5600 s'applique à toute sigma nulle. `dead_time` utilise le MAD global et
reste rapporté séparément.

La calibration est approximative, conditionnée aux acceptations antérieures, et ne
constitue pas une garantie conforme exacte.

## A — moniteur séquentiel d'agence

Après chaque prédiction de E et l'observation suivante:

```text
halfwidth_t = max(q × sigma_t, 0,087890625°)
z_t = min(10, abs(observed_t - mean_E_t) / halfwidth_t)
w_t = moyenne(z_{t-3},...,z_t) pour t>=4
score_trial_A = max_t w_t
```

Le score n'utilise jamais la condition de faute. Il accumule quatre innovations
consécutives afin qu'une transition isolée ne suffise pas.

Le détecteur trivial reçoit la même banque:

```text
u_t = abs(observed_t-current_angle_t)
score_trial_trivial = moyenne_t u_t
```

Son orientation AUROC est choisie dans le sens favorable, comme dans
BODY-SCHEMA-001.

Le seuil opérationnel `h` de A est le quantile `0,90`, interpolation `higher`, des
`score_trial_A` des 90 trials privés normaux des six organismes smoke. Il est écrit dans
un manifeste avec digest avant toute graine `19501+`. Au test, la première fenêtre
`w_t>h` est l'instant de détection.

## Banques faute

Les quinze plans privés sont rejoués sous trois conditions appariées. L'intervention
commence après huit pas normaux et reste active jusqu'à la fin:

1. `blocked`: vitesse maximale du limiteur mise à zéro;
2. `degraded`: vitesse maximale divisée par trois;
3. `mirrored`: le modèle reçoit toujours la cible demandée `a_t`, mais l'actionneur
   reçoit `180°-a_t`.

`mirrored` conserve les bornes, le retour neutre et la magnitude marginale des cibles.
Elle inverse la correspondance directionnelle sans fournir ce fait au modèle. C'est la
seule condition qui porte une revendication spécifique de schéma corporel. `blocked`
qualifie la commande sans effet exigée par J1; `degraded` reste un contrôle cinétique.

Pour éviter une connaissance privilégiée de l'instant d'intervention, A calcule ses
fenêtres depuis le premier pas du trial. Le délai est mesuré depuis le pas 8, sans
retirer les fausses alarmes antérieures.

## Graines

- smoke: `19391..19396`, deux organismes par régime;
- test: `19501..19524`, huit organismes par régime;
- statistique: `2026072707`.

Espaces SHA-256 distincts: `organism`, `execution`, `bootstrap_member`,
`fault_condition`, `statistics`. Aucune graine BODY-SCHEMA-001 ou LIFE n'est réutilisée.

## Smoke

Les tests restent fermés jusqu'à dix portes toutes vertes:

1. comptes, coûts, bornes, rôles, digests, disjonction de contenu et replay exact;
2. six organismes `2/2/2`, sans remplacement, prédictions finies;
3. F accepte au moins une mise à jour et termine à `<=90 %` du prior sur chacun;
4. E termine à `<=1,02×MAE_F` sur chacun et ne dégrade jamais sa protection;
5. couverture globale E `[0,80;0,98]`, largeur médiane `<6×MAE_E` sur chacun;
6. couverture agrégée `[0,80;0,98]` sur rampe, plateau et chaque tercile de déplacement
   prédit; toutes les tailles de cellule sont exportées;
7. F bat B-action d'au moins 15 % de MAE angle et variation sur chacun;
8. AUROC trial A `>=0,95` sur `blocked`, `>=0,80` sur `degraded`, `>=0,90` sur
   `mirrored`; A n'est pas inférieur au trivial sur `blocked` et dépasse le trivial
   d'au moins `0,15` sur `mirrored`;
9. au seuil smoke, FPR normale `<=0,10`, TPR `blocked>=0,80` et
   `mirrored>=0,80`; reproduction analytique bit-identique;
10. projection complète des vingt-quatre tests `<=90 minutes`.

Une porte rouge clôt BODY-SCHEMA-002 sans ouvrir `19501+`.

## Test gelé

### H0 — prédiction J1 contre persistance

Sur angle et variation d'angle, F doit être meilleur que B0 avec:

- au moins 16/24 organismes favorables;
- moyenne favorable dans chaque régime;
- test de signes Monte-Carlo unilatéral, 200 000 tirages.

### H1 — gain sur le prior

Sur angle et variation, F doit améliorer B1 d'au moins 15 % avec les mêmes conditions.

### H2 — effet causal de la commande

Sur angle et variation, F doit améliorer B-action d'au moins 15 % avec les mêmes
conditions. H0–H2 forment une famille Holm de six tests, graine explicite
`2026072707`, `p_corrigé<=0,05`.

### H3 — séparation moyenne/incertitude

E doit être non inférieur à F sur l'angle et la variation avec marge normalisée `2 %`
de la MAE initiale. Les deux tests de non-infériorité forment une famille Holm séparée.
Une victoire de E sur F n'est pas requise.

### H4 — calibration

- couverture marginale agrégée `[0,87;0,93]`;
- couverture par régime `[0,85;0,95]`;
- couverture agrégée rampe, plateau et terciles `[0,80;0,98]`;
- largeur médiane `<6×MAE_E` sur au moins 20/24 organismes;
- couverture sans facteur conforme rapportée.

Les cellules conditionnelles par organisme sont toutes publiées avec leurs effectifs
mais ne sont pas des minima binaires: l'unité indépendante primaire est l'organisme,
pas chaque transition déterministe.

### H5 — agence et commande sans effet

Au niveau trial:

- `blocked`: AUROC A agrégée `>=0,95`, par régime `>=0,85`, A au moins égal au trivial;
- `mirrored`: AUROC A agrégée `>=0,90`, par régime `>=0,80`, avantage sur trivial
  `>=0,15`;
- seuil `h`: FPR normale `<=0,10`, TPR `blocked>=0,80`, TPR `mirrored>=0,80`;
- délai médian de détection après intervention `<=8` pas sur `blocked` et `mirrored`;
- `degraded` est publié avec les mêmes métriques, sans porte test confirmatoire.

H4 et H5 sont des portes conjointes descriptives pré-enregistrées; aucun seuil n'est
choisi sur le test.

## Décision

BODY-SCHEMA-002 qualifie J1 seulement si le smoke, H0–H5 et la revue contradictoire des
résultats sont verts. La promotion signifie:

- prédiction tenue à part de l'angle et de sa variation;
- dépendance démontrée à la commande correctement alignée;
- incertitude conditionnelle suffisamment calibrée;
- détection séquentielle d'une commande sans effet et d'une inversion de contingence.

Elle ne qualifie ni J2, J5, causalité générale, transfert physique, conscience ou
sécurité matérielle. Toute reprise de J5 exige cette promotion explicite.
