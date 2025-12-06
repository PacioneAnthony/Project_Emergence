import torch
import torch.nn as nn
import torch.nn.functional as F

class ReflexActor(nn.Module):
    def __init__(self, input_dim, action_dim, hidden_dim=256):
        """
        Le réseau qui décide de l'action immédiate.
        input_dim : taille du vecteur sensoriel (vision + corps)
        action_dim : nombre de moteurs à contrôler
        """
        super(ReflexActor, self).__init__()
        
        # Architecture simple et rapide (MLP)
        self.layer1 = nn.Linear(input_dim, hidden_dim)
        self.layer2 = nn.Linear(hidden_dim, hidden_dim)
        self.output_layer = nn.Linear(hidden_dim, action_dim)
        
        # On déplace le modèle sur le GPU (RTX 5080) si dispo
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.to(self.device)

    def forward(self, state):
        """
        Passe avant : Sensoriel -> Action
        """
        # Assurer que l'état est un Tensor sur le bon device
        if not isinstance(state, torch.Tensor):
            state = torch.tensor(state, dtype=torch.float32).to(self.device)
            
        # Si on reçoit une seule entrée (pas de batch), on ajoute une dimension
        if state.dim() == 1:
            state = state.unsqueeze(0)

        # Propagation
        x = F.gelu(self.layer1(state)) # GELU est plus moderne que ReLU
        x = F.gelu(self.layer2(x))
        
        # Sortie Tanh pour borner les actions entre -1.0 (reculer) et +1.0 (avancer)
        action = torch.tanh(self.output_layer(x))
        
        return action

    def get_action(self, state_numpy):
        """
        Fonction utilitaire pour l'usage en temps réel (numpy -> torch -> numpy)
        """
        with torch.no_grad(): # Pas de calcul de gradient en mode inférence (plus rapide)
            action_tensor = self.forward(state_numpy)
            return action_tensor.cpu().numpy().flatten()
    
    def save_model(self, filename="actor.pth"):
        torch.save(self.state_dict(), filename)
        print(f"Cerveau (Acteur) sauvegardé dans {filename}")

    def load_model(self, filename="actor.pth"):
        import os
        if os.path.exists(filename):
            self.load_state_dict(torch.load(filename))
            print(f"Cerveau (Acteur) chargé depuis {filename}")
        else:
            print("Aucun cerveau existant trouvé. Démarrage à neuf.")
        
class ReflexCritic(nn.Module):
    def __init__(self, input_dim, action_dim, hidden_dim=256):
        """
        Le Critique : Estime la qualité (Q-Value) d'une action dans un état donné.
        Input : État + Action
        Output : Score (Scalar)
        """
        super(ReflexCritic, self).__init__()
        
        # On concatène l'état et l'action en entrée
        self.layer1 = nn.Linear(input_dim + action_dim, hidden_dim)
        self.layer2 = nn.Linear(hidden_dim, hidden_dim)
        self.output_layer = nn.Linear(hidden_dim, 1) # Sort un seul chiffre (le score)
        
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.to(self.device)

    def forward(self, state, action):
        # Concaténation
        x = torch.cat([state, action], dim=1)
        
        x = F.gelu(self.layer1(x))
        x = F.gelu(self.layer2(x))
        q_value = self.output_layer(x)
        
        return q_value
    
    def save_model(self, filename="critic.pth"):
        torch.save(self.state_dict(), filename)
        print(f"Cerveau (Critique) sauvegardé dans {filename}")

    def load_model(self, filename="critic.pth"):
        import os
        if os.path.exists(filename):
            self.load_state_dict(torch.load(filename))
            print(f"Cerveau (Critique) chargé depuis {filename}")
        else:
            print("Aucun cerveau existant trouvé. Démarrage à neuf.")