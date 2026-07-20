# Résultats J6-R001 — rétention visuelle séquentielle

Date: 2026-07-20. Simulation uniquement (D-008). Protocole et seuils: `j6_replay_001_preregistration.md`.
Aucune promotion n'est effectuée avant la revue contradictoire Claude.

## Intégrité

- 12 triplets appariés, graines `10301..10312`, 36 runs complets.
- Corpus partagé bit à bit par graine; 12 000 images, 2 400 décisions et 4 500 pas par condition.
- B1, B2 et B3 ont été appliqués avant tout calcul réservé; smoke 10991 vert.

## Portes gelées

| Porte | A | B |
|---|---:|---:|
| Garde d'oubli B1 | FAIL | PASS |
| H1 replay uniforme | NON INTERPRETABLE: le monde n'a pas induit d'oubli mesurable | PASS |
| H2 priorité | FAIL | FAIL |

La garde B1 n'est pas atteinte sur A: régression naïve moyenne `0.0397` (< 0,05), malgré un IC BCa dont la borne basse vaut `0.0007`. H1A est donc **NON INTERPRÉTABLE**, et non rejetée. Sur B, la régression naïve moyenne vaut `0.1414` avec borne basse `0.0922`: la garde passe.

H1B passe: réduction relative moyenne `0.1506`, borne basse `0.1066`, p Holm `0.000488`, `6/6` bins. La réduction absolue moyenne `0.0501` est de même signe (B2). H2 ne démontre aucune valeur ajoutée à cette puissance: moyennes relatives A/B `-0.0001` / `0.0039`.

H3 uniform: **FAIL**. H3 priorité: **FAIL**.
Après Holm, p H3 vaut `0.08203` pour uniform et `0.08765` pour priorisé; leurs pires bins C régressent respectivement de `14.25 %` et `13.47 %`, au-dessus de la limite régionale 10 %.
Garde apprenant: **PASS**. Garde TV B/C: **PASS**.
Excès moyen de replay TV priorisé face à uniform: B `0.001` point, C `-0.104` point (limite +5 points). Temps cumulé enregistré: 26,9 minutes, sous le plafond de 90 minutes.

## Décision mécanique, suspendue à la revue

- Replay uniforme admissible selon les portes: `False`.
- Replay priorisé admissible selon les portes: `False`.
- Statut: promotion suspendue; revue de résultats Claude requise.

## Résultats complets audités

Le fichier versionné `docs/research/j6_replay_001_analysis.json` contient les moyennes, IC BCa 95 %, signes, tests exacts/Holm, effets descriptifs, gardes B1/B2, H3, apprenant et TV. `docs/research/j6_replay_001_runs.json` conserve les métriques auditables des 36 runs par graine, domaine et bin.

```json
{
  "b1_forgetting_guard": {
    "A": {
      "bca_95": [
        0.0007346450000262126,
        0.11565615789356637
      ],
      "cohen_dz": 0.4075210325299254,
      "mean": 0.03970457365273901,
      "p_exact_greater": 0.0869140625,
      "passed": false,
      "rank_biserial": 0.41025641025641024,
      "signs": {
        "negative": 4,
        "positive": 8,
        "zero": 0
      }
    },
    "B": {
      "bca_95": [
        0.0921884597379433,
        0.17862141087619854
      ],
      "cohen_dz": 1.8193361814563405,
      "mean": 0.14141460822999943,
      "p_exact_greater": 0.00048828125,
      "passed": true,
      "rank_biserial": 0.9743589743589743,
      "signs": {
        "negative": 1,
        "positive": 11,
        "zero": 0
      }
    }
  },
  "decision": {
    "error_prioritized_promoted": false,
    "promotion_pending_claude_review": true,
    "uniform_promoted": false
  },
  "h1": {
    "A": {
      "absolute": {
        "bca_95": [
          0.013055857513880723,
          0.04805264792752462
        ],
        "cohen_dz": 0.9210864728435859,
        "mean": 0.029829992602268856,
        "p_exact_greater": 0.00439453125,
        "rank_biserial": 0.8205128205128205,
        "signs": {
          "negative": 2,
          "positive": 10,
          "zero": 0
        }
      },
      "b2_sign_agreement": true,
      "favorable_bins": 4,
      "interpretation": "NON INTERPRETABLE: le monde n'a pas induit d'oubli mesurable",
      "p_holm": 0.010009765625,
      "passed": false,
      "relative": {
        "bca_95": [
          0.020990641435711402,
          0.11229471584933302
        ],
        "cohen_dz": 0.7764199108439872,
        "mean": 0.06593152146133421,
        "p_exact_greater": 0.010009765625,
        "rank_biserial": 0.717948717948718,
        "signs": {
          "negative": 2,
          "positive": 10,
          "zero": 0
        }
      },
      "threshold": 0.05
    },
    "B": {
      "absolute": {
        "bca_95": [
          0.03406125880873224,
          0.07137695547140975
        ],
        "cohen_dz": 1.4700943391260772,
        "mean": 0.05012961704697874,
        "p_exact_greater": 0.000244140625,
        "rank_biserial": 1.0,
        "signs": {
          "negative": 0,
          "positive": 12,
          "zero": 0
        }
      },
      "b2_sign_agreement": true,
      "favorable_bins": 6,
      "interpretation": "PASS",
      "p_holm": 0.00048828125,
      "passed": true,
      "relative": {
        "bca_95": [
          0.10660106511455394,
          0.20526673637371526
        ],
        "cohen_dz": 1.6729817984743247,
        "mean": 0.15055691920645534,
        "p_exact_greater": 0.000244140625,
        "rank_biserial": 1.0,
        "signs": {
          "negative": 0,
          "positive": 12,
          "zero": 0
        }
      },
      "threshold": 0.05
    }
  },
  "h2": {
    "A": {
      "absolute": {
        "bca_95": [
          -0.008393493691929781,
          0.0036176690522378165
        ],
        "cohen_dz": -0.11721910874151341,
        "mean": -0.0012769988841480678,
        "p_exact_greater": 0.6552734375,
        "rank_biserial": 0.05128205128205128,
        "signs": {
          "negative": 6,
          "positive": 6,
          "zero": 0
        }
      },
      "b2_sign_agreement": true,
      "favorable_bins": 4,
      "interpretation": "FAIL",
      "p_holm": 0.83544921875,
      "passed": false,
      "relative": {
        "bca_95": [
          -0.015186495801522055,
          0.013468334718552303
        ],
        "cohen_dz": -0.0019148755292875143,
        "mean": -5.0225693679005826e-05,
        "p_exact_greater": 0.50341796875,
        "rank_biserial": 0.07692307692307693,
        "signs": {
          "negative": 6,
          "positive": 6,
          "zero": 0
        }
      },
      "threshold": 0.03
    },
    "B": {
      "absolute": {
        "bca_95": [
          -0.008550359852949963,
          0.017825016618504306
        ],
        "cohen_dz": 0.08568506466668648,
        "mean": 0.0020175994270377686,
        "p_exact_greater": 0.392822265625,
        "rank_biserial": -0.02564102564102564,
        "signs": {
          "negative": 6,
          "positive": 6,
          "zero": 0
        }
      },
      "b2_sign_agreement": true,
      "favorable_bins": 4,
      "interpretation": "FAIL",
      "p_holm": 0.83544921875,
      "passed": false,
      "relative": {
        "bca_95": [
          -0.02386094284873059,
          0.044455917780700384
        ],
        "cohen_dz": 0.06430789608201352,
        "mean": 0.003949528372690257,
        "p_exact_greater": 0.417724609375,
        "rank_biserial": -0.02564102564102564,
        "signs": {
          "negative": 6,
          "positive": 6,
          "zero": 0
        }
      },
      "threshold": 0.03
    }
  },
  "h3": {
    "error_prioritized_replay": {
      "margin": 0.018139737026972906,
      "mean_difference": 0.009917513156930615,
      "p_exact": 0.087646484375,
      "p_holm": 0.087646484375,
      "passed": false,
      "regional_relative": [
        0.13474766372803812,
        0.05884893949177883,
        0.03720586038344085,
        -0.0035901429414521013,
        0.0035406359233647136,
        -0.011873490288272484
      ]
    },
    "uniform_replay": {
      "margin": 0.018139737026972906,
      "mean_difference": 0.008218985671798398,
      "p_exact": 0.041015625,
      "p_holm": 0.08203125,
      "passed": false,
      "regional_relative": [
        0.1425424889312811,
        0.057154810737338434,
        0.0316446714114469,
        -0.01061356701917704,
        -0.004298476997233347,
        -0.019724409238512625
      ]
    }
  },
  "learner_guard": {
    "failures": [],
    "passed": true
  },
  "seeds": [
    10301,
    10302,
    10303,
    10304,
    10305,
    10306,
    10307,
    10308,
    10309,
    10310,
    10311,
    10312
  ],
  "tv_guard": {
    "B": {
      "mean_excess": 5.642361111111068e-06,
      "passed": true
    },
    "C": {
      "mean_excess": -0.0010391908458193336,
      "passed": true
    }
  }
}
```
