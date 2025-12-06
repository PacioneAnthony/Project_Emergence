import torch
import numpy as np
import cv2
import zmq
from ultralytics import YOLO

class VisionModule:
    def __init__(self, model_size='n'):
        """
        Version Client Réseau : Reçoit les images depuis Windows via ZeroMQ.
        """
        print(f"Chargement du modèle YOLOv8{model_size} sur GPU...")
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        self.model = YOLO(f'yolov8{model_size}.pt') 
        
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
            
        print(f"Tentative de connexion à l'Oeil sur {windows_ip}:5555 ...")
        self.socket.connect(f"tcp://{windows_ip}:5555")
        
    def get_latent_vector(self):
        """
        Reçoit une image jpg du réseau, la décode, et lance YOLO.
        """
        try:
            # On attend une image (max 10ms d'attente pour ne pas bloquer)
            if self.socket.poll(10) == 0:
                return np.zeros(64), None
                
            # Réception du paquet
            jpg_buffer = self.socket.recv()
            
            # Décodage de l'image (JPG -> Matrice de pixels)
            np_arr = np.frombuffer(jpg_buffer, dtype=np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
            
            if frame is None:
                return np.zeros(64), None

            # --- INFÉRENCE YOLO (Sur la RTX 5080) ---
            results = self.model(frame, device=self.device, verbose=False, half=True)
            result = results[0]
            
            # Création du vecteur
            boxes = result.boxes
            cls_ids = boxes.cls.cpu().numpy().astype(int)
            confidences = boxes.conf.cpu().numpy()
            
            latent_vector = np.zeros(64, dtype=np.float32)
            for cls_id, conf in zip(cls_ids, confidences):
                if cls_id < 64:
                    latent_vector[cls_id] = conf
                    
            annotated_frame = result.plot()
            return latent_vector, annotated_frame
            
        except Exception as e:
            # Si erreur, on retourne rien (pour éviter le crash)
            return np.zeros(64), None

    def release(self):
        self.socket.close()
        self.context.term()