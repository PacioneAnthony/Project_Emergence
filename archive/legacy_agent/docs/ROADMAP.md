# 🗺️ Roadmap & Pistes d'Exploration

État actuel : **Architecture Hybride & Intelligence Bicamérale**.
L'agent possède un corps (Windows/Stepper), un cerveau (Linux/RTX 5080), et une double intelligence (Reflexe + Llama 3.2).

> Cette roadmap historique est conservée pour contexte. La roadmap active est désormais définie par les jalons J0 à J8 de [`DEVELOPMENTAL_ARCHITECTURE.md`](DEVELOPMENTAL_ARCHITECTURE.md), en commençant par l'instrumentation multimodale du banc physique et le schéma corporel du cou.

## 🎯 Priorités Immédiates

0.  **Simulation 2D avant le réel :**
    *   Le dépôt contient maintenant un backend `sim2d/` pour simuler un robot circulaire avec servo horizontal, ultrason, gyroscope, bruit, latence, obstacles et logs CSV.
    *   **Action :** générer des trajectoires avec `python simulate.py --episodes 5 --steps 6000`, puis entraîner progressivement le JEPA minimal avant de reconnecter l'Arduino.

1.  **Intégration du Moteur dans la Boucle de Vie :**
    *   Le Moteur Pas-à-Pas (Stepper) remplace le Servo.
    *   **Action :** Tester `main.py` avec le nouveau moteur et ajuster la "patience" du cerveau si nécessaire (risque de décalage temporel si le cerveau est trop rapide pour le moteur).

2.  **Montage Physique ("Le Cou") :**
    *   **Objectif :** Fixer la webcam sur le moteur (ou le moteur sous la webcam).
    *   **Pourquoi :** Indispensable pour fermer la boucle "Action -> Changement de Vue -> Curiosité". Sans ça, l'agent est aveugle aux conséquences de ses mouvements.

3.  **La "Télépathie" Vectorielle (Plan Géométrique) :**
    *   Actuellement, le Cortex (LLM) envoie des vecteurs aléatoires fixes pour ses stratégies ("EXPLORE", "FOCUS"...).
    *   **L'évolution :** Utiliser les Embeddings d'Ollama.
    *   **Le but :** Que le LLM puisse nuancer ("Explorer vers la lumière", "Explorer avec peur") et que le Cervelet reçoive la "forme mathématique" exacte de cette pensée.

4.  **Le Bras / L'Agence (Futur) :**
    *   Une fois la vision active maîtrisée, ajouter une tige au moteur pour toucher ou pousser des objets.
    *   Objectif : Découvrir l'impact physique sur le monde.

## 🔮 Moyen / Long Terme

- [ ] **Mémoire Long Terme (Vectorielle) :**
    - Intégrer FAISS. Le LLM doit pouvoir dire "Tiens, cette situation me rappelle un souvenir stocké il y a 3 jours" et l'injecter dans le contexte du Cervelet.

- [ ] **Apprentissage Continue (Online Learning) :**
    - Tenter de stabiliser l'apprentissage pendant l'éveil (attention aux oublis catastrophiques).

## 🧪 Pistes Expérimentales

* **Douleur Sursaturée :** Que se passe-t-il si on sature la caméra de lumière (flash) ? Cela devrait-il être une punition pour protéger le capteur ?
* **Ennui :** Si la récompense de curiosité reste faible trop longtemps, l'agent doit générer des actions aléatoires plus fortes (Epsilon-Greedy dynamique).
