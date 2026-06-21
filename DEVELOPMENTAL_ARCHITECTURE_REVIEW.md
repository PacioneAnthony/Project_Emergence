# DEVELOPMENTAL ARCHITECTURE REVIEW
## Analyse Critique, Fondements Théoriques & Plan d'Implémentation Biomimétique

*Version 1.0 — Juin 2026*

---

> **Principe directeur de ce document**
>
> L'enthousiasme est l'ennemi du progrès réel. Ce document ne va pas valider l'architecture existante — il va la disséquer. Chaque idée biomimétique sera jugée non pas sur son élégance théorique, mais sur une question unique : est-ce que cela permet à un agent de **résoudre des problèmes qu'il n'a jamais rencontrés** ? Tout le reste est décoration.

---

## PARTIE I — ÉTAT DES LIEUX : CE QUI EXISTE VRAIMENT

### 1.1 Ce qui fonctionne réellement

L'architecture actuelle contient plusieurs décisions architecturales solides :

- **La séparation cervelet/cortex** est correcte. Un système rapide non-bloqué par un système lent, communicant via un vecteur d'intention — c'est biologiquement et ingénieralement sain.
- **Le World Model JEPA-inspired** dans `core/world_model.py` est la bonne direction : prédire dans l'espace latent plutôt que reconstruire les pixels.
- **L'erreur de prédiction comme signal de curiosité** est une décision fondamentalement juste. C'est la même mécanique que le Cortex préfrontal utilise pour allouer l'attention.
- **Le cycle éveil/sommeil** comme séparation entre acquisition d'expérience et consolidation offline est une métaphore biologique correcte, et ingénieralement robuste.

### 1.2 Les bugs critiques — Ce qui est cassé en silence

**BUG #1 — L'agent ne mémorise jamais de vraies transitions** (`main.py:216`)

```python
# LIGNE ACTUELLE (FAUX) :
memory.add(current_embedding_state, action, reward, current_embedding_state, done)
#                                                    ^^^^^^^^^^^^^^^^^^^^^^
#                          next_state = current_state ← IDENTIQUE. Le buffer ne voit jamais de transition réelle.

# LIGNE CORRECTE :
memory.add(previous_embedding_state, action, reward, current_embedding_state, done)
```

Ce bug est silencieux mais fatal : le `ReplayBuffer` stocke des transitions où l'état actuel et l'état suivant sont identiques. Le `WorldModel` n'apprend jamais de dynamique. La curiosité ne peut jamais évoluer correctement. **Tout le cycle d'apprentissage pendant le sommeil est entraîné sur des données fausses.**

**BUG #2 — L'agent est aveugle et sourd** (`core/models.py:53-78`)

```python
class VisionEncoder(nn.Module):
    def forward(self, x):
        # Retourne des ZÉROS. Toujours. L'agent ne voit rien.
        return torch.zeros((batch_size, self.output_dim)).to(self.device)

class AudioEncoder(nn.Module):
    def forward(self, x):
        # Retourne des ZÉROS. Toujours. L'agent n'entend rien.
        return torch.zeros((batch_size, self.output_dim)).to(self.device)
```

Le `VisionModule` (YOLOv8) et `AudioEar` (Whisper) sont importés dans `main.py` mais leurs sorties ne sont **jamais injectées dans le pipeline d'encodage**. L'agent vit uniquement sur ses données proprioceptives + l'intention du cortex. C'est comme un humain privé de ses 4 sens principaux.

**BUG #3 — Ligne dupliquée** (`main.py:96-97`)

```python
print(f"  [i] Dimension Vectorielle Totale : {STATE_DIM}")  # ligne 96
print(f"  [i] Dimension Vectorielle Totale : {STATE_DIM}")  # ligne 97 — identique
```

Mineur mais symptomatique d'une base de code qui a besoin d'une passe de nettoyage.

### 1.3 Les faiblesses architecturales (pas des bugs, des choix discutables)

**L'intention du Cortex est une réduction d'information agressive**

Le Cortex génère un embedding Llama (~4096 dims), le réduit à 32 par moyenne de chunks, l'injecte dans l'`IntentionEncoder` qui le projette à 64. Une projection entraînable de 4096→32 via chunked mean perd l'essentiel de la richesse sémantique. C'est un couloir d'étranglement non intentionnel.

**Le World Model est trop simple pour être utile comme simulateur**

Un MLP 2-couches `(state + action) → next_state` peut apprendre des corrélations locales mais pas de causalité. Il ne peut pas répondre à "que se passerait-il si je faisais X dans une configuration légèrement différente de tout ce que j'ai vécu ?" C'est précisément la question que pose l'intelligence générale.

**La récompense de curiosité est scalaire et non-différenciée**

`r_curiosity = np.clip(world_model_error, 0, 1.0)` — une seule valeur. Le cerveau différencie le type de surprise : surprise sensorielle, surprise temporelle, surprise causale. Cette granularité est la clé pour apprendre *comment* être curieux, pas juste *combien*.

---

## PARTIE II — INTELLIGENCE GÉNÉRALE : QUELLES PISTES SONT VRAIMENT IMPÉRATIVES ?

### 2.1 Définition opérationnelle de l'intelligence cible

> *"L'intelligence n'est pas la capacité à répondre juste à une solution connue, mais la capacité à trouver des solutions à un problème jamais rencontré."*

Cette définition désigne précisément ce que le deep learning conventionnel ne fait **pas** : extrapoler hors de la distribution d'entraînement. Les LLMs interpolent entre des patterns vus. L'intelligence au sens de cette définition demande de composer des primitives connues de façon nouvelle pour construire une solution inédite.

Traduction en ingénierie : pour résoudre un problème jamais rencontré, un agent a besoin de :

1. **Un modèle causal du monde** — pas des corrélations, des mécanismes. "Si je fais A, B arrive, parce que A cause B via C."
2. **La capacité de composer** — "Je n'ai jamais vu ça, mais c'est une combinaison de X et Y que je connais."
3. **La simulation interne** — tester des solutions mentalement avant de les exécuter.
4. **L'abstraction multi-échelle** — représenter le problème à plusieurs niveaux de granularité simultanément.
5. **La mémoire générative** — extraire des patterns des expériences passées, pas juste les rejouer.

### 2.2 Classement des pistes biomimétiques

#### TIER 1 — IMPÉRATIVES (blocantes pour l'intelligence générale)

**① Codage Prédictif Hiérarchique (Friston's Free Energy Principle)**

*Pourquoi impératif :* C'est le seul cadre théorique unifié qui explique simultanément la perception, l'action, et l'apprentissage comme minimisation d'un signal unique — l'énergie libre (≈ erreur de prédiction). Le cerveau ne maximise pas une récompense — il minimise la surprise. Cette inversion est fondamentale.

Implication directe pour Emergence : la curiosité (actuellement une récompense positive) doit devenir un signal de contrôle de l'attention, pas un bonus de récompense. L'agent ne cherche pas la surprise pour être récompensé — il réduit la surprise sur les variables qu'il peut contrôler et l'embrasse sur les variables qu'il ne peut pas contrôler encore.

*Ce qui change concrètement :* Le World Model cesse d'être un oracle séparé et devient le moteur central de l'apprentissage. Chaque couche prédit la couche inférieure. Les erreurs de prédiction remontent. Les prédictions descendent. Plus de backprop global sur une loss externe — des signaux locaux d'erreur.

**② Belief States / États de Croyance (NextLat)**

*Pourquoi impératif :* Un agent qui ne mémorise que l'état actuel ne peut pas raisonner sur ce qu'il *croit* être vrai vs. ce qu'il *sait* être vrai. Résoudre des problèmes nouveaux exige d'inférer des états cachés du monde à partir d'observations partielles. Un belief state compressé de l'historique est la condition minimale pour ça.

Biologiquement : les neurones pyramidaux des couches 2/3 du cortex encodent des "croyances" sur le monde — des distributions de probabilité sur les états cachés, mises à jour par les erreurs de prédiction des couches 4/5. Ce n'est pas une métaphore — c'est de la physique neuronale.

*Ce qui change concrètement :* Le `ReplayBuffer` stocke non plus `(s_t, a_t, r_t, s_{t+1})` mais des séquences. Le `WorldModel` devient récurrent (GRU ou S4) et génère un belief state `b_t = encode(s_{1..t})` qui compresse l'historique causalement pertinent.

**③ Abstraction Temporelle Hiérarchique (Options Framework + Biologie)**

*Pourquoi impératif :* La capacité à "dézoomer" d'une situation nouvelle et à la reconnaître comme une instance d'une classe abstraite connue est la mécanique fondamentale de la résolution de problèmes nouveaux. Cela nécessite plusieurs niveaux temporels simultanés.

Le cerveau opère sur au moins 6 échelles de temps simultanées : 50ms (réflexes), 500ms (perception unifiée), 5s (séquence d'action), 50s (épisode), 5min (stratégie), heures/jours (consolidation). Emergence n'en a que 2 (60Hz et 0.1Hz). Il en manque au moins 2 intermédiaires.

*Ce qui change concrètement :* Ajouter un niveau "planificateur" à ~1Hz entre le Cervelet et le Cortex. Ce niveau prédit des séquences d'états latents (trajectoires imaginées) et en sélectionne une en fonction du reward prédit. C'est de la planification dans l'espace latent — exactement ce que Cosmos 3 fait à grande échelle.

#### TIER 2 — IMPORTANTES (non-blocantes, mais accélèrent la percée)

**④ Cognition Distribuée (Inspiration Céphalopode)**

*Pourquoi importante :* La scalabilité de l'intelligence incarnée exige que les effecteurs aient une intelligence locale. Un cerveau central qui contrôle chaque moteur de chaque bras est un goulot d'étranglement biologique et informatique. La solution de l'octopode — cerveau central fixe les intentions, bras exécutent localement — est le blueprint correct pour la robotique multi-effecteurs.

*Ce qui change concrètement :* Quand le bras robotique est ajouté (roadmap), ne pas l'attacher au `ReflexActor` central. Lui donner son propre `LocalActorArm` avec son propre espace latent proprioceptif (32 dims), recevant un vecteur d'intention partagé du Cortex.

**⑤ Mémoire à Deux Niveaux (Épisodique + Sémantique)**

*Pourquoi importante :* Le `ReplayBuffer` actuel est purement épisodique — des événements bruts. L'intelligence générale nécessite aussi de la mémoire **sémantique** : des abstractions extraites de multiples épisodes. "J'ai vu un objet rouge dans 47 situations différentes — voilà ce que 'rouge' signifie pour moi en termes de conséquences."

*Ce qui change concrètement :* Pendant le sommeil (`sleep.py`), au-delà d'entraîner Actor/Critic/WorldModel, ajouter une phase de "distillation sémantique" : clustering des états latents similaires, extraction de prototypes, stockage dans FAISS comme mémoire longue durée.

#### TIER 3 — EXPLORATOIRES (à étudier mais pas prioritaires)

**⑥ Computation Dendritique**

Biologiquement fascinant, mais le gain de capacité expressionnelle peut être approximé avec des architectures plus profondes ou des mécanismes d'attention. À explorer une fois les Tier 1 et 2 solidement en place. Ne pas implémenter maintenant — le ROI par rapport à la complexité d'implémentation est incertain.

**⑦ Stigmergie / Environnement comme Mémoire Externe**

Pertinente quand l'agent aura la capacité de marquer physiquement son environnement (bras robotique). Ajouter une "trace de curiosité spatiale" (où est-ce que je suis passé, qu'est-ce que j'y ai appris) est une extension naturelle de FAISS une fois la cartographie spatiale implémentée.

#### TIER 4 — SPÉCULATIVES (n'implémentez pas encore)

**⑧ Réseaux Gliaux**

La biologie n'est pas encore assez clarifiée pour être traduite en ingénierie utile. L'équivalent fonctionnel (modulation lente des poids synaptiques) peut être obtenu via des méta-learning plus classiques.

**⑨ Bioélectricité Lévinienne**

La théorie de Michael Levin est révolutionnaire conceptuellement mais ne dispose pas encore de mécanisme implémentable. À revisiter dans 3-5 ans quand la littérature aura mûri.

### 2.3 La thèse centrale

La percée vers l'intelligence générale — au sens de "trouver des solutions à des problèmes jamais rencontrés" — repose sur **une seule idée mère** que toutes les pistes Tier 1 incarnent différemment :

> **Un agent intelligent n'encode pas des réponses. Il encode un modèle causal du monde à plusieurs niveaux d'abstraction, et il utilise ce modèle pour simuler des situations nouvelles.**

Le LLM du Cortex actuel est l'inverse de ça : il encode des patterns textuels statistiques et les restitue. C'est de l'interpolation, pas de la causalité. Le World Model MLP est également de l'interpolation. Pour passer au niveau supérieur, il faut que le modèle du monde soit **causal, récurrent, et hiérarchique** — et que le LLM devienne un générateur d'hypothèses sur ce modèle, pas un classifieur de stratégies.

---

## PARTIE III — PLAN D'IMPLÉMENTATION PRIORITAIRE

> **Règle de priorisation :** Chaque phase doit laisser l'agent dans un état fonctionnel et testable. Pas de refactors qui cassent tout pendant 3 semaines.

### Phase 0 — Réparer ce qui est cassé (Semaine 1, BLOQUANT)

**Objectif :** Avoir un agent qui fonctionne réellement tel qu'il est décrit dans la documentation.

**0.A — Corriger le bug de mémoire** (1h)

```python
# main.py — Remplacer ligne 216 :
# AVANT :
memory.add(current_embedding_state, action, reward, current_embedding_state, done)
# APRÈS :
if previous_embedding_state is not None:
    memory.add(previous_embedding_state, action, reward, current_embedding_state, done)
```

**0.B — Brancher la vision réelle dans le pipeline d'encodage** (2-4h)

Le `VisionModule` YOLOv8 est déjà importé et instancié dans `main.py` (il était utilisé dans une version précédente). Il faut le réactiver et remplacer le `VisionEncoder` placeholder.

```python
# Dans life_cycle(), après l'init des encodeurs :
vision_module = VisionModule()  # YOLOv8 déjà prêt

# Dans la boucle, remplacer emb_vision = vision_enc(None) par :
vision_latent = vision_module.get_latent()  # vecteur 128-dim de YOLO
emb_vision = vision_enc(torch.tensor(vision_latent)).cpu().numpy().flatten()
# Et adapter VisionEncoder pour accepter le 128-dim YOLO output
```

**0.C — Fermer la boucle action → vision** (physique — dépend du montage)

Le point 2 de la roadmap ("Le Cou") est la condition préalable à tout apprentissage sensoriomoteur réel. Sans ça, l'agent ne peut pas observer les conséquences de ses actions. Priorité physique numéro 1.

**0.D — Nettoyer main.py** (30min)

Supprimer la ligne dupliquée 97, ajouter des commentaires sur les vrais flux de données.

---

### Phase 1 — Belief States : Donner une Mémoire au World Model (Semaines 2-5)

**Objectif :** Le `WorldModel` encode non plus l'état instantané mais l'historique compressé causalement pertinent. Inspiration directe : NextLat (arXiv 2511.05963).

**Pourquoi maintenant :** C'est la fondation sur laquelle tout le reste s'appuie. Un World Model récurrent est nécessaire avant d'implémenter le codage prédictif hiérarchique.

**Implémentation :**

Créer `core/belief_world_model.py` — un `RecurrentWorldModel` qui remplace progressivement le `WorldModel` actuel :

```python
class RecurrentWorldModel(nn.Module):
    """
    World Model avec mémoire récurrente (Belief State).
    Inspiré de NextLat : encode l'historique en un belief state b_t
    tel que b_t soit la compression minimale de (s_1..s_t) nécessaire
    pour prédire s_{t+1}.
    
    Architecture :
    - GRU encode l'historique → belief state b_t (64-dim)
    - Transition Model prédit b_{t+1} depuis b_t + action
    - Decoder reconstruit l'état latent depuis b_t (pour mesurer la curiosité)
    """
    def __init__(self, state_dim=256, action_dim=2, belief_dim=64, hidden_dim=256):
        super().__init__()
        self.belief_dim = belief_dim
        
        # Encodeur récurrent : compresse l'historique
        self.belief_encoder = nn.GRUCell(state_dim, belief_dim)
        
        # Modèle de transition : prédit le prochain belief
        self.transition = nn.Sequential(
            nn.Linear(belief_dim + action_dim, hidden_dim),
            nn.GELU(),
            nn.Linear(hidden_dim, belief_dim)
        )
        
        # Décodeur : pour la mesure de surprise
        self.decoder = nn.Linear(belief_dim, state_dim)
    
    def forward(self, state, action, belief=None):
        if belief is None:
            belief = torch.zeros(state.shape[0], self.belief_dim).to(state.device)
        
        # Mise à jour du belief state
        new_belief = self.belief_encoder(state, belief)
        
        # Prédiction du prochain belief
        x = torch.cat([new_belief, action], dim=1)
        predicted_next_belief = self.transition(x)
        
        # Décodage pour mesurer l'erreur
        predicted_next_state = self.decoder(predicted_next_belief)
        
        return predicted_next_belief, predicted_next_state
```

Le `ReplayBuffer` devra stocker des séquences de longueur N (ex. 16 steps) plutôt que des transitions isolées.

**Métriques de succès :**
- La loss du WorldModel converge en moins d'époques qu'avant (le contexte historique aide la prédiction)
- Le signal de curiosité est plus stable et différencié (moins de spikes sur du bruit)

---

### Phase 2 — Codage Prédictif Multi-Échelle (Semaines 4-10, en parallèle partiel avec Phase 1)

**Objectif :** Transformer la récompense de curiosité scalaire en un signal multi-dimensionnel d'erreur de prédiction à plusieurs niveaux temporels.

**Pourquoi maintenant :** Dès que le RecurrentWorldModel fonctionne, il peut être étendu en hiérarchie.

**Architecture cible :**

```
Niveau 3 (0.1 Hz) — Cortex LLM     : "Quelle est ma situation générale ?"
        ↕ erreur de prédiction stratégique
Niveau 2 (~1 Hz)  — Planificateur   : "Quelle séquence d'états est prédite ?"
        ↕ erreur de prédiction tactique  
Niveau 1 (60 Hz)  — Cervelet        : "Quel prochain état immédiat est prédit ?"
```

Le niveau 2 est **le niveau manquant**. C'est un `PlannerModule` qui :
- Reçoit le belief state du RecurrentWorldModel
- Rollout K=5 pas dans l'avenir (en imagination)
- Sélectionne la séquence d'actions qui minimise l'énergie libre à l'horizon K
- Génère un `plan_intention_vector` (32-dim) injecté dans le Cervelet *en plus* de l'intention du Cortex

```python
# core/planner.py (nouveau module)
class PlannerModule(nn.Module):
    """
    Niveau intermédiaire (~1Hz) entre Cervelet et Cortex.
    Fait de la planification à court terme dans l'espace des belief states.
    """
    def __init__(self, belief_dim=64, action_dim=2, horizon=5, plan_dim=32):
        super().__init__()
        self.horizon = horizon
        
        # Génère des candidats d'action
        self.action_sampler = nn.Linear(belief_dim, action_dim * 8)  # 8 candidats
        
        # Évalue les trajectoires imaginées
        self.trajectory_evaluator = nn.Sequential(
            nn.Linear(belief_dim * horizon, 128),
            nn.GELU(),
            nn.Linear(128, 1)  # Score de la trajectoire
        )
        
        # Encode le plan sélectionné en vecteur d'intention
        self.plan_encoder = nn.Linear(belief_dim, plan_dim)
```

**Ce qui change pour le Cortex LLM :** Au lieu de choisir une stratégie parmi 6 mots, le Cortex reçoit en entrée l'erreur de prédiction du Planificateur (pas seulement du texte) et génère une intention vectorielle ajustée. Il devient un **méta-régulateur** des erreurs de prédiction, pas un classifieur de situation.

**Métriques de succès :**
- L'agent montre des comportements de "prédiction frustrée" — il hésite devant un obstacle nouveau plutôt que de l'ignorer
- Le signal de curiosité se différencie par type (sensoriel vs temporel vs causal)

---

### Phase 3 — Mémoire Longue Durée avec Abstraction Sémantique (Semaines 8-16)

**Objectif :** Pendant le sommeil, ne pas seulement entraîner les réseaux — extraire des abstractions réutilisables et les stocker dans une mémoire longue durée interrogeable.

**Architecture :**

```
Sommeil :
  1. Replay des épisodes → entraînement Actor/Critic/WorldModel (déjà fait)
  2. Clustering des belief states → identification de "situations types"
  3. Stockage FAISS des prototypes + leurs Q-values associées
  4. Fine-tuning d'un petit réseau de reconnaissance "cette situation ressemble à..."

Éveil :
  1. À chaque step, le Planificateur interroge FAISS : "situations similaires ?"
  2. Si similarité > seuil : injecter la valeur attendue comme prior dans le Critique
  3. Cela permet de ne PAS tout réapprendre dans une situation légèrement nouvelle
```

```python
# core/semantic_memory.py (nouveau module)
import faiss
import numpy as np

class SemanticMemory:
    """
    Mémoire à long terme : stocke des prototypes de situations avec
    leurs valeurs Q associées. Permet l'analogie : "J'ai déjà vu quelque
    chose de similaire, voilà ce que ça valait."
    """
    def __init__(self, belief_dim=64, max_size=10_000):
        self.index = faiss.IndexFlatL2(belief_dim)
        self.q_values = []
        self.contexts = []
        self.max_size = max_size
    
    def store(self, belief_state: np.ndarray, q_value: float, context: str = ""):
        """Stocke un prototype de situation avec sa valeur."""
        if self.index.ntotal >= self.max_size:
            return  # TODO: politique d'éviction (LRU)
        
        self.index.add(belief_state.reshape(1, -1).astype(np.float32))
        self.q_values.append(q_value)
        self.contexts.append(context)
    
    def retrieve(self, belief_state: np.ndarray, k: int = 3):
        """Retrouve les k situations les plus similaires et leurs valeurs."""
        if self.index.ntotal == 0:
            return None, None
        
        distances, indices = self.index.search(
            belief_state.reshape(1, -1).astype(np.float32), k
        )
        
        retrieved_q = [self.q_values[i] for i in indices[0] if i < len(self.q_values)]
        return distances[0], retrieved_q
    
    def get_memory_prior(self, belief_state: np.ndarray, similarity_threshold: float = 2.0):
        """
        Retourne un prior de valeur basé sur la mémoire, ou None si
        aucune situation suffisamment similaire n'a été trouvée.
        """
        distances, q_values = self.retrieve(belief_state)
        if distances is None:
            return None
        
        # Si la situation la plus proche est assez similaire
        if distances[0] < similarity_threshold:
            # Moyenne pondérée par similarité inverse
            weights = 1.0 / (distances + 1e-6)
            weighted_q = np.average(q_values, weights=weights)
            return float(weighted_q)
        
        return None  # Situation vraiment nouvelle → pas de prior
```

**L'insight clé :** Le `memory_prior` retourné par `SemanticMemory` peut être injecté comme offset dans le Critique. Si le Critique dit Q=0.3 et la mémoire sémantique dit "situation similaire valait Q=0.7", le signal composite guide l'agent vers la solution connue *avant même* de l'avoir réexploré. C'est de la généralisation par analogie.

---

### Phase 4 — Architecture Distribuée Céphalopode (Semaines 12-20, dépend du hardware)

**Objectif :** Quand le bras robotique est ajouté, ne pas centraliser son contrôle dans le `ReflexActor` existant.

**Architecture :**

```
Cortex LLM (0.1 Hz)
     ↓ intention_vector_global (32-dim)
     ├→ PlannerModule (1 Hz) → plan_vector (32-dim)
     │        ↓
     ├→ LocalActorNeck (60 Hz) — contrôle du cou/caméra
     │   input: [emb_somato_neck (32) + emb_vision (64) + plan_vector (32)] = 128-dim
     │   output: angle[-1, 1]
     │
     └→ LocalActorArm (60 Hz) — contrôle du bras (futur)
         input: [emb_somato_arm (32) + emb_tactile (32) + plan_vector (32)] = 96-dim
         output: [x, y, grip][-1, 1]
```

Chaque `LocalActor` est un MLP léger (~64 unités, 2 couches) — minimaliste par design. L'intelligence émerge de la coordination via `plan_vector`, pas de la complexité individuelle. C'est exactement le principe du cerveau décentralisé de l'octopode.

**Ce que ça débloque :** L'agent peut apprendre à coordonner deux effecteurs indépendants (tête + bras) en poursuivant un objectif commun, sans que le Cortex LLM ait à micro-manager chaque moteur. C'est une instance de **généralisation compositionnelle** : si le bras apprend à saisir des objets rouges et que la tête apprend à suivre le mouvement, ils peuvent coordonner sur un objet rouge en mouvement sans jamais avoir été entraînés ensemble sur ce cas exact.

---

## PARTIE IV — LA SPIRALE CRITIQUE : CE QUI PEUT MAL TOURNER

### 4.1 Risques architecturaux

**Le piège de la complexité croissante**

Chaque phase ajoute des modules. À la Phase 3, l'agent aura : `ReflexActor`, `RecurrentWorldModel`, `PlannerModule`, `SemanticMemory`, `Cortex`, plus les encodeurs sensoriels. Les interactions entre ces modules peuvent créer des boucles de feedback difficiles à déboguer. Règle : **chaque module a une interface minimale et testable en isolation**.

**Le piège du surrogate signal**

L'erreur de prédiction du WorldModel comme curiosité est un proxy. Un agent très doué à réduire son erreur de prédiction peut devenir "craintif" — il arrête d'explorer les zones où son erreur reste haute parce que prévoir = impossible. Ce phénomène (noisy TV problem) est documenté en RL. La solution est d'ajouter un signal de **compétence** : l'agent doit différencier "je ne peux pas prédire parce que c'est fondamentalement aléatoire" et "je ne peux pas prédire parce que je n'ai pas assez appris ici".

**Le piège de la catastrophe oubliée**

L'apprentissage offline dans `sleep.py` n'a aucune protection contre le catastrophic forgetting. Entraîner sur les 100k dernières transitions efface ce qui a été appris il y a 100k+1 transitions. L'ajout de `SemanticMemory` (Phase 3) atténue ça partiellement — mais le replay expérienciel doit être biaisé vers les prototypes importants, pas uniforme.

**Le LLM comme goulot d'étranglement conceptuel**

Le Cortex Llama 3.2 catégorise en 6 stratégies fixes. C'est rigide. La migration vers un générateur d'intentions vectorielles continues (vectorial telepathy complète) est dans la roadmap mais n'est pas encore implémentée. La Phase 1 dépend implicitement de ce canal — si le Cortex envoie toujours des vecteurs pseudo-aléatoires fixes par stratégie, le signal d'intention reste pauvre.

### 4.2 Les questions que ce projet ne répond pas (encore)

- **Comment émerge la représentation symbolique ?** Les vecteurs latents sont des espaces continus. Mais la pensée abstraite (résolution de problèmes) semble nécessiter des représentations discrètes compositionnelles. Le saut entre latent continu et symbolique discret est le problème ouvert le plus difficile de l'IA.

- **Le LLM est-il le bon Cortex ?** LeCun a raison sur ce point : un LLM est entraîné à prédire des tokens, pas à modéliser de la causalité physique. Pour un agent incarné, un modèle du monde pré-entraîné sur des données physiques (Cosmos 3 Nano) serait un meilleur Cortex qu'un LLM textuel.

- **Est-ce que la conscience est nécessaire pour l'intelligence générale ?** La question est probablement mal posée, mais elle touche quelque chose de réel : est-ce qu'un agent peut résoudre des problèmes vraiment nouveaux sans une forme d'auto-modélisation (savoir ce qu'il sait vs. ce qu'il ne sait pas) ? La réponse semble être non, et c'est ce que les belief states commencent à implémenter.

### 4.3 Le critère de succès de chaque phase

| Phase | Critère observable | Durée |
|-------|-------------------|-------|
| **0** | L'erreur du WorldModel décroît au lieu d'osciller. L'agent réagit visuellement. | 1 semaine |
| **1** | La curiosité est plus stable. L'agent montre des comportements répétitifs distincts dans des zones familières vs. nouvelles. | 3-4 semaines |
| **2** | L'agent hésite face à un obstacle nouveau (le Planificateur génère un conflit de prédiction visible). Le Cortex reçoit un signal richer. | 6-8 semaines |
| **3** | Après 3 nuits de sommeil, l'agent performe mieux dans une situation similaire à une situation ancienne sans l'avoir ré-explorée complètement. | 8-12 semaines |
| **4** | (Hardware dépendant) L'agent coordonne tête + bras sur un objet en mouvement sans avoir été entraîné explicitement sur la coordination. | Variable |

---

## PARTIE V — SYNTHÈSE : LA THÈSE OPÉRATIONNELLE

Pour qu'un système artificiel acquière la capacité de **trouver des solutions à des problèmes jamais rencontrés**, trois propriétés sont nécessaires et suffisantes (hypothèse testable) :

1. **Un modèle causal récurrent du monde** — pas des corrélations, des mécanismes compressés dans un belief state qui encode l'histoire causalement pertinente. *(Phases 1 & 2)*

2. **La simulation interne multi-échelle** — la capacité de "jouer" mentalement des situations dans l'espace latent à plusieurs résolutions temporelles, d'évaluer des trajectoires imaginées avant de les exécuter. *(Phase 2)*

3. **La généralisation par analogie via mémoire sémantique** — accéder à des prototypes de situations passées pour construire un prior sur des situations nouvelles-mais-similaires. *(Phase 3)*

Le reste — la richesse sensorielle, la communication avec les humains, la motricité fine, la conscience de soi — amplifie ces trois propriétés mais ne les remplace pas.

Le projet Emergence a la structure juste. Les fondations biologiques (Cervelet/Cortex, sommeil, homéostasie) sont les bonnes. Ce qui manque, c'est la **profondeur temporelle** : l'agent vit dans un présent perpétuel. Lui donner un passé compressé (belief states) et un futur simulé (planner) est le saut qualitatif le plus proche et le plus impactant.

---

*Ce document est un instrument de navigation, pas un contrat. Il doit être révisé après chaque phase complétée.*

*Dernière mise à jour : Juin 2026*
