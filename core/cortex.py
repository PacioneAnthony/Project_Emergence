import requests
import json
import numpy as np
import threading
import time

class Cortex:
    def __init__(self, model="llama3.2"):
        self.model = model
        self.url = "http://localhost:11434/api/generate"
        
        # Le "Vecteur d'Intention" (32 dimensions)
        # C'est ce que le Cortex envoie au Cervelet.
        self.current_intention = np.zeros(32)
        
        # Les pensées du Cortex (pour le debug)
        self.last_thought = "En attente..."
        self.active_strategy = "NEUTRAL"
        
        # Dictionnaire des Stratégies -> Vecteurs
        # On crée des vecteurs aléatoires fixes pour chaque émotion/stratégie
        # Le Cervelet apprendra à associer ce "goût" vectoriel à une action.
        np.random.seed(42) # Seed fixe pour que les vecteurs ne changent pas à chaque reboot !
        self.strategies = {
            "NEUTRAL": np.zeros(32),
            "EXPLORE": np.random.uniform(-1, 1, 32), # Curiosité max
            "SURVIVE": np.random.uniform(-1, 1, 32), # Économie d'énergie
            "FOCUS":   np.random.uniform(-1, 1, 32), # Regarder fixement
            "PLAY":    np.random.uniform(-1, 1, 32)  # Interaction objet
        }

    def think(self, context_text):
        """
        Fonction LENTE (1-2 secondes). Appelle le LLM.
        """
        prompt = f"""
        Tu es le cortex conscient d'un robot. Analyse la situation et choisis UNE SEULE stratégie.
        
        Situation: {context_text}
        
        Stratégies possibles :
        - SURVIVE : Si batterie faible (< 20%) ou douleur/choc.
        - EXPLORE : Si batterie ok et rien de spécial à voir.
        - FOCUS : Si un humain ou un objet est détecté.
        - PLAY : Si tu te sens en sécurité et curieux.
        
        Réponds UNIQUEMENT par le mot de la stratégie. Rien d'autre.
        """
        
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.2} # Très déterministe
            }
            
            response = requests.post(self.url, json=payload)
            result = response.json()['response'].strip().upper()
            
            # Nettoyage basique (au cas où il bavarde un peu)
            found_strat = "NEUTRAL"
            for strat in self.strategies:
                if strat in result:
                    found_strat = strat
                    break
            
            self.active_strategy = found_strat
            self.last_thought = f"Situation: {context_text} -> Choix: {found_strat}"
            
            # Mise à jour du vecteur (C'est ça que le Cervelet lira)
            self.current_intention = self.strategies[found_strat]
            
            return self.active_strategy
            
        except Exception as e:
            print(f"Erreur Cortex: {e}")
            return "NEUTRAL"

    def get_intention(self):
        """
        Fonction RAPIDE (Appelée par la boucle 60Hz).
        Retourne le dernier vecteur décidé.
        """
        return self.current_intention