import requests
import json
import numpy as np
import threading
import time

class Cortex:
    def __init__(self, model="llama3.2"):
        self.model = model
        self.url = "http://localhost:11434/api/generate"
        
        self.current_intention = np.zeros(32)
        self.last_thought = "En attente..."
        self.active_strategy = "NEUTRAL"
        
        # Dictionnaire des Stratégies -> Vecteurs
        np.random.seed(42) 
        self.strategies = {
            "NEUTRAL": np.zeros(32),
            "EXPLORE": np.random.uniform(-1, 1, 32),
            "SURVIVE": np.random.uniform(-1, 1, 32),
            "FOCUS":   np.random.uniform(-1, 1, 32),
            "PLAY":    np.random.uniform(-1, 1, 32),
            "SEARCH":  np.random.uniform(-1, 1, 32)  # <--- NOUVEAU VECTEUR
        }

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
            
            self.current_intention = self.strategies[found_strat]
            
            return self.active_strategy
            
        except Exception as e:
            print(f"Erreur Cortex: {e}")
            return "NEUTRAL"

    def get_intention(self):
        return self.current_intention