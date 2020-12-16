#include <SPI.h>
#include "SD.h"

File data;

// the baud rate for the serial connection
#define BAUD_RATE 115200

// SD Card SPI Chip Select
#define SD_CARD_SPI_CS 5

#define ROOT_PATH "/"


char stringBuf[256];

void setup() {
  Serial.begin(BAUD_RATE);

  Serial.println("Initializing SD card...");
  if (!SD.begin(SD_CARD_SPI_CS)) {
    Serial.println("ERROR - SD card initialization failed!");
    return;    // init failed
  }

//  listDir(SD, "/", 2);

//  deleteAllFiles();

//  appendFile(SD, "/data1.txt", "henlo big boi\n");
//  appendFile(SD, "/data2.txt", "henlo big boi\n");
//  appendFile(SD, "/data3.txt", "henlo big boi\n");
//  appendFile(SD, "/data4.txt", "henlo big boi\n");
//  readFile(SD, "/data1.txt");
//
  testFileIO(SD, "/data.txt");
}

void listDir(fs::FS &fs, const char * dirname, uint8_t levels){
    Serial.printf("Listing directory: %s\n", dirname);

    File root = fs.open(dirname);
    if(!root){
        Serial.println("Failed to open directory");
        return;
    }
    if(!root.isDirectory()){
        Serial.println("Not a directory");
        return;
    }

    File file = root.openNextFile();
    while(file){
        if(file.isDirectory()){
            Serial.print("  DIR : ");
            Serial.println(file.name());
            if(levels){
                listDir(fs, file.name(), levels -1);
            }
        } else {
            Serial.print("  FILE: ");
            Serial.print(file.name());
            Serial.print("  SIZE: ");
            Serial.println(file.size());
        }
        file = root.openNextFile();
    }
}

// Write to the SD card
void appendFile(fs::FS &fs, const char * path, const char * message) {
  File file = fs.open(path, FILE_APPEND);
  if (!file) {
    Serial.println("Failed to open file for writing");
    return;
  }
  if (file.print(message)) {
    Serial.printf("Wrote to file %s\n", path);
  } else {
    Serial.println("Write failed");
  }
  file.close();
}

void readFile(fs::FS &fs, const char * path){
  File file = fs.open(path);
  if(!file){
    Serial.println("Failed to open file for reading");
    return;
  }
  
  Serial.printf("Read from file %s:\n", path);
  while(file.available()){
    Serial.write(file.read());
  }
  file.close();
}

void testFileIO(fs::FS &fs, const char * path) {
  File file = fs.open(path);
  static uint8_t buf[512];
  size_t len = 0;
  uint32_t start = millis();
  uint32_t end = start;
  if (file) {
    len = file.size();
    size_t flen = len;
    start = millis();
    while (len) {
      size_t toRead = len;
      if (toRead > 512) {
        toRead = 512;
      }
      file.read(buf, toRead);
      len -= toRead;
    }
    end = millis() - start;
    Serial.printf("%u bytes read for %u ms\n", flen, end);
    file.close();
  } else {
    Serial.println("Failed to open file for reading");
  }

  file = fs.open(path, FILE_APPEND);
  if (!file) {
    Serial.println("Failed to open file for writing");
    return;
  }

  size_t i;
  start = millis();
  for (i = 0; i < 4; i++) {
    file.write(buf, 512);
  }
  end = millis() - start;
  Serial.printf("%u bytes written for %u ms\n", 4 * 512, end);
  file.close();
}

void deleteAllFiles() {
  File root;

  root = SD.open(ROOT_PATH);
  delay(2000);

  rm(root, ROOT_PATH);
}

void rm(File dir, String tempPath) {
  while(true) {
    File entry =  dir.openNextFile();
    String localPath;

    Serial.println("");
    if (entry) {
      if ( entry.isDirectory() )
      {
        localPath = tempPath + entry.name() + ROOT_PATH + '\0';
        char folderBuf[localPath.length()];
        localPath.toCharArray(folderBuf, localPath.length() );
        rm(entry, folderBuf);


        if( SD.rmdir( folderBuf ) )
        {
          Serial.print("Deleted folder ");
          Serial.println(folderBuf);
        } 
        else
        {
          Serial.print("Unable to delete folder ");
          Serial.println(folderBuf);
        }
      } 
      else
      {
        localPath = tempPath + entry.name() + '\0';
        char charBuf[localPath.length()];
        localPath.toCharArray(charBuf, localPath.length() );

        if( SD.remove( charBuf ) )
        {
          Serial.print("Deleted ");
          Serial.println(localPath);
        } 
        else
        {
          Serial.print("Failed to delete ");
          Serial.println(localPath);
        }

      }
    } 
    else {
      // break out of recursion
      break;
    }
  }
}

void loop() {}
