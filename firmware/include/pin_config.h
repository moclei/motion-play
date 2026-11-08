#pragma once

#ifdef HAS_DISPLAY
// T-Display-S3 display pins (8-bit parallel interface)
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

// T-Display-S3 power control
#define PIN_POWER_ON 15

// Touch Screen (Note: PIN_TOUCH_INT conflicts with LED strip)
#define PIN_TOUCH_RES 21
// #define PIN_TOUCH_INT 16  // DISABLED - conflicts with LED strip
#endif // HAS_DISPLAY

#if defined(BOARD_MOTION_PLAY_V8)
// ---------------------------------------------------------------------------
// Main PCB v8 (debug board). Source: hardware/pcb-main-v8/CONTEXT.md
// "GPIO allocation" and "Jumper matrix" rows a and g; nets checked against
// hardware/pcb-main-v8/kicad/circuit-context.json (schematic freeze tag
// v8-schematic-freeze): JP1 = U3_IO16 / I2C_SDA / U3_IO43 / UART0_TX,
// JP2 = U3_IO15 / I2C_SCL / U3_IO44 / UART0_RX, JP5 = U3_IO18 / LED_DATA /
// U3_IO16.
//
// Jumper (a) is a separate header per line, so each line is chosen on its
// own. The build flag must match where the shunt is fitted:
//   (none)          SDA = GPIO16 (JP1 shunts on 1-2 and 3-4, v8 default)
//   V8_I2C_SDA_ALT  SDA = GPIO43 (JP1 shunt on 2-3, v7 position)
//   (none)          SCL = GPIO15 (JP2 shunts on 1-2 and 3-4, v8 default)
//   V8_I2C_SCL_ALT  SCL = GPIO44 (JP2 shunt on 2-3, v7 position)
// Common sets: both default (env motion-play-v8), both ALT (env
// motion-play-v8-v7bus), SDA ALT only (repeats V7R-019 in reverse).
// ---------------------------------------------------------------------------
#ifdef V8_I2C_SDA_ALT
#define PIN_IIC_SDA 43
#else
#define PIN_IIC_SDA 16
#endif
#ifdef V8_I2C_SCL_ALT
#define PIN_IIC_SCL 44
#else
#define PIN_IIC_SCL 15
#endif

// UART0 (GPIO43 TX / GPIO44 RX) reaches the UART0 header only when both
// lines are in the v8 position (JP1/JP2 3-4 shunts fitted; header J11). Then the ROM and
// bootloader log is readable there, and main.cpp also starts Serial0 on it.
// With either line on GPIO43/44, UART0 is left alone (that pin is the bus).
#if !defined(V8_I2C_SDA_ALT) && !defined(V8_I2C_SCL_ALT)
#define V8_UART0_HEADER 1
#endif

// Jumper (g): LED_DATA source. Default (JP5 pin 1-2) = GPIO18.
// V8_LED_DATA_GPIO16 = JP5 2-3 (v7 position), valid only with SDA on GPIO43.
#ifdef V8_LED_DATA_GPIO16
#define PIN_LED_STRIP_DATA 16
#else
#define PIN_LED_STRIP_DATA 18
#endif
#if (PIN_LED_STRIP_DATA == PIN_IIC_SDA)
// JP1 at v8 with JP5 at v7 puts the LED loads on SDA (V7R-019's fixture
// state). For that state build with the default LED pin (GPIO18, then
// unconnected), so firmware never drives the bus as LED data.
#error "v8: LED_DATA and SDA both on GPIO16. Drop V8_LED_DATA_GPIO16 or set V8_I2C_SDA_ALT."
#endif

// Debug LEDs: high = on (R103/R104 470 R to D14/D15; CONTEXT "Debug LEDs")
#define PIN_DBG_LED_1 47 // DBG1, blue
#define PIN_DBG_LED_2 48 // DBG2, white

#define PIN_CHRG_INT 21 // BQ24195 INT (R38 10 k pull-up)

#else
// I2C (Custom PCB connections — same on T-Display-S3 and v7 WROOM)
#define PIN_IIC_SCL 44
#define PIN_IIC_SDA 43
#define PIN_LED_STRIP_DATA 16 // WS2818B LED strip data (72 LEDs)
#endif // BOARD_MOTION_PLAY_V8

// Motion Play Hardware Control (same on v6, v7 and v8)
#define PIN_TCA_RESET 10      // TCA9548A reset pin
#define PIN_SENSOR_INT_1 11   // Sensor board 1 interrupt
#define PIN_SENSOR_INT_2 12   // Sensor board 2 interrupt
#define PIN_SENSOR_INT_3 13   // Sensor board 3 interrupt

#ifdef HAS_DISPLAY
// SD Card (Note: Some pins conflict with Motion Play hardware)
#define PIN_SD_CS 10   // CONFLICTS with TCA_RESET - choose one
#define PIN_SD_MISO 13 // CONFLICTS with SENSOR_INT_3 - choose one
#define PIN_SD_MOSI 11 // CONFLICTS with SENSOR_INT_1 - choose one
#define PIN_SD_SCLK 12 // CONFLICTS with SENSOR_INT_2 - choose one
#endif // HAS_DISPLAY

#ifdef HAS_BUTTONS
// T-Display-S3 built-in buttons
#define PIN_BUTTON_1 14
#define PIN_BUTTON_2 0
#endif // HAS_BUTTONS
