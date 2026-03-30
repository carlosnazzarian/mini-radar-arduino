"""
==========================================================
MINI RADAR SYSTEM - PYTHON INTERFACE
==========================================================

Description:
Desktop radar interface for the Arduino-based Mini Radar System.

This application:
- Receives real-time angle, distance, and mode data from Arduino
- Displays a radar-style visualization using Pygame
- Supports AUTO and MANUAL modes
- Sends control commands back to Arduino through serial communication
- Provides on-screen controls for manual interaction

Main features:
- Real-time radar sweep visualization
- Persistent target rendering
- Interactive mode buttons
- Manual angle slider
- Serial communication with Arduino firmware

Dependencies:
- pyserial
- pygame

Author: Carlos Nazzarian
==========================================================
"""
import math
import time
import serial
import pygame

# =========================
# CONFIG
# =========================
PORT = "COM3"
BAUDRATE = 9600

WINDOW_WIDTH = 1400
WINDOW_HEIGHT = 820

MAX_DISPLAY_DISTANCE_CM = 200
DETECTION_THRESHOLD_CM = 50
MIN_VALID_DISTANCE_CM = 5
PERSISTENCE_SECONDS = 2.2

DEBUG_SERIAL = False

# =========================
# INIT SERIAL
# =========================
ser = serial.Serial(PORT, BAUDRATE, timeout=0.05)
time.sleep(2)

# =========================
# INIT PYGAME
# =========================
pygame.init()
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Mini Radar Arduino")
clock = pygame.time.Clock()

font_tiny = pygame.font.SysFont("consolas", 16)
font_small = pygame.font.SysFont("consolas", 20)
font_medium = pygame.font.SysFont("consolas", 28)
font_big = pygame.font.SysFont("consolas", 42, bold=True)

# =========================
# COLORS
# =========================
BLACK = (3, 8, 10)
PANEL_DARK = (8, 18, 20)
PANEL_BORDER = (20, 100, 85)

GREEN = (0, 255, 145)
GREEN_SOFT = (0, 170, 110)
GREEN_DIM = (0, 90, 60)
GREEN_FADE = (0, 55, 35)
GREEN_ULTRA_DIM = (0, 35, 25)

RED = (255, 72, 72)
ORANGE = (255, 180, 70)
CYAN = (80, 220, 255)
YELLOW = (255, 240, 110)
WHITE_GREEN = (220, 255, 235)
GRAY = (120, 140, 140)

# =========================
# LAYOUT
# =========================
LEFT_PANEL_X = 24
LEFT_PANEL_Y = 24
LEFT_PANEL_W = 360
LEFT_PANEL_H = WINDOW_HEIGHT - 48

RADAR_CENTER_X = 900
RADAR_CENTER_Y = WINDOW_HEIGHT - 85
RADAR_RADIUS = 520

BUTTON_W = 145
BUTTON_H = 52

SLIDER_X = LEFT_PANEL_X + 26
SLIDER_Y = LEFT_PANEL_Y + 630
SLIDER_W = 300
SLIDER_H = 8
SLIDER_HANDLE_R = 12

ANGLE_MIN = 20
ANGLE_MAX = 160

current_angle = 90
current_distance = 999
current_mode = "AUTO"

detections = []

manual_target_angle = 90
dragging_slider = False


def clamp(value, low, high):
    """
    Clamp a numeric value within a specified range.

    Parameters:
        value (int | float): Value to limit.
        low (int | float): Minimum allowed value.
        high (int | float): Maximum allowed value.

    Returns:
        int | float: Clamped value in the interval [low, high].
    """
    return max(low, min(high, value))


def polar_to_screen(angle_deg, distance_cm):
    """
    Convert radar polar coordinates to screen coordinates.

    The radar logic works with:
    - angle in degrees
    - distance in centimeters

    Pygame drawing requires:
    - x coordinate
    - y coordinate

    Parameters:
        angle_deg (float | int): Angle of the detected object in degrees.
        distance_cm (float | int): Distance of the detected object in centimeters.

    Returns:
        tuple[int, int]:
            Screen coordinates (x, y) corresponding to the radar position.
    """
    distance_cm = clamp(distance_cm, 0, MAX_DISPLAY_DISTANCE_CM)
    scaled = (distance_cm / MAX_DISPLAY_DISTANCE_CM) * RADAR_RADIUS

    rad = math.radians(angle_deg)
    x = RADAR_CENTER_X + scaled * math.cos(rad)
    y = RADAR_CENTER_Y - scaled * math.sin(rad)
    return int(x), int(y)


def send_command(command: str):
    """
    Send a text command to the Arduino through the serial port.

    A newline character is appended automatically so the Arduino can
    detect the end of the command.

    Supported command examples:
        "AUTO"
        "MANUAL"
        "JOYSTICK"
        "ANGLE:90"

    Parameters:
        command (str): Command string to send.

    Returns:
        None
    """
    try:
        ser.write((command + "\n").encode())
    except Exception as e:
        if DEBUG_SERIAL:
            print("Erreur envoi commande:", e)


def send_manual_angle(angle_value: int):
    """
    Send a manual target angle to the Arduino.

    The angle is clamped within the allowed servo range before being sent
    as a serial command in the form: ANGLE:<value>

    Parameters:
        angle_value (int): Desired servo angle in degrees.

    Returns:
        None
    """
    angle_value = int(clamp(angle_value, ANGLE_MIN, ANGLE_MAX))
    send_command(f"ANGLE:{angle_value}")


def draw_glow_line(surface, color, start_pos, end_pos):
    """
    Draw a glowing radar line using layered strokes.

    This function improves the visual appearance of the sweep line by
    drawing multiple lines of different thicknesses and intensities.

    Parameters:
        surface (pygame.Surface): Surface on which to draw.
        color (tuple[int, int, int]): Main RGB color of the glow.
        start_pos (tuple[int, int]): Start position (x, y).
        end_pos (tuple[int, int]): End position (x, y).

    Returns:
        None
    """
    pygame.draw.line(surface, (0, 60, 35), start_pos, end_pos, 9)
    pygame.draw.line(surface, (0, 95, 55), start_pos, end_pos, 5)
    pygame.draw.line(surface, color, start_pos, end_pos, 2)


def draw_panel():
    """
    Draw the left-side control and information panel.

    This panel contains:
    - title
    - live data cards
    - controls
    - footer text

    Returns:
        None
    """
    panel_rect = pygame.Rect(LEFT_PANEL_X, LEFT_PANEL_Y, LEFT_PANEL_W, LEFT_PANEL_H)
    pygame.draw.rect(screen, PANEL_DARK, panel_rect, border_radius=18)
    pygame.draw.rect(screen, PANEL_BORDER, panel_rect, 2, border_radius=18)


def draw_card(x, y, w, h, title, value, value_color):
    """
    Draw an information card in the side panel.

    Used for displaying live values such as:
    - angle
    - distance
    - status
    - mode

    Parameters:
        x (int): Left position of the card.
        y (int): Top position of the card.
        w (int): Card width.
        h (int): Card height.
        title (str): Card label.
        value (str): Main displayed value.
        value_color (tuple[int, int, int]): RGB color of the value text.

    Returns:
        None
    """
    rect = pygame.Rect(x, y, w, h)
    pygame.draw.rect(screen, (10, 24, 27), rect, border_radius=14)
    pygame.draw.rect(screen, (22, 110, 90), rect, 1, border_radius=14)

    title_surface = font_tiny.render(title, True, GREEN_SOFT)
    value_surface = font_medium.render(value, True, value_color)

    screen.blit(title_surface, (x + 16, y + 10))
    screen.blit(value_surface, (x + 16, y + 34))


def draw_radar_grid():
    """
    Draw the static radar background.

    This includes:
    - radar arcs
    - angle guide lines
    - distance labels
    - angle labels
    - center marker
    - horizontal baseline

    Returns:
        None
    """
    screen.fill(BLACK)

    for i in range(1, 6):
        r = int(RADAR_RADIUS * i / 5)
        rect = pygame.Rect(RADAR_CENTER_X - r, RADAR_CENTER_Y - r, 2 * r, 2 * r)
        width = 2 if i == 5 else 1
        color = GREEN_DIM if i == 5 else GREEN_ULTRA_DIM
        pygame.draw.arc(screen, color, rect, math.radians(180), math.radians(360), width)

    for angle in [30, 60, 90, 120, 150]:
        rad = math.radians(angle)
        x = RADAR_CENTER_X + RADAR_RADIUS * math.cos(rad)
        y = RADAR_CENTER_Y - RADAR_RADIUS * math.sin(rad)
        pygame.draw.line(screen, GREEN_ULTRA_DIM, (RADAR_CENTER_X, RADAR_CENTER_Y), (x, y), 1)

    pygame.draw.line(
        screen,
        GREEN_SOFT,
        (RADAR_CENTER_X - RADAR_RADIUS, RADAR_CENTER_Y),
        (RADAR_CENTER_X + RADAR_RADIUS, RADAR_CENTER_Y),
        2,
    )

    pygame.draw.circle(screen, GREEN_SOFT, (RADAR_CENTER_X, RADAR_CENTER_Y), 5)
    pygame.draw.circle(screen, GREEN_DIM, (RADAR_CENTER_X, RADAR_CENTER_Y), 12, 1)

    for i in range(1, 6):
        cm = int(MAX_DISPLAY_DISTANCE_CM * i / 5)
        r = int(RADAR_RADIUS * i / 5)
        txt = font_small.render(f"{cm} cm", True, GREEN_SOFT)
        screen.blit(txt, (RADAR_CENTER_X + 12, RADAR_CENTER_Y - r - 14))

    for angle in [30, 60, 90, 120, 150]:
        rad = math.radians(angle)
        x = RADAR_CENTER_X + (RADAR_RADIUS + 18) * math.cos(rad)
        y = RADAR_CENTER_Y - (RADAR_RADIUS + 18) * math.sin(rad)
        txt = font_tiny.render(f"{angle}°", True, GREEN_DIM)
        screen.blit(txt, (x - 10, y - 10))


def draw_sweep(angle_deg):
    """
    Draw the animated radar sweep line.

    The function renders:
    - the main current sweep line
    - trailing ghost lines for a motion effect

    Parameters:
        angle_deg (float | int): Current sweep angle in degrees.

    Returns:
        None
    """
    rad = math.radians(angle_deg)
    end_x = RADAR_CENTER_X + RADAR_RADIUS * math.cos(rad)
    end_y = RADAR_CENTER_Y - RADAR_RADIUS * math.sin(rad)

    for offset, alpha_strength in [(16, 20), (12, 30), (8, 45), (4, 65)]:
        ghost_angle = angle_deg - offset
        if ghost_angle < 0:
            continue
        grad = math.radians(ghost_angle)
        gx = RADAR_CENTER_X + RADAR_RADIUS * math.cos(grad)
        gy = RADAR_CENTER_Y - RADAR_RADIUS * math.sin(grad)
        pygame.draw.line(screen, (0, alpha_strength, alpha_strength // 2), (RADAR_CENTER_X, RADAR_CENTER_Y), (gx, gy), 2)

    draw_glow_line(screen, GREEN, (RADAR_CENTER_X, RADAR_CENTER_Y), (end_x, end_y))


def draw_target(x, y, color, size):
    """
    Draw a radar target marker with concentric visual effects.

    Parameters:
        x (int): Target x-coordinate on screen.
        y (int): Target y-coordinate on screen.
        color (tuple[int, int, int]): RGB color for the target.
        size (int): Radius of the main target marker.

    Returns:
        None
    """
    pygame.draw.circle(screen, (40, 40, 40), (x, y), size + 10)
    pygame.draw.circle(screen, color, (x, y), size + 5, 1)
    pygame.draw.circle(screen, color, (x, y), size + 10, 1)
    pygame.draw.circle(screen, color, (x, y), size)
    pygame.draw.circle(screen, WHITE_GREEN, (x, y), max(2, size // 3))


def draw_detections():
    """
    Draw and manage persistent target detections.

    Each detection is kept temporarily on screen using its timestamp.
    Old detections are discarded after PERSISTENCE_SECONDS.

    Behavior:
    - red targets for alert-range detections
    - orange targets for non-alert detections
    - progressive fade through size reduction over time

    Returns:
        None
    """
    global detections

    now = time.time()
    kept = []

    for d in detections:
        age = now - d["timestamp"]
        if age <= PERSISTENCE_SECONDS:
            x, y = polar_to_screen(d["angle"], d["distance"])

            age_ratio = 1.0 - (age / PERSISTENCE_SECONDS)
            if d["is_alert"]:
                color = RED
                size = int(5 + 3 * age_ratio)
            else:
                color = ORANGE
                size = int(4 + 2 * age_ratio)

            draw_target(x, y, color, size)
            kept.append(d)

    detections = kept


def angle_to_slider_x(angle_value):
    """
    Convert a servo angle to the horizontal position of the slider handle.

    Parameters:
        angle_value (int | float): Angle in degrees.

    Returns:
        int: X-coordinate of the slider handle on screen.
    """
    ratio = (angle_value - ANGLE_MIN) / (ANGLE_MAX - ANGLE_MIN)
    return int(SLIDER_X + ratio * SLIDER_W)


def slider_x_to_angle(mouse_x):
    """
    Convert a slider mouse position to a servo angle.

    Parameters:
        mouse_x (int): Horizontal mouse coordinate.

    Returns:
        int: Corresponding servo angle in degrees, clamped to valid bounds.
    """
    ratio = (mouse_x - SLIDER_X) / SLIDER_W
    ratio = clamp(ratio, 0.0, 1.0)
    return int(ANGLE_MIN + ratio * (ANGLE_MAX - ANGLE_MIN))


def draw_buttons(mouse_pos):
    """
    Draw the AUTO and MANUAL mode buttons.

    Button appearance changes depending on:
    - active mode
    - mouse hover state

    Parameters:
        mouse_pos (tuple[int, int]): Current mouse position.

    Returns:
        tuple[pygame.Rect, pygame.Rect]:
            Rectangle objects for the AUTO and MANUAL buttons,
            used later for click detection.
    """
    auto_rect = pygame.Rect(LEFT_PANEL_X + 26, LEFT_PANEL_Y + 340, BUTTON_W, BUTTON_H)
    manual_rect = pygame.Rect(LEFT_PANEL_X + 190, LEFT_PANEL_Y + 340, BUTTON_W, BUTTON_H)

    auto_active = current_mode == "AUTO"
    manual_active = current_mode == "MANUAL"

    auto_hover = auto_rect.collidepoint(mouse_pos)
    manual_hover = manual_rect.collidepoint(mouse_pos)

    def draw_button(rect, label, active, hover):
        if active:
            fill = (10, 40, 45)
            border = CYAN
            text_color = CYAN
        elif hover:
            fill = (14, 28, 30)
            border = GREEN_SOFT
            text_color = WHITE_GREEN
        else:
            fill = (10, 18, 20)
            border = GRAY
            text_color = GRAY

        pygame.draw.rect(screen, fill, rect, border_radius=12)
        pygame.draw.rect(screen, border, rect, 2, border_radius=12)

        txt = font_medium.render(label, True, text_color)
        txt_rect = txt.get_rect(center=rect.center)
        screen.blit(txt, txt_rect)

    draw_button(auto_rect, "AUTO", auto_active, auto_hover)
    draw_button(manual_rect, "MANUAL", manual_active, manual_hover)

    return auto_rect, manual_rect


def draw_manual_slider(mouse_pos):
    """
    Draw the manual angle slider and its handle.

    The slider is used to set the target servo angle visually in MANUAL mode.

    Parameters:
        mouse_pos (tuple[int, int]): Current mouse position.

    Returns:
        pygame.Rect:
            Clickable rectangle used for detecting slider interaction.
    """
    slider_bar_rect = pygame.Rect(SLIDER_X, SLIDER_Y, SLIDER_W, SLIDER_H)
    handle_x = angle_to_slider_x(manual_target_angle)
    handle_y = SLIDER_Y + SLIDER_H // 2

    screen.blit(font_small.render("MANUAL ANGLE", True, GREEN_SOFT), (SLIDER_X, SLIDER_Y - 34))
    value_txt = font_small.render(f"{manual_target_angle}°", True, CYAN if current_mode == "MANUAL" else GRAY)
    screen.blit(value_txt, (SLIDER_X + 220, SLIDER_Y - 34))

    pygame.draw.rect(screen, GREEN_ULTRA_DIM, slider_bar_rect, border_radius=6)
    pygame.draw.rect(screen, GREEN_DIM, slider_bar_rect, 1, border_radius=6)

    fill_rect = pygame.Rect(SLIDER_X, SLIDER_Y, handle_x - SLIDER_X, SLIDER_H)
    pygame.draw.rect(screen, (0, 110, 80), fill_rect, border_radius=6)

    handle_hover = math.hypot(mouse_pos[0] - handle_x, mouse_pos[1] - handle_y) <= 18
    handle_color = CYAN if (current_mode == "MANUAL" or handle_hover or dragging_slider) else GRAY

    pygame.draw.circle(screen, (15, 35, 40), (handle_x, handle_y), 14)
    pygame.draw.circle(screen, handle_color, (handle_x, handle_y), 12)
    pygame.draw.circle(screen, WHITE_GREEN, (handle_x, handle_y), 4)

    left_label = font_tiny.render(f"{ANGLE_MIN}°", True, GREEN_DIM)
    right_label = font_tiny.render(f"{ANGLE_MAX}°", True, GREEN_DIM)
    screen.blit(left_label, (SLIDER_X - 4, SLIDER_Y + 18))
    screen.blit(right_label, (SLIDER_X + SLIDER_W - 26, SLIDER_Y + 18))

    slider_hit_rect = pygame.Rect(SLIDER_X - 10, SLIDER_Y - 12, SLIDER_W + 20, 30)
    return slider_hit_rect


def draw_hud():
    """
    Draw the full side-panel user interface.

    This function renders:
    - application title
    - subtitle
    - live information cards
    - control instructions
    - footer message

    Returns:
        None
    """
    draw_panel()

    title = font_big.render("TACTICAL RADAR", True, GREEN)
    subtitle = font_tiny.render("Arduino • Ultrasonic • Servo", True, GREEN_SOFT)

    screen.blit(title, (LEFT_PANEL_X + 22, LEFT_PANEL_Y + 24))
    screen.blit(subtitle, (LEFT_PANEL_X + 24, LEFT_PANEL_Y + 74))

    draw_card(
        LEFT_PANEL_X + 22, LEFT_PANEL_Y + 120, 150, 88,
        "ANGLE", f"{current_angle:3d}°", GREEN
    )

    draw_card(
        LEFT_PANEL_X + 188, LEFT_PANEL_Y + 120, 150, 88,
        "DISTANCE", f"{current_distance:3d} cm", GREEN
    )

    detected = MIN_VALID_DISTANCE_CM <= current_distance <= DETECTION_THRESHOLD_CM
    status_text = "DETECTED" if detected else "CLEAR"
    status_color = RED if detected else GREEN

    draw_card(
        LEFT_PANEL_X + 22, LEFT_PANEL_Y + 225, 150, 88,
        "STATUS", status_text, status_color
    )

    mode_color = CYAN if current_mode == "MANUAL" else YELLOW
    draw_card(
        LEFT_PANEL_X + 188, LEFT_PANEL_Y + 225, 150, 88,
        "MODE", current_mode, mode_color
    )

    help_title = font_small.render("CONTROL", True, GREEN_SOFT)
    help_line_1 = font_tiny.render("Keyboard: A = AUTO, M = MANUAL", True, GRAY)
    help_line_2 = font_tiny.render("Mouse: click AUTO / MANUAL", True, GRAY)
    help_line_3 = font_tiny.render("In MANUAL, drag the slider below", True, GRAY)

    screen.blit(help_title, (LEFT_PANEL_X + 24, LEFT_PANEL_Y + 420))
    screen.blit(help_line_1, (LEFT_PANEL_X + 24, LEFT_PANEL_Y + 452))
    screen.blit(help_line_2, (LEFT_PANEL_X + 24, LEFT_PANEL_Y + 474))
    screen.blit(help_line_3, (LEFT_PANEL_X + 24, LEFT_PANEL_Y + 496))

    footer = font_tiny.render("Close the window to quit", True, GREEN_DIM)
    screen.blit(footer, (LEFT_PANEL_X + 24, LEFT_PANEL_Y + LEFT_PANEL_H - 28))


def read_serial_data():
    """
    Read and parse live data sent by the Arduino.

    Expected serial format:
        angle,distance,mode

    Example:
        90,42,AUTO

    Behavior:
    - validates format and values
    - updates current UI state
    - stores valid detections with timestamps

    Returns:
        None
    """
    global current_angle, current_distance, current_mode, detections

    try:
        line = ser.readline().decode(errors="ignore").strip()

        if DEBUG_SERIAL and line:
            print("RECU:", line)

        if not line or "," not in line:
            return

        parts = line.split(",")
        if len(parts) != 3:
            return

        angle = int(parts[0])
        distance = int(parts[1])
        mode = parts[2].strip().upper()

        if not (0 <= angle <= 180):
            return

        if mode not in ("AUTO", "MANUAL"):
            mode = "AUTO"

        current_angle = angle
        current_distance = distance
        current_mode = mode

        if MIN_VALID_DISTANCE_CM <= distance <= MAX_DISPLAY_DISTANCE_CM:
            detections.append({
                "angle": angle,
                "distance": distance,
                "timestamp": time.time(),
                "is_alert": distance <= DETECTION_THRESHOLD_CM
            })

    except Exception as e:
        if DEBUG_SERIAL:
            print("Erreur série:", e)


def main():
    """
    Run the main application loop.

    Responsibilities:
    - maintain frame rate
    - read serial data
    - render all visual elements
    - process keyboard and mouse events
    - send mode and angle commands to Arduino
    - restore joystick control on exit
    - close Pygame and serial resources cleanly

    Returns:
        None
    """
    global dragging_slider, manual_target_angle

    running = True

    while running:
        clock.tick(144)
        mouse_pos = pygame.mouse.get_pos()

        read_serial_data()

        draw_radar_grid()
        draw_sweep(current_angle)
        draw_detections()
        draw_hud()

        auto_rect, manual_rect = draw_buttons(mouse_pos)
        slider_rect = draw_manual_slider(mouse_pos)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_a:
                    send_command("AUTO")
                elif event.key == pygame.K_m:
                    send_command("MANUAL")
                elif event.key == pygame.K_LEFT and current_mode == "MANUAL":
                    manual_target_angle = max(ANGLE_MIN, manual_target_angle - 2)
                    send_manual_angle(manual_target_angle)
                elif event.key == pygame.K_RIGHT and current_mode == "MANUAL":
                    manual_target_angle = min(ANGLE_MAX, manual_target_angle + 2)
                    send_manual_angle(manual_target_angle)

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if auto_rect.collidepoint(event.pos):
                    send_command("AUTO")
                elif manual_rect.collidepoint(event.pos):
                    send_command("MANUAL")
                elif slider_rect.collidepoint(event.pos):
                    dragging_slider = True
                    manual_target_angle = slider_x_to_angle(event.pos[0])
                    send_manual_angle(manual_target_angle)

            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                dragging_slider = False

            elif event.type == pygame.MOUSEMOTION:
                if dragging_slider:
                    manual_target_angle = slider_x_to_angle(event.pos[0])
                    send_manual_angle(manual_target_angle)

        pygame.display.flip()
    try:
        send_command("JOYSTICK")
        time.sleep(0.2)
    except:
        pass
    pygame.quit()
    ser.close()


if __name__ == "__main__":
    main()
