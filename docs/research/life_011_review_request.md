# Demande de revue contradictoire Claude Opus 5 — LIFE-011

Date: 2026-07-27
Statut: prête; aucun code, smoke ou calcul LIFE-011 lancé

## Prompt exact

```text
Tu es le relecteur contradictoire pré-calcul de LIFE-011. Lis intégralement:
- docs/research/life_011_preregistration.md;
- docs/research/life_010_preregistration.md;
- docs/research/life_010_review.md;
- docs/research/life_010_technical_stop.md;
- docs/research/life_009_technical_stop.md;
- docs/research/kernel_001_implementation.md;
- DEVELOPMENTAL_ARCHITECTURE.md;
- DECISIONS.md, en particulier D-037 à D-041;
- PILOTAGE.md;
- SESSION_HANDOFF.md;
- cognitive/observed_signals.py;
- cognitive/experiments.py;
- sim3d/life_executor.py.

Contexte inviolable:
- LIFE-009 est close sur marge oracle insuffisante;
- LIFE-010 est close avant métrique parce que son plan step_hold devient inéligible
  (`predicted_risk=0.75 > 0.50`);
- aucun seuil LIFE-010 n'a été relevé et son smoke n'est pas repris;
- LIFE-011 emploie de nouveaux plans, coût 480° et graines 18491+;
- aucune graine LIFE-011, simulation, code ou calcul n'a été lancé;
- D-008 interdit toute action physique.

Audite d'abord si LIFE-011 est un nouvel essai légitime plutôt qu'un contournement de la
garde. Vérifie en particulier que recentrer 20/160 vers 30/150 est justifié par le proxy
LIFE-002 sans rendre les plans non informatifs ou la tâche artificiellement facile.

Audite contradictoirement:
1. longueur, coût, retour, bornes et changements des trois plans v2;
2. compatibilité attendue avec `boundary_exposure` et `predicted_risk`;
3. pertinence de la porte d'éligibilité après historique propre;
4. risque de fuite ou consommation causé par ce préflight;
5. catalogue gelé à risque 0.50/coût 0.80;
6. maintien de la complémentarité 5/12/24;
7. modèle résiduel, protection et limites héritées de LIFE-010;
8. banque privée et égalité de distribution;
9. professeur, branches et comptes;
10. nouvelles graines et espaces RNG;
11. six politiques, ancrage dynamique et oracle;
12. les dix portes smoke et leur capacité à prévenir un troisième non-résultat;
13. projection 90 minutes sur assiette complète;
14. P0 et ses gardes par régime;
15. P1–P4, effets, Monte-Carlo, Holm et non-infériorité;
16. portée exacte d'une promotion.

Cherche les décisions non gelées, gardes tautologiques mal présentées, plans encore
inéligibles, baseline faible, marge impossible, fuite de préflight ou ajustement post hoc.
Vérifie que tous nombres et contrats sont implémentables sans décision scientifique.

Rends un verdict unique:
- AUTORISER;
- AUTORISER AVEC CORRECTIONS BLOQUANTES;
- NE PAS AUTORISER.

Pour chaque correction bloquante, fournis un texte normatif intégrable. Sépare les
remarques non bloquantes. Écris uniquement `docs/research/life_011_review.md`. Ne
modifie aucun autre fichier et ne lance aucun calcul.
```

