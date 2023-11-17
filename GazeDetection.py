import cv2
import os
import pygame
import math
import time

# Open a video capture object (0 represents the default camera)
cap = cv2.VideoCapture(1)
icon_path = '/Users/afl/Documents/Uni/Year 2/Lectures/SEM1/AIED/Proj-TEST/icon'

# Variables to keep track of detected eyes and player's HP
detected_eyes = []
player_hp = 100
last_hp_update_time = time.time()

# Threshold for detecting gaze on the screen (adjust as needed)
initial_gaze_threshold = 90
dynamic_gaze_threshold = initial_gaze_threshold

# Cooldown period for notifications (in seconds)
notification_cooldown = 2
last_notification_time = 0

# Gradual increase parameters
gradual_increase_rate = 1  # HP restored per second
gradual_increase_delay = 10  # Delay before gradual increase starts

# Smooth eye tracking parameters
smoothing_factor = 5
previous_gaze_point = None

# Calibration phase parameters
calibration_frames = 200  # Adjust as needed
calibration_counter = 0
calibration_data = []

# Initialize pygame for sound
pygame.mixer.init()

# Load a sound file for the notification
notification_sound = pygame.mixer.Sound('/Users/afl/Documents/Uni/Year 2/Lectures/SEM1/AIED/Proj-TEST/sound.wav')  # Replace with the actual path to your sound file

while True:
    ret, frame = cap.read()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Calibration phase
    if calibration_counter < calibration_frames:
        faces = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml').detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

        # Reset the list of detected eyes for each frame
        detected_eyes = []

        for (x, y, w, h) in faces:
            roi_gray = gray[y:y + h, x:x + w]
            eyes = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml').detectMultiScale(
                roi_gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

            if len(eyes) >= 2 and eyes[0][0] < eyes[1][0]:
                for (ex, ey, ew, eh) in eyes:
                    eye_center_x = x + ex + ew // 2
                    eye_center_y = y + ey + eh // 2

                    detected_eyes.append((eye_center_x, eye_center_y))
                    calibration_data.append((eye_center_x, eye_center_y))

        calibration_counter += 1

        # Draw calibration progress on the frame
        cv2.putText(frame, f'Calibration: {calibration_counter}/{calibration_frames}', (10, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)

    else:
        # Calculate the average calibration point
        calibration_average = (
            sum(coord[0] for coord in calibration_data) // max(1, len(calibration_data)),
            sum(coord[1] for coord in calibration_data) // max(1, len(calibration_data))
        )

        # Detect faces in the frame
        faces = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml').detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

        # Reset the list of detected eyes for each frame
        detected_eyes = []

        for (x, y, w, h) in faces:
            roi_gray = gray[y:y + h, x:x + w]
            eyes = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_eye.xml').detectMultiScale(
                roi_gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

            if len(eyes) >= 2 and eyes[0][0] < eyes[1][0]:
                for (ex, ey, ew, eh) in eyes:
                    eye_center_x = x + ex + ew // 2
                    eye_center_y = y + ey + eh // 2

                    detected_eyes.append((eye_center_x, eye_center_y))

                    # Smooth eye tracking
                    if previous_gaze_point is not None:
                        eye_center_x = int(previous_gaze_point[0] + smoothing_factor * (eye_center_x - previous_gaze_point[0]))
                        eye_center_y = int(previous_gaze_point[1] + smoothing_factor * (eye_center_y - previous_gaze_point[1]))

                    previous_gaze_point = (eye_center_x, eye_center_y)

        # Draw ovals and crosses for the detected eyes
        for (eye_center_x, eye_center_y) in detected_eyes:
            eye_width = 30
            eye_height = 20
            cv2.ellipse(frame, (eye_center_x, eye_center_y), (eye_width, eye_height), 0, 0, 360, (255, 0, 0), 2)

            cross_size = 10
            cv2.line(frame, (eye_center_x - cross_size, eye_center_y), (eye_center_x + cross_size, eye_center_y),
                     (255, 255, 255), 2)
            cv2.line(frame, (eye_center_x, eye_center_y - cross_size), (eye_center_x, eye_center_y + cross_size),
                     (255, 255, 255), 2)

        # Display player's HP on the camera feed
        cv2.putText(frame, f'HP: {player_hp}', (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)

        # Check if both eyes are detected but not within the gaze threshold
        if len(detected_eyes) == 2:
            gaze_distance = math.sqrt((calibration_average[0] - eye_center_x) ** 2 + (
                        calibration_average[1] - eye_center_y) ** 2)

            dynamic_gaze_threshold = max(initial_gaze_threshold, gaze_distance * 0.8)

            # Check if the gaze is elsewhere other than the screen
            if gaze_distance > dynamic_gaze_threshold:
                current_time = time.time()
                if current_time - last_notification_time >= notification_cooldown:
                    player_hp -= 2

                    if player_hp <= 0:
                        os.system(
                            'osascript -e \'display notification "YOU HAVE BEEN CAUGHT CHEATING!" with title "Gaze Detection"\'')
                        print("\033[91mYOU HAVE BEEN CAUGHT CHEATING!\033[0m")
                        player_hp = 0

                    else:
                        os.system(
                            'osascript -e \'display notification "You are not looking at the screen!" with title "Gaze Detection"\'')
                        notification_sound.play()
                        print("\033[91mGaze detection: You are not looking at the screen!\033[0m")

                    last_notification_time = current_time

        # Regain 1 HP every second after a delay of 60 seconds without warnings
        if player_hp < 100:
            current_time = time.time()
            if current_time - last_hp_update_time >= gradual_increase_delay:
                player_hp = min(100, player_hp + gradual_increase_rate)
                last_hp_update_time = current_time

    # Display the resulting frame
    cv2.imshow('Gaze Detection', frame)

    # Break the loop when 'q' is pressed
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

# Release the video capture object and close the OpenCV window
cap.release()
cv2.destroyAllWindows()
