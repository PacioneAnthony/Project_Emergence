# Demande de revue contradictoire Claude Opus 5 — LIFE-009

Date: 2026-07-27  
Statut: prête; aucun code appris, entraînement, smoke ou calcul LIFE-009 lancé

## Prompt exact

```text
Tu es le relecteur contradictoire pré-calcul de LIFE-009. Lis intégralement:
- docs/research/life_009_preregistration.md;
- docs/research/life_008_spec.md;
- docs/research/life_006_spec.md;
- docs/research/life_007_spec.md;
- docs/research/kernel_001_implementation.md;
- DEVELOPMENTAL_ARCHITECTURE.md;
- DECISIONS.md, en particulier D-027 à D-035;
- PILOTAGE.md;
- SESSION_HANDOFF.md.

Contexte inviolable:
- REF-001 est close sans promotion; REF-002 et REF-003 sont des non-résultats
  techniques et leurs campagnes ne doivent pas être rouvertes ou analysées;
- D-008 interdit toute action physique;
- LIFE-008 qualifie la plomberie déterministe, pas une capacité apprise;
- aucun code appris, entraînement, smoke 17991, banque 17901..17940 ou test
  18001..18024 de LIFE-009 n'a été lancé;
- ne lance aucun test expérimental, génération de données, entraînement ou calcul.

Audite d'abord si LIFE-009 fait réellement avancer l'objectif final: un organisme
développemental cumulatif qui apprend les conséquences de ses actions et consacre ses
expériences au progrès encore possible. Cherche en particulier un faux succès où le
statut change sans apprentissage, où la politique choisit l'épreuve la plus facile, ou
où le professeur fournit à l'inférence une information indisponible.

Audite contradictoirement:
1. la définition de la compétence `neck_one_step_prediction`, sa base ridge, son prior
   et sa capacité à représenter les dynamiques MuJoCo proposées;
2. la pertinence et l'équité des trois primitives fine/medium/wide;
3. les distributions d'organismes, leur plausibilité, les risques de configurations
   invalides et l'interdiction de resampling;
4. l'étanchéité entre données d'ajustement de compétence, banque privée, professeur,
   validation et test;
5. la légitimité du professeur contrefactuel et toute information privilégiée qui
   empêcherait un transfert ultérieur;
6. l'exactitude de la copie d'état contrefactuelle, notamment RNG, MuJoCo, mémoire et
   modèle de compétence;
7. la liste des features d'inférence et les chemins possibles de fuite des paramètres
   cachés, labels privés ou métriques test;
8. le régresseur de politique, la cible de progrès, la standardisation et les
   hyperparamètres gelés;
9. la comparabilité des cinq politiques lorsque leurs trajectoires divergent et le
   couplage des flux aléatoires par `(organisme,cycle,primitive)`;
10. la force de `greedy_uncertainty`, `life006_transparent_score`, round-robin et
    uniforme comme baselines;
11. la métrique AUC, la MAE finale, la pire amplitude et le coût moteur;
12. les seuils P0–P4, la puissance des 24 graines, les tests de permutation, Holm,
    la non-infériorité et les risques de degrés de liberté post hoc;
13. les garanties empêchant la politique de sacrifier une amplitude, de répéter une
    seule primitive ou de contourner les gardes LIFE;
14. la reproductibilité analytique sans réexécution J0;
15. le plafond de 60 minutes, le smoke, les arrêts et l'interdiction d'analyse partielle;
16. ce qu'un succès autoriserait exactement et si cette promotion est trop large.

Vérifie aussi que les nombres, plans, graines, espaces RNG, digests, unités et formules
sont assez précis pour être implémentés sans décision scientifique supplémentaire.
Signale toute porte impossible, triviale, redondante ou susceptible d'être satisfaite
par construction.

Rends un verdict unique:
- AUTORISER;
- AUTORISER AVEC CORRECTIONS BLOQUANTES;
- NE PAS AUTORISER.

Pour chaque correction bloquante, fournis un texte normatif directement intégrable au
pré-enregistrement. Sépare les remarques non bloquantes. Écris uniquement
docs/research/life_009_review.md. Ne modifie aucun autre fichier et ne lance aucun
calcul.
```

