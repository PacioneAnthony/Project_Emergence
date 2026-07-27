# LIFE-005 — résultats exécutés vers compétences

Date: 2026-07-27  
Statut: implémenté et vérifié, simulation uniquement

## But

Transformer une fenêtre de résultats LIFE-003 vérifiés en évaluation de compétence,
puis appliquer automatiquement le graphe d'acquisition, régression et récupération:

`résultats J0 vérifiés → métrique → preuve → transition persistante`

La tranche reste analytique. Elle n'apprend ni seuil, ni politique, ni primitive.

## Compétence initiale

Nom: `bounded_servo_tracking`  
Expérience source: `diagnose-servo`  
Métrique: `mean_absolute_tracking_error_deg`

Pour chaque `ServoTrialSummary`, la valeur est:

`mean_absolute_error * servo_span_deg`

avec `servo_span_deg = 160°`. La métrique couvre l'intégralité des douze pas de la
primitive, transitoires compris; elle mesure donc le suivi moyen du plan borné et non
la seule précision terminale.

L'évaluation utilise explicitement les `window_size` derniers essais complets, ordonnés
par LIFE-003. `window_size` doit être au moins égal à `min_samples`; les essais
antérieurs restent dans l'histoire mais ne pilotent pas l'état courant. La preuve
contient sessions, digests sources, fenêtre, span, critère, valeurs et digest.

Critère du smoke:

- validation si le maximum de la fenêtre est `≤ 9°`;
- régression si le maximum est `> 15°`;
- zone inconclusive entre les deux;
- deux essais par fenêtre.

Calibration d'ingénierie avant clôture du smoke: la primitive nominale LIFE-004 sur
17501/17502 produit une moyenne exacte de `8,1884765625°` sur douze pas, car la métrique
inclut le départ à 90° et son transitoire vers 40°. Le seuil rond initial de `8°`
classait donc le nominal en zone inconclusive. `9°` conserve environ 9,9 % de marge sur
le nominal mesuré et une séparation de `6°` avec la régression; primitive, graines,
fenêtre et seuil de régression restent inchangés.

## Application idempotente

Le schéma mémoire passe en v3 avec une table `competence_assessments`. Sa clé
`(competence_name, assessment_digest)` empêche un replay identique de créer de nouvelles
transitions.

Une application écrit dans une seule transaction:

- la preuve de l'évaluation;
- toutes les transitions nécessaires;
- l'état final de la compétence.

Chemins automatiques:

- résultat validé:
  - `unknown → learning → candidate → validated`;
  - `learning → candidate → validated`;
  - `candidate → validated`;
  - `regressed → learning → candidate → validated`;
  - `validated → validated` sans nouvelle transition;
- résultat régressé:
  - `validated → regressed`;
  - `candidate → learning`;
  - `unknown → learning`;
  - `learning` ou `regressed`: état inchangé;
- résultat inconclusive: état inchangé.

Une compétence `suspended` n'est jamais réactivée automatiquement. L'application est
refusée et exige une autorité explicite.

## Intégrité

- Seuls des résumés recalculés par `recompute_observed_history` sont admis par
  l'orchestrateur LIFE-005.
- Tous les essais de la fenêtre doivent porter le même `experiment_id`.
- Le nom de métrique doit correspondre exactement à la sémantique ci-dessus.
- Le digest d'évaluation est utilisé comme `validation_digest` lors de la promotion.
- Aucune valeur capteur brute n'entre dans SQLite.
- La migration v1→v2→v3 est additive; une version inconnue reste refusée.

## Portes du smoke

1. Deux exécutions nominales LIFE-004 doivent valider la compétence.
2. Deux exécutions lentes injectées et vérifiées par J0 doivent la faire régresser.
3. Après redémarrage, deux nouvelles exécutions nominales doivent la récupérer.
4. Le cycle attendu est:
   `unknown→learning→candidate→validated→regressed→learning→candidate→validated`.
5. Réappliquer le même digest ne doit ajouter ni assessment ni transition.
6. Une fenêtre inconclusive ne doit pas changer l'état.
7. Une compétence suspendue ne doit pas être réactivée.
8. Une base v2 représentative doit migrer en v3 sans perte.
9. Toute la suite doit rester verte.

## Interprétation

Un succès démontre que l'organisme peut faire dépendre son état de compétence de son
histoire exécutée et vérifiable. Les seuils et la fenêtre restent définis par
l'ingénieur; il ne s'agit donc pas encore d'une compétence découverte, d'un diagnostic
causal ou d'une métacognition apprise.

## Résultat d'ingénierie

Les essais nominaux 17501/17502 valent chacun `8,1884765625°` sur le plan complet et
produisent `unknown→learning→candidate→validated`. Les essais lents 17503/17504 valent
`47,59765625°` et produisent `validated→regressed`. Après redémarrage, 17505/17506
retrouvent `8,1884765625°` et appliquent
`regressed→learning→candidate→validated`.

Le replay du dernier digest n'ajoute aucune ligne. Une preuve ancienne, une fenêtre
mal définie, une métrique différente et une compétence suspendue sont refusées. Les
migrations v1→v2→v3 et v2→v3 conservent les propositions et tables d'exécution.

Les 45 tests KERNEL/LIFE ciblés et les 266 tests complets passent dans `.venv`.
LIFE-005 est close comme succès d'infrastructure sous D-031.
