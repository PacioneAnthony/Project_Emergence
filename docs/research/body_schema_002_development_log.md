# Journal de développement BODY-SCHEMA-002 r2

2026-09-09, D-052. Toutes les variantes sont exploratoires ; aucune validation ouverte.

## Variante v1 — arrêt technique de la vérification de reprise

Premier organisme friction_dominant/0 : diversité verte, arrêt avant publication de
performances. La branche de vérification restaurait un snapshot dont la liste history
restait partagée ; sa mise à jour modifiait le snapshot utilisé ensuite comme référence.
La comparaison échouait donc malgré la concordance retrouvée depuis le paquet persisté.
Correction : copie indépendante de history/diagnostics à la restauration ; ajout d'un
test vérifiant explicitement l'immuabilité du snapshot source lors d'une continuation.

## Variante v2 — relance complète après correction

Même provenance de développement réutilisable et mêmes paramètres. Nouveau répertoire,
ancien manifeste et artefacts conservés. Le budget SQLite initial est commun et ne
revient pas à zéro. Refaire les tests de contrat puis le premier organisme et les six
si l'intégrité est verte. Aucune reprise sélective de performances.


## Clôture du lot — D-053

v2 : six organismes complets, intégrité et reprise vertes. Recette figée avant
validation : B3 retenu, seuils 1° à un pas et 2° aux horizons, gains de 15 %.
Validation : six apprenants neufs, mêmes portes toutes vertes ; aucun réglage après
lecture. Six F de développement activés après tests de réception, preuve/version liées.
Suite finale : 327 tests. Budget commun environ 121 secondes. Voir le rapport de résultats.
