import cv2
import mediapipe as mp
from qhue import Bridge

mp_hands = mp.solutions.hands.Hands()
# Place bridge IP and user ID here, bridge ID first then user ID.
b = Bridge("", '')
lights=b.lights

# Initialize the webcam
cap = cv2.VideoCapture(0)

while True:
    # Read a frame from the webcam
    ret, frame = cap.read()

    # Convert the frame to RGB
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Process the RGB frame with MediaPipe Hands
    results = mp_hands.process(rgb_frame)

    # Check if any hands are detected
    if results.multi_hand_landmarks:
        # Hand detected
        print("Hand detected")
        x=200
    else:
        # No hand detected
        print("No hand detected")
        x=0

    # Display the frame
    cv2.imshow('Hand Detection', frame)
# Specify your lights here, Ie: [1, 2, 3, 4]
    b.lights[3,2].state(bri=x, hue=300)
    # Exit the loop if 'q' is pressed
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release the webcam and close the window
cap.release()
cv2.destroyAllWindows()
