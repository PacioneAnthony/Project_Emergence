import numpy as np

class HomeostaticSystem:
    def __init__(self, config):
        """
        Gère l'état interne du corps (batterie, température, intégrité).
        """
        # Paramètres idéaux (Point de confort)
        self.targets = {
            "energy": 1.0,      # 100% batterie
            "integrity": 1.0,   # 100% pas de collision/dégâts
            "temperature": 0.4, # ~40% de la charge thermique max
        }
        
        # État actuel (initialisé à l'idéal)
        self.current_state = self.targets.copy()
        
        # Sensibilité à la douleur (poids de chaque variable)
        self.sensitivities = config.get("homeostasis_weights", {
            "energy": 2.0,      # La faim
            "integrity": 5.0,   # La douleur physique
            "temperature": 1.0
        })

    def update_state(self, sensor_data):
        """
        Met à jour l'état interne via les capteurs bruts.
        sensor_data: dict contenant 'battery_level', 'collision_impact', 'gpu_temp'
        """
        self.current_state["energy"] = sensor_data.get("battery_level", self.current_state["energy"])
        
        # L'intégrité baisse si collision
        impact = sensor_data.get("collision_impact", 0.0)
        self.current_state["integrity"] -= impact 
        self.current_state["integrity"] = max(0.0, self.current_state["integrity"]) # Clamp à 0
        
        # Température normalisée (0.0 = froid, 1.0 = surchauffe)
        self.current_state["temperature"] = sensor_data.get("gpu_temp", 0.4)

    def compute_homeostatic_reward(self):
        """
        Calcule la 'douleur' ou le 'confort'. 
        Retourne une valeur négative (douleur) ou proche de 0 (confort).
        """
        penalty = 0.0
        details = {}
        
        for key, target in self.targets.items():
            val = self.current_state[key]
            weight = self.sensitivities[key]
            
            # Calcul de l'écart au carré
            dist = (val - target) ** 2
            term_penalty = - (weight * dist)
            
            penalty += term_penalty
            details[key] = term_penalty
            
        return penalty, details


class RewardSystem:
    def __init__(self, config):
        self.homeostasis = HomeostaticSystem(config)
        
        # Pondération globale des 3 pulsions
        self.w_homeostasis = 1.0
        self.w_curiosity = 2.5
        self.w_social = 2.0
        
    def get_reward(self, sensor_data, world_model_error, social_signal):
        """
        Fonction maîtresse appelée à chaque tick.
        """
        # 1. Mise à jour du corps
        self.homeostasis.update_state(sensor_data)
        
        # 2. Calcul des composantes
        r_homeo, homeo_details = self.homeostasis.compute_homeostatic_reward()
        
        # Curiosité
        r_curiosity = np.clip(world_model_error, 0, 1.0)
        
        # Social
        r_social = social_signal 

        # 3. Agrégation
        total = (self.w_homeostasis * r_homeo) + \
                (self.w_curiosity * r_curiosity) + \
                (self.w_social * r_social)
        
        return total, {"H": r_homeo, "C": r_curiosity, "S": r_social, "details": homeo_details}