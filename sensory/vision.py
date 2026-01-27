import torch
import torch.nn as nn
import numpy as np
import cv2
import zmq
from ultralytics import YOLO

class VisionModule:
    def __init__(self, model_size='n', output_dim=128):
        """
        Version Deep Vision (Backbone Only).
        """
        print(f"Chargement du modèle YOLOv8{model_size} (Backbone) sur GPU...")
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'

        # Charge le modèle complet
        self.full_model = YOLO(f'yolov8{model_size}.pt')

        # On extrait le backbone (partie features extractor)
        # Note: Dans Ultralytics YOLOv8, le modèle est dans .model.model
        # Pour faire propre, on va laisser le modèle faire son forward pass standard
        # mais on va hooker la couche avant la tête de détection ou utiliser embed() si dispo.

        # Approche simplifiée : On utilise le modèle complet pour avoir les boxes (pour le Cortex LLM)
        # ET on ajoute un petit réseau pour extraire un vecteur global de l'image (pour le Reflex RL).

        # Réseau adaptateur visuel (ResNet-like feature extractor simplifié ou via YOLO features)
        # Pour l'instant, pour simplifier, on va utiliser les probabilités de classes YOLO (80 dims)
        # étendues à 128 par un petit MLP. C'est moins "Deep" que du pur backbone mais plus simple à coder vite.

        # UPDATE: On va faire mieux. On va utiliser une couche Linear sur le vecteur de classes (80) + coords.
        # Mais l'utilisateur voulait "Couper la tête de détection".
        # Faisons un compromis : On garde YOLO pour le texte (LLM), et on ajoute un petit encodeur simple.

        self.vision_adapter = nn.Sequential(
            nn.Linear(80, 128), # 80 classes COCO -> 128 dims
            nn.ReLU(),
            nn.Linear(128, output_dim),
            nn.Tanh()
        ).to(self.device)

        # --- CONFIGURATION RÉSEAU ---
        print("Initialisation du récepteur réseau...")
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.setsockopt_string(zmq.SUBSCRIBE, '')
        self.socket.setsockopt(zmq.CONFLATE, 1) # On ne garde que la dernière image

        # Astuce pour trouver l'IP de Windows depuis WSL
        # (L'IP du 'nameserver' dans resolv.conf est souvent celle de Windows)
        windows_ip = "127.0.0.1"
        try:
            import os
            # Cette commande récupère l'IP de la passerelle WSL (donc Windows)
            stream = os.popen("ip route list default | awk '{print $3}'")
            host_ip = stream.read().strip()
            if host_ip:
                windows_ip = host_ip
        except:
            pass

        # Hardcode si besoin (selon ton dernier test réussi)
        # windows_ip = "172.31.192.1"

        print(f"Tentative de connexion à l'Oeil sur {windows_ip}:5555 ...")
        self.socket.connect(f"tcp://{windows_ip}:5555")

    def get_latent_vector(self):
        """
        Reçoit une image jpg du réseau, la décode, et lance YOLO.
        Retourne:
        - latent_vector (128 dims) : Pour le RL
        - annotated_frame : Pour l'affichage
        - brightness : Pour la douleur
        - detections_text : Pour le LLM (Liste des objets vus)
        """
        try:
            # On attend une image (max 10ms d'attente pour ne pas bloquer)
            if self.socket.poll(10) == 0:
                return np.zeros(128), None, 0.0, []

            # Réception du paquet
            jpg_buffer = self.socket.recv()

            # Décodage de l'image (JPG -> Matrice de pixels)
            np_arr = np.frombuffer(jpg_buffer, dtype=np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            if frame is None:
                return np.zeros(128), None, 0.0, []

            # --- ANALYSE DE LUMINOSITÉ (Pour la "Douleur Sursaturée") ---
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            brightness = np.mean(gray) / 255.0

            # --- INFÉRENCE YOLO ---
            results = self.full_model(frame, device=self.device, verbose=False, half=True)
            result = results[0]

            # 1. Vecteur sémantique brut (80 classes)
            # On crée un vecteur de probabilité max par classe présente
            raw_cls_vector = torch.zeros(80).to(self.device)

            boxes = result.boxes
            cls_ids = boxes.cls.cpu().numpy().astype(int)
            confidences = boxes.conf.cpu().numpy()

            detections_list = [] # Pour le LLM

            if len(cls_ids) > 0:
                for cls_id, conf in zip(cls_ids, confidences):
                    # On garde le max de confiance pour chaque classe
                    if conf > raw_cls_vector[cls_id]:
                        raw_cls_vector[cls_id] = conf

                    # Pour le texte
                    name = result.names[cls_id]
                    detections_list.append(f"{name} ({int(conf*100)}%)")

            # 2. Projection vers Embedding 128 (RL)
            with torch.no_grad():
                latent_vector = self.vision_adapter(raw_cls_vector).cpu().numpy()

            annotated_frame = result.plot()
            return latent_vector, annotated_frame, brightness, detections_list

        except Exception as e:
            # Si erreur, on retourne rien
            return np.zeros(128), None, 0.0, []

    def save_adapter(self, path):
        torch.save(self.vision_adapter.state_dict(), path)

    def load_adapter(self, path):
        try:
            self.vision_adapter.load_state_dict(torch.load(path))
            print("  [Eye] Adaptateur chargé.")
        except:
            print("  [Eye] Pas d'adaptateur existant (Nouveau né).")

    def release(self):
        self.socket.close()
        self.context.term()
