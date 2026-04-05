import torch
import torch.nn as nn
import torch.nn.functional as F

import os

def load_with_partial_fallback(model, filename):
    if not os.path.exists(filename):
        print(f"[i] Aucun fichier trouvé pour {filename}. Initialisation à neuf.")
        return

    try:
        saved_state = torch.load(filename, map_location=model.device)
        model_state = model.state_dict()

        matched_weights = 0
        total_weights = len(model_state)

        for name, param in saved_state.items():
            if name in model_state:
                if param.shape == model_state[name].shape:
                    model_state[name].copy_(param)
                    matched_weights += 1
                else:
                    print(f"  [!] Dimension mismatch pour {name}: saved {param.shape} != model {model_state[name].shape}. Ignoré.")

        model.load_state_dict(model_state)
        print(f"[V] Modèle chargé depuis {filename} ({matched_weights}/{total_weights} couches correspondantes).")
    except Exception as e:
        print(f"[X] Erreur lors du chargement de {filename}: {e}. Le modèle utilisera des poids aléatoires.")

class SomatosensoryEncoder(nn.Module):
    """
    Encode les données brutes du corps (Arduino, etc.) en un espace latent.
    """
    def __init__(self, input_dim=7, output_dim=64):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 32),
            nn.GELU(),
            nn.Linear(32, output_dim)
        )
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.to(self.device)

    def forward(self, x):
        if not isinstance(x, torch.Tensor):
            x = torch.tensor(x, dtype=torch.float32).to(self.device)
        if x.dim() == 1:
            x = x.unsqueeze(0)
        return self.net(x)

class VisionEncoder(nn.Module):
    """
    Placeholder pour l'encodeur visuel.
    """
    def __init__(self, input_dim=128, output_dim=64):
        super().__init__()
        self.output_dim = output_dim
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    def forward(self, x):
        # Pour l'instant, on ignore l'entrée et on retourne des zéros
        batch_size = x.shape[0] if isinstance(x, torch.Tensor) and x.dim() > 1 else 1
        return torch.zeros((batch_size, self.output_dim)).to(self.device)

class AudioEncoder(nn.Module):
    """
    Placeholder pour l'encodeur audio.
    """
    def __init__(self, input_dim=64, output_dim=64):
        super().__init__()
        self.output_dim = output_dim
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    def forward(self, x):
        batch_size = x.shape[0] if isinstance(x, torch.Tensor) and x.dim() > 1 else 1
        return torch.zeros((batch_size, self.output_dim)).to(self.device)

class IntentionEncoder(nn.Module):
    """
    Encode le vecteur d'intention du Cortex en espace latent.
    """
    def __init__(self, input_dim=32, output_dim=64):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, output_dim),
            nn.GELU()
        )
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.to(self.device)

    def forward(self, x):
        if not isinstance(x, torch.Tensor):
            x = torch.tensor(x, dtype=torch.float32).to(self.device)
        if x.dim() == 1:
            x = x.unsqueeze(0)
        return self.net(x)
