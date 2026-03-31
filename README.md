## Interface Overview

The Python application provides a real-time radar-style interface connected to the Arduino system.

The interface displays:
- Current servo angle
- Measured distance
- Detection status
- Current operating mode
- Radar sweep animation
- Persistent target markers

It also includes on-screen controls for switching modes and adjusting the servo angle manually.

---
## Setup and Usage

### 1. Hardware Setup

To use the Arduino radar system, assemble the following components:

- Arduino Uno (or compatible board)
- Ultrasonic sensor (HC-SR04)
- Servo motor (SG90)
- Optional joystick module for manual control

#### Connections

**Ultrasonic Sensor**
- VCC → 5V
- GND → GND
- TRIG → Arduino digital pin
- ECHO → Arduino digital pin

**Servo Motor**
- VCC → 5V
- GND → GND
- Signal → PWM pin (for example, D9)

**Joystick (optional)**
- VRx → Analog pin (for example, A0)
- VCC → 5V
- GND → GND

> Make sure all grounds are connected together.

---

### 2. Upload the Arduino Code

1. Open the Arduino IDE
2. Connect the Arduino board via USB
3. Select the correct board and serial port
4. Upload the radar Arduino code

---

### 3. Install Python Requirements

Make sure Python 3 is installed, then install the required libraries:

pip install pygame pyserial

### 4. Configure the Serial Port

Before running the Python interface, update the serial port in the Python script.

Example:

serial_port = "COM3"  # Change this to your actual port

Examples of ports:

Windows: COM3, COM4, etc.
macOS / Linux: /dev/tty.usbmodem... or /dev/ttyUSB0

### 5. Run the Python Interface

Once the Arduino is connected and the correct port is selected, run the Python program:

python radar.py

This will open the real-time radar interface.

### 6. How to Use the System

When the program starts:

The Python radar window opens
The Arduino begins sending live angle and distance data
The system starts in the active operating mode
Mode Selection

You can switch between modes in two ways:

Press A to activate AUTO mode
Press M to activate MANUAL mode
Click the AUTO or MANUAL buttons in the Python interface

### AUTO Mode

In AUTO mode:

The servo automatically sweeps between its minimum and maximum angles
The ultrasonic sensor continuously measures distance
The radar interface updates in real time with the current scan

### MANUAL Mode

In MANUAL mode:

The servo stops sweeping automatically
The angle can be controlled manually

Two manual control methods are supported:

Physical joystick control
Python interface slider control

The Python slider sends angle commands directly to the Arduino, allowing desktop-based control of the radar angle.

Keyboard Shortcuts
A = AUTO mode
M = MANUAL mode
Left arrow = decrease manual target angle
Right arrow = increase manual target angle

### 7. Radar Visualization

The Python radar interface is designed to provide a clear real-time view of the system.

It displays:

Current servo angle
Measured distance
Detection status
Current operating mode
Radar sweep animation
Persistent target markers

Additional interface features include:

On-screen buttons for switching between AUTO and MANUAL modes
A slider for manual angle control
Live sweep line showing the current radar direction
Target points based on measured distance
Short-lived persistent detections after scanning

The interface was developed using Pygame and communicates with the Arduino through serial communication.

### 8. Expected Behavior

When everything is working correctly:

The servo rotates and scans the environment in AUTO mode
The ultrasonic sensor measures object distances
The Python application displays live radar motion
Objects appear as target markers on the radar screen
In MANUAL mode, the angle can be changed using the slider or joystick

### Troubleshooting
No data is displayed
Check that the correct serial port is selected
Make sure the Arduino code is uploaded and running
Verify that the baud rate in Python matches the baud rate in the Arduino code
Servo is not moving
Verify the wiring
Check that the servo signal wire is connected to the correct PWM pin
Make sure the servo has sufficient power
Incorrect or unstable distance readings
Check the ultrasonic sensor wiring
Ensure the sensor is mounted securely
Avoid measuring objects that are too close to the sensor
Reduce electrical noise if needed
Python interface does not start
Confirm that pygame and pyserial are installed
Make sure the serial port is not already in use by another application such as the Arduino Serial Monitor

## Controls

The system can be controlled directly from the Python interface.

### Mode Selection
You can switch between operating modes in two ways:
- Press `A` to activate AUTO mode
- Press `M` to activate MANUAL mode
- Click the `AUTO` or `MANUAL` buttons in the interface

### Manual Control
In MANUAL mode, the radar angle can be adjusted:
- By dragging the on-screen slider in the Python interface
- By using the physical joystick in the hardware setup

### Keyboard Shortcuts
- `A` = AUTO mode
- `M` = MANUAL mode
- Left arrow = decrease manual target angle
- Right arrow = increase manual target angle

---

## How the Modes Work

### AUTO Mode
In AUTO mode, the servo automatically sweeps between its minimum and maximum angles.
The radar interface updates continuously with the current angle and measured distance.

### MANUAL Mode
In MANUAL mode, the radar no longer sweeps automatically.
Instead, the angle can be controlled manually.

Two manual control methods are supported:
- Hardware joystick control
- Python interface control through the slider

The Python slider sends angle commands to the Arduino, allowing direct control from the desktop interface.

---

## Radar Visualization

The radar screen is designed to make the system easier to interpret visually.

Features include:
- A live sweep line showing the current angle
- Target markers based on measured distance
- Persistent detections that remain visible briefly after being scanned
- Status indicators for object detection and operating mode

This interface was developed using Pygame and communicates with the Arduino through serial communication.

## Media

### Hardware Setup
![Hardware Setup](images/radar-hardware-1.jpg)
![Hardware Setup](images/radar-hardware-2.jpg)

### Circuit Diagram
![Circuit Diagram](images/circuit.png)

### Radar Interface
![Radar UI](images/radar-ui.png)

### Demo Video
[Watch the demo video](https://youtu.be/t6CY_emrd0A)

## Developer Notes

The Python interface communicates with the Arduino through serial commands to:
- switch between AUTO and MANUAL modes
- set a manual target angle
- return control to the joystick when needed
