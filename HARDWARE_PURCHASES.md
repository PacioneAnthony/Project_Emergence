# Émergence - Achats matériels

Dernière mise à jour: 2026-06-11

## P-001 - Vérité terrain d'angle AS5600

Statut: `validation Anthony demandée`  
Besoin: J1a, non bloquant pour l'essai court J0  
Recommandation Codex: acheter un kit officiel `AS5600-SO_EK_AB` comprenant la carte adaptatrice AS5600 et l'aimant de référence `AS5000-MD6H-1`.

### Pourquoi ce choix

- mesure absolue sans contact sur 360 degrés;
- résolution 12 bits et interface I2C;
- alimentation 3,3 V ou 5 V compatible avec le banc Arduino Mega;
- carte déjà assemblée avec composants externes et connecteur 2,54 mm;
- aimant diamétral de référence inclus, ce qui évite le principal risque d'un module générique livré avec un aimant axial inadapté;
- usage limité à la vérité terrain de banc: le capteur ne remplace pas l'IMU et ne devient pas une entrée obligatoire du robot final.

### Contraintes de montage

- aimant diamétral centré sur l'axe du cou;
- aimant solidaire de la partie rotative et capteur solidaire de la base, ou inversement;
- entrefer initial visé: 0,5 à 2,5 mm;
- support d'aimant non ferromagnétique;
- alignement vérifié avec le registre AGC avant calibration;
- aucun collage définitif avant lecture stable sur toute la plage 10 à 170 degrés.

### Budget indicatif

DigiKey affichait le kit autour de 19,40 USD hors port et taxes lors de la préparation. Le prix livré en France doit être vérifié au moment de la commande. Un module générique moins cher reste possible, mais seulement s'il inclut explicitement un aimant **diamétral** adapté et expose I2C, VDD et GND.

### Références

- [Produit AS5600 officiel](https://ams-osram.com/products/sensor-solutions/position-sensors/ams-as5600-position-sensor)
- [Manuel du kit AS5600-SO_EK_AB](https://look.ams-osram.com/m/4f8342513a447495/original/AS5600_UG000254_2-00.pdf)
- [Fiche DigiKey du kit](https://www.digikey.com/en/products/detail/ams-osram-usa-inc/AS5600-SO-EK-AB/5066879)

### Décision attendue d'Anthony

Valider l'achat du kit officiel, demander une alternative moins chère, ou différer l'achat jusqu'après l'essai court J0.

