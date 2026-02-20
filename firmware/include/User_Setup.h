//                            USER DEFINED SETTINGS
//   Set driver type, fonts to be loaded, pins used and SPI control method etc
//
//   See the User_Setup_Select.h file if you wish to be able to define multiple
//   setups and then easily select which setup file is used by the compiler.

// User defined information reported by "Read_User_Setup" test & diagnostics example
#define USER_SETUP_INFO "User_Setup for T-Display-S3"

// ##################################################################################
//
// Section 1. Basic Configuration for T-Display-S3
//
// ##################################################################################

// CORRECT driver for T-Display-S3
#define ST7789_DRIVER // Full configuration option, define additional parameters below for this display

// T-Display-S3 Display Resolution
#define TFT_WIDTH 170
#define TFT_HEIGHT 320

// T-Display-S3 Pin Configuration
#include "pin_config.h" // Include the pin definitions

// For T-Display-S3 we use 8-bit parallel interface
#define TFT_PARALLEL_8_BIT

// Configure the display interface pins
#define TFT_CS PIN_LCD_CS   // Chip select control pin
#define TFT_DC PIN_LCD_DC   // Data Command control pin
#define TFT_RST PIN_LCD_RES // Reset pin (could connect to RST pin)
#define TFT_WR PIN_LCD_WR   // Write strobe control pin - must use pin 8 for the T-Display-S3
#define TFT_RD PIN_LCD_RD   // Read strobe control pin

// Parallel port pins (8-bit parallel interface)
#define TFT_D0 PIN_LCD_D0 // Must use pins in sequence starting with D0...D7
#define TFT_D1 PIN_LCD_D1
#define TFT_D2 PIN_LCD_D2
#define TFT_D3 PIN_LCD_D3
#define TFT_D4 PIN_LCD_D4
#define TFT_D5 PIN_LCD_D5
#define TFT_D6 PIN_LCD_D6
#define TFT_D7 PIN_LCD_D7

// ##################################################################################
//
// Section 2. Font Configuration
//
// ##################################################################################

// Comment out the #defines below with // to stop that font being loaded
// The ESP32-S3 has plenty of memory so commenting out fonts is not
// normally necessary. If all fonts are loaded the extra FLASH space required is
// about 17Kbytes. To save FLASH space only enable the fonts you need!

#define LOAD_GLCD  // Font 1. Original Adafruit 8 pixel font needs ~1820 bytes in FLASH
#define LOAD_FONT2 // Font 2. Small 16 pixel high font, needs ~3534 bytes in FLASH, 96 characters
#define LOAD_FONT4 // Font 4. Medium 26 pixel high font, needs ~5848 bytes in FLASH, 96 characters
#define LOAD_FONT6 // Font 6. Large 48 pixel font, needs ~2666 bytes in FLASH, only characters 1234567890:-.apm
#define LOAD_FONT7 // Font 7. 7 segment 48 pixel font, needs ~2438 bytes in FLASH, only characters 1234567890:.
#define LOAD_FONT8 // Font 8. Large 75 pixel font needs ~3256 bytes in FLASH, only characters 1234567890:-.
// #define LOAD_FONT8N // Font 8. Alternative to Font 8 above, slightly narrower, so 3 digits fit a 160 pixel TFT
#define LOAD_GFXFF // FreeFonts. Include access to the 48 Adafruit_GFX free fonts FF1 to FF48 and custom fonts

// Enable smooth font support
#define SMOOTH_FONT

// ##################################################################################
//
// Section 3. Other Options
//
// ##################################################################################

// Optional reduced SPI frequency for reading TFT
#define SPI_READ_FREQUENCY 20000000

// Touch screen interface — do NOT define TOUCH_CS for parallel mode
// T-Display-S3 uses I2C touch, not SPI touch
// #define TOUCH_CS -1

// Support for "SPIFFS" filesystem, used by smooth fonts
#define SUPPORT_TRANSACTIONS

// DMA configuration (leave commented out unless you know you need them)
// #define DMA_CHANNEL 1
// #define ESP32_DMA
// #define DMA_HALF_WORD_ALIGNED