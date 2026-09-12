# Émergence — Boîte de réception d'Anthony

Dernière mise à jour : 2026-09-11.

Ce document ne contient que **ce qui demande quelque chose à Anthony**. L'état du projet
est dans `PILOTAGE.md`, l'historique des campagnes dans `SESSION_HANDOFF.md`, les
arbitrages dans `DECISIONS.md`.

## En attente aujourd'hui

**Rien ne t'attend dans l'immédiat.** `ANT-011` reste ouverte mais n'appelle plus de réponse
de ta part pour l'instant : la revue de GPT Astra est rentrée et son verdict conditionne la
suite à une mesure, pas à un arbitrage. Je l'exécute. Tu seras sollicité seulement si son
résultat ferme la piste C1.

Le travail lui-même se fait entièrement en simulation sous D-008 et ne demande ni achat, ni
manipulation physique, ni information.

Deux demandes matérielles de juin restent en sommeil, avec leur propre question.

### ANT-011 — Ouvrir la phase des mécanismes sur C1

- Statut : `à arbitrer`, 2026-09-12.
- Contexte : la sonde de marge de C1 a joué trois banques, chacune avec ses seuils écrits et
  commités avant tout chiffre. v1 rejetée sur la faisabilité à une pièce près, v2 rejetée à
  deux pièces, **v3 verte** : faisabilité 298/300 = 99,3 %, verdict **MARGE EXPLOITABLE**.
- Ce que cela change : D-060 interdisait tout mécanisme, tout pré-enregistrement et toute
  banque de confirmation « avant que la marge existe ». Elle existe désormais.
- Ce que cela ne change pas, et qu'il faut lire avec : le balayage exhaustif résout 88,3 %
  des pièces sans mémoire ni apprentissage, pour quinze mouvements au lieu d'un. Le coin à
  prendre est « juste **et** économe », il est étroit, et rien ne prouve encore qu'un
  mécanisme saura l'occuper.
- **Question :** j'ouvre la phase des mécanismes sur C1 — pré-enregistrement, puis
  construction — ou tu veux d'abord autre chose ?
- Point de procédure : sous D-062, une décision à fort impact est contredite par un agent qui
  n'a pas produit le travail, dans une session distincte. Celle-ci en est une.
- Détail : `docs/research/c1_journal.md`, entrées 1 à 9 ; `PILOTAGE.md` pour l'état courant.

**Réponse Anthony, 2026-09-12 :**

> Je vais demander à GPT Astra de faire la revue. Donne moi le prompt à lui transmettre.

- Intégration : dossier de revue écrit dans `docs/research/c1_margin_review_request.md`,
  au format du protocole §6, avec sept points contradictoires obligatoires que j'ai dressés
  contre ma propre conclusion. Revue attendue dans `docs/research/c1_margin_review.md`.
- Revue rendue le 2026-09-12 par GPT Astra : **AUTORISER AVEC CORRECTIONS BLOQUANTES**
  (`docs/research/c1_margin_review.md`, commit `0bdb686`). Elle a refait l'ordre des commits,
  les quinze empreintes du manifeste v3 et tous les chiffres depuis le résultat brut. J'ai
  revérifié son arithmétique contre mes données avant d'intégrer : tout concorde. **Aucune de
  ses recommandations n'est rejetée.**
- Ce qu'elle bloque, et qu'elle a raison de bloquer : le témoin simple le plus fort disponible
  n'a jamais été joué — « mémoriser, vérifier la seule cellule mémorisée, ne balayer qu'après
  réfutation ». Il occupe exactement le compromis que la marge revendique. C'était le point
  que j'avais moi-même inscrit au dossier ; la revue le fait passer de « à considérer » à
  « bloquant », et D-060 exige bien le témoin le plus fort *disponible*.
- **Sonde complémentaire jouée le 12 septembre : B1 est levée.** Cent pièces neuves,
  faisabilité 99/100, aucune des quatre variantes adaptatives n'est proche de l'oracle.
  Verdict **MARGE EXPLOITABLE**. La marge survit donc au témoin simple le plus fort
  disponible, ce qui était la seule chose qui manquait.
- **Ce que la mesure a resserré, et qu'il faut avoir en tête** : la baseline adaptative égale
  le balayage exhaustif pour la moitié du prix — 90,0 % de succès en 8,0 mouvements contre
  15,9. Le coin laissé à un mécanisme vaut **+9 points de succès et −7 mouvements** contre une
  politique qui n'apprend rien, et non le contraste 1 contre 16 que la v3 laissait croire. Une
  règle de vérification de trois lignes détecte déjà le changement de monde neuf fois sur dix.
- **Statut : la question ne t'attend toujours pas.** Sous D-004 j'écris le pré-enregistrement
  de C1 avec les corrections P1 à P4 de la revue, et je te le signalerai. Tu n'as à intervenir
  que si tu veux arbitrer autrement — par exemple arrêter là et considérer que ce coin est trop
  étroit pour valoir une campagne.
- **Pré-enregistrement écrit le 12 septembre** : `docs/research/c1_preregistration.md`,
  campagne C1-M1, commité avant la première ligne de code du mécanisme, avec P1 à P4 intégrées.
- **Une objection que je porte contre mon propre travail y figure**, et elle réduit de moitié
  ce que je t'ai annoncé : le repli de ma baseline visite les quatorze cellules restantes sans
  jamais s'arrêter. Une politique qui s'arrête au premier bon appariement coûterait 4,52
  mouvements au lieu de 8,02, ce qui ramène la marge contre l'oracle de 7,02 à **3,52**. Le
  verdict B1 survit, mais le vrai concurrent d'un mécanisme est à 4,5 mouvements, pas 8. Cette
  politique devient une porte du pré-enregistrement, pas une référence protégée.
**Réponse Anthony, 2026-09-12 :**

> Oui, prépare le prompt pour GPT Astra

- Intégration : dossier écrit dans `docs/research/c1_preregistration_review_request.md`, au
  format du protocole §6, avec sept points contradictoires dont deux que je ne sais pas
  résoudre seul — l'hypothèse pourrait n'avoir plus d'objet une fois les bornes que j'ai
  moi-même établies prises au sérieux, et l'apprentissage en ligne casse peut-être la validité
  des intervalles BCa. Revue attendue dans `docs/research/c1_preregistration_review.md`.
- **Revue rendue le 2026-09-12 : AUTORISER AVEC CORRECTIONS BLOQUANTES**, huit corrections
  toutes exigibles avant la première ligne de code. Elle ne refuse pas, donc l'arbitrage ne
  te revient pas — mais **le mécanisme n'est pas autorisé** et le calendrier change : un
  diagnostic d'une centaine de pièces neuves passe d'abord, pour établir s'il reste un objet
  expérimental. Rien à rejeter de nouveau ; j'ai revérifié son arithmétique et ses
  affirmations sur le code avant d'intégrer.
- **Ce qu'elle me reprend, et que je t'avais dit trop vite** : le placement après brassage
  n'est uniforme qu'au tirage, pas en loi finale ; la détection du changement n'est pas
  « résolue », ce sont des taux de vérification ; et « B1 survit puisque 3,52 > 3 » ne peut
  pas certifier une politique jamais jouée, puisque B1 exigeait une borne basse d'intervalle
  et non un coût idéal moyen.
- **L'issue qui te reviendrait** : si le diagnostic ne montre aucun manque mesurable
  compatible avec les marges, C1-M1 s'arrête avant construction. B1 resterait valide et le
  substrat ne serait pas épuisé — le résultat serait que la marge de C1 est réelle mais déjà
  prise par des politiques simples. Je te le signalerai, et l'arbitrage sur la suite —
  chercher ailleurs sur C1, ou passer à C2 — serait le tien.

## En sommeil — matériel

Ces deux demandes datent de juin et n'ont jamais été closes. Depuis, D-008 a suspendu tout
travail physique, et D-060 a déplacé le substrat vers la vision en simulation : le banc à
un axe n'est plus le terrain des travaux cognitifs. Elles ne sont donc pas en retard sur
Anthony — elles sont sans objet tant que le projet reste en simulation.

**Question à Anthony, sans urgence :** veux-tu les fermer, ou les garder en sommeil en vue
d'un éventuel retour au matériel ? Tant qu'il n'y a pas de réponse, elles restent en
sommeil et ne bloquent rien.

### ANT-008 — Achat du kit AS5600

- Statut : `en sommeil` depuis le 2026-06-11, sans objet sous D-008 et D-060.
- Besoin d'origine : vérité terrain d'angle pour J1a ; non bloquant pour l'essai court J0.
- Question d'origine : valider l'achat du kit officiel `AS5600-SO_EK_AB`, choisir une
  alternative moins chère, ou différer jusqu'après J0 ?
- Recommandation alors formulée : kit officiel avec aimant diamétral de référence, environ
  19,40 USD hors port et taxes.
- Détail : `HARDWARE_PURCHASES.md`, entrée P-001.

### ANT-009 — Construction et réception du banc v1.0

- Statut : `en sommeil` depuis le 2026-06-12. L'état `en cours` affiché jusqu'ici était
  faux : rien n'a avancé depuis juin, et D-008 suspend le travail physique.
- Besoin d'origine : bloquant pour la session J0 de 30 minutes et pour J1a.
- Action d'origine : poursuivre la conception, les mesures, le coupon de tolérances,
  l'impression et l'assemblage décrits dans `BENCH_DESIGN.md`.
- Sécurité, toujours valable : **ne plus exécuter d'essai moteur sur le montage v0.1**
  (D-005). Le firmware passif patch 2 ne sera flashé que si un nouveau banc est prêt.
- Retour attendu s'il reprend un jour : message « banc v1.0 prêt », écarts par rapport au
  dossier, jeu ou friction perçus, photo facultative.

## Comment ce document fonctionne

Anthony écrit directement sous **Réponse Anthony**, en une phrase ou en dix, et une
réponse partielle suffit. Ce qui est répondu est ensuite intégré aux spécifications, aux
décisions ou aux protocoles concernés, et l'entrée passe à l'historique — **la réponse
d'Anthony y est conservée mot pour mot, jamais reformulée**. Les nouvelles demandes sont
signalées dans la conversation ; ce fichier n'a pas besoin d'être surveillé.

Statuts : `en sommeil`, `à arbitrer`, `à effectuer`, `répondu`, `intégré`, `clos`.

## Historique

Les réponses d'Anthony sont reproduites telles qu'il les a écrites. Plusieurs sont encore
des contraintes actives du projet.

### ANT-010 — Revue du contrat BODY-SCHEMA-002 révisé

- Statut : `clos`, 2026-09-09, sous D-052 et D-053.
- Ce qui était demandé : transmettre à Claude la demande de revue
  `docs/research/body_schema_002_review_request.md` et rapporter le verdict.
- Ce qui s'est passé : la revue a été rédigée par Codex, à la demande d'Anthony, en
  remplacement de Claude. Les corrections C1–C6 ont été intégrées et le lot de
  développement puis de validation est terminé.

### ANT-007 — Qualification physique courte de J0

- Statut : `clos`. Demandé le 2026-06-11, répondu le 2026-06-12.
- Première tentative `j0-20260612T122444.759901Z-e6395a2f`, avortée par le pilote audio
  WASAPI ; cause corrigée.
- Session servo `j0-20260612T123848.687322Z-afac9e86` : 10 719 événements, aucun CRC ni
  perte, blobs intègres, replay déterministe, servo 90/80/100/90 acquitté.
- Session de synchronisation `j0-20260612T125102.028740Z-a0dc0f70` : vidéo `+12,69 ms`,
  IMU `−10,78 ms`, cible de 20 ms respectée.

**Réponse Anthony :**

> Les mouvements de l'essai de 60s semblaient un peu tremblant quand même. Mais je dois
> préciser que le banc d'essai actuel était ma version v0.1, la tête est directement posée
> sur l'axe du servomoteur, avec une vis pour les relier mais je sens que l'assemblage
> reste assez fragile.

- Intégration : D-005, firmware passif patch 2, rapport `j0 mechanics`, critères de
  réception de `BENCH_DESIGN.md`, et suspension des nouveaux essais moteur sur v0.1.

### ANT-006 — Stockage et rétention des données

- Statut : `intégré`. Demandé et répondu le 2026-06-11.
- Question : quel volume de stockage local consacrer au projet, et combien de temps
  conserver les enregistrements audio/vidéo bruts ?

**Réponse Anthony :**

> 200Go actuellement, avec possibilité d'ajouter un SSD dédié sur mon PC ultérieurement.
> Concernant la durée de conservation, étant donné que ça reste privé, je n'ai pas
> réellement de contraintes hormis l'espace de stockage et la pertinence des données.

- Intégration : quota initial de 200 Go, revue à 160 Go, suspension des enregistrements
  bruts longs à 180 Go, aucune suppression silencieuse.

### ANT-005 — Disponibilité d'une seconde personne

- Statut : `intégré`. Demandé et répondu le 2026-06-11.
- Question : une seconde personne pourra-t-elle participer occasionnellement à de courtes
  sessions de voix ou de présence ?

**Réponse Anthony :**

> Oui, je pourrai occasionnellement faire venir 2 à 3 autres personnes (séparément). Mais
> dans > 90% des cas ce sera moi uniquement.

- Intégration : protocole J4 cadré pour au moins une autre personne réelle sur trois
  sessions, et dix sessions au total.

### ANT-004 — Vérité terrain de l'angle

- Statut : `intégré`. Demandé et répondu le 2026-06-11.
- Question : peut-on ajouter temporairement une mesure indépendante de l'angle réel du
  cou ? La consigne envoyée au servo n'est pas une mesure fiable de l'angle atteint.

**Réponse Anthony :**

> J'ai un potentiomètre 10K 2PCS fourni avec "The Most Complete Starter Kit Mega Project
> ELEGOO", j'avais cru comprendre par Claude qu'on pourrait peut-être l'utiliser. Sinon je
> préfèrerais acheter le bon matériel directement.

- Intégration : AS5600 retenu comme cible de vérité terrain (voir ANT-008, en sommeil) ;
  potentiomètre 10 kΩ conservé comme solution de prototypage.

### ANT-003 — Limites mécaniques du servomoteur

- Statut : `intégré`. Demandé et répondu le 2026-06-11.
- Question : quelles limites d'angle sont sûres pour le MF90 et le montage du cou ?

**Réponse Anthony :**

> Pour être large, on prendre de 10° à 170°. Je n'ai remarqué aucun comportement
> particulier en dehors de ça.

- Intégration : limites **10° à 170°** inscrites dans la spécification et appliquées à
  tous les chemins moteurs actifs. Ces bornes sont toujours celles du jumeau MuJoCo.

### ANT-002 — Microphone utilisé

- Statut : `intégré`. Demandé et répondu le 2026-06-11.
- Question : quel microphone au départ, modèle, intégration à la webcam, interface PC ?

**Réponse Anthony :**

> Actuellement j'utilise le micro de ma webcam, une BRIO 100.

**Remarques :**

> Je pourrai éventuellement brancher un vrai micro, un TRUST GTX 232, mais il est gros donc
> serait positionné à côté du banc d'éssai.

- Intégration : BRIO 100 retenue pour J0, Trust GXT 232 comme référence optionnelle pour
  F1. Le champ de 30° de la caméra du jumeau MuJoCo vient de cette webcam.

### ANT-001 — Position de l'IMU

- Statut : `intégré`. Demandé et répondu le 2026-06-11.
- Question : l'IMU est-elle fixée sur la tête mobile avec la webcam et l'ultrason, ou sur
  une partie fixe du banc ? Cela détermine si elle mesure le mouvement du cou ou du
  support.

**Réponse Anthony :**

> Il est fixé sur la tête mobile directement.

- Intégration : position mobile inscrite dans `DEVELOPMENTAL_ARCHITECTURE.md` et le
  protocole.

### ANT-H001 — Validation de D-002

- Statut : `intégré`, 2026-06-11.
- Réponse Anthony : validation de l'avis conjoint concernant D-002.
- Intégration : `DECISIONS.md`, `SESSION_HANDOFF.md` et `COLLABORATION_PROTOCOL.md`.
