# LIFE-009 — arrêt de conception au smoke

Date: 2026-07-27  
Statut: close comme non-résultat de conception; aucune banque réservée ouverte

## Autorisation

Claude Opus 5 a rendu `AUTORISER AVEC CORRECTIONS BLOQUANTES`. B1–B7 ont été intégrées
sous D-036 avant code et calcul. Elles autorisaient l'implémentation puis uniquement le
smoke non réservé `17991`.

Le smoke devait démontrer avant toute banque:

- une réduction de MAE entre les cycles 12 et 24 sous round-robin;
- une amélioration oracle d'au moins 10 % face à `greedy_uncertainty`;
- une projection complète inférieure ou égale à 60 minutes;
- intégrité, isolation et reproductibilité vertes.

## Exécution

Seule la graine `17991` a été ouverte. Les graines développement `17901..17932`,
validation `17933..17940` et test `18001..18024` n'ont produit aucune configuration,
banque privée, exécution, feature, poids ou métrique.

Artefact canonique:
`data/processed/experiments/life_009_smoke/smoke_report.json`.

Digest logique:
`26610a6678f5af92aefc7d708256ba8069d5a2d3d1f7621689e2a9b2f52fa7f1`.

## Portes du smoke

Vertes:

- banque privée: 48 transitions, huit par amplitude;
- professeur: 72 exemples sur un organisme smoke;
- replay branche→principal bit-identique;
- poids ridge bit-identiques au second ajustement;
- comptes principaux exacts: 24 propositions/exécutions/cycles par trajectoire;
- progrès round-robin 12→24:
  `12,3110770766° → 12,2867277806°`;
- projection conservatrice:
  `696,2451677 s`, soit environ 11 min 36 s, sous 60 minutes.

Rouge:

- amélioration relative oracle face à `greedy_uncertainty`:
  `2,3832203646 % < 10 %`.

La seule porte rouge est suffisante pour interdire la campagne.

Les 61 tests KERNEL/LIFE ciblés et les 282 tests complets du dépôt sont verts.

## Mesures descriptives autorisées du smoke

| Politique | AUC normalisée | MAE finale |
|---|---:|---:|
| oracle privilégié | 1,510406 | 11,948146° |
| round-robin | 1,541603 | 12,286728° |
| greedy uncertainty | 1,547281 | 12,239106° |
| politique apprise smoke | 1,607873 | 12,283276° |
| score LIFE-006 | 1,616054 | 13,768705° |
| uniforme aléatoire | 1,728848 | 12,304058° |

Ces valeurs ne sont ni une campagne, ni un test de généralisation. Le smoke entraîne et
évalue fonctionnellement sur le même organisme non réservé; sa seule portée scientifique
est la démonstration de marge demandée par B2.

Toutes les AUC dépassent `1`, donc le modèle ajusté dégrade globalement le prior
`angle_suivant = angle_courant` sur ce protocole. Cette observation renforce le
diagnostic de tâche mal conditionnée, mais n'autorise aucune conclusion sur la valeur
d'un curriculum appris.

## Décision mécanique

Conformément à B2:

- LIFE-009 est close comme non-résultat de conception;
- aucune banque réservée n'est ouverte;
- P0, P1, P2, P3 et P4 de campagne ne sont pas calculées;
- aucun seuil, plafond moteur, modèle, plan ou catalogue n'est retuné;
- aucune seconde campagne LIFE-009 n'est autorisée.

Il ne s'agit pas d'un échec de la politique apprise: l'oracle privilégié lui-même ne
dispose pas des 10 % de marge pré-enregistrés face à la baseline principale.

## Suite permise

Une nouvelle tentative doit porter un nouvel identifiant, de nouvelles graines et une
nouvelle revue pré-calcul. Elle devra d'abord construire une compétence dont:

- le prior est améliorable par les observations choisies;
- les expériences produisent des informations réellement complémentaires;
- l'oracle possède une marge démontrable avant réservation des banques;
- le coût moteur n'encode pas presque directement l'allocation;
- la métrique reste alignée sur une capacité utile à l'objectif final.
