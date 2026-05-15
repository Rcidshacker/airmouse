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

# Thumb-pinch thresholds
THUMB_INDEX_CLICK_DIST  = 0.045   # thumb tip ↔ index tip → left click
THUMB_MIDDLE_CLICK_DIST = 0.050   # thumb tip ↔ middle tip → right click

# Legacy (kept for reference during migration — unused after Task 5)
CLICK_DISTANCE_THRESHOLD = 0.03
RIGHT_CLICK_DISTANCE_THRESHOLD = 0.06

DRAG_HOLD_SECONDS = 0.4           # thumb+index pinch held → drag activates
GESTURE_COOLDOWN_SECONDS = 0.4    # min gap between discrete gesture events

DOUBLE_CLICK_WINDOW_S = 0.4       # second pinch within this window = double click

# Fist detection — all finger tips must be below their PIP joints
FIST_CURL_THRESHOLD = 0.0         # unused numerically; fist = all 5 curled (boolean)

# Wrist scroll (peace-sign posture)
WRIST_VELOCITY_THRESHOLD = 0.008  # normalized units/s — minimum wrist flick to register
SCROLL_TICK_SCALE        = 0.003  # velocity / scale = tick count (clamped 1–5)
SCROLL_COOLDOWN_S        = 0.12   # minimum gap between scroll emissions

# Scroll: number of OS scroll ticks per gesture detection cycle (legacy fallback)
SCROLL_TICKS = 3

# Two-hand gestures
ZOOM_WRIST_DELTA    = 0.05        # normalized wrist-to-wrist distance change per zoom tick
LOCK_SCREEN_HOLD_S  = 1.0         # both fists held this long → Win+L

# ── Windows OS ────────────────────────────────────────────────────────────────
# Do not change these unless you understand the Windows scheduler implications.
TIMER_RESOLUTION_MS = 1          # Sets Windows multimedia timer floor to 1ms
# psutil priority constant: HIGH_PRIORITY_CLASS = 0x80
# Do NOT use REALTIME_PRIORITY_CLASS (0x100) — it can starve system threads.
PROCESS_PRIORITY = 0x80
