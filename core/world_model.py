import torch
import torch.nn as nn
import torch.nn.functional as F

class WorldModel(nn.Module):
    def __init__(self, input_dim, action_dim, hidden_dim=256):
        """
        Le Modèle du Monde (Forward Model - JEPA inspired).
        Prédit l'état latent futur à partir de l'état latent actuel et de l'action choisie,
        sans reconstruire les pixels.

        input_dim : taille du vecteur d'état latent (vision + audio + corps + intention)
        action_dim : nombre de moteurs à contrôler
        """
        super(WorldModel, self).__init__()

        # Architecture simple et rapide (MLP)
        # On concatène l'état (input_dim) et l'action (action_dim) en entrée
        self.layer1 = nn.Linear(input_dim + action_dim, hidden_dim)
        self.layer2 = nn.Linear(hidden_dim, hidden_dim)
        self.output_layer = nn.Linear(hidden_dim, input_dim) # La sortie a la même dimension que l'état

        # On déplace le modèle sur le GPU si disponible
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.to(self.device)

    def forward(self, state, action):
        """
        Passe avant : État Actuel + Action -> État Futur Prédit
        """
        # Assurer que l'état et l'action sont des Tenseurs sur le bon device
        if not isinstance(state, torch.Tensor):
            state = torch.tensor(state, dtype=torch.float32).to(self.device)
        if not isinstance(action, torch.Tensor):
            action = torch.tensor(action, dtype=torch.float32).to(self.device)

        # Si on reçoit une seule entrée (pas de batch), on ajoute une dimension
        if state.dim() == 1:
            state = state.unsqueeze(0)
        if action.dim() == 1:
            action = action.unsqueeze(0)

        # Concaténation de l'état et de l'action
        x = torch.cat([state, action], dim=1)

        # Propagation (GELU est souvent plus performant que ReLU)
        x = F.gelu(self.layer1(x))
        x = F.gelu(self.layer2(x))
        predicted_next_state = self.output_layer(x)

        return predicted_next_state

    def save_model(self, filename="world_model.pth"):
        """Sauvegarde les poids du modèle."""
        torch.save(self.state_dict(), filename)
        print(f"Modèle du monde (WorldModel) sauvegardé dans {filename}")

    def load_model(self, filename="world_model.pth"):
        """Charge les poids du modèle s'ils existent."""
        from core.models import load_with_partial_fallback
        load_with_partial_fallback(self, filename)
