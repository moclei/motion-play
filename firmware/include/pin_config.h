#pragma once

// Display pins
#define PIN_LCD_BL 38
#define PIN_LCD_D0 39
#define PIN_LCD_D1 40
#define PIN_LCD_D2 41
#define PIN_LCD_D3 42
#define PIN_LCD_D4 45
#define PIN_LCD_D5 46
#define PIN_LCD_D6 47
#define PIN_LCD_D7 48
#define PIN_LCD_RES 5
#define PIN_LCD_CS 6
#define PIN_LCD_DC 7
#define PIN_LCD_WR 8
#define PIN_LCD_RD 9

// Power control
#define PIN_POWER_ON 15

// Touch Screen (Note: PIN_TOUCH_INT conflicts with LED strip)
#define PIN_TOUCH_RES 21
// #define PIN_TOUCH_INT 16  // DISABLED - conflicts with LED strip

// I2C (Custom PCB connections)
#define PIN_IIC_SCL 44
#define PIN_IIC_SDA 43

// Motion Play Hardware Control
#define PIN_TCA_RESET 10      // TCA9548A reset pin
#define PIN_SENSOR_INT_1 11   // Sensor board 1 interrupt
#define PIN_SENSOR_INT_2 12   // Sensor board 2 interrupt
#define PIN_SENSOR_INT_3 13   // Sensor board 3 interrupt
#define PIN_LED_STRIP_DATA 16 // WS2818B LED strip data (72 LEDs)

// SD Card (Note: Some pins conflict with Motion Play hardware)
#define PIN_SD_CS 10   // CONFLICTS with TCA_RESET - choose one
#define PIN_SD_MISO 13 // CONFLICTS with SENSOR_INT_3 - choose one
#define PIN_SD_MOSI 11 // CONFLICTS with SENSOR_INT_1 - choose one
#define PIN_SD_SCLK 12 // CONFLICTS with SENSOR_INT_2 - choose one

// Built-in button
#define PIN_BUTTON_1 14
#define PIN_BUTTON_2 0