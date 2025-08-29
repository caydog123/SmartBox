Smart Letterbox System
Overview
This project implements a Smart Letterbox System using a Raspberry Pi, designed to enhance security and convenience for mail delivery. The system integrates a keypad for PIN entry, an RFID reader for secure access, an ultrasonic sensor for mail detection, a servo motor for locking/unlocking, an LED indicator, and an LCD display for user interaction. It also sends WhatsApp notifications via Twilio when new mail is detected.
Features

PIN Authentication: Unlock the letterbox by entering a 4-digit PIN via a 4x4 keypad.
RFID Access: Authorized RFID tags can unlock the box and initiate PIN change mode.
Mail Detection: An ultrasonic sensor detects new mail and triggers a WhatsApp notification.
Servo Lock Mechanism: A servo motor locks and unlocks the letterbox.
LCD Display: A 16x2 LCD displays prompts, status messages, and user feedback.
LED Indicator: Signals new mail detection.
Power Button: Triggers a system reboot for maintenance.
WhatsApp Notifications: Sends alerts for new mail using Twilio's WhatsApp API.

Hardware Requirements

Raspberry Pi (any model with GPIO pins, e.g., Raspberry Pi 3 or 4)
16x2 LCD display with I2C interface (address: 0x27)
4x4 membrane keypad
HC-SR04 ultrasonic sensor
MFRC522 RFID reader
Servo motor (e.g., SG90)
LED and appropriate resistor
Push button (for power/reboot)
Jumper wires and breadboard/prototyping board
Power supply for Raspberry Pi

Software Requirements

Raspbian OS (or compatible Raspberry Pi OS)
Python 3 (pre-installed on Raspbian)
Python Libraries:
RPi.GPIO: For GPIO pin control
smbus: For I2C communication with the LCD
mfrc522: For RFID reader communication
twilio: For sending WhatsApp notifications


Twilio Account: Required for WhatsApp notifications (set up with your account_sid and auth_token)

Installation

Set up the Raspberry Pi:

Install Raspbian OS and ensure the Raspberry Pi is connected to the internet.
Enable I2C and SPI interfaces via raspi-config.


Install Python libraries:
pip install RPi.GPIO smbus2 python-mfrc522 twilio


Connect the hardware:

Wire the components according to the GPIO pin assignments in the code:
Ultrasonic Sensor: Trigger (GPIO 17), Echo (GPIO 18)
Servo Motor: GPIO 12
LED: GPIO 21
Power Button: GPIO 4
Keypad: Rows (GPIO 5, 6, 13, 19), Columns (GPIO 26, 20, 16, 23)
LCD: I2C connection (SDA, SCL)
RFID Reader: SPI connection


Ensure proper grounding and power connections.


Configure Twilio:

Sign up for a Twilio account and obtain your account_sid and auth_token.
Update the client = Client("your_account_sid", "your_auth_token") line in the code with your credentials.
Verify the WhatsApp number and template SID in the send_whatsapp() function.


Clone the repository:
git clone <repository_url>
cd <repository_directory>


Run the program:
python Final(Comments).py



Usage

Power On: The system initializes and displays the main menu on the LCD ("Enter PIN or *").
Unlocking the Letterbox:
Enter the 4-digit PIN (default: "1234") using the keypad.
Press * to scan an RFID tag (default authorized UID: "909938959676").
If the PIN or RFID is correct, the servo unlocks the box, and the LCD shows "Box Unlocked!".


Locking the Box:
Press # to lock the box after opening. The LCD displays "Box Locked!".


Mail Detection:
The ultrasonic sensor checks for mail every 2 seconds.
If mail is detected (distance < 5 cm), the LED turns on, and a WhatsApp notification is sent.


PIN Change:
After a successful RFID scan, enter a new 4-digit PIN within 20 seconds.
The new PIN is saved, and the LCD displays "PIN Changed!".


Power Off/Reboot:
Press the power button to initiate a system reboot.



File Description

Final(Comments).py: The main Python script containing the complete smart letterbox system logic, including LCD control, keypad input, RFID authentication, ultrasonic sensing, servo control, and Twilio notifications.

Notes

Replace "your_account_sid" and "your_auth_token" in the code with your actual Twilio credentials.
Ensure the AUTHORIZED_UID matches your RFID tag's UID (check by scanning and logging the ID).
The ultrasonic sensor's distance threshold (5 cm) can be adjusted in the check_mail() function.
The system assumes a stable power supply and proper hardware connections to avoid erratic behavior.
The power button triggers a system reboot (sudo reboot), requiring appropriate permissions.

Troubleshooting

LCD not displaying: Verify I2C address (use i2cdetect -y 1) and connections.
RFID not reading: Ensure SPI is enabled and check wiring to the MFRC522 module.
No WhatsApp notifications: Confirm Twilio credentials, internet connectivity, and correct phone numbers.
Servo not moving: Check the servo pin (GPIO 12) and power supply (servos may require external power).
Keypad issues: Verify row and column pin assignments and ensure proper pull-up/pull-down resistors.

Contributing
Contributions are welcome! Please fork the repository, make changes, and submit a pull request. Ensure your code follows the existing style and includes comments for clarity.
License
This project is licensed under the MIT License. See the LICENSE file for details.
