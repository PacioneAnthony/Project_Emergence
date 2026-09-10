# Brief Codex — substrat visuel à deux axes (D-060)

Date : 10 septembre 2026. Ce fichier remplace intégralement le brief du 20 juillet, écrit
après l'arrêt de la famille d'ordonnanceurs à gain fractionnel. Il est le prompt de
référence de la phase ouverte par D-060.

## Ce que ce brief corrige

Le brief précédent envoyait Codex sur un « test de la télévision » comme étape 1 et
affirmait que les campagnes visuelles durent environ 250 minutes. Les deux points sont
caducs. La mesure du 10 septembre sur la machine actuelle donne 1 878 pas/s avec rendu
128×128, soit 37,6× le temps réel, et 18 720 images/s d'entraînement VisualJEPA sur
RTX 5080 : le goulot est le simulateur et non le GPU, d'un facteur dix, et une campagne
complète avec vision tient dans l'heure.

Le fond a également changé. Neuf campagnes de LIFE-009 à RESILIENCE-002 ont montré le même
motif sur le banc à un axe : la régression réussit toujours, jusqu'à 0,0795° d'erreur
d'angle, et toute porte mesurant la connaissance de soi ou la qualité d'un choix échoue ou
ne se réplique pas. Le problème n'était pas le mécanisme mais le terrain. D-060 change le
terrain et impose une sonde de marge sur le banc lui-même.

Révision du 10 septembre au soir. Le brief porte désormais D-061 : les octets bruts des
sources sont l'unité d'audit du projet, Git ne les normalise plus, et l'allègement
documentaire de D-060 ne touche pas l'archive des sources gelées. La sonde de marge exige
en outre que son seuil soit écrit avant d'être exécutée.

## Prompt à donner à Codex

```text
Continue le projet Emergence. Lis d'abord PILOTAGE.md, SESSION_HANDOFF.md,
PROPOSITION_SUBSTRAT.md et D-060 dans DECISIONS.md, puis DEVELOPMENTAL_ARCHITECTURE.md
pour le cadrage D-056. Exécute la phase ci-dessous jusqu'au prochain besoin réel
d'arbitrage humain. Tu décides des choix logiciels et expérimentaux (D-004) ; tu ne
demandes pas à Anthony de trancher des questions d'implémentation. Mets à jour les
documents de reprise avant de terminer.

POURQUOI LE SUBSTRAT CHANGE

Sur le banc à un axe observé par cinq scalaires, un prior analytique fait l'essentiel du
travail et une ridge est presque optimale. Aucun mécanisme cognitif n'a de quoi se payer :
la mémoire n'a rien à retenir puisque l'état tient dans l'observation, la consolidation
n'a rien à protéger puisque l'oubli naïf est faible, l'exploration active n'a rien à
allouer puisque tout est visitable. Quatre campagnes sont mortes sur une porte de marge
avant même de tourner. La marge était donc déjà bien mesurée, mais appliquée à la variante
proposée et jamais au banc.

CE QUE TU CONSTRUIS

Un cou à deux axes qui voit. L'observation devient une image plus la proprioception ;
l'angle cesse d'être l'état du monde et devient un pointeur vers une portion du monde.

Réutilise sans réécrire : sim3d/bench_model.py et sim3d/bench_env.py, qui contiennent déjà
la pièce meublée, les panneaux contrastés, l'éclairage, l'objet externe sur rail, la caméra
embarquée de 30 degrés de champ et son rendu ; learning/visual_jepa.py ; learning/
paired_stats.py pour toutes les portes statistiques ; le noyau persistant, FunctionalStore
et l'infrastructure de reprise, tous qualifiés.

ORDRE DE TRAVAIL — arrête-toi à la première porte rouge

1. Ajoute l'articulation d'inclinaison. Le modèle est généré en XML : imbrique dans le
   corps de tête un corps portant la caméra, avec une charnière d'axe 0 1 0 et un second
   actionneur de position. Mets à jour le contrat d'observation et l'API de pas pour deux
   consignes. Le champ de 30 degrés sur une course de 160 ne donne qu'environ 5,3 vues
   distinctes ; le second axe doit porter l'espace à une quinzaine de cellules. Vérifie
   par des images rendues que les cellules sont effectivement distinctes.

2. Construis la tâche C1 — retrouver un objet désigné par son apparence. Plusieurs objets
   distincts sont visibles dans différentes cellules pendant une phase d'exploration.
   Après un délai occupé par d'autres mouvements, une image de référence désigne un objet
   et la tête doit s'orienter vers lui. Les objets peuvent avoir changé de place entre
   deux visites.

3. Exécute la SONDE DE MARGE, et rien d'autre. Elle ne contient aucun mécanisme cognitif,
   aucun apprentissage et aucun pré-enregistrement. Elle oppose seulement :
   - le témoin trivial : revenir au dernier angle où quelque chose a été vu, et le
     balayage exhaustif ;
   - une borne supérieure : un oracle qui connaît la cellule de l'objet cible.
   Elle produit deux chiffres, pas un :
   - FAISABILITÉ — la performance absolue de l'oracle. Si l'oracle lui-même échoue, la
     tâche est mal construite : les objets ne sont pas distinguables à cette résolution,
     ou la manipulation n'est pas visible. C'est exactement ce qui a tué REF-002 et
     REF-003. Vérifie la manipulation dans les images rendues AVANT tout entraînement.
   - MARGE — l'écart entre le témoin trivial et l'oracle, en réussite et en coût de
     mouvements. Si le témoin trivial est déjà proche de l'oracle, la tâche est rejetée.
   Écris ce que « proche » veut dire AVANT de lancer la sonde : un seuil chiffré sur la
   réussite et sur le coût de mouvements, déposé dans le journal de la capacité. Quatre
   campagnes sont mortes sur une porte de marge ; aucune ne doit mourir sur une porte
   déplacée après coup, et un seuil choisi en voyant les chiffres n'est pas une porte.
   Publie ces deux chiffres seuls. Quelques dizaines de vies, moins d'une heure de calcul.

4. N'écris aucun mécanisme, aucun pré-enregistrement et n'ouvre aucune banque de
   confirmation tant que la marge n'est pas établie. Si elle ne l'est pas, dis-le : le
   substrat est déclaré épuisé à son tour et on n'y construit rien. C'est un résultat, pas
   un échec, et il doit coûter deux jours et non deux mois.

APRÈS C1, ET SEULEMENT APRÈS

C2 — localiser un changement sous budget de mouvements très inférieur au nombre de
cellules. La pièce change entre deux sessions ; l'éclairage varie indépendamment. Le
témoin simple est fort et doit être traité comme tel : balayage uniforme et différence de
pixels contre une image de référence mémorisée par cellule. Il échoue sur la nuisance
photométrique, sur le bruit visuel et surtout sur l'allocation d'un budget serré. Mesure
séparément les vrais changements de scène et les nuisances.

C3 — conserver C1 en apprenant C2, sur la même instance, puis retrouver C1 plus vite
qu'une instance neuve. C'est la démonstration décisive du diagnostic du 9 septembre, qui
n'avait pas de sens sur l'ancien banc puisque rien n'y était à consolider.

Applique la sonde de marge à C2 et à C3 avant de les concevoir, exactement comme à C1.

DISCIPLINE QUI NE CHANGE PAS

1. Tout mécanisme est comparé à une baseline simple recevant la même information. C'est
   cette règle qui a permis de conclure honnêtement sur DC-001..005 et il ne faut pas
   l'affaiblir parce que le substrat est plus riche.
2. Réutilise learning/paired_stats.py : permutation par signes, BCa, Holm, non-infériorité.
   N'écris pas un second module statistique.
3. Graines vierges à chaque campagne ; aucun réglage sur les mondes d'une campagne passée ;
   l'unité indépendante est l'organisme ou la vie, jamais le tick corrélé.
4. Ne ressuscite pas les familles gelées : developmental_curiosity.py,
   fractional_curiosity_benchmark.py, pooled_curiosity.py et leurs artefacts sont de
   l'histoire. Une reprise exigerait une hypothèse neuve, pas un réglage.
5. Simulation uniquement (D-008) : aucune action matérielle, aucun flash, aucun achat.
6. Un mécanisme inspiré du vivant qui ne bat pas une baseline bête n'est pas un progrès,
   c'est une complexité non payée.
7. Ne modifie pas une source gelée pour ensuite appeler cela une reprise. Ne réouvre pas
   les banques consommées. Les acquis conservent leur niveau de preuve ET leurs limites.
8. Les octets bruts des sources sont l'unité d'audit (D-061). `.gitattributes` déclare
   `* -text` : n'ajoute aucun attribut `text`, `eol` ni `working-tree-encoding`, sous aucun
   motif. Une normalisation de fin de ligne casse des empreintes gelées en silence, sans
   qu'aucun test ne le signale. Et si une empreinte ne correspond plus, l'anomalie est dans
   les octets et non dans le manifeste : on restaure les octets, on ne recalcule jamais
   l'empreinte pour faire repasser un test au vert.

DISCIPLINE QUI CHANGE — D-060

1. La sonde de marge s'applique AU BANC avant conception, et non à la variante après coup.
2. Le développement est libre. Déboguer, essayer et jeter ne demandent ni hypothèse neuve
   ni banque confirmatoire. Ne rebaptise pas une correction en nouvelle campagne.
3. Un pré-enregistrement, un rapport et un journal par capacité. RESILIENCE-002 a produit
   21 fichiers dans docs/research pour dix minutes de calcul : ce volume était calibré pour
   des campagnes de plusieurs heures. Les audits d'empreintes, reçus et diagnostics
   séparés ne sont plus produits par défaut. L'allègement porte sur les documents et jamais
   sur l'archive : toute source que tu gèles reste copiée à côté de ses résultats, selon la
   convention `source_v1`. C'est cette copie, et elle seule, qui a rendu six des onze
   sources réécrites récupérables sans reconstruction lors de l'incident du 10 septembre.
4. La confirmation est rare et réservée à une capacité dont la marge est déjà établie.
5. Le calcul n'est pas la contrainte et ne l'a jamais été : RESILIENCE-002 a consommé 618 s
   sur 5400 s. Ne dimensionne pas une campagne comme si le GPU était rare ; le simulateur
   l'est dix fois plus. Mesure avant de planifier.

LIVRABLE DE FIN DE SESSION

Action agent : ce que tu peux faire seul et dois exécuter ensuite.
Action Anthony : manipulation, observation ou achat précis ; sinon « aucune ».
Revue contradictoire : ouverte ou non, avec le fichier et le prompt si elle l'est. Sous
D-062 elle est faite par un agent qui n'a pas produit le travail, dans une session
distincte — tu l'ouvres toi-même, tu ne la fais pas transiter par Anthony.
Blocage : condition réelle empêchant la suite ; sinon « aucun ».

Commence par l'étape 1, puis l'étape 2, puis la sonde de l'étape 3, et mets à jour
PILOTAGE.md et SESSION_HANDOFF.md. N'enchaîne sur C2 qu'une fois C1 conclue, dans un sens
ou dans l'autre.
```

## Ce qui reste gelé

Les modules et artefacts de la famille fractionnelle, les campagnes REF-001 à REF-003, les
variantes LIFE-009 à LIFE-012 et les banques de BODY-SCHEMA, CUMULATIVE et RESILIENCE sont
de l'histoire conservée. Ils ne sont ni réouverts, ni réglés, ni recalculés. Leurs
conclusions, y compris négatives, restent valides dans leurs limites déclarées.

## Note pour Anthony

Ce brief acte l'option (a) de `PROPOSITION_SUBSTRAT.md`. Il retire deux consignes devenues
fausses — l'étape 1 « test de la télévision » et le coût supposé des campagnes visuelles —
et ajoute la seule règle qui aurait épargné les quatre campagnes LIFE : mesurer la marge du
banc avant de concevoir quoi que ce soit dessus. Si tu veux revenir sur l'axe d'inclinaison
et rester strictement équivalent au montage physique à un servo, c'est l'étape 1 du prompt
qu'il faut amender, et la mémoire spatiale retombe à environ cinq cellules.

La révision du soir ajoute trois choses. La règle sur les octets bruts, parce que rien
n'empêchait de recréer l'incident de D-061. La précision que l'allègement documentaire ne
supprime pas l'archive des sources : lu seul, le brief disait à Codex d'arrêter de produire
les audits d'empreintes, ce qui pouvait se comprendre comme arrêter d'archiver les sources,
alors que c'est exactement ce qui a sauvé la moitié des fichiers. Enfin l'obligation
d'écrire le seuil de marge avant de lancer la sonde : sans cela « écart exploitable » se
tranche en voyant les chiffres, ce qui est précisément la porte molle que D-060 veut
supprimer. Le seuil lui-même reste un choix de Codex sous D-004 ; c'est son moment de
décision qui est contraint, pas sa valeur.
