import requests
import json
import numpy as np

class Cortex:
    def __init__(self, model="qwen2.5:7b"): # Ou qwen2.5:7b si tu as changé
        self.model = model
        self.url_embeddings = "http://localhost:11434/api/embeddings"
        
        self.current_intention = np.zeros(32)
        self.last_thought = "Initialisation latente..."

    def think(self, context_text):
        """
        Génère un vecteur sémantique (Embedding) de la situation actuelle.
        Aucun "texte" n'est produit, on utilise les couches internes du LLM.
        """
        try:
            payload = {
                "model": self.model,
                "prompt": context_text
            }
            
            # On demande directement l'accès aux couches d'embedding
            response = requests.post(self.url_embeddings, json=payload)
            data = response.json()
            
            if 'embedding' in data:
                embedding = np.array(data['embedding'])
                
                # --- RÉDUCTION DE DIMENSION (Pour le cervelet) ---
                # Llama/Qwen sortent souvent 4096 dimensions. On condense en 32.
                new_dim = 32
                chunk_size = len(embedding) // new_dim
                reshaped = embedding[:new_dim*chunk_size].reshape(new_dim, chunk_size)
                reduced_embedding = reshaped.mean(axis=1)
                
                self.current_intention = reduced_embedding
                
                # Pour le debug, on affiche un résumé du vecteur (sa magnitude)
                magnitude = np.linalg.norm(reduced_embedding)
                self.last_thought = f"Vecteur Latent | Magnitude: {magnitude:.3f}"
                
            elif 'error' in data:
                print(f"  [X] Ollama API Error: {data['error']}")
                self.last_thought = "Erreur LLM"
                
        except Exception as e:
            self.last_thought = "Déconnexion Cortex"
            
        return self.last_thought

    def get_intention(self):
        return self.current_intention