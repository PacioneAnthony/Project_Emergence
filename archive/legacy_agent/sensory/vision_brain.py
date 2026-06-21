import torch
import torch.nn as nn
from ultralytics import YOLO
import numpy as np
import cv2
import zmq

class DeepVision:
    def __init__(self):
        print("Chargement de la Deep Vision (Hybrid)...")
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        
        # 1. Le Modèle Complet (pour la détection Humain/Batterie)
        self.full_model = YOLO('yolov8n.pt')
        
        # 2. Le "Backbone" (pour l'extraction de sens profond)
        # On prend les couches internes du modèle pour avoir la "représentation" de l'image
        self.backbone = self.full_model.model.model[:9] 
        self.backbone.to(self.device)
        
        # 3. L'Adaptateur (Ce qui va apprendre VOS gestes)
        # Il compresse les features de YOLO (taille variable) en un vecteur fixe de 128
        self.adapter = nn.Sequential(
            nn.AdaptiveAvgPool2d((1, 1)),
            nn.Flatten(),
            nn.Linear(256, 128), # 256 est la sortie typique du backbone v8n
            nn.Tanh() # Pour borner entre -1 et 1
        ).to(self.device)
        
        # Réseau (Réception image brute de Windows)
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.setsockopt_string(zmq.SUBSCRIBE, '')
        self.socket.setsockopt(zmq.CONFLATE, 1)
        
        try:
            import os
            stream = os.popen("ip route list default | awk '{print $3}'")
            host_ip = stream.read().strip()
            self.socket.connect(f"tcp://{host_ip}:5555")
            print(f"  [V] Nerf Optique connecté sur {host_ip}:5555")
        except:
            print("  [X] Erreur réseau vision")

    def see(self):
        """
        Retourne : 
        1. deep_vector (np.array 128) -> Pour le Cervelet (Mouvement)
        2. human_info (tuple) -> (Est_visible?, Position_X) -> Pour le Cortex/Batterie
        3. frame (img) -> Pour l'affichage
        """
        try:
            if self.socket.poll(10) == 0:
                return None, (False, None), None
            
            jpg_buffer = self.socket.recv()
            np_arr = np.frombuffer(jpg_buffer, dtype=np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            
            if frame is None: return None, (False, None), None

            # --- A. VISION PROFONDE (Pour le Cervelet) ---
            # Prétraitement image pour PyTorch
            img_tensor = torch.from_numpy(frame).to(self.device).float() / 255.0
            img_tensor = img_tensor.permute(2, 0, 1).unsqueeze(0) 
            img_tensor = torch.nn.functional.interpolate(img_tensor, size=(128, 128)) # Resize rapide

            with torch.no_grad(): # On n'entraîne pas le backbone YOLO, juste l'adaptateur
                features = self.backbone(img_tensor)
                
            # Passage dans l'adaptateur (C'est lui qu'on entraînera la nuit !)
            latent_vector = self.adapter(features).cpu().detach().numpy()[0]

            # --- B. VISION CLASSIQUE (Pour la Batterie/Cortex) ---
            # On fait une détection rapide pour savoir s'il y a un humain
            # (Car le vecteur profond ne nous le dit pas explicitement au début)
            results = self.full_model(frame, device=self.device, verbose=False, half=True, classes=[0]) # Classe 0 = Person
            
            human_detected = False
            human_x = None
            
            if len(results[0].boxes) > 0:
                human_detected = True
                # On prend le centre X du premier humain détecté
                human_x = results[0].boxes.xywhn[0, 0].item()

            return latent_vector, (human_detected, human_x), frame

        except Exception as e:
            # print(f"Vision Error: {e}")
            return None, (False, None), None

    def save_adapter(self, path="vision_adapter.pth"):
        torch.save(self.adapter.state_dict(), path)
        
    def load_adapter(self, path="vision_adapter.pth"):
        import os
        if os.path.exists(path):
            self.adapter.load_state_dict(torch.load(path))
            print("  [V] Adaptateur visuel chargé.")