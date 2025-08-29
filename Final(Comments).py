# Smart Letterbox System
# Copyright (c) 2025 Cayden Dimech
# Licensed under the MIT License. See LICENSE file in the repository for details.

import RPi.GPIO as GPIO
import time
import smbus
from mfrc522 import SimpleMFRC522
from twilio.rest import Client
import logging
import os

# Setup logging configuration for debugging and to track program execution
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# LCD1602 class for handling the 16x2 LCD display
class LCD1602:
    def __init__(self, address=0x27, bus=1):
        self.address = address  # I2C address of the LCD
        self.bus = smbus.SMBus(bus)  # Initialize I2C bus
        self.LCD_WIDTH = 16  # The number of characters which can fit in each line
        self.LCD_CHR = True  # Mode for sending character data
        self.LCD_CMD = False  # Mode for sending commands
        self.LCD_LINE_1 = 0x80  # Address for line 1
        self.LCD_LINE_2 = 0xC0  # Address for line 2
        self.LCD_BACKLIGHT = 0x08  # LCD backlight control
        self.ENABLE = 0x04  # Enable bit for data transmission
        
        for _ in range(3):
            try:
                self.write(0x33, self.LCD_CMD)  # Initialize in 8-bit mode
                self.write(0x32, self.LCD_CMD)  # Switch to 4-bit mode
                self.write(0x06, self.LCD_CMD)  # Set cursor move direction
                self.write(0x0C, self.LCD_CMD)  # Display on, cursor off
                self.write(0x28, self.LCD_CMD)  # 2-line display, 5x8 font
                self.write(0x01, self.LCD_CMD)  # Clear display
                time.sleep(0.002)  # Wait for command to complete
                break
            except:
                time.sleep(0.1)  # Retry after delay if initialization fails

    def write(self, data, mode):
        # Write 4-bit data to the LCD in two nibbles
        high = mode | (data & 0xF0) | self.LCD_BACKLIGHT  # High nibble
        low = mode | ((data << 4) & 0xF0) | self.LCD_BACKLIGHT  # Low nibble
        self.bus.write_byte(self.address, high)
        self.toggle_enable(high)  # Pulse enable for high nibble
        self.bus.write_byte(self.address, low)
        self.toggle_enable(low)  # Pulse enable for low nibble

    def toggle_enable(self, data):
        # Pulse the enable pin to latch data
        time.sleep(0.0005)  # Short delay
        self.bus.write_byte(self.address, data | self.ENABLE)  # Set enable high
        time.sleep(0.0005)  # Short delay
        self.bus.write_byte(self.address, data & ~self.ENABLE)  # Set enable low
        time.sleep(0.0005)  # Short delay

    def clear(self):
        # Clear the LCD display
        self.write(self.LCD_LINE_1, self.LCD_CMD)  # Move to start of line 1
        self.write(0x01, self.LCD_CMD)  # Clear display command
        time.sleep(0.002)  # Wait for command to complete

    def message(self, text, line=1):
        # Display text on the specified line (1 or 2)
        line_addr = self.LCD_LINE_1 if line == 1 else self.LCD_LINE_2
        self.write(line_addr, self.LCD_CMD)  # Set cursor to line start
        time.sleep(0.002)  # Wait for command to complete
        text = text[:self.LCD_WIDTH].ljust(self.LCD_WIDTH)  # Truncate/pad text
        for char in text:
            self.write(ord(char), self.LCD_CHR)  # Write each character

# GPIO setup for Raspberry Pi
GPIO.setmode(GPIO.BCM)  # Use BCM numbering for GPIO pins
GPIO.setwarnings(False)  # Disable GPIO warnings

# Define GPIO pin assignments
ULTRASONIC_TRIG = 17  # Trigger pin for ultrasonic sensor
ULTRASONIC_ECHO = 18  # Echo pin for ultrasonic sensor
SERVO_PIN = 12  # Pin for servo motor control
LED_PIN = 21  # Pin for LED indicator
POWER_BUTTON = 4  # Pin for power button
ROW_PINS = [5, 6, 13, 19]  # Row pins for 4x4 keypad
COL_PINS = [26, 20, 16, 23]  # Column pins for 4x4 keypad

# Initialize GPIO pins
GPIO.setup(ULTRASONIC_TRIG, GPIO.OUT)  # Ultrasonic trigger as output
GPIO.setup(ULTRASONIC_ECHO, GPIO.IN)  # Ultrasonic echo as input
GPIO.setup(SERVO_PIN, GPIO.OUT)  # Servo pin as output
GPIO.setup(LED_PIN, GPIO.OUT)  # LED pin as output
GPIO.setup(POWER_BUTTON, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Power button
GPIO.setup(DOOR_SENSOR, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Door sensor
for pin in ROW_PINS:
    GPIO.setup(pin, GPIO.OUT)
    GPIO.output(pin, GPIO.LOW)
for pin in COL_PINS:
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# Define 4x4 keypad layout
KEYPAD = [
    ["1", "2", "3", "A"],  # Row 1
    ["4", "5", "6", "B"],  # Row 2
    ["7", "8", "9", "C"],  # Row 3
    ["*", "0", "#", "D"]   # Row 4
]

def poll_keypad():
    # Scan the keypad for any key press
    for i, row in enumerate(ROW_PINS):
        GPIO.output(row, GPIO.HIGH)  # Set current row high
        for j, col in enumerate(COL_PINS):
            if GPIO.input(col) == GPIO.HIGH:  # Check if column is high
                time.sleep(0.02)
                if GPIO.input(col) == GPIO.HIGH:  # Confirm key press
                    GPIO.output(row, GPIO.LOW)  # Reset row
                    return KEYPAD[i][j]  # Return pressed key
        GPIO.output(row, GPIO.LOW)  # Reset row
    return None  # No key pressed

# Initialize hardware components
lcd = LCD1602()  # Initialize LCD display
servo = GPIO.PWM(SERVO_PIN, 50)  # Initialize servo with 50Hz PWM
servo.start(0)  # Servo start state
reader = SimpleMFRC522()  # Initialize RFID reader
client = Client("your_account_sid", "your_auth_token")  # Initialize Twilio client

# Initialize program variables
pin_code = ["1", "2", "3", "4"]  # Define the default PIN code
entered_code = []  # List to store the entered PIN digits
AUTHORIZED_UID = "909938959676"  # Authorized RFID card UID
changing_pin = False  # Boolean for PIN change mode
new_pin = []  # List to store new PIN during change
pin_change_start = 0  # Timestamp for PIN change start
mail_detected = False  # Boolean for mail detection
notification_sent = False  # Boolean to track if notification was sent for current mail

def display_main_menu():
    # Display the main menu prompt on the LCD
    lcd.clear()  # Clear the LCD
    lcd.message("Enter PIN or *  ", 1)  # Prompt for PIN
    lcd.message("* for RFID Scan", 2)  # Prompt for RFID scan

def send_whatsapp():
    # Send WhatsApp message via Twilio
    if client:
        client.messages.create(
            from_='your_twilio_number',  # Twilio number
            content_sid='your_content_sid',  # Message template ID
            to='your_recipient_number'  # Recipient's number
        )
        logging.info("WhatsApp notification sent: New mail detected")

def check_mail():
    # Check for new mail using the ultrasonic sensor
    global mail_detected, notification_sent
    GPIO.output(ULTRASONIC_TRIG, True)  # Send an ultrasonic pulse
    time.sleep(0.00001)  # Duration of the pulse
    GPIO.output(ULTRASONIC_TRIG, False)  # Stop the pulse

    start = time.time()  # Record start time with the current time
    while GPIO.input(ULTRASONIC_ECHO) == 0 and time.time() - start < 0.1:
        pulse_start = time.time()  # Record the pulse start time
    while GPIO.input(ULTRASONIC_ECHO) == 1 and time.time() - start < 0.1:
        pulse_end = time.time()  # Record the pulse end time

    # Calculate the distance and update mail detection state
    if 'pulse_end' in locals() and 'pulse_start' in locals():
        dist = (pulse_end - pulse_start) * 17150  # Convert the time of the pulse to distance (cm)
        if dist < 5 and not mail_detected:  # If the distance is less than 5cm and no mail is detected
            mail_detected = True  # Set mail_detected to true
            lcd.clear()
            lcd.message("Enter PIN or *  ", 1)  # Prompt for PIN or RFID
            lcd.message("New Mail!       ", 2)  # Display mail notification
            GPIO.output(LED_PIN, True)  # Turn on LED
            if notification_sent == False:  # Send notification only if not already sent
                send_whatsapp()  # Send WhatsApp notification
                notification_sent = True  # Mark notification as sent
        elif dist >= 5 and mail_detected:  # If no mail detected
            mail_detected = False  # Set mail_detected to false
            GPIO.output(LED_PIN, False)  # Turn off LED
            display_main_menu()  # Display main menu

def unlock_box():
    # Unlock the letterbox using the servo
    global notification_sent
    lcd.clear()  # Clear LCD display
    lcd.message("Box Unlocking... ", 1)  # Display unlocking message
    GPIO.output(LED_PIN, GPIO.LOW)  # Turn off LED
    servo.ChangeDutyCycle(2.5)  # Rotate servo to unlock position
    time.sleep(1)  # Wait for servo to finish movement
    servo.ChangeDutyCycle(0)  # Stop servo
    lcd.clear()  # Clear LCD
    lcd.message("Box Unlocked!   ", 1)  # Display unlocked message
    time.sleep(2)
    lcd.message("Press # to Lock ", 2)  # Prompt to lock
    time.sleep(10)  # Display message for 10 seconds

def lock_box():
    # Lock the letterbox using the servo
    lcd.clear()  # Clear LCD
    lcd.message("Locking Box...  ", 1)  # Display locking message
    servo.ChangeDutyCycle(7.5)  # Rotate servo to lock position
    time.sleep(1)  # Wait for servo to finish movement
    servo.ChangeDutyCycle(0)  # Stop servo
    lcd.clear()  # Clear LCD
    lcd.message("Box Locked!     ", 1)  # Display the locked message
    GPIO.output(LED_PIN, GPIO.LOW)  # Turn lighting LED pin as output
    notification_sent = False  # Reset notification Boolean when box is closed
    time.sleep(2)  # Display locked message for 2 seconds

def check_mail():
    # Check for new mail using the ultrasonic sensor
    global mail_detected, notification_sent
    GPIO.output(ULTRASONIC_TRIG, True)  # Send an ultrasonic pulse
    time.sleep(0.00001)  # Duration of the pulse
    GPIO.output(ULTRASONIC_TRIG, False)  # Stop the pulse

    start = time.time()  # Record start time with the current time
    while GPIO.input(ULTRASONIC_ECHO) == 0 and time.time() - start < 0.1:
        pulse_start = time.time()  # Record the pulse start time
    while GPIO.input(ULTRASONIC_ECHO) == 1 and time.time() - start < 0.1:
        pulse_end = time.time()  # Record the pulse end time

    # Calculate the distance and update mail detection state
    if 'pulse_end' in locals() and 'pulse_start' in locals():
        dist = (pulse_end - pulse_start) * 17150  # Convert the time of the pulse to distance (cm)
        if dist < 5 and not mail_detected:  # If the distance is less than 5cm and no mail is detected
            mail_detected = True  # Set mail_detected to true
            lcd.clear()
            lcd.message("Enter PIN or *  ", 1)  # Prompt for PIN or RFID
            lcd.message("New Mail!       ", 2)  # Display mail notification
            GPIO.output(LED_PIN, True)  # Turn on LED
            if notification_sent == False:  # Send notification only if not already sent
                send_whatsapp()  # Send WhatsApp notification
                notification_sent = True  # Mark notification as sent
        elif dist >= 5 and mail_detected:  # If no mail detected
            mail_detected = False  # Set mail_detected to false
            GPIO.output(LED_PIN, False)  # Turn off LED
            display_main_menu()  # Display main menu

def rfid_unlock():
    # Authenticate RFID card and initiate PIN change
    global changing_pin, new_pin, pin_change_start
    lcd.clear()
    lcd.message("Scan your tag  ", 1)  # Prompt for RFID scan
    id = reader.read()[0]  # Read RFID tag UID
    if str(id).strip() == AUTHORIZED_UID:  # Check if UID matches with the authorized one
        lcd.clear()
        lcd.message("RFID Accepted!  ", 1)  # Display RFID acceptance message
        time.sleep(1)
        unlock_box()  # Unlock the box
        changing_pin = True  # Enter the PIN change mode
        new_pin = []  # Clear new PIN
        pin_change_start = time.time()  # Record PIN change start time
        lcd.clear()
        lcd.message("Enter new PIN:  ", 1)  # Prompt for new PIN
    else: #If the UID does not match
        lcd.clear()
        lcd.message("Access Denied!  ", 1)  # Display denial message
        time.sleep(2)  # Show message for 2 seconds
        display_main_menu()  # Display the main menu

def handle_key(key):
    # Process keypad input
    global entered_code, changing_pin, new_pin, pin_code, pin_change_start
    if not key:
        return  # Ignore if no key pressed

    if changing_pin:  # Handle PIN change mode
        if key.isdigit():  # Accept only digits
            new_pin.append(key)  # Add digits pressed to the new PIN
            lcd.clear()
            lcd.message("Enter new PIN:  ", 1)  # Prompt for new PIN
            lcd.message("PIN: " + ''.join(new_pin).ljust(11), 2)  # Display the entered digits on the display
            if len(new_pin) == 4:  # Check that the netered pin is equal to 4 digits
                pin_code = new_pin  # Update the PIN code
                changing_pin = False  # Exit PIN change mode
                lcd.clear()
                lcd.message("PIN Changed!    ", 1)  # Display success message
                time.sleep(2)  # Show message for 2 seconds
                display_main_menu()  # Display the main menu
        return

    if key == "#":  # Handle the lock command
        lock_box()  # Lock the box
        entered_code.clear()  # Clear the entered code
        display_main_menu()  # Display main menu
    elif key == "*":  # Handle RFID scan request
        rfid_unlock()  # Initiate RFID authentication
    elif key.isdigit():  # Handle PIN digit input
        entered_code.append(key)  # Add digit to entered code
        lcd.clear()
        lcd.message("Code: " + ''.join(entered_code).ljust(10), 1)  # Display entered code on the display
        if len(entered_code) == len(pin_code):  # Check if entered code is the same length of the pin code
            if entered_code == pin_code:  # Check if PIN is correct
                unlock_box()  # Unlock the box
            else:#If entered pin is incorrect
                lcd.clear()
                lcd.message("Wrong PIN!      ", 1)  # Display error message
                time.sleep(2)  # Show message for 2 seconds
            entered_code.clear()  # Clear entered code
            display_main_menu()  # Display main menu

def power_off(channel):
    # Handle power button press to reboot system
    lcd.clear()
    lcd.message("Restarting...   ", 1)  # Display a reboot message
    time.sleep(2)  # Show message for 2 seconds
    servo.stop()  # Stop servo PWM
    GPIO.cleanup()  # Cleanup GPIO settings
    os.system("sudo reboot")  # Reboot the system

# Setup event detection for power button
GPIO.add_event_detect(POWER_BUTTON, GPIO.FALLING, callback=power_off, bouncetime=300)

# Main program loop
display_main_menu()  # Display the main menu
last_mail_check = 0  # Timestamp for last mail check
last_key = None  # Store last key pressed

while True:
    key = poll_keypad()  # Poll for keypad input
    if key != last_key and key is not None:  # Process a new key press
        handle_key(key)  # Handle the key input
    last_key = key  # Update the last key variable

    # Check for mail every 2 seconds
    if time.time() - last_mail_check >= 2:
        check_mail()  # call the check mail function
        last_mail_check = time.time()  # Update last check time

    # Timeout PIN change mode after 20 seconds
    if changing_pin and time.time() - pin_change_start > 20:#Check if the time exceeded 20 seconds
        changing_pin = False  # Exit the PIN change mode
        new_pin = []  # Clear new PIN
        lcd.clear()
        lcd.message("Timeout! TryAgain", 1)  # Display timeout message
        time.sleep(2)  # Show message for 2 seconds
        display_main_menu()  # Display main menu