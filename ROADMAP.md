# 🗺️ Roadmap & Pistes d'Exploration

État actuel : **Stade "Babillage Corporel" (Body Babbling)**.
L'agent sait bouger, voir, et ressentir la fatigue et la curiosité visuelle simple.

## 🎯 Court Terme (La Semaine)

- [ ] **Vision Active (Le Cou) :**
    - Fixer physiquement la caméra sur le servo-moteur.
    - Objectif : L'agent doit apprendre que "Bouger le moteur = Changer la vue = Récompense Curiosité".
    - Cela fermera la boucle sensorimotrice.

- [ ] **L'Agence (La Main) :**
    - Ajouter une tige au servo pour qu'il puisse interagir avec un objet léger (balle, étiquette).
    - Objectif : Découvrir qu'il peut modifier son environnement, pas juste l'observer.

- [ ] **Mémoire Visuelle Améliorée :**
    - Remplacer le vecteur YOLO (catégories) par un vecteur d'embedding sémantique (CLIP ou SigLIP).
    - Cela permettra de distinguer "ce chat" de "ce chien", et pas juste "animal".

## 🔮 Moyen Terme (Le Mois)

- [ ] **Architecture Bicamérale (Système 1 / Système 2) :**
    - **Système 1 (Rapide) :** La Policy Réflexe actuelle. Elle gère l'action immédiate.
    - **Système 2 (Lent) :** Le LLM. Il tourne en tâche de fond pendant l'éveil.
    - **Dialogue :** Le Système 1 envoie des alertes ("Je suis bloqué", "Douleur inconnue") au LLM. Le LLM répond par des injections vectorielles ("Contexte : Explore à droite", "Contexte : Calme-toi").

- [ ] **Intégration LLM Local (Llama-3 ou Mistral) :**
    - Faire tourner un petit LLM (quantisé 4-bit) sur la même machine.
    - Créer un pont asynchrone pour que le ralentissement du LLM ne bloque pas les réflexes moteurs (latence < 20ms maintenue pour le corps).

- [ ] **Mémoire Long Terme (Vectorielle) :**
    - Intégrer FAISS. Le LLM doit pouvoir dire "Tiens, cette situation me rappelle un souvenir stocké il y a 3 jours" et l'injecter dans le contexte du Cervelet.

## 🧪 Pistes Expérimentales

* **Douleur Sursaturée :** Que se passe-t-il si on sature la caméra de lumière (flash) ? Cela devrait-il être une punition pour protéger le capteur ?
* **Ennui :** Si la récompense de curiosité reste faible trop longtemps, l'agent doit générer des actions aléatoires plus fortes (Epsilon-Greedy dynamique).