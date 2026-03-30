// ==========================================================
// MINI RADAR SYSTEM - ARDUINO
// ==========================================================
//
// Description:
// Embedded system controlling a radar-like scanner using:
// - Ultrasonic sensor (HC-SR04)
// - Servo motor (angular sweep)
// - Joystick (manual control)
// - Serial communication (Python interface)
//
// Features:
// - AUTO mode (smooth scanning with easing)
// - MANUAL mode (joystick or Python control)
// - Real-time distance measurement
// - LED alert for close objects
// - Bidirectional communication with Python UI
//
// Author: Carlos Nazzarian
// ==========================================================
#include <Servo.h>

Servo radarServo;

// =========================
// Pins
// =========================
const int trigPin = 9;
const int echoPin = 10;
const int servoPin = 6;
const int ledPin = 3;

const int joystickXPin = A0;
const int joystickButtonPin = 2;

// =========================
// Distance
// =========================
const int DETECTION_THRESHOLD_CM = 50;
const int MIN_VALID_DISTANCE_CM = 5;
const int MAX_VALID_DISTANCE_CM = 300;

// =========================
// Angles
// =========================
const float ANGLE_MIN = 20.0;
const float ANGLE_MAX = 160.0;

// =========================
// Auto scan easing
// =========================
float currentAngle = 90.0;
int directionSign = 1;

const float STEP_MIN = 0.25;
const float STEP_MAX = 2.20;

// =========================
// Manual joystick
// =========================
const int JOYSTICK_CENTER = 512;
const int JOYSTICK_DEADZONE = 60;
const float MANUAL_STEP_SLOW = 0.25;
const float MANUAL_STEP_FAST = 2.50;

// =========================
// Timing
// =========================
const unsigned long SERVO_UPDATE_MS = 20;
const unsigned long MEASURE_INTERVAL_MS = 55;
const unsigned long BUTTON_DEBOUNCE_MS = 250;

unsigned long lastServoUpdate = 0;
unsigned long lastMeasureTime = 0;
unsigned long lastButtonToggleTime = 0;

// =========================
// Modes
// =========================
enum ControlMode {
  MODE_AUTO,
  MODE_MANUAL
};

ControlMode currentMode = MODE_AUTO;

// =========================
// State
// =========================
int lastButtonState = HIGH;
int currentDistance = 999;

// manuel via Python
bool pythonManualControlActive = false;
float pythonTargetAngle = 90.0;

// =========================
// Serial command buffer
// =========================
String commandBuffer = "";

/**
 * @brief Converts the control mode enum to a readable string.
 *
 * @param mode Current control mode (MODE_AUTO or MODE_MANUAL)
 * @return const char* String representation ("AUTO" or "MANUAL")
 */
const char* modeToString(ControlMode mode) {
  if (mode == MODE_AUTO) return "AUTO";
  return "MANUAL";
}

/**
 * @brief Measures distance using the ultrasonic sensor with noise filtering.
 *
 * This function performs multiple measurements (3 samples),
 * filters invalid values, and returns the average valid distance.
 *
 * @return int Distance in centimeters
 *         - Returns 999 if no valid measurement is detected
 */
int mesurerDistance() {
  long total = 0;
  int count = 0;

  for (int i = 0; i < 3; i++) {
    digitalWrite(trigPin, LOW);
    delayMicroseconds(3);

    digitalWrite(trigPin, HIGH);
    delayMicroseconds(10);
    digitalWrite(trigPin, LOW);

    long duration = pulseIn(echoPin, HIGH, 30000);
    if (duration == 0) {
      delay(5);
      continue;
    }

    int d = duration * 0.0343 / 2.0;

    if (d >= MIN_VALID_DISTANCE_CM && d <= MAX_VALID_DISTANCE_CM) {
      total += d;
      count++;
    }

    delay(5);
  }

  if (count == 0) return 999;
  return total / count;
}

/**
 * @brief Computes a dynamic step size for smooth servo motion.
 *
 * The step is larger near the center and smaller near the edges
 * to create a smooth "ease-in / ease-out" radar sweep effect.
 *
 * @param angle Current servo angle (degrees)
 * @return float Step size to apply for next movement
 */
float computeEasedStep(float angle) {
  float center = (ANGLE_MIN + ANGLE_MAX) / 2.0;
  float halfRange = (ANGLE_MAX - ANGLE_MIN) / 2.0;

  float normalized = 1.0 - abs(angle - center) / halfRange;
  if (normalized < 0.0) normalized = 0.0;
  if (normalized > 1.0) normalized = 1.0;

  float eased = normalized * normalized;
  return STEP_MIN + (STEP_MAX - STEP_MIN) * eased;
}

/**
 * @brief Updates servo position in automatic scanning mode.
 *
 * Uses easing to vary speed and reverses direction at boundaries.
 *
 * Behavior:
 * - Moves between ANGLE_MIN and ANGLE_MAX
 * - Smooth acceleration/deceleration
 */
void updateServoAuto() {
  float step = computeEasedStep(currentAngle);
  currentAngle += directionSign * step;

  if (currentAngle >= ANGLE_MAX) {
    currentAngle = ANGLE_MAX;
    directionSign = -1;
  } else if (currentAngle <= ANGLE_MIN) {
    currentAngle = ANGLE_MIN;
    directionSign = 1;
  }

  radarServo.write((int)currentAngle);
}
/**
 * @brief Updates servo angle based on joystick input.
 *
 * Reads analog X-axis and applies:
 * - Deadzone filtering
 * - Speed proportional to joystick displacement
 *
 * @note Small joystick movements result in slow motion,
 *       large movements result in faster motion.
 */
void updateServoManualJoystick() {
  int xValue = analogRead(joystickXPin);
  int delta = xValue - JOYSTICK_CENTER;

  if (abs(delta) < JOYSTICK_DEADZONE) {
    return;
  }

  int effectiveDelta = abs(delta) - JOYSTICK_DEADZONE;
  int maxDelta = 512 - JOYSTICK_DEADZONE;

  float ratio = (float)effectiveDelta / (float)maxDelta;
  if (ratio < 0.0) ratio = 0.0;
  if (ratio > 1.0) ratio = 1.0;

  float step = MANUAL_STEP_SLOW + ratio * (MANUAL_STEP_FAST - MANUAL_STEP_SLOW);

  if (delta > 0) {
    currentAngle += step;
  } else {
    currentAngle -= step;
  }

  if (currentAngle > ANGLE_MAX) currentAngle = ANGLE_MAX;
  if (currentAngle < ANGLE_MIN) currentAngle = ANGLE_MIN;

  radarServo.write((int)currentAngle);
}

/**
 * @brief Updates servo position based on Python commands.
 *
 * The target angle is received via serial communication.
 * The function clamps the angle within valid bounds and applies it.
 */
void updateServoManualPython() {
  if (pythonTargetAngle < ANGLE_MIN) pythonTargetAngle = ANGLE_MIN;
  if (pythonTargetAngle > ANGLE_MAX) pythonTargetAngle = ANGLE_MAX;

  currentAngle = pythonTargetAngle;
  radarServo.write((int)currentAngle);
}

/**
 * @brief Handles joystick button input to toggle control modes.
 *
 * Implements debounce logic to avoid false triggering.
 *
 * Behavior:
 * - Toggles between AUTO and MANUAL modes
 * - Resets Python control when switching modes
 */
void updateModeButton() {
  int buttonState = digitalRead(joystickButtonPin);

  if (lastButtonState == HIGH && buttonState == LOW) {
  unsigned long now = millis();
  if (now - lastButtonToggleTime > BUTTON_DEBOUNCE_MS) {
    if (currentMode == MODE_AUTO) {
      currentMode = MODE_MANUAL;
      pythonManualControlActive = false;   // joystick reprend la main
    } else {
      currentMode = MODE_AUTO;
      pythonManualControlActive = false;   // sécurité
    }
    lastButtonToggleTime = now;
  }
}

  lastButtonState = buttonState;
}

/**
 * @brief Controls LED based on detected distance.
 *
 * @param distance Measured distance in cm
 *
 * Behavior:
 * - LED ON  → object is within detection threshold
 * - LED OFF → otherwise
 */
void updateLed(int distance) {
  if (distance >= MIN_VALID_DISTANCE_CM && distance <= DETECTION_THRESHOLD_CM) {
    digitalWrite(ledPin, HIGH);
  } else {
    digitalWrite(ledPin, LOW);
  }
}

/**
 * @brief Sends system data to the Python interface.
 *
 * Format:
 * angle,distance,mode
 *
 * Example:
 * 90,42,AUTO
 *
 * @param angle Current servo angle
 * @param distance Measured distance
 * @param mode Current control mode
 */
void sendSerialData(int angle, int distance, ControlMode mode) {
  Serial.print(angle);
  Serial.print(",");
  Serial.print(distance);
  Serial.print(",");
  Serial.println(modeToString(mode));
}

/**
 * @brief Processes incoming serial commands from Python.
 *
 * Supported commands:
 * - "AUTO"      → switch to automatic mode
 * - "MANUAL"    → switch to manual mode
 * - "ANGLE:x"   → set target angle (Python control)
 * - "JOYSTICK"  → return control to joystick
 *
 * @param cmd Incoming command string
 */
void handleCommand(String cmd) {
  cmd.trim();
  cmd.toUpperCase();

  if (cmd == "AUTO") {
    currentMode = MODE_AUTO;
    pythonManualControlActive = false;
    return;
  }

  if (cmd == "MANUAL") {
    currentMode = MODE_MANUAL;
    return;
  }

  if (cmd.startsWith("ANGLE:")) {
    String valuePart = cmd.substring(6);
    int angleValue = valuePart.toInt();

    if (angleValue < (int)ANGLE_MIN) angleValue = (int)ANGLE_MIN;
    if (angleValue > (int)ANGLE_MAX) angleValue = (int)ANGLE_MAX;

    pythonTargetAngle = angleValue;
    pythonManualControlActive = true;
    currentMode = MODE_MANUAL;
    return;
  }

  if (cmd == "JOYSTICK") {
    pythonManualControlActive = false;
    currentMode = MODE_MANUAL;
    return;
  }
}

/**
 * @brief Reads serial input and reconstructs commands.
 *
 * Accumulates characters until newline is received,
 * then sends the full command to handleCommand().
 */
void readSerialCommands() {
  while (Serial.available() > 0) {
    char c = Serial.read();

    if (c == '\n' || c == '\r') {
      if (commandBuffer.length() > 0) {
        handleCommand(commandBuffer);
        commandBuffer = "";
      }
    } else {
      commandBuffer += c;
    }
  }
}

/**
 * @brief Initializes system components.
 *
 * - Sets pin modes
 * - Starts serial communication
 * - Attaches servo
 * - Sets initial position
 */
void setup() {
  Serial.begin(9600);

  pinMode(trigPin, OUTPUT);
  pinMode(echoPin, INPUT);
  pinMode(ledPin, OUTPUT);
  pinMode(joystickButtonPin, INPUT_PULLUP);

  radarServo.attach(servoPin);
  radarServo.write((int)currentAngle);

  delay(500);
}

/**
 * @brief Main execution loop.
 *
 * Handles:
 * - Serial communication
 * - Mode switching
 * - Servo updates (AUTO or MANUAL)
 * - Distance measurement
 * - LED control
 * - Data transmission to Python
 */
void loop() {
  unsigned long now = millis();

  readSerialCommands();
  updateModeButton();

  if (now - lastServoUpdate >= SERVO_UPDATE_MS) {
    lastServoUpdate = now;

    if (currentMode == MODE_MANUAL) {
      if (pythonManualControlActive) {
        updateServoManualPython();
      } else {
        updateServoManualJoystick();
      }
    } else {
      updateServoAuto();
    }
  }

  if (now - lastMeasureTime >= MEASURE_INTERVAL_MS) {
    lastMeasureTime = now;

    currentDistance = mesurerDistance();
    updateLed(currentDistance);
    sendSerialData((int)currentAngle, currentDistance, currentMode);
  }
}
