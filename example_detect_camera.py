import cv2
import mediapipe as mp
import numpy as np

mp_hands = mp.solutions.hands
draw = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    static_image_mode=False,
    model_complexity=0,
    max_num_hands=1,
    min_detection_confidence=0.6,
    min_tracking_confidence=0.6
)

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

# ===== helper =====
def dist(a, b):
    return np.linalg.norm(a - b)

def get_pts(hand):
    return np.array([[lm.x, lm.y, lm.z] for lm in hand.landmark])

def detect_gesture(pts):
    wrist = pts[0]

    thumb = pts[4]
    index = pts[8]
    middle = pts[12]
    ring = pts[16]
    pinky = pts[20]

    # khoảng cách đầu ngón → cổ tay
    d_index = dist(index, wrist)
    d_middle = dist(middle, wrist)
    d_ring = dist(ring, wrist)
    d_pinky = dist(pinky, wrist)

    # pinch
    if dist(thumb, index) < 0.04:
        return "PINCH"

    # point (ngón trỏ chìa ra, các ngón khác gập)
    if (
        d_index > 0.25 and
        d_middle < 0.2 and
        d_ring < 0.2 and
        d_pinky < 0.2 and
        index[2] < wrist[2] - 0.02   # dùng Z
    ):
        return "POINT"

    # fist
    if all(d < 0.2 for d in [d_index, d_middle, d_ring, d_pinky]):
        return "FIST"

    # open
    if all(d > 0.25 for d in [d_index, d_middle, d_ring, d_pinky]):
        return "OPEN"

    return "UNKNOWN"

# ===== main loop =====
while True:
    ret, frame = cap.read()
    if not ret:
        break

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    res = hands.process(rgb)

    if res.multi_hand_landmarks:
        for hand in res.multi_hand_landmarks:
            pts = get_pts(hand)
            gesture = detect_gesture(pts)

            draw.draw_landmarks(frame, hand, mp_hands.HAND_CONNECTIONS)

            cv2.putText(
                frame,
                gesture,
                (30, 50),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.2,
                (0, 255, 0),
                3
            )

    cv2.imshow("HAND GESTURE", frame)
    if cv2.waitKey(1) == 27:
        break

cap.release()
cv2.destroyAllWindows()
