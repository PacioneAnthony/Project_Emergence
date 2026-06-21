import torch
import torch.nn as nn
import numpy as np
import whisper

class AudioEar(nn.Module):
    def __init__(self, model_size="base", output_dim=64):
        super().__init__()
        print(f"  [Ear] Chargement du modèle Whisper '{model_size}'...")
        self.model = whisper.load_model(model_size)

        # On gèle le modèle Whisper (on ne veut pas le détruire par rétropropagation)
        for param in self.model.parameters():
            param.requires_grad = False

        # Dimension de sortie de l'encodeur Whisper (base = 512)
        whisper_dim = self.model.dims.n_audio_state

        # Petit réseau de compression pour le RL (512 -> 64)
        self.compressor = nn.Sequential(
            nn.Linear(whisper_dim, 128),
            nn.ReLU(),
            nn.Linear(128, output_dim),
            nn.Tanh() # Pour normaliser entre -1 et 1
        )

        print(f"  [Ear] Oreille prête. Sortie compressée : {output_dim} dims")

    def listen(self, audio_array):
        """
        Traite un bout de son (array numpy) et retourne :
        - embedding (64 floats) : Pour le Cervelet (Reflexes)
        - volume (float) : Pour la peur/sursaut
        - text (str) : Pour le Cortex (Contexte sémantique)
        """
        if audio_array is None or len(audio_array) < 100:
            return np.zeros(64), 0.0, ""

        # 1. Volume (RMS)
        volume = np.sqrt(np.mean(audio_array**2))

        # 2. Transcriptions (Sémantique)
        # Note: Whisper attend 30s d'audio à 16kHz idéalement.
        # Ici on fait du "hack" temps réel sur des petits bouts, la qualité du texte sera moyenne.
        audio_tensor = torch.from_numpy(audio_array.astype(np.float32))

        # Pad or trim to 30 seconds
        audio_tensor = whisper.pad_or_trim(audio_tensor)
        mel = whisper.log_mel_spectrogram(audio_tensor).to(self.model.device)

        # A. Embedding (Deep Hearing)
        with torch.no_grad():
            # L'encodeur sort [1, 1500, 512]. On fait un Average Pooling temporel.
            features = self.model.encoder(mel.unsqueeze(0))
            pooled_features = features.mean(dim=1) # [1, 512]

            embedding = self.compressor(pooled_features).cpu().numpy().flatten()

        # B. Texte (Si volume suffisant, sinon c'est du bruit)
        text = ""
        if volume > 0.05:
            # On décode (lent !) - Peut-être à mettre dans un thread séparé si ça lag trop
            # options = whisper.DecodingOptions(fp16=False)
            # result = whisper.decode(self.model, mel, options)
            # text = result.text
            pass # Désactivé par défaut pour latence < 50ms

        return embedding, volume, text

    def save_adapter(self, path):
        torch.save(self.compressor.state_dict(), path)

    def load_adapter(self, path):
        try:
            self.compressor.load_state_dict(torch.load(path))
            print("  [Ear] Adaptateur chargé.")
        except:
            print("  [Ear] Pas d'adaptateur existant (Nouveau né).")
