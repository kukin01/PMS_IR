#include <SPI.h>
#include <MFRC522.h>

#define SS_PIN 10
#define RST_PIN 9

MFRC522 mfrc522(SS_PIN, RST_PIN);
MFRC522::MIFARE_Key key;

void setup() {
  Serial.begin(9600);
  SPI.begin();
  mfrc522.PCD_Init();
  Serial.println("Scan a card to write plate and balance...");

  // Default key for authentication
  for (byte i = 0; i < 6; i++) key.keyByte[i] = 0xFF;
}

// Function to write 16 bytes to a block after authentication
bool writeBlock(byte block, byte *data) {
  MFRC522::StatusCode status = mfrc522.PCD_Authenticate(
    MFRC522::PICC_CMD_MF_AUTH_KEY_A, block, &key, &(mfrc522.uid)
  );
  if (status != MFRC522::STATUS_OK) {
    Serial.print("Authentication failed for block ");
    Serial.print(block);
    Serial.print(": ");
    Serial.println(mfrc522.GetStatusCodeName(status));
    return false;
  }

  status = mfrc522.MIFARE_Write(block, data, 16);
  if (status != MFRC522::STATUS_OK) {
    Serial.print("Write failed for block ");
    Serial.print(block);
    Serial.print(": ");
    Serial.println(mfrc522.GetStatusCodeName(status));
    return false;
  }
  Serial.print("Write successful for block ");
  Serial.println(block);
  return true;
}

void loop() {
  if (!mfrc522.PICC_IsNewCardPresent()) return;
  if (!mfrc522.PICC_ReadCardSerial()) return;

  Serial.println("Card detected");

  // Prepare plate number data (block 2) - pad or truncate to 16 bytes
  char plate[] = "RAC123Z"; // Example plate number
  byte plateData[16] = {0};
  strncpy((char*)plateData, plate, 16);

  // Prepare balance data (block 4)
  int balance = 8000; // Example balance in RWF
  char balanceStr[16] = {0};
  snprintf(balanceStr, sizeof(balanceStr), "%d", balance); // Convert int to string

  byte balanceData[16] = {0};
  strncpy((char*)balanceData, balanceStr, 16);

  // Write plate number to block 2
  if (!writeBlock(2, plateData)) {
    Serial.println("Failed to write plate number");
  }

  // Write balance to block 4
  if (!writeBlock(4, balanceData)) {
    Serial.println("Failed to write balance");
  }

  mfrc522.PICC_HaltA();
  mfrc522.PCD_StopCrypto1();

  delay(3000); // Wait before next card
}
