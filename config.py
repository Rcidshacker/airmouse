# config.py
# All tunable parameters for the AI Air Mouse system.
# Adjust these to calibrate for different environments; never scatter constants across modules.

# ── Camera ─────────────────────────────────────────────────────────────────────
CAMERA_INDEX = 0                  # Webcam device index
CAMERA_WIDTH = 1280               # Capture resolution width
CAMERA_HEIGHT = 720               # Capture resolution height
CAMERA_FPS = 60                   # Target capture FPS; webcam must support this
CAMERA_BUFFER_SIZE = 1            # DirectShow buffer: 1 = always freshest frame

# ── MediaPipe ──────────────────────────────────────────────────────────────────
MP_MODEL_PATH = "models/hand_landmarker.task"  # float16 Tasks API bundle
MP_MAX_HANDS = 1
MP_DETECTION_CONFIDENCE = 0.7
MP_TRACKING_CONFIDENCE = 0.5

# ── Virtual Trackpad ───────────────────────────────────────────────────────────
# Shrink the active tracking zone inward from webcam edges by this many pixels.
# Prevents the user needing to stretch their hand to screen corners.
TRACKPAD_MARGIN = 100             # pixels, applied to all four edges

# ── 1€ Filter ─────────────────────────────────────────────────────────────────
# Casiez et al. 2012 — adaptive low-pass filter for cursor smoothing.
# mincutoff: lower = more smoothing at rest (reduce jitter)
# beta: higher = less lag at high speed (reduce lag during fast motion)
# dcutoff: derivative smoothing; usually leave at 1.0
ONE_EURO_MINCUTOFF = 0.5           # lower = more smoothing at rest (less jitter)
ONE_EURO_BETA = 0.007
ONE_EURO_DCUTOFF = 1.0

# ── Gesture Thresholds ────────────────────────────────────────────────────────
# All distances are Euclidean norms of normalized MediaPipe coordinates [0.0–1.0].
# These are aspect-ratio independent.

CLICK_DISTANCE_THRESHOLD = 0.03   # Index–Middle pinch → Left click (tighter = fewer false fires)
RIGHT_CLICK_DISTANCE_THRESHOLD = 0.06  # Index–Ring pinch → Right click (looser = easier to trigger)
DRAG_HOLD_SECONDS = 0.4           # Pinch held this long → drag mode activates
GESTURE_COOLDOWN_SECONDS = 0.4   # Minimum gap between discrete gesture events

# Scroll: number of OS scroll ticks per gesture detection cycle
SCROLL_TICKS = 3

# ── Windows OS ────────────────────────────────────────────────────────────────
# Do not change these unless you understand the Windows scheduler implications.
TIMER_RESOLUTION_MS = 1          # Sets Windows multimedia timer floor to 1ms
# psutil priority constant: HIGH_PRIORITY_CLASS = 0x80
# Do NOT use REALTIME_PRIORITY_CLASS (0x100) — it can starve system threads.
PROCESS_PRIORITY = 0x80
