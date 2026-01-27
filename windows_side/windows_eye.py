import cv2
import zmq
import time

print("--- INITIALISATION DE L'OEIL (WINDOWS) ---")

# 1. Connexion au réseau (Serveur ZMQ)
context = zmq.Context()
socket = context.socket(zmq.PUB)
# On ouvre le port 5555 pour que Linux puisse s'y connecter
socket.bind("tcp://0.0.0.0:5555") 
print("Flux vidéo diffusé sur le port 5555...")

# 2. Ouverture Caméra
# 0 est généralement la webcam par défaut. Si ça ne marche pas, essayez 1.
cap = cv2.VideoCapture(0)

# Optimisation (30 FPS, 640x480)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
cap.set(cv2.CAP_PROP_FPS, 30)

if not cap.isOpened():
    print("ERREUR : Impossible d'ouvrir la caméra.")
    exit()

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        # 3. Compression JPG (Vital pour la vitesse réseau)
        # On compresse l'image à 80% de qualité avant l'envoi
        encoded, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        
        # 4. Envoi vers Linux
        socket.send(buffer)
        
        # Affichage local pour vérifier que Windows voit bien
        cv2.imshow("Windows Eye (Server)", frame)
        
        # Appuyez sur 'q' pour quitter
        if cv2.waitKey(1) == ord('q'):
            break
            
except KeyboardInterrupt:
    pass
finally:
    cap.release()
    cv2.destroyAllWindows()
    print("Fermeture de l'oeil.")