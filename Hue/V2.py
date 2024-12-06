import cv2
import mediapipe as mp
from qhue import Bridge
import math

mp_hands = mp.solutions.hands.Hands(static_image_mode=False, max_num_hands=1, min_detection_confidence=0.7)
mp_draw = mp.solutions.drawing_utils
# Place bridge IP and user ID here, bridge ID first then user ID.
b = Bridge("", '')
# Specify your lights here, Ie: [1, 2, 3, 4]
LIGHT_IDS = [2, 3]
MAX_BRIGHTNESS, MIN_BRIGHTNESS = 254, 0
MAX_HUE, MIN_HUE = 65535, 0
lights = b.lights

def calculate_distance(p1, p2):
    return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)

def is_hand_closed(landmarks):
    wrist = landmarks[mp.solutions.hands.HandLandmark.WRIST]
    tips = [mp.solutions.hands.HandLandmark.THUMB_TIP, mp.solutions.hands.HandLandmark.INDEX_FINGER_TIP,
            mp.solutions.hands.HandLandmark.MIDDLE_FINGER_TIP, mp.solutions.hands.HandLandmark.RING_FINGER_TIP,
            mp.solutions.hands.HandLandmark.PINKY_TIP]
    return all(calculate_distance(landmarks[tip], wrist) < 0.2 for tip in tips)

def send_to_lights(brightness, hue):
    for light_id in LIGHT_IDS:
        try:
            lights[light_id].state(bri=brightness, hue=hue)
            print(f"Light {light_id} updated: Brightness={brightness}, Hue={hue}")
        except Exception as e:
            print(f"Error updating light {light_id}: {e}")

def process_hand(landmarks):
    wrist = landmarks[mp.solutions.hands.HandLandmark.WRIST]
    index_mcp = landmarks[mp.solutions.hands.HandLandmark.INDEX_FINGER_MCP]
    pinky_mcp = landmarks[mp.solutions.hands.HandLandmark.PINKY_MCP]

    brightness = int((1 - wrist.y) * MAX_BRIGHTNESS)
    brightness = max(MIN_BRIGHTNESS, min(MAX_BRIGHTNESS, brightness))

    hand_direction = math.atan2(pinky_mcp.y - index_mcp.y, pinky_mcp.x - index_mcp.x)
    hue = int((hand_direction + math.pi) / (2 * math.pi) * MAX_HUE)
    hue = max(MIN_HUE, min(MAX_HUE, hue))

    return brightness, hue

cap = cv2.VideoCapture(0)

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to grab frame.")
            break

        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = mp_hands.process(rgb_frame)

        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                landmarks = hand_landmarks.landmark
                if not is_hand_closed(landmarks):
                    brightness, hue = process_hand(landmarks)
                    send_to_lights(brightness, hue)
                    print(f"Hand Detected: Brightness={brightness}, Hue={hue}")
                else:
                    print("Hand is closed. No adjustments.")

                mp_draw.draw_landmarks(frame, hand_landmarks, mp.solutions.hands.HAND_CONNECTIONS)

        cv2.imshow('Brightness & Hue Control', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    cap.release()
    cv2.destroyAllWindows()
    print("Resources released.")
