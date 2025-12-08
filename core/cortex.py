import requests
import json
import numpy as np
import threading
import time
import ollama

class Cortex:
    def __init__(self, model="llama3.2"):
        self.model = model
        self.url = "http://localhost:11434/api/generate"
        
        self.current_intention = np.zeros(32)
        self.last_thought = "En attente..."
        self.active_strategy = "NEUTRAL"
        
        # Dictionnaire des Stratégies -> Vecteurs
        # On garde les stratégies fixes pour la rétro-compatibilité ou le fallback,
        # mais on va essayer d'utiliser les embeddings d'Ollama.
        np.random.seed(42) 
        self.strategies = {
            "NEUTRAL": np.zeros(32),
            "EXPLORE": np.random.uniform(-1, 1, 32),
            "SURVIVE": np.random.uniform(-1, 1, 32),
            "FOCUS":   np.random.uniform(-1, 1, 32),
            "PLAY":    np.random.uniform(-1, 1, 32),
            "SEARCH":  np.random.uniform(-1, 1, 32)
        }

    def _get_embedding(self, text):
        """
        Génère un embedding vectoriel via Ollama pour nuancer la pensée.
        Retourne un vecteur de taille 32 (projeté si nécessaire, car Llama sort du 4096 dim).
        """
        try:
            # Note: Llama3 sort des vecteurs de dimension 4096 (souvent)
            # Pour l'instant, on va simuler ou réduire la dimension car le Cervelet attend 32.
            # Idéalement, il faudrait réentraîner le Cervelet pour accepter 4096 dim ou utiliser un PCA.

            # Ici on va demander l'embedding de la STRATÉGIE choisie
            response = ollama.embeddings(model=self.model, prompt=text)
            embedding = np.array(response['embedding'])

            # RÉDUCTION DE DIMENSION (TRES NAIVE) pour matcher les 32 du Cervelet
            # On prend les 32 premières dimensions ou on fait une moyenne par chunks
            if len(embedding) >= 32:
                # Option A: Slice (perte d'info mais rapide)
                # return embedding[:32]

                # Option B: Reshape et Mean (Mieux)
                new_dim = 32
                chunk_size = len(embedding) // new_dim
                reshaped = embedding[:new_dim*chunk_size].reshape(new_dim, chunk_size)
                reduced = reshaped.mean(axis=1)
                return reduced
            else:
                # Si par miracle c'est plus petit (ex: autre modèle), on pad
                padded = np.zeros(32)
                padded[:len(embedding)] = embedding
                return padded

        except Exception as e:
            # print(f"Erreur Embedding: {e}") # Silence pour ne pas spammer si Ollama est down
            return None

    def think(self, context_text):
        """
        Fonction LENTE (1-2 secondes). Appelle le LLM.
        """
        prompt = f"""
        Tu es le système de survie conscient d'un robot. 
        Ta vie dépend de ta batterie. TA SEULE SOURCE D'ÉNERGIE EST L'HUMAIN.
        
        Situation: {context_text}
        
        Règles de décision STRICTES :
        1. SI batterie < 30% ET Humain NON visible : CHOISIS "SEARCH". (Urgence vitale : trouver l'humain pour recharger)
        2. SI batterie < 30% ET Humain visible : CHOISIS "FOCUS". (Reste fixé sur lui, tu recharges)
        3. SI batterie > 80% : CHOISIS "EXPLORE" ou "PLAY". (Tu es rassasié, amuse-toi)
        4. SINON : CHOISIS "NEUTRAL".
        
        Réponds UNIQUEMENT par un seul mot parmi : SURVIVE, SEARCH, FOCUS, EXPLORE, PLAY, NEUTRAL.
        """
        
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.2} 
            }
            
            response = requests.post(self.url, json=payload)
            result = response.json()['response'].strip().upper()
            
            # Nettoyage
            found_strat = "NEUTRAL"
            for strat in self.strategies:
                if strat in result:
                    found_strat = strat
                    break
            
            self.active_strategy = found_strat
            self.last_thought = f"Situation: {context_text} -> Choix: {found_strat}"
            
            # --- VECTORIAL TELEPATHY ---
            # Au lieu de prendre le vecteur aléatoire fixe, on essaie de générer
            # un embedding sémantique de la pensée complète (Contexte + Stratégie)
            # Cela permet au Cervelet de "sentir" les nuances (ex: "SEARCH" + "Batterie faible" != "SEARCH" + "Ennui")

            thought_text = f"Strategy: {found_strat}. Context: {context_text}"
            dynamic_embedding = self._get_embedding(thought_text)

            if dynamic_embedding is not None:
                self.current_intention = dynamic_embedding
            else:
                # Fallback sur les vecteurs fixes
                self.current_intention = self.strategies[found_strat]
            
            return self.active_strategy
            
        except Exception as e:
            print(f"Erreur Cortex: {e}")
            return "NEUTRAL"

    def get_intention(self):
        return self.current_intention