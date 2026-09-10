# CUMULATIVE-001 — journal des avancées et échecs

Date de début : 2026-09-09. Toutes les entrées sont exploratoires sauf mention contraire.
Les variantes, recettes et provenances sont conservées ; aucune réussite n'efface un échec.

## v1 — première vie, friction_dominant/0

Contrats : 5 tests verts. GPU réellement utilisé : RTX 5080, calcul CUDA déterministe.
La première vie A→B→A→C termine ; état Adam, RNG, paramètres et prochaine mise à jour
sont identiques lors d'une reprise dans un nouveau processus.

Avancée : réseau avec rejeu, MAE A fin de phase 0,186°, B 0,147°, C 0,154° ; ridge
cumulative C 0,557°. Au retour A, moyenne des checkpoints 0,116° avec mémoire contre
0,310° pour un réseau neuf recevant les mêmes nouveaux essais.

Limite : l'oubli A du naïf après B vaut seulement +0,022°, sous le repère pratique de
0,2°. Ne pas présenter cette vie comme une démonstration de résistance à un oubli
catastrophique. Les cinq autres vies sont exécutées sans changement de recette.

Le résultat doit encore être confronté à de nouvelles vies et à un usage comportemental.


## Développement v1 complet et échec comportemental v1

Six vies A→B→A→C complètes : réseau avec rejeu MAE C entre 0,042 et 0,154°.
Au retour A, la moyenne des checkpoints est inférieure à celle du réseau neuf sur
les six vies. Reprises CUDA bit-identiques sur les six vies et les deux réseaux.
L'oubli naïf A après B reste entre −0,016 et +0,055° : pas de démonstration de
résistance à un oubli important. Validation sur 12 nouvelles vies gelée et lancée.

Orientation v1 : erreur moyenne de suivi identique, 3,345122°, et erreur finale
0,025838°, pour commande directe, prior, ridge et réseau planifiés. Les trajectoires
observées sont identiques dans chaque cas malgré des commandes demandées différentes.
Coût de commande : direct 72,778°, réseau 87,403°, ridge 94,931° par épisode en moyenne.
Le limiteur et le servo permettent déjà à la commande directe ce déplacement ; la
meilleure prévision ne rend pas cette tâche de régulation plus performante.
Aucune promotion du planificateur v1. Ne pas retoucher ses résultats.

Suite prévue : test distinct de choix d'une orientation atteignable avant échéance,
où la connaissance de sa propre dynamique peut changer la décision. Protocole fixé
avant calcul ; la comparaison inclura un prior prudent et le choix de la cible proche.

## Validation cumulative v1 complète — résultat positif borné

Douze nouvelles vies, quatre par régime, sans réglage après accès. Toutes les portes
acquisition/rétention/récupération/reprise passent. Après C, MAE moyenne égale A/B/C :
rejeu 0,079515°, naïf 0,169863°, ridge cumulative 0,360182°, prior 0,955423°.
Gains du rejeu : 53,19 % contre naïf et 77,92 % contre ridge, 12/12 vies favorables.
Retour A : réduction relative moyenne par vie de 69,93 % face au réseau neuf.
Reprises interprocessus exactes sur les deux réseaux de chaque vie.

Limite conservée : naïf, oubli A après B moyen +0,084963°, maximum +0,229262° ;
seulement 2/12 vies dépassent 0,2°. Rejeu : A s'améliore sur 12/12. Rétention utile,
mais oubli catastrophique corrigé non démontré ; ridge cumulative retient aussi A.

## Choix d'une cible atteignable v2 — développement puis validation

Protocole v2 fixé après l'échec v1, modèles inchangés. Développement six corps,
150 situations : rejeu 97,33 % de réussite, utilité 41,633° ; prior prudent 28,667°,
ridge 40,167°. Trois portes vertes. friction_dominant/0 réussit seulement 84 %.

Validation comportementale préspécifiée après ce développement : 12 autres corps,
192 situations, tous départs nouveaux et deux échéances nouvelles. Aucun apprentissage
pendant le choix. Réseau 190/192 réussites, utilité 47,031°, regret 0,677° ; prior
prudent 95,83 %, 38,125°, regret 9,583° ; ridge 79,17 %, 41,667°, regret 6,042°.
Utilité +23,36 % contre meilleur témoin simple et +12,88 % contre ridge. Portes vertes.

Échecs locaux : deux choix ratés sur speed_dominant/1 (87,5 % de réussite) ; trop
de prudence sur settling_dominant/2 (50,625° contre oracle/prior 52,5°).
Le réseau naïf n'est pas comparé ici : gain comportemental non attribuable au seul
rejeu. Le succès v2 concerne une décision, et n'efface pas l'échec de régulation v1.

## Clôture du cycle — D-055

336 tests verts en 24,29 s. Audit de publication : 141 empreintes, sources gelées
inchangées, reprises vérifiées, métriques comportementales recalculées depuis les
futurs enregistrés. Rapport JSON et graphique produits, graphique inspecté.
Budget exact 496,812 s / 5400 s, aucun processus ni réservation inachevés.
RTX 5080 utilisée ; temps CUDA des seuls deux réseaux principaux total 137,94 s
sur les 18 vies. Le modèle est petit ; aucun besoin d'occuper artificiellement la VRAM.

Incidents de finition sans effet sur les expériences : une commande PowerShell de
lecture du budget a échoué par guillemets imbriqués, puis a été corrigée ; une mise
à jour documentaire a été rejetée pour contexte introuvable, puis appliquée après
vérification. Aucune banque ni score modifiés pour ces incidents.

Livrable : [bilan et limites](cumulative_001_results.md), JSON et figure associés.
Le candidat est conservé pour intégration ultérieure au noyau, sans activation
neurale implicite. Le point d'arrêt demandé, avancées notables et prometteuses,
est atteint pour ce cycle. Suite ciblée : noyau puis rupture de dynamique observable
et récupération, avec nouvelle variante ; conserver toutes ces banques closes.
