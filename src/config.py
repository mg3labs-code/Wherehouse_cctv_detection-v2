# """Configuration Module"""
# import logging

# class Config:
#     """GLS Safety System Configuration"""
    
#     # ====== CLASSES ======
#     CLASSES = {
#         0: 'person',
#         1: 'forklift',
#         2: 'safety_harness',
#         3: 'oil_tray',
#         4: 'wheel_stopper',
#         5: 'conveyor',
#         6: 'goods_pallet'
#     }
    
#     # ====== SAFETY THRESHOLDS ======
#     CONVEYOR_DANGER_DISTANCE = 150
#     WHEEL_STOPPER_RANGE = 100
#     FORKLIFT_SPEED_THRESHOLD = 100
#     MODEL_CONFIDENCE = 0.5
    
#     # ====== COLORS (BGR) ======
#     COLOR_PASS = (0, 255, 0)
#     COLOR_FAIL = (0, 0, 255)
#     COLOR_WARN = (0, 165, 255)
#     COLOR_INFO = (255, 0, 0)
    
#     # ====== TRAINING ======
#     EPOCHS = 150
#     BATCH_SIZE = 16
#     IMAGE_SIZE = 640
#     LEARNING_RATE = 0.01
#     PATIENCE = 30
#     GPU_DEVICE_ID = 'cpu'
    
#     # ====== PATHS ======
#     LOG_FILE = 'outputs/logs/gls_violations.log'
#     REPORT_FILE = 'outputs/reports/gls_report.json'
#     MODEL_PATH = 'runs/detect/yolov8_gls_safety/weights/best.pt'
    
#     @staticmethod
#     def setup_logging():
#         """Setup logging configuration"""
#         logging.basicConfig(
#             level=logging.INFO,
#             format='%(asctime)s - %(levelname)s - %(message)s',
#             handlers=[
#                 logging.FileHandler(Config.LOG_FILE),
#                 logging.StreamHandler()
#             ]
#         )
#         return logging.getLogger(__name__)

"""Configuration Module"""
import os
import logging

class Config:
    """GLS Safety System Configuration"""
    
    # ====== PROJECT PATHS ======
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR = os.path.join(PROJECT_ROOT, 'data')
    OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'outputs')
    
    # ====== DIRECTORY PATHS (REQUIRED BY MONITOR) ======
    LOG_DIR = os.path.join(OUTPUT_DIR, 'logs')
    REPORT_DIR = os.path.join(OUTPUT_DIR, 'reports')
    VIDEO_DIR = os.path.join(OUTPUT_DIR, 'videos')
    
    # ====== FILE PATHS ======
    LOG_FILE = os.path.join(LOG_DIR, 'gls_violations.log')
    REPORT_FILE = os.path.join(REPORT_DIR, 'gls_report.json')
    # Default detector: Ultralytics YOLO26 (COCO). YOLO-World is tried first when
    # the Windows regex DLL is available; otherwise YOLO26 is used.
    MODEL_PATH = os.path.join(PROJECT_ROOT, 'yolo26m.pt')
    
    # ====== CLASSES ======
    CLASSES = {
        0: 'person',
        1: 'forklift',
        2: 'safety_harness',
        3: 'oil_tray',
        4: 'wheel_stopper',
        5: 'conveyor',
        6: 'goods_pallet'
    }

    # Prompt classes for YOLO-World open-vocabulary detection
    # "warehouse forklift" scores much better than plain "forklift" on these cams
    WORLD_CLASSES = [
        'person',
        'warehouse forklift',
        'forklift',
        'hard hat',
        'helmet',
        'safety vest',
        'high visibility vest',
        'cardboard box',
        'pallet',
        'sack',
    ]

    # Map model class names -> GLS category (substring match, lowercase)
    CLASS_ALIASES = {
        'person': 'person',
        'forklift': 'forklift',
        'warehouse forklift': 'forklift',
        'industrial forklift': 'forklift',
        # Do NOT alias COCO 'truck' here — racks/sacks get false forklifts.
        # Truck→forklift is only allowed for YOLO-World in monitor._map_class_name.
        'safety harness': 'safety_harness',
        'safety_harness': 'safety_harness',
        'hard hat': 'helmet',
        'helmet': 'helmet',
        'safety vest': 'vest',
        'high visibility vest': 'vest',
        'vest': 'vest',
        'oil tray': 'oil_tray',
        'oil_tray': 'oil_tray',
        'wheel stopper': 'wheel_stopper',
        'wheel_stopper': 'wheel_stopper',
        'conveyor': 'conveyor',
        'conveyor belt': 'conveyor',
        'pallet': 'goods_pallet',
        'goods_pallet': 'goods_pallet',
        'cardboard box': 'box',
        'box': 'box',
        'sack': 'box',
    }

    DASHBOARD_TITLE = 'Hypervis Warehouse Safety Monitor - AI Powered'
    ZONE_NAME = 'Zone B - Aisle 4'
    
    # ====== SAFETY THRESHOLDS ======
    CONVEYOR_DANGER_DISTANCE = 150
    WHEEL_STOPPER_RANGE = 100
    FORKLIFT_SPEED_THRESHOLD = 100  # legacy px/s (kept for settings.yaml compat)
    # Warehouse aisle speed limit shown on UI / used for OVERSPEED alerts
    FORKLIFT_SPEED_LIMIT_KMH = 8.0
    # Approx real forklift height for px→m scale (cab+mast in frame)
    FORKLIFT_REF_HEIGHT_M = 2.2
    FORKLIFT_SPEED_EMA = 0.35  # smoothing (0..1); higher = more responsive
    FORKLIFT_TRACK_MAX_DIST = 160  # px match radius between frames
    FORKLIFT_TRACK_TTL = 1.5  # seconds before a lost track is dropped
    MODEL_CONFIDENCE = 0.25
    # Open-vocab warehouse forklift scores are typically low on these cams
    FORKLIFT_CONFIDENCE = 0.08
    PERSON_CONFIDENCE = 0.35
    INFER_IMGSZ = 960
    FORKLIFT_MIN_AREA = 800  # allow distant/small forklifts
    # Reject rack-side / oversized false forklifts (fraction of frame)
    FORKLIFT_MAX_WIDTH_FRAC = 0.30
    FORKLIFT_MAX_AREA_FRAC = 0.10
    FORKLIFT_AISLE_X_MIN = 0.24
    FORKLIFT_AISLE_X_MAX = 0.76
    # Hybrid fallback: blue beacon + red floor safety lights (ITC aisle cams)
    USE_FORKLIFT_LIGHT_DETECTOR = True
    # Extra YOLO aisle zooms are accurate but slow — off by default for realtime
    USE_AISLE_ZOOM = False
    FORKLIFT_MAX_DETS = 2

    # ====== CAMERA PROFILES ======
    # Config-driven, per-camera profile/zone file (see camera_profiles.py).
    # Overridable via env var for deployments that keep config outside the repo.
    CAMERA_CONFIG_PATH = os.environ.get(
        "HYPERVIS_CAMERA_CONFIG",
        os.path.join(PROJECT_ROOT, "config", "cameras.json"),
    )

    # ====== API SECURITY ======
    # Shared-secret API key required on every /api/* request (see api/app.py).
    # Set this via a real environment variable in your deployment — never
    # commit a real key to source control. No default: with none set, the
    # API refuses every request rather than silently running wide open.
    API_KEY = os.environ.get("HYPERVIS_API_KEY", "").strip()

    # Comma-separated list of exact origins allowed to call this API from a
    # browser (e.g. "https://your-dashboard.up.railway.app,http://localhost:5173").
    # Defaults to localhost dev origins only — set this explicitly for any
    # real deployment. Never use "*" once real cameras/data are involved.
    ALLOWED_ORIGINS = [
        o.strip()
        for o in os.environ.get(
            "HYPERVIS_ALLOWED_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        ).split(",")
        if o.strip()
    ]

    # ====== COLORS (BGR - OpenCV Format) ======
    COLORS = {
        'PASS': (0, 255, 0),      # Green
        'FAIL': (0, 0, 255),      # Red
        'WARN': (0, 165, 255),    # Orange
        'INFO': (255, 255, 0)     # Cyan
    }
    
    # Backward compatibility
    COLOR_PASS = (0, 255, 0)
    COLOR_FAIL = (0, 0, 255)
    COLOR_WARN = (0, 165, 255)
    COLOR_INFO = (255, 0, 0)
    
    # ====== TRAINING ======
    EPOCHS = 150
    BATCH_SIZE = 16
    IMAGE_SIZE = 640
    LEARNING_RATE = 0.01
    PATIENCE = 30
    GPU_DEVICE_ID = 'cpu'
    
    @staticmethod
    def setup_logging():
        """Setup logging configuration"""
        # Ensure log directory exists
        os.makedirs(Config.LOG_DIR, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(Config.LOG_FILE),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger(__name__)