# Architecture théorique JEPA–LNN pour robot sensorimoteur multimodal

> Document de synthèse mathématique pour reprendre le projet dans Codex ou dans un dépôt local.

## 0. Objectif général

On cherche à concevoir une architecture hybride pour un robot apprenant, capable de :

- prédire l’évolution abstraite de son environnement via un **JEPA** ;
- contrôler des dynamiques physiques continues via un **Liquid Neural Network** ou système neuronal à temps continu ;
- intégrer progressivement des capteurs : proprioception, gyroscope, ultrason, audition, vision ;
- comprendre des commandes vocales en les projetant vers un espace latent d’intention ;
- piloter des servomoteurs ou moteurs de locomotion avec une boucle rapide et stable.

Le principe central est :

\[
\boxed{\text{Le LLM donne le sens, le JEPA donne le monde, le LNN donne le mouvement.}}
\]

Le JEPA ne doit **pas** remplacer les capteurs rapides. Il fournit un contexte lent, abstrait, prédictif. Le LNN conserve une voie sensorimotrice haute fréquence.

---

## 1. Analogie neurobiologique

On peut modéliser l’architecture en s’inspirant de la séparation fonctionnelle suivante :

| Système biologique | Rôle | Module artificiel |
|---|---|---|
| Néocortex | abstraction, prédiction, intention | JEPA |
| Cervelet | correction, modèle interne, prédiction sensorimotrice | LNN / contrôleur continu |
| Moelle épinière | réflexes rapides, exécution locale | microcontrôleur / Arduino |
| Boucles proprioceptives | feedback rapide | IMU, encodeurs, ultrason, contact |
| Langage cortical | consigne abstraite | ASR + LLM/embedding + projecteur latent |

Dans cette vision, le cortex ne commande pas directement chaque fibre musculaire. Il fournit une intention ou trajectoire abstraite. Les boucles cérébelleuses et spinales ajustent ensuite le mouvement en temps réel.

Pour le robot :

\[
\text{Intention abstraite} \rightarrow \text{modulation du champ dynamique} \rightarrow \text{commande continue}
\]

et non :

\[
\text{Intention abstraite} \rightarrow \text{commande moteur directe}
\]

---

## 2. Variables principales

### 2.1 Temps discret et temps continu

Le JEPA fonctionne sur un temps discret :

\[
T_k = k\Delta
\]

avec :

\[
k \in \mathbb{N}
\]

Le LNN fonctionne en temps continu :

\[
t \in [T_k, T_{k+1}]
\]

On a donc deux échelles :

- échelle lente : prédiction abstraite du JEPA ;
- échelle rapide : intégration continue du LNN.

---

### 2.2 Observations multimodales

On définit l’observation multimodale :

\[
o_t = \{r_{fast}(t), v_t, a^{audio}_t, m_t\}
\]

où :

- \(r_{fast}(t)\) : capteurs rapides : IMU, gyroscope, encodeurs, ultrason, capteurs de contact ;
- \(v_t\) : observation visuelle : caméra RGB, profondeur, LiDAR ;
- \(a^{audio}_t\) : signal audio ;
- \(m_t\) : état moteur : angle servo, vitesse, PWM, courant moteur si disponible.

Dans votre matériel actuel, la version minimale est :

\[
o_t = \{d_{ultra}(t), \theta_{servo}(t), \omega_{gyro}(t), a_{servo}(t)\}
\]

avec :

- \(d_{ultra}(t)\) : distance mesurée par le capteur ultrason ;
- \(\theta_{servo}(t)\) : orientation du capteur ultrason ;
- \(\omega_{gyro}(t)\) : vitesse angulaire mesurée ;
- \(a_{servo}(t)\) : commande envoyée au servo.

---

## 3. Représentation latente JEPA

Le JEPA encode l’état observé vers un latent abstrait :

\[
S_k = E_\theta(o_{T_k})
\]

avec :

\[
S_k \in \mathbb{R}^{d_S}
\]

Mais on suppose que ces latents appartiennent en réalité à une variété de plus faible dimension :

\[
S_k \in \mathcal{M}, \qquad \dim(\mathcal{M}) = m \leq d_S
\]

Le JEPA prédit ensuite l’état latent suivant :

\[
\hat{S}_{k+1} = P_\theta(S_k, A_k, \bar{x}_{k-1}, z_{lang})
\]

où :

- \(A_k\) : commande macro, consigne tenue, ou action planifiée disponible au temps \(T_k\) ;
- \(\bar{x}_{k-1}\) : résumé causal de l’état continu du LNN déjà observé ;
- \(z_{lang}\) : vecteur latent d’intention issu du langage.

Le résumé continu peut être :

\[
\bar{x}_{k-1} = \frac{1}{\Delta}\int_{T_{k-1}}^{T_k} H_\rho(x(t))\,dt
\]

ou, en discret :

\[
\bar{x}_{k-1} \approx \frac{1}{N}\sum_{i=1}^{N} H_\rho(x(t_i)),
\qquad t_i \in [T_{k-1},T_k]
\]

La contrainte importante est la causalité temporelle : au temps \(T_k\), le prédicteur ne peut pas dépendre du futur continu \(x(t)\) sur \([T_k,T_{k+1}]\), car ce futur dépend lui-même du chemin latent construit à partir de \(\hat{S}_{k+1}\).

En apprentissage offline, on peut journaliser après coup une action agrégée sur \([T_k,T_{k+1}]\), mais elle ne doit pas être confondue avec l’entrée causale disponible pour un contrôleur en ligne.

Une variante plus locale consiste à remplacer le résumé précédent par l’état instantané disponible au saut :

\[
\hat{S}_{k+1} = P_\theta(S_k, A_k, x(T_k), z_{lang})
\]

Le résumé \(\bar{x}_k\), calculé après l’intégration sur \([T_k,T_{k+1}]\), devient alors une information disponible pour la prédiction suivante ou pour les pertes auxiliaires, mais pas une entrée de la prédiction courante.

---

## 4. Module langage

L’objectif n’est pas d’entraîner un LLM depuis zéro. On utilise un modèle de compréhension du langage gelé ou faiblement adapté.

Pipeline recommandé :

\[
\text{audio} \rightarrow \text{ASR} \rightarrow \text{texte} \rightarrow \text{embedding} \rightarrow z_{lang}
\]

Formellement :

\[
\tau = ASR(a^{audio}_{t:t+L})
\]

\[
e_{text} = LLM_{emb}(\tau)
\]

\[
z_{lang} = P_\psi(e_{text})
\]

avec :

\[
e_{text} \in \mathbb{R}^{d_{LLM}}, \qquad z_{lang} \in \mathbb{R}^{d_Z}
\]

Le projecteur \(P_\psi\) peut être un petit MLP :

\[
z_{lang} = W_2\sigma(W_1e_{text} + b_1) + b_2
\]

Une commande comme :

```text
avance doucement jusqu’à l’objet rouge sans toucher le mur
```

peut aussi être traduite en structure symbolique :

```json
{
  "goal": "move_to",
  "target": "red_object",
  "speed": "slow",
  "avoid_obstacles": true
}
```

puis encodée vers :

\[
z_{lang}
\]

Ce choix est plus stable que d’utiliser directement les états cachés internes d’un LLM, qui peuvent dépendre fortement de la couche, du prompt, de la quantification et du contexte.

---

## 5. Pont géométrique JEPA → LNN

Le paradoxe initial est :

- le JEPA produit des états discrets \(S_k\) ;
- le LNN a besoin d’un flux continu ;
- si l’on force brutalement \(S_k\) dans le LNN, on risque de détruire la dynamique haute fréquence ;
- si le latent s’effondre, plusieurs situations deviennent indiscernables.

La solution proposée est de transformer le saut discret :

\[
S_k \rightarrow \hat{S}_{k+1}
\]

en un chemin latent continu :

\[
c_k(t), \qquad t \in [T_k,T_{k+1}]
\]

---

### 5.1 Interpolation euclidienne simple

Version minimale :

\[
\alpha(t) = \frac{t-T_k}{\Delta}
\]

\[
c_k(t) = (1-\alpha(t))S_k + \alpha(t)\hat{S}_{k+1}
\]

et :

\[
\dot{c}_k(t) = \frac{\hat{S}_{k+1}-S_k}{\Delta}
\]

Cette version est simple, mais elle ignore la géométrie du latent.

---

### 5.2 Interpolation géodésique

On suppose que \(\mathcal{M}\) est munie d’une métrique riemannienne apprise :

\[
g_\theta(S)
\]

On définit alors :

\[
c_k(t)
=
\operatorname{Exp}_{S_k}
\left(
\alpha(t)\operatorname{Log}_{S_k}(\hat{S}_{k+1})
\right)
\]

avec :

\[
\alpha(t)=\frac{t-T_k}{\Delta}
\]

Ici :

- \(\operatorname{Log}_{S_k}(\hat{S}_{k+1})\) donne le vecteur tangent au point \(S_k\) pointant vers \(\hat{S}_{k+1}\) ;
- \(\operatorname{Exp}_{S_k}\) projette ce vecteur tangent sur la variété.

Cette interpolation limite les transitions latentes absurdes.

---

### 5.3 Métrique latente

Une métrique peut être induite par un décodeur auxiliaire \(D_\eta\) :

\[
g_\theta(S) = J_D(S)^T J_D(S) + \epsilon I
\]

avec :

\[
J_D(S) = \frac{\partial D_\eta(S)}{\partial S}
\]

La distance entre deux états latents devient :

\[
d_g(S_i,S_j)
=
\inf_{\gamma}
\int_0^1
\sqrt{\dot{\gamma}(u)^Tg_\theta(\gamma(u))\dot{\gamma}(u)}\,du
\]

au lieu de la simple distance euclidienne.

---

## 6. LNN : dynamique continue contrôlée

Le LNN possède un état continu :

\[
x(t) \in \mathbb{R}^{d_X}
\]

et évolue selon une ODE :

\[
\frac{dx}{dt} = F_\phi(x(t), r_{fast}(t), c(t), \dot{c}(t), z_{lang}, t)
\]

Une forme concrète :

\[
\dot{x}(t)
=
-\frac{x(t)}{\tau(c(t), r_{fast}(t))}
+
\sigma
\left(
W_xx(t) + W_rr_{fast}(t) + W_cc(t) + W_zz_{lang} + b
\right)
\]

avec constantes de temps modulées :

\[
\tau_i(t)
=
\tau_{min}
+
(\tau_{max}-\tau_{min})\cdot \sigma_\tau
\left(
W_{\tau,i}x(t)+U_{\tau,i}c(t)+V_{\tau,i}r_{fast}(t)+b_{\tau,i}
\right)
\]

On force :

\[
0 < \tau_{min} \leq \tau_i(t) \leq \tau_{max}
\]

pour éviter des constantes de temps nulles ou explosives.

---

### 6.1 Champ dynamique avec potentiel attracteur

Une forme plus stable du LNN est :

\[
\dot{x}(t)
=
f_{LNN}(x(t),r_{fast}(t);\Theta_\phi(c(t),z_{lang}))
-
\lambda\nabla_xV_\psi(x(t),c(t),z_{lang})
+
G_\phi(x(t),c(t))\dot{c}(t)
\]

Interprétation :

- \(f_{LNN}\) : dynamique rapide ;
- \(\Theta_\phi(c,z_{lang})\) : paramètres modulés par le contexte ;
- \(V_\psi\) : potentiel d’attraction vers un comportement souhaité ;
- \(G_\phi\dot{c}\) : correction liée au mouvement du contexte latent.

Le JEPA ne fixe donc pas directement l’état du LNN. Il crée une vallée d’énergie ou un champ de forces dans lequel le LNN évolue.

---

## 7. Politique motrice

Le LNN produit ensuite une action continue :

\[
a(t) = \pi_\omega(x(t), r_{fast}(t), c(t), z_{lang})
\]

Pour un robot mobile différentiel :

\[
a(t) = [v(t), \omega(t)]
\]

Pour un servo unique :

\[
a(t) = [\theta_{servo}^{target}(t)]
\]

Pour plusieurs servomoteurs :

\[
a(t) = [\theta_1(t), \theta_2(t), ..., \theta_n(t)]
\]

On ajoute une couche de sécurité bas niveau :

\[
a_{safe}(t) = \operatorname{clip}(a(t), a_{min}, a_{max})
\]

et éventuellement :

\[
\left|\frac{da}{dt}\right| \leq \dot{a}_{max}
\]

pour limiter les mouvements brusques.

Sur le matériel réel, cette action continue est ensuite discrétisée par l’électronique de contrôle. Pour un servo MG996R piloté en PWM classique, on modélise un bloqueur d’ordre zéro :

\[
\Delta_{PWM}=20\text{ ms}
\]

\[
a_{actuel}(t)=a_{safe}(T_{PWM,n})
\qquad
t \in [T_{PWM,n},T_{PWM,n}+\Delta_{PWM}[
\]

avec :

\[
T_{PWM,n}=n\Delta_{PWM}
\]

Le LNN peut produire \(a(t)\), mais le moteur reçoit \(a_{actuel}(t)\). Le simulateur doit donc apprendre cette contrainte dès le départ pour éviter des micro-oscillations continues impossibles à reproduire physiquement.

---

## 8. Système unifié complet

La formulation centrale du système JEPA–LNN est :

\[
\boxed{
\begin{aligned}
S_k &= E_\theta(o_{T_k}) \\
\bar{x}_{k-1} &= \frac{1}{\Delta}\int_{T_{k-1}}^{T_k}H_\rho(x(t))\,dt \\
\hat{S}_{k+1} &= P_\theta(S_k,A_k,\bar{x}_{k-1},z_{lang}) \\
c_k(t) &= \operatorname{GeoInterp}_{g_\theta}(S_k,\hat{S}_{k+1},t) \\
\dot{x}(t) &= F_\phi(x(t),r_{fast}(t),c_k(t),\dot{c}_k(t),z_{lang}) \\
a(t) &= \pi_\omega(x(t),r_{fast}(t),c_k(t),z_{lang}) \\
\bar{x}_k &= \frac{1}{\Delta}\int_{T_k}^{T_{k+1}}H_\rho(x(t))\,dt
\end{aligned}
}
\]

Dans ce système, \(\bar{x}_{k-1}\) est une entrée causale de la prédiction courante. \(\bar{x}_k\) n’est produit qu’après avoir intégré l’intervalle courant ; il sert donc à la prochaine itération, aux logs, ou aux pertes auxiliaires, pas à construire \(\hat{S}_{k+1}\) au même pas.

La dynamique continue entre deux pas JEPA est :

\[
x(T_{k+1})
=
x(T_k)
+
\int_{T_k}^{T_{k+1}}
F_\phi(x(t),r_{fast}(t),c_k(t),\dot{c}_k(t),z_{lang})\,dt
\]

---

## 9. Préservation de la voie haute fréquence

Il est crucial de garder deux voies séparées :

### Voie lente

\[
S_k \rightarrow c(t) \rightarrow \Theta(c)
\]

Elle module :

- les objectifs ;
- les constantes de temps ;
- les gains ;
- les attracteurs ;
- les priorités comportementales.

### Voie rapide

\[
r_{fast}(t) \rightarrow F_{fast}(x,r_{fast})
\]

Elle gère :

- obstacles proches ;
- collisions ;
- correction d’orientation ;
- instabilité ;
- latence capteur ;
- réflexes locaux.

La condition de séparation temporelle est :

\[
\left\|\frac{dc}{dt}\right\| \ll \left\|\frac{dr_{fast}}{dt}\right\|
\]

Le JEPA ne doit pas filtrer ou écraser les variations rapides nécessaires au contrôle.

---

## 10. Anti-effondrement du latent

Le risque est que le JEPA apprenne un latent dégénéré :

\[
S_k \approx S_j \quad \text{pour des situations différentes}
\]

Cela donne un mode collapse.

---

### 10.1 Perte JEPA principale

On encode l’état courant avec l’encodeur en ligne :

\[
S_k = E_\theta(o_{T_k})
\]

La cible du pas suivant provient d’un encodeur cible séparé, gelé pour la rétropropagation :

\[
S_{k+1}^{target} = E_{\theta_{target}}(o_{T_{k+1}})
\]

Le prédicteur apprend alors :

\[
\mathcal{L}_{JEPA}
=
\left\|
Q_\theta(S_k,A_k,\bar{x}_{k-1},z_{lang})
-
\operatorname{sg}(S_{k+1}^{target})
\right\|^2
\]

avec \(\operatorname{sg}\) = stop-gradient appliqué à la cible.

L’encodeur cible n’est pas optimisé directement par gradient. Il suit l’encodeur en ligne par moyenne mobile exponentielle :

\[
\theta_{target} \leftarrow \beta \theta_{target} + (1-\beta)\theta,
\qquad \beta \in [0.99,0.9999]
\]

Cette séparation évite que la cible se déplace brutalement au même rythme que le prédicteur. Les régularisations de variance/covariance restent utiles, mais elles ne remplacent pas cette cible EMA.

---

### 10.2 Régularisation de variance

Pour chaque dimension latente :

\[
\mathcal{L}_{var}
=
\sum_i
\max(0,\gamma-\sqrt{\operatorname{Var}(S_i)+\epsilon})
\]

Cela empêche une dimension de devenir constante.

---

### 10.3 Régularisation de covariance

\[
\mathcal{L}_{cov}
=
\sum_{i\neq j}\operatorname{Cov}(S)_{ij}^2
\]

Cela force les dimensions latentes à porter des informations différentes.

---

### 10.4 Régularisation de volume

\[
\mathcal{L}_{vol}
=
-\log\det(\operatorname{Cov}(S)+\epsilon I)
\]

Cela force le latent à occuper un volume non nul.

---

### 10.5 Régularisation du rang du pont

Soit le pont latent :

\[
B_\eta : S \mapsto c
\]

et son jacobien :

\[
J_B(S)=\frac{\partial B_\eta(S)}{\partial S}
\]

On peut imposer :

\[
\mathcal{L}_{rank}
=
\left\|J_B(S)^TJ_B(S)-I\right\|_F^2
\]

ou :

\[
\mathcal{L}_{rank}
=
-\log\det(J_B(S)^TJ_B(S)+\epsilon I)
\]

Objectif : éviter que plusieurs intentions ou états différents produisent la même modulation LNN.

---

## 11. Régularisation géométrique

### 11.1 Courbure de trajectoire latente

On pénalise les trajectoires latentes trop courbées :

\[
\mathcal{L}_{geo}
=
\int_{T_k}^{T_{k+1}}
\left\|
\nabla_{\dot{c}}\dot{c}
\right\|_{g_\theta}^2dt
\]

Si \(\mathcal{L}_{geo}\) est faible, le chemin latent est proche d’une géodésique.

---

### 11.2 Régularisation de type Ricci

Version théorique :

\[
\frac{\partial g}{\partial \ell}
=
-2\operatorname{Ric}(g)
+
\mu(g_0-g)
\]

Ici, \(\ell\) est un temps d’entraînement, pas le temps physique.

En pratique, on évite souvent de calculer un vrai flot de Ricci. On peut utiliser une pénalisation de courbure :

\[
\mathcal{L}_{Ricci}
=
\int_\mathcal{M}
\left\|
\operatorname{Ric}(g_\theta)-\kappa g_\theta
\right\|^2d\mu
\]

ou une approximation locale par graphes de voisinage.

But : éviter des régions latentes avec courbure extrême qui déstabiliseraient le solveur ODE.

---

## 12. État augmenté du LNN

Les ODE neuronales pures peuvent être limitées topologiquement, car leurs trajectoires ne se croisent pas dans l’espace d’état. On peut augmenter l’état :

\[
x(t) = [h(t),z(t)]
\]

avec :

\[
h(t) \in \mathbb{R}^{d_H}, \qquad z(t) \in \mathbb{R}^{d_A}
\]

La dynamique devient :

\[
\frac{d}{dt}
\begin{bmatrix}
h \\
z
\end{bmatrix}
=
F_\phi(h,z,r_{fast},c,\dot{c},z_{lang})
\]

Les dimensions auxiliaires \(z(t)\) servent de volume dynamique tampon.

---

## 13. Stabilité de l’adjointe et des gradients

Pour entraîner un Neural ODE ou un LNN, on peut rétropropager via la méthode adjointe.

Soit :

\[
\dot{x}=F_\phi(x,t)
\]

et une perte finale :

\[
\mathcal{L}(x(T))
\]

L’adjoint est :

\[
a(t)=\frac{\partial \mathcal{L}}{\partial x(t)}
\]

et vérifie :

\[
\frac{da}{dt}
=
-a(t)^T\frac{\partial F}{\partial x}
\]

Le risque d’explosion vient du terme :

\[
\frac{\partial F}{\partial x}
\]

On peut borner :

\[
\|a(t)\|
\leq
\|a(T)\|
\exp\left(
\int_t^T
\mu\left(\frac{\partial F}{\partial x}\right)d\tau
\right)
\]

où \(\mu\) est la norme logarithmique.

On impose donc :

\[
\mu\left(\frac{\partial F}{\partial x}\right) \leq \kappa
\]

avec \(\kappa\) petit, idéalement négatif sur les sous-dynamiques rapides.

Perte de stabilité :

\[
\mathcal{L}_{stab}
=
\int
\max\left(
0,
\mu\left(\frac{\partial F}{\partial x}\right)-\kappa
\right)^2dt
\]

Cette contrainte limite l’explosion des gradients, mais elle ne suffit pas à éliminer la raideur numérique. Le terme

\[
G_\phi(x(t),c(t))\dot{c}(t)
\]

agit comme un champ d’advection imposé par le contexte JEPA sur le LNN. Si ce flux rapide s’oppose fortement à l’attracteur lent \(-\lambda\nabla_xV_\psi\), l’ODE peut devenir stiff même avec des constantes de temps bornées.

Conséquence pratique : la stabilité analytique et la stabilité numérique doivent être traitées séparément. Une intégration à pas fixe peut rester bornée tout en donnant une trajectoire physiquement mauvaise si le pas ne résout pas les modes rapides.

---

## 14. Pertes d’entraînement

### 14.1 Perte de contrôle moteur

Pour imitation learning :

\[
\mathcal{L}_{ctrl}
=
\int
\|a(t)-a^*(t)\|^2dt
\]

En discret :

\[
\mathcal{L}_{ctrl}
\approx
\frac{1}{N}\sum_{i=1}^{N}
\|a(t_i)-a^*(t_i)\|^2
\]

---

### 14.2 Perte de sécurité

Obstacle :

\[
\mathcal{L}_{safe}
=
\int
\max(0,d_{min}-d_{obstacle}(t))^2dt
\]

Collision :

\[
\mathcal{L}_{collision}
=
\sum_t \mathbf{1}_{collision}(t)\cdot C
\]

---

### 14.3 Perte de lissage des commandes

\[
\mathcal{L}_{smooth}
=
\int
\left\|\frac{da}{dt}\right\|^2dt
\]

ou :

\[
\mathcal{L}_{smooth}
\approx
\frac{1}{N-1}\sum_{i=1}^{N-1}
\|a_{i+1}-a_i\|^2
\]

---

### 14.4 Perte langage-intention

Si on dispose d’étiquettes d’intention \(z_{goal}\) :

\[
\mathcal{L}_{lang}
=
\|P_\psi(e_{text})-z_{goal}\|^2
\]

Si l’intention est symbolique :

\[
\mathcal{L}_{intent}
=
\operatorname{CE}(\hat{y}_{intent},y_{intent})
\]

---

### 14.5 Perte totale

\[
\boxed{
\begin{aligned}
\mathcal{L}
=&
\lambda_{task}\mathcal{L}_{task}
+
\lambda_{JEPA}\mathcal{L}_{JEPA}
+
\lambda_{var}\mathcal{L}_{var}
+
\lambda_{cov}\mathcal{L}_{cov}
+
\lambda_{vol}\mathcal{L}_{vol}
\\
&+
\lambda_{geo}\mathcal{L}_{geo}
+
\lambda_{Ricci}\mathcal{L}_{Ricci}
+
\lambda_{rank}\mathcal{L}_{rank}
+
\lambda_{stab}\mathcal{L}_{stab}
\\
&+
\lambda_{ctrl}\mathcal{L}_{ctrl}
+
\lambda_{safe}\mathcal{L}_{safe}
+
\lambda_{smooth}\mathcal{L}_{smooth}
+
\lambda_{lang}\mathcal{L}_{lang}
\end{aligned}
}
\]

---

## 15. Paradigme d’entraînement recommandé

Il ne faut pas commencer par un entraînement end-to-end complet. Le système serait trop instable.

### Phase 1 — Simulation minimale sans deep learning

Créer un environnement 2D :

- robot circulaire ;
- orientation ;
- capteur ultrason rotatif ;
- servo simulé ;
- bloqueur d’ordre zéro PWM pour le servo ;
- gyro simulé ;
- obstacles/murs ;
- bruit ;
- latence ;
- logs.

État simulé :

\[
q_t = [x_t,y_t,\theta_t,\theta_{servo,t},v_t,\omega_t]
\]

Observation :

\[
o_t = [d_{ultra,t},\theta_{servo,t},\omega_{gyro,t}]
\]

Action :

\[
a_t = [v_{cmd,t},\omega_{cmd,t},\theta^{target}_{servo,t}]
\]

Discrétisation actionneur :

\[
\Delta_{PWM}=20\text{ ms}
\]

\[
a_{actuel}(t)=a(T_{PWM,n})
\qquad
t \in [T_{PWM,n},T_{PWM,n}+\Delta_{PWM}[
\]

Le simulateur applique \(a_{actuel}\), pas la commande continue instantanée. Pour le servo :

\[
\theta^{held}_{servo,t} = \theta^{target}_{servo}(T_{PWM,n})
\]

tant que \(t \in [T_{PWM,n},T_{PWM,n}+\Delta_{PWM}[\).

Dynamique simple :

\[
x_{t+1}=x_t+v_t\cos(\theta_t)\Delta t
\]

\[
y_{t+1}=y_t+v_t\sin(\theta_t)\Delta t
\]

\[
\theta_{t+1}=\theta_t+\omega_t\Delta t
\]

Servo :

\[
\theta_{servo,t+1}
=
\theta_{servo,t}
+
\operatorname{clip}
(\theta^{held}_{servo,t}-\theta_{servo,t},
-\dot{\theta}_{max}\Delta t,
\dot{\theta}_{max}\Delta t)
\]

Ultrason :

\[
d_{ultra,t}=Raycast(q_t,\theta_t+\theta_{servo,t})+\epsilon_d
\]

Gyro :

\[
\omega_{gyro,t}=\omega_t+\epsilon_\omega
\]

---

### Phase 2 — Entraînement JEPA seul

Le JEPA apprend :

\[
S_t=E_\theta(o_t)
\]

\[
\hat{S}_{t+1}=P_\theta(S_t,a_t)
\]

Perte :

\[
\mathcal{L}_1
=
\mathcal{L}_{JEPA}
+
\lambda_{var}\mathcal{L}_{var}
+
\lambda_{cov}\mathcal{L}_{cov}
+
\lambda_{vol}\mathcal{L}_{vol}
\]

Objectif : apprendre un espace latent prédictif de la dynamique sensorielle.

---

### Phase 3 — Entraînement LNN seul

On fige le JEPA. On entraîne :

\[
\dot{x}=F_\phi(x,r_{fast},c,\dot{c})
\]

et :

\[
a(t)=\pi_\omega(x,r_{fast},c)
\]

Perte :

\[
\mathcal{L}_2
=
\mathcal{L}_{ctrl}
+
\lambda_{safe}\mathcal{L}_{safe}
+
\lambda_{smooth}\mathcal{L}_{smooth}
+
\lambda_{stab}\mathcal{L}_{stab}
\]

---

### Phase 4 — Couplage JEPA–LNN

On connecte le pont :

\[
S_k,\hat{S}_{k+1}\rightarrow c(t),\dot{c}(t)
\]

On entraîne le pont et le LNN :

\[
\mathcal{L}_3
=
\mathcal{L}_{ctrl}
+
\lambda_{rank}\mathcal{L}_{rank}
+
\lambda_{geo}\mathcal{L}_{geo}
+
\lambda_{stab}\mathcal{L}_{stab}
\]

---

### Phase 5 — Ajout du langage

On ajoute :

\[
z_{lang}=P_\psi(LLM_{emb}(ASR(audio)))
\]

On commence avec des commandes simples :

- stop ;
- avance ;
- recule ;
- tourne à gauche ;
- tourne à droite ;
- scanne ;
- évite l’obstacle.

Puis on complexifie vers :

- avance doucement ;
- va vers l’objet ;
- contourne l’obstacle ;
- suis la cible.

---

### Phase 6 — Fine-tuning conjoint contrôlé

On déverrouille partiellement le JEPA avec :

- learning rate faible ;
- gradient clipping ;
- horizons courts ;
- checkpointing ;
- régularisation de stabilité ;
- pas de modification brutale du target encoder.

---

## 16. Curriculum sensoriel inspiré du développement fœtal

L’ordre proposé :

\[
\boxed{
\text{proprioception}
\rightarrow
\text{vestibulaire}
\rightarrow
\text{proximité/toucher}
\rightarrow
\text{audition/langage}
\rightarrow
\text{vision}
\rightarrow
\text{fusion multimodale}
}
\]

---

### Stade 0 — Corps minimal

Capteurs :

- état moteur ;
- commande servo ;
- position servo simulée.

Le modèle apprend :

\[
a_t \rightarrow \Delta m_t
\]

Question apprise :

> Quand j’envoie une commande, qu’est-ce qui change dans mon propre état ?

---

### Stade 1 — Vestibulaire

Capteurs :

- gyroscope ;
- accélération ;
- orientation.

Le modèle apprend :

\[
a_t \rightarrow \Delta \theta_t, \Delta \omega_t
\]

---

### Stade 2 — Proximité / toucher

Capteurs :

- ultrason ;
- ToF ;
- bumper ;
- contact.

Le modèle apprend :

\[
a_t,d_t \rightarrow d_{t+1}
\]

et :

\[
P(collision_{t+1}|o_t,a_t)
\]

---

### Stade 3 — Audition / langage simple

On introduit une variable d’intention :

\[
z_{lang}
\]

D’abord symbolique :

\[
z_{lang}=OneHot(intent)
\]

puis issue du texte :

\[
z_{lang}=P_\psi(LLM_{emb}(texte))
\]

---

### Stade 4 — Vision

On ajoute :

\[
v_t=E_{vision}(I_t)
\]

Le JEPA devient :

\[
S_t=E_\theta(r_{fast}(t),v_t,z_{lang})
\]

La vision doit arriver tard, car elle risque de dominer les autres modalités.

---

### Stade 5 — Fusion multimodale

\[
S_t=E_\theta(r_{fast}(t),v_t,z_{lang},m_t)
\]

\[
\hat{S}_{t+1}=P_\theta(S_t,a_t,z_{lang})
\]

\[
\dot{x}=F_\phi(x,r_{fast},c(t),z_{lang})
\]

---

## 17. Simulation avant réel

L’ordre recommandé est :

\[
\boxed{
\text{Python 2D maison}
\rightarrow
\text{Arduino réel minimal}
\rightarrow
\text{Gazebo + ROS2}
\rightarrow
\text{robot réel mobile}
\rightarrow
\text{Isaac Sim / MuJoCo si besoin}
}
\]

---

### 17.1 Simulateur 2D maison

Objectif immédiat :

- robot circulaire ;
- murs ;
- obstacles ;
- servo scan horizontal ;
- ultrason simulé ;
- gyroscope simulé ;
- bruit ;
- latence ;
- logs compatibles PyTorch.

Le modèle ne doit pas savoir s’il lit :

\[
\text{capteur simulé}
\]

ou :

\[
\text{capteur réel}
\]

On crée donc une interface commune :

```python
class SensorInterface:
    def read(self) -> Observation:
        ...

class ActuatorInterface:
    def apply(self, action: Action) -> None:
        ...
```

---

### 17.2 Domain randomization

À chaque épisode de simulation, on échantillonne des paramètres :

\[
\theta_{sim} \sim p(\theta)
\]

Exemples :

- bruit ultrason ;
- erreur gyroscope ;
- latence servo ;
- vitesse maximale servo ;
- friction ;
- glissement ;
- masse ;
- taille du robot ;
- position des obstacles ;
- formes des obstacles.

La politique devient robuste :

\[
\pi(a|o,\theta_{sim})
\]

et non dépendante d’un monde simulé trop parfait.

---

## 18. Architecture logicielle recommandée

### Version minimale actuelle

```text
robot_project/
  README.md
  pyproject.toml
  src/
    sim2d/
      world.py
      robot.py
      sensors.py
      actuators.py
      physics.py
      renderer.py
      logger.py
      config.py
    learning/
      datasets.py
      jepa.py
      lnn.py
      train_jepa.py
      train_lnn.py
    real/
      arduino_serial.py
      sensor_interface.py
      actuator_interface.py
    common/
      types.py
      math_utils.py
      time_utils.py
  data/
    raw/
    processed/
  notebooks/
  tests/
```

---

## 19. Pseudo-code de boucle simulation

```python
obs = env.reset()

for step in range(num_steps):
    action = policy(obs)
    next_obs, reward, done, info = env.step(action)

    logger.write({
        "t": env.time,
        "obs": obs,
        "action": action,
        "next_obs": next_obs,
        "state": info["state"],
        "collision": info["collision"],
    })

    obs = next_obs

    if done:
        obs = env.reset()
```

---

## 20. Pseudo-code JEPA minimal

```python
class SensorJEPA(nn.Module):
    def __init__(self, obs_dim, action_dim, latent_dim):
        super().__init__()
        self.encoder = MLP(obs_dim, latent_dim)
        self.predictor = MLP(latent_dim + action_dim, latent_dim)

    def forward(self, obs_t, action_t):
        s_t = self.encoder(obs_t)
        pred = self.predictor(torch.cat([s_t, action_t], dim=-1))
        return s_t, pred

    def encode(self, obs):
        return self.encoder(obs)
```

Perte :

```python
s_t, pred_s_next = model(obs_t, action_t)
with torch.no_grad():
    target_s_next = target_encoder(obs_next)

loss_jepa = mse(pred_s_next, target_s_next)
loss = loss_jepa + lambda_var * var_loss + lambda_cov * cov_loss

with torch.no_grad():
    for p_target, p_online in zip(target_encoder.parameters(), model.encoder.parameters()):
        p_target.data.mul_(beta).add_(p_online.data, alpha=1.0 - beta)
```

---

## 21. Pseudo-code LNN minimal

```python
class SimpleLNN(nn.Module):
    def __init__(self, state_dim, input_dim, hidden_dim):
        super().__init__()
        self.tau_net = MLP(state_dim + input_dim, hidden_dim)
        self.dyn_net = MLP(state_dim + input_dim, state_dim)

    def f(self, t, x, u):
        xu = torch.cat([x, u], dim=-1)
        tau = tau_min + (tau_max - tau_min) * torch.sigmoid(self.tau_net(xu))
        drive = torch.tanh(self.dyn_net(xu))
        dx = -x / tau + drive
        return dx
```

Entrée du LNN :

\[
u(t) = [r_{fast}(t),c(t),\dot{c}(t),z_{lang}]
\]

Note d’implémentation pour la Phase 4 : un Euler explicite ou un RK4 à pas fixe suffit pour les prototypes et les tests unitaires, mais ne doit pas être le solveur principal du couplage JEPA-LNN. Pour l’entraînement continu, utiliser un solveur ODE adaptatif, par exemple `dopri5` avec contrôle d’erreur. Si le système devient trop raide, passer à un solveur implicite ou semi-implicite adapté aux ODE stiff, puis journaliser les pas rejetés et la taille de pas minimale pour diagnostiquer les conflits entre flux rapide et attracteur lent.

---

## 22. Hardware et rôle des composants

### Arduino

Rôle : moelle épinière / contrôle bas niveau.

- PWM servo ;
- maintien Zero-Order Hold de la consigne servo entre deux périodes PWM ;
- lecture ultrason ;
- lecture IMU ;
- watchdog ;
- arrêt d’urgence ;
- limites mécaniques.

### PC RTX 5080

Rôle : cortex lourd.

- simulation ;
- entraînement JEPA/LNN ;
- ASR ;
- LLM/embeddings ;
- visualisation ;
- logs.

### Raspberry Pi ou kit robot futur

Rôle : cerveau embarqué léger.

- ROS2 ;
- streaming capteurs ;
- caméra ;
- LiDAR ;
- communication robot/PC.

---

## 23. Résumé mathématique final

Le modèle complet :

\[
\boxed{
\begin{aligned}
\tau &= ASR(audio) \\
e_{text} &= LLM_{emb}(\tau) \\
z_{lang} &= P_\psi(e_{text}) \\
S_k &= E_\theta(o_{T_k},z_{lang}) \\
\bar{x}_{k-1} &= \frac{1}{\Delta}\int_{T_{k-1}}^{T_k}H_\rho(x(t))\,dt \\
\hat{S}_{k+1} &= P_\theta(S_k,A_k,\bar{x}_{k-1},z_{lang}) \\
c_k(t) &= \operatorname{GeoInterp}_{g_\theta}(S_k,\hat{S}_{k+1},t) \\
\dot{x}(t) &= F_\phi(x(t),r_{fast}(t),c_k(t),\dot{c}_k(t),z_{lang}) \\
a(t) &= \pi_\omega(x(t),r_{fast}(t),c_k(t),z_{lang}) \\
a_{safe}(t) &= SafetyLayer(a(t)) \\
a_{actuel}(t) &= ZOH_{\Delta_{PWM}}(a_{safe})(t)
\end{aligned}
}
\]

avec contraintes :

\[
\det(\operatorname{Cov}(S)+\epsilon I)>0
\]

\[
\operatorname{rank}(J_B) \approx d_S
\]

\[
\mu\left(\frac{\partial F}{\partial x}\right)\leq \kappa
\]

\[
\left\|\nabla_{\dot{c}}\dot{c}\right\|_{g_\theta}^2 \text{ faible}
\]

\[
\left\|\frac{da}{dt}\right\| \leq \dot{a}_{max}
\]

---

## 24. Priorité immédiate pour Codex

La première tâche raisonnable n’est pas d’implémenter tout ce modèle.

La première tâche est :

> Créer un simulateur 2D minimal, modulaire et loggable, représentant le montage actuel : servo horizontal + ultrason + gyroscope + bruit + latence.

Prompt utile pour Codex :

```text
Crée un projet Python modulaire pour un simulateur robotique 2D minimal.

Objectif : simuler un robot circulaire avec orientation, capteur ultrason rotatif monté sur servo horizontal, gyroscope simulé, obstacles/murs, bruit capteur et latence.

Je veux :
- une architecture de projet propre ;
- des classes World, Robot, UltrasonicSensor, GyroSensor, Servo, Logger ;
- une boucle de simulation ;
- un rendu simple matplotlib ou pygame ;
- des logs CSV/Parquet contenant observations, actions, états réels et collisions ;
- une interface qui permettra plus tard de remplacer la simulation par l’Arduino réel sans changer le code d’apprentissage ;
- pas encore de deep learning.

Prépare le code pour qu’on puisse ensuite entraîner un JEPA puis un LNN avec PyTorch.
```

---

## 25. Références conceptuelles à consulter

- I-JEPA : Image-based Joint-Embedding Predictive Architecture.
- MC-JEPA : JEPA appliqué au contenu et au mouvement.
- Liquid Time-Constant Networks : réseaux continus à constantes de temps variables.
- Neural ODEs : apprentissage par équations différentielles neuronales.
- Augmented Neural ODEs : augmentation dimensionnelle contre les limites topologiques.
- Neural Controlled Differential Equations : modèles continus contrôlés par des chemins d’observation.
- VICReg : régularisation variance/covariance pour éviter l’effondrement latent.
- Domain Randomization : transfert simulation → réel par randomisation des paramètres.
- Théorie des modèles internes cérébelleux : contrôle moteur prédictif et correction rapide.

---

## 26. Idée directrice

Ne pas chercher immédiatement un robot intelligent généraliste.

Chercher d’abord un organisme artificiel minimal qui apprend :

\[
\text{action} \rightarrow \text{sensation} \rightarrow \text{prédiction} \rightarrow \text{correction}
\]

Puis ajouter les sens progressivement.

Le robot doit d’abord apprendre qu’il a un corps avant de prétendre comprendre le monde. C’est aussi valable pour certains humains, mais ce n’est pas le sujet du dépôt.
