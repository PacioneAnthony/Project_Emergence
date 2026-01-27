#include <Stepper.h>

// Le 28BYJ-48 a 2048 pas par révolution
#define STEPS_PER_REV 2048

// Initialisation sur les pins 8, 10, 9, 11
// ATTENTION : L'ordre 8-10-9-11 est souvent nécessaire pour ce moteur spécifique avec cette librairie !
Stepper myStepper(STEPS_PER_REV, 8, 10, 9, 11);

String inputString = "";
boolean stringComplete = false;

// On garde en mémoire où on est (en degrés)
// IMPORTANT : Au démarrage, on suppose qu'on est au milieu (90°)
// Vous devrez centrer la caméra manuellement avant de brancher l'USB !
int currentAngle = 90;

void setup() {
  Serial.begin(9600);
  
  // Vitesse du moteur (max environ 15 RPM pour ce modèle)
  myStepper.setSpeed(10); 
  
  inputString.reserve(200);
}

void loop() {
  if (stringComplete) {
    int targetAngle = inputString.toInt();
    
    // Sécurité bornes
    if (targetAngle < 0) targetAngle = 0;
    if (targetAngle > 180) targetAngle = 180;
    
    // Calcul de la différence
    int diffAngle = targetAngle - currentAngle;
    
    if (diffAngle != 0) {
      // Conversion Angle -> Pas
      // 2048 pas = 360 degrés
      // donc 1 degré = ~5.688 pas
      int stepsToMove = diffAngle * 5.688;
      
      // Mouvement !
      myStepper.step(stepsToMove);
      
      // On met à jour notre position connue
      currentAngle = targetAngle;
    }
    
    inputString = "";
    stringComplete = false;
  }
}

void serialEvent() {
  while (Serial.available()) {
    char inChar = (char)Serial.read();
    inputString += inChar;
    if (inChar == '\n') {
      stringComplete = true;
    }
  }
}