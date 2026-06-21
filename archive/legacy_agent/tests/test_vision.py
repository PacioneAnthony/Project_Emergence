import time
import cv2
import numpy as np
from sensory.vision import VisionModule

print("--- INITIALISATION VISION ---")
eye = VisionModule(model_size='n') 

print("Appuyez sur 'q' dans la fenêtre vidéo pour quitter.")

# On garde en mémoire la dernière image vue pour ne pas avoir d'écran noir
last_frame = None

try:
    while True:
        start = time.perf_counter()
        
        # 1. L'agent regarde
        latent, frame = eye.get_latent_vector()
        
        # 2. Gestion de l'image
        if frame is not None:
            # Si on a une nouvelle image, on met à jour
            last_frame = frame
            status = "DIRECT"
        else:
            # Si pas de nouvelle image, on garde l'ancienne (si elle existe)
            status = "MEMOIRE"
        
        # 3. Affichage ET Sauvegarde
        if last_frame is not None:
            display_frame = last_frame.copy()
            
            color = (0, 255, 0) if status == "DIRECT" else (0, 0, 255)
            cv2.putText(display_frame, f"Mode: {status}", (10, 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            
            # --- TEST DE VIE : ON SAUVEGARDE UNE IMAGE ---
            # Si le fichier "preuve_de_vie.jpg" apparait dans votre dossier, c'est gagné.
            cv2.imwrite("preuve_de_vie.jpg", display_frame)
            # ---------------------------------------------

            cv2.imshow("Vue de l'Agent", display_frame)
            
        # 4. Rafraîchissement fenêtre (CRITIQUE : Doit être hors du 'if')
        # C'est ça qui empêche la fenêtre de devenir fantôme
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

except KeyboardInterrupt:
    pass
finally:
    eye.release()
    cv2.destroyAllWindows()
    print("Extinction.")