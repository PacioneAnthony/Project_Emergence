#include <Servo.h>

Servo myServo;
String inputString = "";         // Pour stocker la commande reçue
boolean stringComplete = false;  // Pour savoir si la commande est finie

void setup() {
  Serial.begin(9600);
  myServo.attach(9); 
  myServo.write(90); // Position centrale au démarrage
  inputString.reserve(200);
}

void loop() {
  // Si on a reçu une nouvelle ligne (ex: "45\n")
  if (stringComplete) {
    int angle = inputString.toInt(); // On convertit en nombre
    
    // Sécurité mécanique (on limite entre 10 et 170 pour pas forcer)
    if (angle < 10) angle = 10;
    if (angle > 170) angle = 170;
    
    myServo.write(angle);
    
    // On vide la mémoire pour la prochaine commande
    inputString = "";
    stringComplete = false;
  }
}

// Interruption automatique quand des données arrivent
void serialEvent() {
  while (Serial.available()) {
    char inChar = (char)Serial.read();
    inputString += inChar;
    if (inChar == '\n') {
      stringComplete = true;
    }
  }
}