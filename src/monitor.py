# """Real-Time Compliance Monitoring Module"""
# import cv2
# import numpy as np
# from ultralytics import YOLO
# from datetime import datetime
# import json
# from .config import Config
# from .utils import calculate_distance, get_bbox_center

# class ComplianceMonitor:
#     """Warehouse Safety Compliance Monitor"""
    
#     def __init__(self, model_path):
#         self.model = YOLO(model_path)
#         self.logger = Config.setup_logging()
#         self.object_tracking = {}
#         self.violations = []
#         self.logger.info(f"Model loaded: {model_path}")
    
#     def check_conveyor(self, frame, detections):
#         """Check 1: Man near conveyor"""
#         violations = []
#         people, conveyors = [], []
        
#         for det in detections:
#             cls = int(det.cls[0])
#             x1, y1, x2, y2 = det.xyxy[0].cpu().numpy()
            
#             if cls == 0 and det.conf[0] > 0.6:
#                 people.append((x1, y1, x2, y2))
#             elif cls == 5:
#                 conveyors.append((x1, y1, x2, y2))
        
#         for px1, py1, px2, py2 in people:
#             pc = get_bbox_center((px1, py1, px2, py2))
#             for cx1, cy1, cx2, cy2 in conveyors:
#                 cc = get_bbox_center((cx1, cy1, cx2, cy2))
#                 dist = calculate_distance(pc, cc)
                
#                 if dist < Config.CONVEYOR_DANGER_DISTANCE:
#                     violations.append({'type': 'MAN_NEAR_CONVEYOR', 'severity': 'HIGH'})
#                     cv2.putText(frame, 'ALERT: PERSON NEAR CONVEYOR!', (10, 50),
#                                cv2.FONT_HERSHEY_SIMPLEX, 1.2, Config.COLOR_FAIL, 3)
#                     self.logger.warning('VIOLATION: Person near conveyor')
        
#         return violations
    
#     def check_harness(self, frame, detections):
#         """Check 2: Safety harness"""
#         violations = []
#         people, harness = [], []
        
#         for det in detections:
#             cls = int(det.cls[0])
#             x1, y1, x2, y2 = det.xyxy[0].cpu().numpy()
            
#             if cls == 0 and det.conf[0] > 0.6:
#                 people.append((x1, y1, x2, y2))
#             elif cls == 2:
#                 harness.append((x1, y1, x2, y2))
        
#         for px1, py1, px2, py2 in people:
#             pc = (px1 + px2) / 2
#             has_harness = any(hx1 < pc < hx2 and hy1 < py2 
#                             for hx1, hy1, hx2, hy2 in harness)
            
#             if not has_harness:
#                 violations.append({'type': 'NO_SAFETY_HARNESS', 'severity': 'CRITICAL'})
#                 cv2.rectangle(frame, (int(px1), int(py1)), (int(px2), int(py2)), 
#                             Config.COLOR_FAIL, 3)
#                 cv2.putText(frame, 'NO HARNESS!', (int(px1), int(py1) - 15),
#                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, Config.COLOR_FAIL, 2)
#                 self.logger.warning('VIOLATION: No safety harness')
        
#         return violations
    
#     def check_oil_tray(self, frame, detections):
#         """Check 3: Oil tray presence"""
#         violations = []
#         forklifts, trays = [], []
        
#         for det in detections:
#             cls = int(det.cls[0])
#             x1, y1, x2, y2 = det.xyxy[0].cpu().numpy()
            
#             if cls == 1:
#                 forklifts.append((x1, y1, x2, y2))
#             elif cls == 3:
#                 trays.append((x1, y1, x2, y2))
        
#         for fx1, fy1, fx2, fy2 in forklifts:
#             fc = (fx1 + fx2) / 2
#             has_tray = any(ox1 < fc < ox2 and oy1 < fy2 < oy2 + 50 
#                           for ox1, oy1, ox2, oy2 in trays)
            
#             if not has_tray:
#                 violations.append({'type': 'MISSING_OIL_TRAY', 'severity': 'HIGH'})
#                 cv2.rectangle(frame, (int(fx1), int(fy1)), (int(fx2), int(fy2)), 
#                             Config.COLOR_WARN, 3)
#                 cv2.putText(frame, 'NO OIL TRAY!', (int(fx1), int(fy1) - 15),
#                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, Config.COLOR_WARN, 2)
#                 self.logger.warning('VIOLATION: Oil tray missing')
        
#         return violations
    
#     def check_wheel_stopper(self, frame, detections):
#         """Check 4: Wheel stopper"""
#         violations = []
#         vehicles, stoppers = [], []
        
#         for det in detections:
#             cls = int(det.cls[0])
#             x1, y1, x2, y2 = det.xyxy[0].cpu().numpy()
            
#             if cls == 1:
#                 vehicles.append((x1, y1, x2, y2))
#             elif cls == 4:
#                 stoppers.append((x1, y1, x2, y2))
        
#         for vx1, vy1, vx2, vy2 in vehicles:
#             vc = ((vx1 + vx2) / 2, vy2)
#             has_stopper = any(calculate_distance(vc, ((sx1 + sx2) / 2, sy2)) 
#                             < Config.WHEEL_STOPPER_RANGE
#                             for sx1, sy1, sx2, sy2 in stoppers)
            
#             if not has_stopper:
#                 violations.append({'type': 'MISSING_WHEEL_STOPPER', 'severity': 'MEDIUM'})
#                 cv2.rectangle(frame, (int(vx1), int(vy1)), (int(vx2), int(vy2)), 
#                             Config.COLOR_INFO, 3)
#                 cv2.putText(frame, 'NO STOPPER!', (int(vx1), int(vy1) - 15),
#                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, Config.COLOR_INFO, 2)
#                 self.logger.warning('VIOLATION: Wheel stopper missing')
        
#         return violations
    
#     def check_speed(self, detections, frame_time):
#         """Check 5: Forklift speed"""
#         violations = []
        
#         for det in detections:
#             if int(det.cls[0]) != 1:
#                 continue
            
#             x1, y1, x2, y2 = det.xyxy[0].cpu().numpy()
#             bid = f"forklift_{int(x1)}_{int(y1)}"
#             center = ((x1 + x2) / 2, (y1 + y2) / 2)
            
#             if bid in self.object_tracking:
#                 pc = self.object_tracking[bid]['center']
#                 pt = self.object_tracking[bid]['time']
                
#                 pixels_moved = calculate_distance(center, pc)
#                 time_diff = frame_time - pt
                
#                 if time_diff > 0:
#                     speed = pixels_moved / time_diff
                    
#                     if speed > Config.FORKLIFT_SPEED_THRESHOLD:
#                         violations.append({'type': 'FORKLIFT_OVERSPEED', 'severity': 'HIGH'})
#                         self.logger.warning(f'VIOLATION: Overspeed {speed:.1f}')
            
#             self.object_tracking[bid] = {'center': center, 'time': frame_time}
        
#         return violations
    
#     def process_frame(self, frame):
#         """Process frame with all checks"""
#         import time
#         frame_time = time.time()
        
#         results = self.model(frame, conf=Config.MODEL_CONFIDENCE)
#         detections = results[0].boxes
#         annotated = results[0].plot()
        
#         violations = []
#         violations += self.check_conveyor(annotated, detections)
#         violations += self.check_harness(annotated, detections)
#         violations += self.check_oil_tray(annotated, detections)
#         violations += self.check_wheel_stopper(annotated, detections)
#         violations += self.check_speed(detections, frame_time)
        
#         self.violations.extend(violations)
#         self.draw_dashboard(annotated, violations)
        
#         return annotated, violations
    
#     def draw_dashboard(self, frame, violations):
#         """Draw compliance dashboard"""
#         cv2.rectangle(frame, (10, 10), (400, 180), (0, 0, 0), -1)
#         cv2.rectangle(frame, (10, 10), (400, 180), (255, 255, 255), 2)
        
#         checks = [
#             ('1. Conveyor', len([v for v in violations if v['type'] == 'MAN_NEAR_CONVEYOR'])),
#             ('2. Harness', len([v for v in violations if v['type'] == 'NO_SAFETY_HARNESS'])),
#             ('3. Oil Tray', len([v for v in violations if v['type'] == 'MISSING_OIL_TRAY'])),
#             ('4. Stopper', len([v for v in violations if v['type'] == 'MISSING_WHEEL_STOPPER'])),
#             ('5. Speed', len([v for v in violations if v['type'] == 'FORKLIFT_OVERSPEED']))
#         ]
        
#         y = 35
#         for name, count in checks:
#             color = Config.COLOR_PASS if count == 0 else Config.COLOR_FAIL
#             status = 'PASS' if count == 0 else f'FAIL ({count})'
#             cv2.putText(frame, f'{name}: {status}', (20, y),
#                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 1)
#             y += 30
        
#         total = len(violations)
#         color = Config.COLOR_PASS if total == 0 else Config.COLOR_FAIL
#         cv2.putText(frame, f'TOTAL: {total}', (20, y + 10),
#                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    
#     def save_report(self, filepath=None):
#         """Save violation report"""
#         if filepath is None:
#             filepath = Config.REPORT_FILE
        
#         report = {
#             'timestamp': datetime.now().isoformat(),
#             'total_violations': len(self.violations),
#             'violations': self.violations
#         }
        
#         with open(filepath, 'w') as f:
#             json.dump(report, f, indent=2)
        
#         self.logger.info(f'Report saved: {filepath}')

#         # Add this to src/monitor.py __init__ method:

# def __init__(self, model_path):
#     import os
    
#     # If model doesn't exist, use pre-trained CPU mode
#     if not os.path.exists(model_path):
#         print("Using pre-trained YOLOv8 model on CPU...")
#         model_path = 'yolov8m.pt'
    
#     # Force CPU
#     self.model = YOLO(model_path)
#     self.device = 'cpu'
    
#     self.logger = setup_logging()
#     self.object_tracking = {}
#     self.violation_log = []
#     self.logger.info(f"Model loaded on CPU: {model_path}")

# # """Professional Multi-Camera Warehouse Safety Monitoring System"""
# # import cv2
# # import numpy as np
# # from ultralytics import YOLO
# # from datetime import datetime
# # import json
# # import logging
# # from collections import defaultdict

# # class ProfessionalComplianceMonitor:
# #     """Professional Warehouse Safety Compliance Monitor with Multi-Camera Dashboard"""
    
# #     # Color scheme - Professional
# #     COLOR_PASS = (0, 200, 0)        # Green
# #     COLOR_FAIL = (0, 0, 255)        # Red
# #     COLOR_WARN = (0, 165, 255)      # Orange
# #     COLOR_TEXT = (255, 255, 255)    # White
# #     COLOR_BG = (30, 30, 30)         # Dark gray
# #     COLOR_ACCENT = (0, 200, 200)    # Cyan
    
# #     def __init__(self, model_path):
# #         import os
# #         if not os.path.exists(model_path):
# #             print("Using pre-trained YOLOv8 model on CPU...")
# #             model_path = 'yolov8m.pt'
        
# #         self.model = YOLO(model_path)
# #         self.setup_logging()
        
# #         # Tracking
# #         self.object_tracking = defaultdict(dict)
# #         self.violations = []
# #         self.frame_count = 0
# #         self.start_time = datetime.now()
        
# #         # Multi-camera data
# #         self.camera_data = {
# #             'cam1': {'name': 'FORKLIFT AISLE', 'violations': [], 'fps': 0, 'people': 0, 'forklifts': 0},
# #             'cam2': {'name': 'CONVEYOR', 'violations': [], 'fps': 0, 'people': 0, 'objects': 0},
# #             'cam3': {'name': 'HARNESS CHECK', 'violations': [], 'fps': 0, 'people': 0, 'harness': 0},
# #             'cam4': {'name': 'PPE DETECTION', 'violations': [], 'fps': 0, 'people': 0, 'ppe': 0}
# #         }
        
# #         self.logger.info("Professional Monitor Initialized - Multi-Camera Mode")
    
# #     def setup_logging(self):
# #         """Setup logging"""
# #         self.logger = logging.getLogger('GLS_Monitor')
# #         if not self.logger.handlers:
# #             handler = logging.FileHandler('outputs/logs/gls_violations.log')
# #             formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
# #             handler.setFormatter(formatter)
# #             self.logger.addHandler(handler)
# #             self.logger.setLevel(logging.INFO)
    
# #     def check_conveyor_safety(self, frame, detections):
# #         """Check 1: Man Movement Near Conveyor"""
# #         violations = []
# #         people_detected = 0
        
# #         for det in detections:
# #             cls = int(det.cls[0])
# #             conf = float(det.conf[0])
# #             x1, y1, x2, y2 = det.xyxy[0].cpu().numpy()
            
# #             if cls == 0 and conf > 0.5:  # Person
# #                 people_detected += 1
# #                 cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), 
# #                             self.COLOR_ACCENT, 2)
# #                 cv2.putText(frame, f'Person {conf:.2f}', (int(x1), int(y1) - 10),
# #                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.COLOR_TEXT, 2)
# #                 violations.append('Person detected near conveyor')
            
# #             elif cls == 5 and conf > 0.5:  # Conveyor
# #                 cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), 
# #                             self.COLOR_WARN, 2)
        
# #         return violations, people_detected
    
# #     def check_harness_compliance(self, frame, detections):
# #         """Check 2: Safety Harness Compliance"""
# #         violations = []
# #         people_detected = 0
# #         harness_detected = 0
        
# #         for det in detections:
# #             cls = int(det.cls[0])
# #             conf = float(det.conf[0])
# #             x1, y1, x2, y2 = det.xyxy[0].cpu().numpy()
            
# #             if cls == 0 and conf > 0.5:  # Person
# #                 people_detected += 1
# #                 color = self.COLOR_PASS
# #                 status = "OK"
                
# #                 # Check if harness detected
# #                 has_harness = any(int(d.cls[0]) == 2 and float(d.conf[0]) > 0.5 
# #                                  for d in detections)
                
# #                 if not has_harness:
# #                     violations.append(f'No Harness {conf:.2f}')
# #                     color = self.COLOR_FAIL
# #                     status = "NO HARNESS"
# #                 else:
# #                     harness_detected += 1
                
# #                 cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
# #                 cv2.putText(frame, status, (int(x1), int(y1) - 10),
# #                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
        
# #         return violations, people_detected, harness_detected
    
# #     def check_ppe_detection(self, frame, detections):
# #         """Check 3 & 4: PPE Detection (Helmet, Harness)"""
# #         violations = []
# #         people_detected = 0
# #         ppe_count = 0
        
# #         for det in detections:
# #             cls = int(det.cls[0])
# #             conf = float(det.conf[0])
# #             x1, y1, x2, y2 = det.xyxy[0].cpu().numpy()
            
# #             if cls == 0 and conf > 0.5:  # Person
# #                 people_detected += 1
                
# #                 # Check for helmet and harness
# #                 has_helmet = any(int(d.cls[0]) == 2 for d in detections if float(d.conf[0]) > 0.5)
# #                 has_harness = any(int(d.cls[0]) == 2 for d in detections if float(d.conf[0]) > 0.5)
                
# #                 if not has_helmet:
# #                     violations.append(f'No Helmet {conf:.2f}')
# #                 if not has_harness:
# #                     violations.append(f'No Harness {conf:.2f}')
                
# #                 color = self.COLOR_PASS if (has_helmet and has_harness) else self.COLOR_FAIL
# #                 cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
                
# #                 status = "WITH PPE" if (has_helmet and has_harness) else "MISSING PPE"
# #                 cv2.putText(frame, status, (int(x1), int(y1) - 10),
# #                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                
# #                 if has_helmet and has_harness:
# #                     ppe_count += 1
        
# #         return violations, people_detected, ppe_count
    
# #     def check_forklift_operations(self, frame, detections):
# #         """Check 5: Forklift Speed & Distance to Workers"""
# #         violations = []
# #         forklift_detected = 0
# #         people_detected = 0
        
# #         people_boxes = []
# #         forklift_boxes = []
        
# #         for det in detections:
# #             cls = int(det.cls[0])
# #             conf = float(det.conf[0])
# #             x1, y1, x2, y2 = det.xyxy[0].cpu().numpy()
            
# #             if cls == 0 and conf > 0.5:  # Person
# #                 people_detected += 1
# #                 people_boxes.append((int(x1), int(y1), int(x2), int(y2)))
# #                 cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), 
# #                             self.COLOR_ACCENT, 2)
            
# #             elif cls == 1 and conf > 0.5:  # Forklift
# #                 forklift_detected += 1
# #                 forklift_boxes.append((int(x1), int(y1), int(x2), int(y2)))
                
# #                 # Draw forklift
# #                 cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), 
# #                             self.COLOR_WARN, 3)
# #                 cv2.putText(frame, f'Forklift {conf:.2f}', (int(x1), int(y1) - 15),
# #                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, self.COLOR_WARN, 2)
                
# #                 # Calculate speed (simulated)
# #                 speed_kmh = 12.6  # Simulated speed
# #                 speed_limit = 8.0
                
# #                 if speed_kmh > speed_limit:
# #                     violations.append(f'Overspeed: {speed_kmh} km/h')
# #                     cv2.putText(frame, f'Speed: {speed_kmh} km/h (LIMIT: {speed_limit})',
# #                                (int(x1), int(y2) + 25),
# #                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.COLOR_FAIL, 2)
# #                 else:
# #                     cv2.putText(frame, f'Speed: {speed_kmh} km/h (OK)',
# #                                (int(x1), int(y2) + 25),
# #                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.COLOR_PASS, 2)
                
# #                 # Check distance to people
# #                 for px1, py1, px2, py2 in people_boxes:
# #                     dist = ((x1 + x2)/2 - (px1 + px2)/2)**2 + ((y1 + y2)/2 - (py1 + py2)/2)**2
# #                     dist = int(dist ** 0.5)
                    
# #                     if dist < 300:  # Danger zone
# #                         violations.append(f'Collision Risk: {dist}px')
# #                         cv2.line(frame, (int((x1+x2)/2), int((y1+y2)/2)), 
# #                                 (int((px1+px2)/2), int((py1+py2)/2)), 
# #                                 self.COLOR_FAIL, 2)
        
# #         return violations, people_detected, forklift_detected
    
# #     def create_professional_dashboard(self, frames, all_violations):
# #         """Create 2x2 multi-camera professional dashboard"""
# #         h, w = 720, 960  # Dashboard size per camera
        
# #         # Create 2x2 grid
# #         dashboard = np.zeros((h * 2, w * 2, 3), dtype=np.uint8)
# #         dashboard[:] = (30, 30, 30)  # Dark background
        
# #         # Process each camera
# #         cameras = [
# #             ('cam1', frames[0] if len(frames) > 0 else np.zeros((h, w, 3), dtype=np.uint8), 
# #              'FORKLIFT AISLE', all_violations[0] if all_violations else []),
# #             ('cam2', frames[1] if len(frames) > 1 else np.zeros((h, w, 3), dtype=np.uint8), 
# #              'CONVEYOR', all_violations[1] if len(all_violations) > 1 else []),
# #             ('cam3', frames[2] if len(frames) > 2 else np.zeros((h, w, 3), dtype=np.uint8), 
# #              'HARNESS CHECK', all_violations[2] if len(all_violations) > 2 else []),
# #             ('cam4', frames[3] if len(frames) > 3 else np.zeros((h, w, 3), dtype=np.uint8), 
# #              'PPE DETECTION', all_violations[3] if len(all_violations) > 3 else [])
# #         ]
        
# #         positions = [(0, 0), (0, w), (h, 0), (h, w)]
        
# #         for idx, (cam_id, frame, name, violations) in enumerate(cameras):
# #             y, x = positions[idx]
            
# #             # Resize frame to fit
# #             resized = cv2.resize(frame, (w, h))
            
# #             # Add camera header with professional styling
# #             cv2.rectangle(resized, (0, 0), (w, 60), (0, 0, 0), -1)
# #             cv2.rectangle(resized, (0, 0), (w, 60), (0, 200, 200), 2)
            
# #             # Camera name and FPS
# #             cv2.putText(resized, f'{name}', (20, 35),
# #                        cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 200, 200), 2)
# #             cv2.putText(resized, f'FPS: 4.3', (w - 150, 35),
# #                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
            
# #             # Add violations summary
# #             violation_text = f'Violations: {len(violations)}'
# #             color = (0, 200, 0) if len(violations) == 0 else (0, 0, 255)
# #             cv2.putText(resized, violation_text, (20, h - 20),
# #                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            
# #             # Place in dashboard
# #             dashboard[y:y+h, x:x+w] = resized
        
# #         # Add global status panel
# #         self.draw_global_status(dashboard, all_violations)
        
# #         return dashboard
    
# #     def draw_global_status(self, dashboard, all_violations):
# #         """Draw global compliance status"""
# #         total_violations = sum(len(v) for v in all_violations)
        
# #         # Status panel at bottom
# #         status_y = dashboard.shape[0] - 80
# #         cv2.rectangle(dashboard, (10, status_y), (dashboard.shape[1] - 10, dashboard.shape[0] - 10),
# #                      (0, 0, 0), -1)
# #         cv2.rectangle(dashboard, (10, status_y), (dashboard.shape[1] - 10, dashboard.shape[0] - 10),
# #                      (0, 200, 200), 2)
        
# #         status_color = (0, 200, 0) if total_violations == 0 else (0, 0, 255)
# #         status_text = "ALL SYSTEMS GREEN" if total_violations == 0 else f"⚠ {total_violations} VIOLATIONS"
        
# #         cv2.putText(dashboard, status_text, (30, status_y + 45),
# #                    cv2.FONT_HERSHEY_SIMPLEX, 1.3, status_color, 3)
        
# #         timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
# #         cv2.putText(dashboard, timestamp, (dashboard.shape[1] - 400, status_y + 45),
# #                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)
    
# #     def process_frame(self, frame):
# #         """Process single camera frame"""
# #         results = self.model(frame, conf=0.5)
# #         detections = results[0].boxes
# #         annotated = frame.copy()
        
# #         # Run all checks
# #         conv_violations, people1 = self.check_conveyor_safety(annotated, detections)
# #         harness_violations, people2, harness_count = self.check_harness_compliance(annotated, detections)
# #         ppe_violations, people3, ppe_count = self.check_ppe_detection(annotated, detections)
# #         forklift_violations, people4, forklift_count = self.check_forklift_operations(annotated, detections)
        
# #         all_violations = conv_violations + harness_violations + ppe_violations + forklift_violations
# #         self.violations.extend(all_violations)
        
# #         return annotated, all_violations
    
# #     def save_report(self, filepath='outputs/reports/gls_report.json'):
# #         """Save detailed violation report"""
# #         report = {
# #             'timestamp': datetime.now().isoformat(),
# #             'total_violations': len(self.violations),
# #             'violations': self.violations,
# #             'duration': str(datetime.now() - self.start_time)
# #         }
        
# #         import os
# #         os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
# #         with open(filepath, 'w') as f:
# #             json.dump(report, f, indent=2)
        
# #         self.logger.info(f'Professional report saved: {filepath}')

"""Real-Time Compliance Monitoring Module"""
import os
import cv2
import numpy as np
import json
import time
from datetime import datetime
from ultralytics import YOLO
from .config import Config
from .utils import calculate_distance, get_bbox_center, ensure_directories, detect_yellow_aisle_lines
from .dashboard import render_dashboard


def _regex_blocked() -> bool:
    """Windows Application Control may block regex/*.pyd on Python 3.14."""
    try:
        import regex  # noqa: F401
        return False
    except Exception as e:
        msg = str(e)
        return (
            '_regex' in msg
            or 'Application Control' in msg
            or 'DLL load failed' in msg
        )


def _coco_fallback_candidates(root):
    """Standard COCO detectors used when YOLO-World cannot load."""
    return [
        os.path.join(root, 'yolo26m.pt'),
        os.path.join(root, 'yolo26s.pt'),
        os.path.join(root, 'yolo26n.pt'),
        'yolo26m.pt',
        os.path.join(root, 'yolov8m.pt'),
        os.path.join(root, 'runs', 'detect', 'runs', 'detect',
                     'yolov8_gls_safety-3', 'weights', 'best.pt'),
        'yolov8m.pt',
    ]


def resolve_model_path(model_path=None):
    """Pick detector weights. Default is YOLO26; YOLO-World only if explicitly passed."""
    candidates = []
    if model_path:
        candidates.append(model_path)

    root = Config.PROJECT_ROOT
    # Primary: Ultralytics YOLO26 (works even when Windows blocks YOLO-World/regex)
    candidates.append(Config.MODEL_PATH)
    candidates.extend(_coco_fallback_candidates(root))

    # Optional open-vocab World model only when regex DLL is usable and file exists
    if not _regex_blocked():
        candidates.append(os.path.join(root, 'yolov8s-worldv2.pt'))
        candidates.append('yolov8s-worldv2.pt')
    elif model_path and 'world' in os.path.basename(str(model_path)).lower():
        print("Note: regex DLL blocked — YOLO-World may fail; prefer yolo26m.pt")

    seen = set()
    for path in candidates:
        if not path or path in seen:
            continue
        seen.add(path)
        if os.path.exists(path):
            return path
    return model_path or Config.MODEL_PATH


class ComplianceMonitor:
    """Warehouse Safety Compliance Monitor"""

    def __init__(self, model_path=None, profile=None):
        ensure_directories()
        self.config = Config
        from .camera_profiles import is_project16, is_safe_route, is_sawant_forklift, resolve_profile
        self.profile = profile if profile is not None else resolve_profile()
        self.is_project16 = is_project16(self.profile)
        self.is_safe_route = is_safe_route(self.profile)
        self.is_sawant = is_sawant_forklift(self.profile)
        self._enable_yellow_lines = bool(self.profile.get("enable_yellow_lines", True))
        self._enable_forklift_detect = bool(self.profile.get("enable_forklift_detect", True))
        self._enable_forklift_lights = bool(
            self.profile.get("enable_forklift_lights", True)
        ) and self._enable_forklift_detect
        self._map_coco_vehicles = bool(self.profile.get("map_coco_vehicles", False))
        self._detect_yellow_forklift = bool(
            self.profile.get("detect_yellow_forklift", False)
        ) and self._enable_forklift_detect
        # Generalized, camera-agnostic person<->forklift proximity/danger-zone
        # check (see danger_zone.py). Replaces per-video hardcoded logic that
        # never existed for this before — the only prior proximity check was
        # person<->conveyor, and conveyors are never actually detected since
        # no custom model was ever trained for that class.
        from .danger_zone import DangerZoneChecker
        self._danger_zone_checker = DangerZoneChecker.from_profile(self.profile)
        self._route_distance_m = 0.0
        self._route_last_center = None
        self._route_t0 = None
        # Temporal lock for Safe Route — hard-freeze after first solid Left+Right
        self._safe_route_locked = {}
        self._safe_route_frame_i = 0
        self._safe_route_frozen = False
        self._safe_route_overlay = None  # exact points + label coords (never moves)
        # Same hard-freeze for warehouse Aisle Road Way (GODOWN-1 / NO-2A)
        self._aisle_road_frozen = False
        self._aisle_road_overlay = None
        self._aisle_road_frame_i = 0
        self.last_stats = {}
        self.last_overlay = None

        model_path = resolve_model_path(model_path)
        self.model_path = model_path
        self.is_world = 'world' in os.path.basename(model_path).lower()

        try:
            self.model = YOLO(model_path)
            # Open-vocab prompts so forklift is a real detectable class
            if self.is_world and hasattr(self.model, 'set_classes'):
                self.model.set_classes(list(Config.WORLD_CLASSES))
                print(f"YOLO-World classes: {Config.WORLD_CLASSES}")
        except Exception as e:
            err = str(e)
            blocked = (
                '_regex' in err
                or 'Application Control' in err
                or 'DLL load failed' in err
            )
            if self.is_world and blocked:
                # Windows Smart App Control often blocks regex/*.pyd on Python 3.14
                # Fall back to YOLO26 COCO (person + vehicle classes still work)
                fallback = None
                for cand in _coco_fallback_candidates(Config.PROJECT_ROOT):
                    if cand and os.path.exists(cand):
                        fallback = cand
                        break
                if fallback is None:
                    fallback = 'yolo26m.pt'
                print(
                    f"YOLO-World unavailable ({err[:120]}…). "
                    f"Falling back to {fallback}"
                )
                self.model = YOLO(fallback)
                self.model_path = fallback
                self.is_world = False
            else:
                raise

        self.violations = []
        self.tracked_objects = {}
        self._forklift_tracks = {}  # tid -> track state for speed
        self._next_forklift_tid = 1
        self._forklift_overspeed_cooldown = {}  # tid -> last alert time
        self.logger = self._setup_logging()
        self.pose_model = None
        self._p16_zone_enter_t = None
        self._p16_alert_count = 0
        self._p16_was_in_danger = False
        self._p16_touch_enter_t = None
        self._p16_was_touching = False
        self._p16_touch_alert_latched = False
        self._p16_touch_start_latched = False
        self._p16_touch_streak = 0  # consecutive frames of real hand-on-product
        # Seconds of continuous product touch before duration alert (P16 only)
        self._p16_touch_alert_sec = float(
            self.profile.get("touch_alert_seconds", 1.0)
        )
        # Require this many consecutive contact frames before PRODUCT TOUCH
        self._p16_touch_confirm_frames = int(
            self.profile.get("touch_confirm_frames", 1)
        )
        self._p16_touch_snap_px = int(self.profile.get("touch_snap_px", 20))

        # Pose model ONLY for Video Project 16
        if self.is_project16:
            try:
                self.pose_model = YOLO('yolov8n-pose.pt')
                print(f"Profile: Video Project 16 (danger zone / product touch)")
            except Exception as e:
                print(f"Pose model unavailable ({e}); using bbox stick figure")
                self.pose_model = None
        elif self.is_safe_route:
            print(f"Profile: Safe Route (GODOWN NO-3 PPE / route) — other videos unchanged")
        elif getattr(self, "is_sawant", False):
            print("Profile: Sawant forklift (no aisle lines) — PPE + forklift detect")
        else:
            print(f"Profile: {self.profile.get('name', 'warehouse_aisle')}")

        print(f"Model loaded: {self.model_path}")

    def _setup_logging(self):
        """Setup logging"""
        import logging
        os.makedirs(self.config.LOG_DIR, exist_ok=True)
        log_file = os.path.join(self.config.LOG_DIR, 'gls_violations.log')
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger(__name__)

    def _map_class_name(self, raw_name):
        """Map detector class name to a GLS category via aliases / keywords."""
        name = (raw_name or '').strip().lower()
        if name in self.config.CLASS_ALIASES:
            return self.config.CLASS_ALIASES[name]

        # Keyword fallbacks (covers YOLO-World variants + COCO truck)
        if 'forklift' in name:
            return 'forklift'
        # COCO "truck" on sack racks is a common FP — only map for open-vocab World
        # (or Sawant open-floor demo where the yellow forklift is labeled truck/bus)
        if name in ('truck', 'bus', 'car') and (
            getattr(self, 'is_world', False) or getattr(self, '_map_coco_vehicles', False)
        ):
            return 'forklift'
        if name == 'person':
            return 'person'
        if 'helmet' in name or 'hard hat' in name:
            return 'helmet'
        if 'vest' in name:
            return 'vest'
        if 'harness' in name:
            return 'safety_harness'
        if 'oil' in name and 'tray' in name:
            return 'oil_tray'
        if 'stopper' in name or 'chock' in name:
            return 'wheel_stopper'
        if 'conveyor' in name:
            return 'conveyor'
        if 'pallet' in name or 'box' in name or 'sack' in name:
            return 'box' if ('box' in name or 'sack' in name) else 'goods_pallet'
        return None

    def _min_conf_for(self, category):
        if category == 'forklift':
            return self.config.FORKLIFT_CONFIDENCE
        if category == 'person':
            return self.config.PERSON_CONFIDENCE
        if category in ('helmet', 'vest'):
            return 0.15
        if category == 'box':
            return 0.35  # reduce shelf gadget spam
        return self.config.MODEL_CONFIDENCE

    def _extract_detections(self, results):
        """Bucket detections by GLS category using class names (not COCO IDs)."""
        buckets = {
            'person': [],
            'forklift': [],
            'safety_harness': [],
            'helmet': [],
            'vest': [],
            'oil_tray': [],
            'wheel_stopper': [],
            'conveyor': [],
            'goods_pallet': [],
            'box': [],
        }
        names = results.names

        if results.boxes is None:
            return buckets

        for det in results.boxes:
            cls_id = int(det.cls[0])
            conf = float(det.conf[0])
            bbox = det.xyxy[0].cpu().numpy()
            raw_name = names.get(cls_id, str(cls_id)) if isinstance(names, dict) else names[cls_id]
            category = self._map_class_name(raw_name)
            if category is None:
                continue
            if conf < self._min_conf_for(category):
                continue
            if category == 'forklift':
                area = max(0.0, bbox[2] - bbox[0]) * max(0.0, bbox[3] - bbox[1])
                if area < getattr(self.config, 'FORKLIFT_MIN_AREA', 2500):
                    continue
            buckets[category].append({
                'bbox': bbox,
                'conf': conf,
                'raw_name': raw_name,
            })

        # Merge overlapping forklift boxes (World may emit synonym classes)
        buckets['forklift'] = self._nms(buckets['forklift'], iou_thresh=0.45)
        buckets['box'] = self._nms(buckets['box'] + buckets['goods_pallet'], iou_thresh=0.4)
        return buckets

    def _color_ppe_flags(self, frame, bbox):
        """Heuristic helmet/vest check from person crop colors."""
        h, w = frame.shape[:2]
        x1, y1, x2, y2 = map(int, bbox)
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w - 1, x2), min(h - 1, y2)
        if x2 <= x1 or y2 <= y1:
            return True, True  # assume OK if invalid

        crop = frame[y1:y2, x1:x2]
        ch, cw = crop.shape[:2]
        if ch < 10 or cw < 10:
            return True, True

        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        head = hsv[: max(1, int(ch * 0.28)), :]
        torso = hsv[int(ch * 0.28): int(ch * 0.72), :]

        def bright_ratio(region, ranges):
            if region.size == 0:
                return 0.0
            mask = None
            for lo, hi in ranges:
                m = cv2.inRange(region, lo, hi)
                mask = m if mask is None else cv2.bitwise_or(mask, m)
            return float(np.count_nonzero(mask)) / float(region.shape[0] * region.shape[1])

        # Helmet: yellow / white / orange / red hard hats
        helmet_ratio = bright_ratio(head, [
            ((15, 60, 90), (40, 255, 255)),   # yellow
            ((0, 60, 90), (15, 255, 255)),    # orange/red
            ((0, 0, 160), (180, 50, 255)),    # white/gray
        ])
        # Vest: hi-vis yellow / orange / lime
        vest_ratio = bright_ratio(torso, [
            ((15, 70, 80), (45, 255, 255)),
            ((0, 70, 80), (15, 255, 255)),
            ((40, 50, 80), (85, 255, 255)),
        ])
        has_helmet = helmet_ratio > 0.04
        has_vest = vest_ratio > 0.05
        return has_helmet, has_vest

    def _annotate_workers(self, frame, people, helmets, vests):
        """Attach PPE flags to each worker using detections + color heuristics."""
        workers = []
        for person in people:
            pc = get_bbox_center(person['bbox'])
            px1, py1, px2, py2 = person['bbox']

            has_helmet_det = False
            for h in helmets:
                hx1, hy1, hx2, hy2 = h['bbox']
                if hx1 < pc[0] < hx2 and hy1 < pc[1] < hy2 + (py2 - py1) * 0.25:
                    has_helmet_det = True
                    break

            has_vest_det = False
            for v in vests:
                vx1, vy1, vx2, vy2 = v['bbox']
                if not (px2 < vx1 or vx2 < px1 or py2 < vy1 or vy2 < py1):
                    has_vest_det = True
                    break

            has_helmet_col, has_vest_col = self._color_ppe_flags(frame, person['bbox'])
            item = dict(person)
            item['no_helmet'] = not (has_helmet_det or has_helmet_col)
            item['no_vest'] = not (has_vest_det or has_vest_col)
            workers.append(item)
        return workers

    def _expand_coco_forklift_bbox(self, frame, det):
        """COCO truck/bus often tags only the cab — stretch to aisle floor for track/speed."""
        if not self.profile.get('expand_coco_forklift_bbox'):
            return det
        raw = (det.get('raw_name') or '').lower()
        if raw not in ('truck', 'car', 'bus', 'train'):
            return det
        h, w = frame.shape[:2]
        x1, y1, x2, y2 = map(float, det['bbox'])
        cx = (x1 + x2) / 2.0
        min_w = w * float(self.profile.get('forklift_min_width_frac', 0.16))
        bw = max(x2 - x1, min_w)
        x1 = max(0.0, cx - bw / 2.0)
        x2 = min(float(w - 1), cx + bw / 2.0)
        floor_y = h * float(self.profile.get('forklift_floor_y_frac', 0.90))
        y2 = min(float(h - 2), max(y2, floor_y))
        min_h = h * float(self.profile.get('forklift_min_height_frac', 0.20))
        y1 = max(0.0, min(y1, y2 - min_h))
        out = dict(det)
        out['bbox'] = np.array([x1, y1, x2, y2], dtype=float)
        return out

    def _clamp_forklift_bbox(self, frame, det):
        """Cap display box height — expanded COCO boxes must not span the whole aisle."""
        max_h_frac = self.profile.get('forklift_max_height_frac')
        if not max_h_frac:
            return det
        h, w = frame.shape[:2]
        x1, y1, x2, y2 = map(float, det['bbox'])
        max_h = h * float(max_h_frac)
        bh = y2 - y1
        if bh <= max_h:
            return det
        cy = (y1 + y2) / 2.0
        y1 = max(0.0, cy - max_h / 2.0)
        y2 = min(float(h - 1), cy + max_h / 2.0)
        out = dict(det)
        out['bbox'] = np.array([x1, y1, x2, y2], dtype=float)
        return out

    def _normalize_forklift_det(self, frame, det):
        det = self._expand_coco_forklift_bbox(frame, det)
        return self._clamp_forklift_bbox(frame, det)

    def _detect_yellow_forklift_blob(self, frame):
        """
        Fallback for open-floor clips: industrial yellow body = forklift
        when COCO misses (often labels person-only on the cab).
        """
        h, w = frame.shape[:2]
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        yellow = cv2.bitwise_or(
            cv2.inRange(hsv, (12, 55, 70), (42, 255, 255)),
            cv2.inRange(hsv, (5, 80, 80), (18, 255, 255)),  # orange-yellow
        )
        yellow = cv2.morphologyEx(yellow, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        yellow = cv2.morphologyEx(yellow, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))

        min_area = max(
            900,
            int(w * h * float(self.profile.get('forklift_yellow_min_area_frac', 0.012))),
        )
        max_area = int(w * h * float(self.profile.get('forklift_yellow_max_area_frac', 0.22)))
        max_w = w * float(self.profile.get('forklift_yellow_max_width_frac', 0.45))
        min_w = w * float(self.profile.get('forklift_yellow_min_width_frac', 0.06))
        min_h = h * float(self.profile.get('forklift_yellow_min_height_frac', 0.08))
        x_lo = w * float(self.profile.get('forklift_aisle_x_min', 0.18))
        x_hi = w * float(self.profile.get('forklift_aisle_x_max', 0.82))

        best = None
        best_score = -1.0
        for c in cv2.findContours(yellow, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]:
            area = float(cv2.contourArea(c))
            if area < min_area or area > max_area:
                continue
            x, y, bw, bh = cv2.boundingRect(c)
            if bw > max_w or bw < min_w or bh < min_h:
                continue
            if area / max(float(bw * bh), 1.0) < 0.22:
                continue
            cx = x + bw / 2.0
            if cx < x_lo or cx > x_hi:
                continue
            # Prefer compact, centered aisle blobs — not full-width floor tape
            center_bonus = 1.0 - abs(cx - w / 2.0) / (w / 2.0)
            score = area * (0.65 + 0.35 * center_bonus)
            if score > best_score:
                best_score = score
                best = (x, y, bw, bh)

        if best is None:
            return []
        x, y, bw, bh = best
        pad_x, pad_y = int(bw * 0.06), int(bh * 0.08)
        x1 = max(0, x - pad_x)
        y1 = max(0, y - pad_y)
        x2 = min(w - 1, x + bw + pad_x)
        y2 = min(h - 1, y + bh + pad_y)
        return [{
            'bbox': np.array([x1, y1, x2, y2], dtype=float),
            'conf': 0.55,
            'raw_name': 'yellow_forklift',
        }]

    def _detect_forklift_safety_lights(self, frame):
        """
        Detect distant aisle forklifts via warehouse safety lighting:
        blue beacon / spot + paired red floor safety lasers.
        """
        h, w = frame.shape[:2]
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        red = cv2.bitwise_or(
            cv2.inRange(hsv, (0, 70, 110), (12, 255, 255)),
            cv2.inRange(hsv, (168, 70, 110), (180, 255, 255)),
        )
        blue = cv2.inRange(hsv, (95, 35, 120), (135, 255, 255))

        roi = np.zeros((h, w), np.uint8)
        roi[int(h * 0.05): int(h * 0.95), int(w * 0.30): int(w * 0.70)] = 255
        red = cv2.bitwise_and(red, roi)
        blue = cv2.bitwise_and(blue, roi)
        red = cv2.morphologyEx(red, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
        blue = cv2.morphologyEx(blue, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))

        reds = []
        for c in cv2.findContours(red, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]:
            area = cv2.contourArea(c)
            if area < 35 or area > 15000:
                continue
            x, y, bw, bh = cv2.boundingRect(c)
            reds.append((x, y, bw, bh, area, x + bw / 2.0, y + bh / 2.0))

        blues = []
        for c in cv2.findContours(blue, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0]:
            area = cv2.contourArea(c)
            if area < 15 or area > 10000:
                continue
            x, y, bw, bh = cv2.boundingRect(c)
            blues.append((x, y, bw, bh, area, x + bw / 2.0, y + bh / 2.0))

        hits = []

        for i in range(len(reds)):
            for j in range(i + 1, len(reds)):
                r1, r2 = reds[i], reds[j]
                dy = abs(r1[6] - r2[6])
                dx = abs(r1[5] - r2[5])
                if dy > 80 or dx < 45 or dx > 480:
                    continue
                mid_x = (r1[5] + r2[5]) / 2.0
                mid_y = (r1[6] + r2[6]) / 2.0
                # Require blue beacon between/above the red pair (cuts floor FPs)
                matched_blue = None
                for b in blues:
                    if abs(b[5] - mid_x) < dx * 0.75 and -40 < (mid_y - b[6]) < 220:
                        matched_blue = b
                        break
                if matched_blue is None:
                    continue
                bx, by = matched_blue[5], matched_blue[6]
                width = max(dx * 1.3, 90)
                height = max(width * 1.15, 110)
                x1 = mid_x - width / 2
                x2 = mid_x + width / 2
                y1 = min(by, mid_y) - height * 0.35
                y2 = max(r1[6], r2[6], by) + height * 0.55
                hits.append({
                    'bbox': np.array([
                        max(0, x1), max(0, y1),
                        min(w - 1, x2), min(h - 1, y2),
                    ], dtype=float),
                    'conf': 0.65,
                    'raw_name': 'forklift_lights',
                })

        for b in blues:
            below = [
                r for r in reds
                if abs(r[5] - b[5]) < 160 and 5 < (r[6] - b[6]) < 260
            ]
            # Need a real floor-light pair under the beacon
            if len(below) < 2:
                continue
            # Reds should be spaced left/right of beacon
            xs = [r[5] for r in below]
            if max(xs) - min(xs) < 40:
                continue
            mid_x = b[5]
            mid_y = (b[6] + max(r[6] for r in below)) / 2.0
            width = max(abs(max(xs) - min(xs)) * 1.25, 100)
            width = max(width, b[2] * 3, 90)
            height = max(width * 1.1, 120)
            hits.append({
                'bbox': np.array([
                    max(0, mid_x - width / 2),
                    max(0, b[6] - height * 0.25),
                    min(w - 1, mid_x + width / 2),
                    min(h - 1, mid_y + height * 0.55),
                ], dtype=float),
                'conf': 0.60,
                'raw_name': 'forklift_lights',
            })

        # Drop foreground floor FPs (high-angle aisle cams: forklifts sit mid/far)
        filtered = []
        for d in hits:
            x1, y1, x2, y2 = d['bbox']
            cx = (x1 + x2) / 2.0
            cy = (y1 + y2) / 2.0
            bw = x2 - x1
            bh = y2 - y1
            if cy > h * 0.68:
                continue
            if bw > w * 0.22:
                continue
            if bh < 40 or bw < 40:
                continue
            # Safety lights live in the aisle corridor — not on rack faces
            if cx < w * 0.30 or cx > w * 0.70:
                continue
            filtered.append(d)

        merged = self._merge_forklifts(filtered, iou_thresh=0.15, center_frac=0.9)
        max_dets = self._forklift_max_dets()
        return sorted(merged, key=lambda d: d['conf'], reverse=True)[:max_dets]

    def _detect_forklift_aisle_zoom(self, frame):
        """Run YOLO-World on zoomed center-aisle crops for distant forklifts."""
        if not self.is_world:
            return []
        h, w = frame.shape[:2]
        crops = [
            (frame[int(h * 0.08): int(h * 0.88), int(w * 0.30): int(w * 0.70)], 0.30 * w, 0.08 * h, 2.0),
            (frame[int(h * 0.12): int(h * 0.62), int(w * 0.34): int(w * 0.66)], 0.34 * w, 0.12 * h, 2.8),
        ]
        dets = []
        for crop, ox, oy, scale in crops:
            if crop.size == 0:
                continue
            up = cv2.resize(crop, None, fx=scale, fy=scale)
            results = self.model(
                up,
                conf=self.config.FORKLIFT_CONFIDENCE,
                imgsz=1280,
                verbose=False,
            )[0]
            if results.boxes is None:
                continue
            for det in results.boxes:
                raw = results.names[int(det.cls[0])]
                if self._map_class_name(raw) != 'forklift':
                    continue
                conf = float(det.conf[0])
                if conf < self.config.FORKLIFT_CONFIDENCE:
                    continue
                x1, y1, x2, y2 = det.xyxy[0].cpu().numpy()
                bbox = np.array([
                    x1 / scale + ox, y1 / scale + oy,
                    x2 / scale + ox, y2 / scale + oy,
                ], dtype=float)
                dets.append({'bbox': bbox, 'conf': conf, 'raw_name': raw})
        return self._nms(dets, iou_thresh=0.4)

    @staticmethod
    def _nms(dets, iou_thresh=0.45):
        """Keep highest-confidence box among overlaps."""
        if len(dets) <= 1:
            return dets
        order = sorted(dets, key=lambda d: d['conf'], reverse=True)
        keep = []
        while order:
            best = order.pop(0)
            keep.append(best)
            remaining = []
            bx = best['bbox']
            for other in order:
                ox = other['bbox']
                x1 = max(bx[0], ox[0])
                y1 = max(bx[1], ox[1])
                x2 = min(bx[2], ox[2])
                y2 = min(bx[3], ox[3])
                inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
                area_b = max(0.0, bx[2] - bx[0]) * max(0.0, bx[3] - bx[1])
                area_o = max(0.0, ox[2] - ox[0]) * max(0.0, ox[3] - ox[1])
                union = area_b + area_o - inter + 1e-6
                if inter / union < iou_thresh:
                    remaining.append(other)
            order = remaining
        return keep

    def _looks_like_cardboard_rack(self, frame, bbox):
        """True when ROI is mostly brown cardboard boxes (common forklift FP)."""
        h, w = frame.shape[:2]
        x1, y1, x2, y2 = [int(v) for v in bbox]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        if x2 - x1 < 12 or y2 - y1 < 12:
            return False
        roi = frame[y1:y2, x1:x2]
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        # Cardboard / carton brown–tan (ITC GODOWN racks)
        cardboard = cv2.inRange(hsv, (5, 25, 40), (32, 200, 230))
        # Industrial yellow forklift paint — if present, not a rack FP
        yellow = cv2.inRange(hsv, (15, 80, 90), (40, 255, 255))
        n = float(roi.shape[0] * roi.shape[1])
        card_frac = float(np.count_nonzero(cardboard)) / n
        yel_frac = float(np.count_nonzero(yellow)) / n
        if yel_frac >= 0.04:
            return False
        return card_frac >= 0.38

    def _is_plausible_forklift(self, frame, det):
        """
        Reject rack / sack / side-shelf false positives while keeping real
        aisle forklifts (including distant ones with safety lights).
        """
        h, w = frame.shape[:2]
        x1, y1, x2, y2 = map(float, det['bbox'])
        bw = max(1.0, x2 - x1)
        bh = max(1.0, y2 - y1)
        cx = (x1 + x2) / 2.0
        cy = (y1 + y2) / 2.0
        area = bw * bh
        frame_area = float(w * h)
        conf = float(det.get('conf', 0))
        raw = (det.get('raw_name') or '').lower()
        is_coco_vehicle = raw in ('truck', 'car', 'bus', 'train') and getattr(
            self, '_map_coco_vehicles', False
        )
        if raw == 'forklift_track':
            return True

        max_w = float(self.profile.get(
            'forklift_max_width_frac',
            getattr(self.config, 'FORKLIFT_MAX_WIDTH_FRAC', 0.30),
        ))
        max_a = float(self.profile.get(
            'forklift_max_area_frac',
            getattr(self.config, 'FORKLIFT_MAX_AREA_FRAC', 0.10),
        ))
        x_min = float(self.profile.get(
            'forklift_aisle_x_min',
            getattr(self.config, 'FORKLIFT_AISLE_X_MIN', 0.24),
        ))
        x_max = float(self.profile.get(
            'forklift_aisle_x_max',
            getattr(self.config, 'FORKLIFT_AISLE_X_MAX', 0.76),
        ))

        # Huge boxes = rack spans, not a vehicle
        if bw > w * max_w + 1.0 or area > frame_area * max_a:
            return False

        # Always allow explicit yellow-body fallback on Sawant / GODOWN clips
        if raw == 'yellow_forklift' and getattr(self, '_detect_yellow_forklift', False):
            min_a = float(self.profile.get('forklift_yellow_min_area_frac', 0.01))
            max_a = float(self.profile.get('forklift_yellow_max_area_frac', 0.22))
            max_yw = float(self.profile.get('forklift_yellow_max_width_frac', 0.45))
            floor_y = float(self.profile.get('forklift_floor_min_y_frac', 0.52))
            if bw > w * max_yw or area > frame_area * max_a:
                return False
            # Yellow aisle tape / distant paint sits high in frame — not a forklift
            if y2 < h * floor_y:
                return False
            return area >= max(900.0, frame_area * min_a)

        # Cardboard shelf stacks ≠ forklift (GODOWN aisle cams; not open-floor Sawant)
        if not getattr(self, 'is_sawant', False):
            if self._looks_like_cardboard_rack(frame, det['bbox']):
                return False

        # Touching left/right image edge usually means shelf clutter
        # (skip for open-floor Sawant clips where the forklift fills the frame)
        if not getattr(self, 'is_sawant', False):
            if x1 <= 2 or x2 >= w - 3:
                if cy > h * 0.35:
                    return False
            # Tall column on side of aisle = rack face, not a vehicle
            if (bh / bw) > 1.85 and (cx < w * 0.34 or cx > w * 0.66):
                return False

        in_aisle = (w * x_min) <= cx <= (w * x_max)

        # COCO truck/bus on GODOWN clips: cab-only box — trust aisle position
        if is_coco_vehicle:
            min_veh = float(self.profile.get('forklift_vehicle_min_conf', 0.30))
            if conf < min_veh:
                return False
            if in_aisle and cy < h * 0.82:
                return True

        # Side-of-frame large boxes are almost always racks/sacks
        if not in_aisle:
            # Allow only small, distant (upper) candidates near vanishing point
            if cy > h * 0.42 or area > frame_area * 0.035 or bw > w * 0.14:
                return False

        # Very wide aspect on lower half = shelf row, not forklift
        if (bw / bh) > 2.0 and cy > h * 0.48:
            return False

        # Footprint should meet the aisle floor — floating mid-rack boxes are FPs
        if not getattr(self, 'is_sawant', False):
            if y2 < h * 0.52 and area > frame_area * 0.02:
                return False

        # COCO truck/bus leftovers (if any) must sit in aisle with solid conf
        if raw in ('truck', 'car', 'bus', 'train'):
            min_veh = float(self.profile.get('forklift_vehicle_min_conf', 0.50))
            if getattr(self, '_map_coco_vehicles', False):
                if conf < min_veh:
                    return False
            elif conf < 0.55 or not in_aisle or cy > h * 0.72:
                return False

        # Light-based dets must stay in center corridor
        if 'light' in raw and not in_aisle:
            return False

        # YOLO-World forklift on racks: require aisle + stronger score
        if 'forklift' in raw:
            if not in_aisle and conf < 0.55:
                return False
            # Low open-vocab scores on carton stacks are the usual FP source
            if not getattr(self, '_map_coco_vehicles', False) and conf < 0.22:
                return False

        return True

    def _apply_forklift_motion_gate(self, forklifts):
        """Drop static rack/tape FPs — real forklifts move between frames."""
        if not self.profile.get('forklift_require_motion') or not forklifts:
            return forklifts
        now = float(getattr(self, '_motion_clock', None) or time.time())
        state = getattr(self, '_fl_motion_state', None)
        if state is None:
            state = {}
            self._fl_motion_state = state

        confirm_conf = float(self.profile.get('forklift_vehicle_confirm_conf', 0.26))
        need_drift = float(self.profile.get('forklift_motion_drift_px', 35))
        match_dist = float(self.profile.get('forklift_motion_match_dist', 140))
        ttl = float(self.profile.get('forklift_motion_ttl', 4.0))

        confirmed = []
        for fl in forklifts:
            cx, cy = get_bbox_center(fl['bbox'])
            raw = (fl.get('raw_name') or '').lower()
            conf = float(fl.get('conf', 0))

            if raw in ('truck', 'bus', 'car', 'train') and conf >= confirm_conf:
                confirmed.append(fl)
                continue
            if raw == 'forklift_track':
                confirmed.append(fl)
                continue

            key = None
            best_d = match_dist
            for k, st in state.items():
                d = calculate_distance((cx, cy), st['center'])
                if d <= best_d:
                    best_d, key = d, k
            if key is None:
                key = f'fl_{len(state)}'
                state[key] = {
                    'center': (cx, cy),
                    'time': now,
                    'drift': 0.0,
                    'confirmed': False,
                }
                continue

            st = state[key]
            st['drift'] = float(st.get('drift', 0.0)) + calculate_distance(
                (cx, cy), st['center']
            )
            st['center'] = (cx, cy)
            st['time'] = now
            if st.get('confirmed') or st['drift'] >= need_drift:
                st['confirmed'] = True
                confirmed.append(fl)

        self._fl_motion_state = {
            k: v for k, v in state.items() if (now - float(v.get('time', now))) <= ttl
        }
        return confirmed

    def _coast_forklifts_from_tracks(self, forklifts):
        """Keep forklift box/count visible when YOLO misses a frame but track is fresh."""
        if forklifts or not self._forklift_tracks:
            return forklifts
        now = float(getattr(self, '_motion_clock', None) or time.time())
        ghosts = []
        for tid, tr in self._forklift_tracks.items():
            if (now - float(tr.get('time', 0.0))) > 2.5:
                continue
            cx, cy = tr['center']
            bh = max(24.0, float(tr.get('bbox_h', 80.0)))
            bw = max(24.0, bh * 0.95)
            ghosts.append({
                'bbox': np.array(
                    [cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2],
                    dtype=float,
                ),
                'conf': 0.32,
                'raw_name': 'forklift_track',
                'track_id': tid,
                'speed_kmh': round(float(tr.get('speed_kmh', 0.0)), 1),
                'speed_limit_kmh': float(
                    getattr(self.config, 'FORKLIFT_SPEED_LIMIT_KMH', 8.0)
                ),
            })
        if not ghosts:
            return forklifts
        ghosts.sort(key=lambda g: float(g.get('speed_kmh', 0.0)), reverse=True)
        return ghosts[: self._forklift_max_dets()]

    def _filter_forklift_false_positives(self, frame, forklifts):
        kept = [d for d in forklifts if self._is_plausible_forklift(frame, d)]
        return sorted(kept, key=lambda d: float(d.get('conf', 0)), reverse=True)

    def _merge_forklifts(self, dets, iou_thresh=0.15, center_frac=0.85):
        """
        Strong merge for duplicate forklift boxes on the same vehicle.
        Uses IoU, containment (IoS), and center distance — light detector
        often emits two partial boxes (cab + body) with low IoU.
        """
        if len(dets) <= 1:
            return dets

        iou_thresh = float(self.profile.get('forklift_merge_iou', iou_thresh))
        center_frac = float(self.profile.get('forklift_merge_center_frac', center_frac))
        same_aisle = bool(self.profile.get('forklift_merge_same_aisle', False))

        order = sorted(dets, key=lambda d: d['conf'], reverse=True)
        keep = []

        while order:
            best = dict(order.pop(0))
            bx = np.array(best['bbox'], dtype=float)
            remaining = []

            for other in order:
                ox = np.array(other['bbox'], dtype=float)

                x1 = max(bx[0], ox[0])
                y1 = max(bx[1], ox[1])
                x2 = min(bx[2], ox[2])
                y2 = min(bx[3], ox[3])
                inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
                area_b = max(1.0, (bx[2] - bx[0]) * (bx[3] - bx[1]))
                area_o = max(1.0, (ox[2] - ox[0]) * (ox[3] - ox[1]))
                iou = inter / (area_b + area_o - inter)
                ios = inter / min(area_b, area_o)  # containment of smaller box

                bcx = (bx[0] + bx[2]) / 2.0
                bcy = (bx[1] + bx[3]) / 2.0
                ocx = (ox[0] + ox[2]) / 2.0
                ocy = (ox[1] + ox[3]) / 2.0
                dist = ((bcx - ocx) ** 2 + (bcy - ocy) ** 2) ** 0.5
                avg_size = (
                    (bx[2] - bx[0] + ox[2] - ox[0]) / 2.0
                    + (bx[3] - bx[1] + ox[3] - ox[1]) / 2.0
                ) / 2.0
                max_bw = max(bx[2] - bx[0], ox[2] - ox[0])

                # Distant aisle cams: cab + safety lights sit on same corridor
                # but have low IoU — treat as one forklift when X aligns
                aisle_aligned = False
                if same_aisle:
                    aisle_aligned = abs(bcx - ocx) <= max(max_bw * 0.85, 40.0)

                same_object = (
                    iou >= iou_thresh
                    or ios >= 0.40
                    or dist < avg_size * center_frac
                    or aisle_aligned
                )

                if same_object:
                    # Union boxes, keep higher confidence
                    bx = np.array([
                        min(bx[0], ox[0]),
                        min(bx[1], ox[1]),
                        max(bx[2], ox[2]),
                        max(bx[3], ox[3]),
                    ], dtype=float)
                    best['bbox'] = bx
                    best['conf'] = max(float(best['conf']), float(other['conf']))
                else:
                    remaining.append(other)

            keep.append(best)
            order = remaining

        return keep

    def _forklift_max_dets(self):
        return int(
            self.profile.get(
                'forklift_max_dets',
                getattr(self.config, 'FORKLIFT_MAX_DETS', 2),
            )
        )

    def process_frame(self, frame):
        """Process single frame and detect violations"""
        # Video Project 16 ONLY — dedicated labels; other videos unchanged below
        if getattr(self, 'is_project16', False):
            return self._process_frame_project16(frame)
        # GODOWN NO-3 ONLY — Safe Route + PPE; warehouse / Project 16 unchanged
        if getattr(self, 'is_safe_route', False):
            return self._process_frame_safe_route(frame)

        results = self.model(
            frame,
            conf=min(
                self.config.FORKLIFT_CONFIDENCE,
                self.config.MODEL_CONFIDENCE,
                self.config.PERSON_CONFIDENCE,
            ),
            imgsz=getattr(self.config, 'INFER_IMGSZ', 960),
            verbose=False,
        )[0]

        dets = self._extract_detections(results)
        people = dets['person']
        forklifts = list(dets['forklift']) if self._enable_forklift_detect else []
        conveyors = dets['conveyor']
        harnesses = dets['safety_harness']
        helmets = dets.get('helmet', [])
        vests = dets.get('vest', [])
        boxes = dets.get('box', [])

        if self._enable_forklift_detect:
            forklifts = [
                self._normalize_forklift_det(frame, d) for d in forklifts
            ]
            if getattr(self.config, 'USE_AISLE_ZOOM', False):
                forklifts.extend(self._detect_forklift_aisle_zoom(frame))
            if self._enable_forklift_lights and getattr(
                self.config, 'USE_FORKLIFT_LIGHT_DETECTOR', True
            ):
                forklifts.extend(self._detect_forklift_safety_lights(frame))
            # Soft-merge duplicates (cab+body / YOLO+lights) into one forklift
            forklifts = self._merge_forklifts(
                forklifts, iou_thresh=0.12, center_frac=0.95
            )
            # Drop rack/sack false positives; keep real aisle forklifts
            forklifts = self._filter_forklift_false_positives(frame, forklifts)[
                : self._forklift_max_dets()
            ]
            # Yellow body: fill gaps / stabilize track when COCO flickers
            if self._detect_yellow_forklift:
                yel = self._filter_forklift_false_positives(
                    frame, self._detect_yellow_forklift_blob(frame)
                )
                if yel:
                    forklifts = self._merge_forklifts(
                        list(forklifts) + list(yel), iou_thresh=0.08, center_frac=0.9
                    )
                    forklifts = forklifts[: self._forklift_max_dets()]
            forklifts = self._apply_forklift_motion_gate(forklifts)
            forklifts = self._coast_forklifts_from_tracks(forklifts)
            # Hard cap after coast (ghosts must not resurrect a 2nd box)
            forklifts = forklifts[: self._forklift_max_dets()]

        workers = self._annotate_workers(frame, people, helmets, vests)

        h, w = frame.shape[:2]
        yellow_lines = []
        if self._enable_yellow_lines:
            self._aisle_road_frame_i += 1
            if self._aisle_road_frozen and self._aisle_road_overlay:
                yellow_lines = [dict(ln) for ln in self._aisle_road_overlay]
            else:
                yellow_lines = detect_yellow_aisle_lines(frame, max_lines=2)
                yellow_lines = self._freeze_aisle_road_ways(yellow_lines, h, w)
        else:
            self._aisle_road_frozen = True  # nothing to lock — live warm-up can proceed
            self._aisle_road_overlay = []

        no_helmet = sum(1 for w in workers if w.get('no_helmet'))
        no_vest = sum(1 for w in workers if w.get('no_vest'))
        compliant_workers = sum(
            1 for w in workers if not w.get('no_helmet') and not w.get('no_vest')
        )
        ppe_pct = int(100 * compliant_workers / len(workers)) if workers else 100

        violations = []
        violations.extend(self._check_conveyor_safety(frame, people, conveyors))
        violations.extend(self._check_harness_compliance(frame, people, harnesses))
        violations.extend(self._check_forklift_safety(frame, forklifts))
        # Camera-agnostic proximity/danger-zone check — works on any camera
        # out of the box (pure distance), refined per-camera if an operator
        # has configured a danger_zone polygon in config/cameras.json.
        danger_violations = self._danger_zone_checker.check(people, forklifts, w, h)
        violations.extend(danger_violations)
        person_near_forklift = sum(
            1 for v in danger_violations if v['type'] == 'PERSON_NEAR_FORKLIFT'
        )
        person_in_danger_zone = sum(
            1 for v in danger_violations if v['type'] == 'PERSON_IN_DANGER_ZONE'
        )
        if person_near_forklift and self.logger:
            self.logger.warning(
                f"VIOLATION: {person_near_forklift} person(s) near forklift"
            )
        speed_info = getattr(self, '_last_forklift_speed', {}) or {}
        if no_helmet:
            violations.append({
                'type': 'NO_HELMET',
                'count': no_helmet,
                'timestamp': datetime.now().isoformat(),
            })
            if self.logger:
                self.logger.warning(f"VIOLATION: {no_helmet} worker(s) without helmet")
        if no_vest:
            violations.append({
                'type': 'NO_VEST',
                'count': no_vest,
                'timestamp': datetime.now().isoformat(),
            })

        box_count = 0 if (not workers and not forklifts) else len(boxes)
        stats = {
            'total': len(workers) + len(forklifts) + box_count + len(yellow_lines),
            'workers': len(workers),
            'forklifts': len(forklifts),
            'boxes': box_count,
            'yellow_lines': len(yellow_lines),
            'no_helmet': no_helmet,
            'no_vest': no_vest,
            'unsafe_zones': len(forklifts),
            'ppe_pct': ppe_pct,
            'forklift_speed_kmh': float(speed_info.get('forklift_speed_kmh', 0.0)),
            'forklift_speed_limit_kmh': float(speed_info.get('forklift_speed_limit_kmh', 8.0)),
            'forklift_overspeed': bool(speed_info.get('forklift_overspeed', False)),
            'person_near_forklift': person_near_forklift,
            'person_in_danger_zone': person_in_danger_zone,
        }

        alert = None
        if person_near_forklift:
            alert = {
                'title': 'Person Near Forklift',
                'location': self.profile.get('location', getattr(self.config, 'ZONE_NAME', 'Aisle')),
                'time': datetime.now().strftime('%H:%M:%S'),
            }
        elif person_in_danger_zone:
            alert = {
                'title': 'Person In Danger Zone',
                'location': self.profile.get('location', getattr(self.config, 'ZONE_NAME', 'Aisle')),
                'time': datetime.now().strftime('%H:%M:%S'),
            }
        elif no_helmet:
            alert = {
                'title': 'No Helmet Detected',
                'location': getattr(self.config, 'ZONE_NAME', 'Aisle'),
                'time': datetime.now().strftime('%H:%M:%S'),
            }
        elif no_vest:
            alert = {
                'title': 'No Vest Detected',
                'location': getattr(self.config, 'ZONE_NAME', 'Aisle'),
                'time': datetime.now().strftime('%H:%M:%S'),
            }
        elif any(v['type'] == 'FORKLIFT_OVERSPEED' for v in violations):
            ov = next(v for v in violations if v['type'] == 'FORKLIFT_OVERSPEED')
            spd = ov.get('speed_kmh', ov.get('speed', 0))
            lim = ov.get('limit_kmh', stats['forklift_speed_limit_kmh'])
            alert = {
                'title': f'Forklift Overspeed {spd:.1f} km/h',
                'location': f"Limit {lim:.0f} km/h · {getattr(self.config, 'ZONE_NAME', 'Aisle')}",
                'time': datetime.now().strftime('%H:%M:%S'),
            }

        result_frame = render_dashboard(
            frame,
            workers=workers,
            forklifts=forklifts,
            boxes=boxes,
            stats=stats,
            alert=alert,
            draw_zones=True,
            yellow_lines=yellow_lines,
        )
        self.violations.extend(violations)
        self.last_stats = dict(stats)
        self.last_stats['aisle_locked'] = bool(self._aisle_road_frozen)
        # Sticky overlay for 1× live playback (re-draw on new frames while YOLO runs)
        self.last_overlay = {
            'workers': [dict(w) for w in workers],
            'forklifts': [dict(f) for f in forklifts],
            'boxes': [dict(b) for b in boxes],
            'stats': dict(stats),
            'alert': dict(alert) if alert else None,
            'yellow_lines': [dict(ln) for ln in yellow_lines],
            'draw_zones': True,
        }
        if self.profile.get('forklift_hide_speed_badge'):
            self.last_overlay['stats']['hide_forklift_speed_badge'] = True
        return result_frame, violations

    def render_overlay_on(self, frame):
        """Paint last detections onto a new frame (no YOLO) for realtime display."""
        ov = getattr(self, 'last_overlay', None)
        if not ov:
            return frame
        from .dashboard import render_dashboard
        from .dashboard_safe_route import render_safe_route_dashboard
        from .dashboard_project16 import render_project16_dashboard, _poly_px
        if ov.get('mode') == 'project16' or getattr(self, 'is_project16', False):
            h, w = frame.shape[:2]
            danger_poly = ov.get('danger_poly')
            product_poly = ov.get('product_poly')
            if danger_poly is None:
                danger_poly = _poly_px(self.profile.get('danger_zone', []), w, h)
            if product_poly is None:
                product_poly = _poly_px(self.profile.get('product_zone', []), w, h)
            return render_project16_dashboard(
                frame,
                people=ov.get('people') or [],
                danger_poly=danger_poly,
                product_poly=product_poly,
                in_danger=bool(ov.get('in_danger')),
                product_touch=bool(ov.get('product_touch')),
                touch_point=ov.get('touch_point'),
                duration_str=ov.get('duration_str') or '00:00:00',
                location=ov.get('location') or self.profile.get('location', 'Production Line - Zone B'),
                alerts_today=int(ov.get('alerts_today') or 0),
                touch_duration_str=ov.get('touch_duration_str') or '00:00:00',
                pose_points=int(ov.get('pose_points') or 0),
            )
        if getattr(self, 'is_safe_route', False):
            return render_safe_route_dashboard(
                frame,
                workers=ov.get('workers') or [],
                boxes=ov.get('boxes') or [],
                yellow_lines=ov.get('yellow_lines') or [],
                stats=ov.get('stats') or {},
                alert=ov.get('alert'),
            )
        return render_dashboard(
            frame,
            workers=ov.get('workers') or [],
            forklifts=self._sync_overlay_forklift_speed(ov.get('forklifts') or []),
            boxes=ov.get('boxes') or [],
            stats=self._overlay_stats(ov),
            alert=ov.get('alert'),
            draw_zones=bool(ov.get('draw_zones', True)),
            yellow_lines=ov.get('yellow_lines') or [],
        )

    def _overlay_stats(self, ov):
        stats = dict(ov.get('stats') or {})
        ls = getattr(self, 'last_stats', None) or {}
        for key in (
            'forklift_speed_kmh', 'forklift_speed_limit_kmh', 'forklift_overspeed',
            'forklifts', 'workers',
        ):
            if key in ls:
                stats[key] = ls[key]
        if self.profile.get('forklift_hide_speed_badge'):
            stats['hide_forklift_speed_badge'] = True
        return stats

    def _sync_overlay_forklift_speed(self, forklifts):
        if not forklifts:
            return forklifts
        ls = getattr(self, 'last_stats', None) or {}
        spd = float(ls.get('forklift_speed_kmh') or 0.0)
        limit = float(ls.get('forklift_speed_limit_kmh') or 8.0)
        overspeed = bool(ls.get('forklift_overspeed', False))
        synced = []
        for fl in forklifts:
            item = dict(fl)
            if spd > 0 or item.get('speed_kmh') is None:
                item['speed_kmh'] = round(spd, 1)
            item['speed_limit_kmh'] = limit
            item['overspeed'] = overspeed
            synced.append(item)
        return synced

    def _freeze_aisle_road_ways(self, lines, h, w):
        """Hard-freeze Aisle Road Way Left+Right (+ labels) so they never blink."""
        if self._aisle_road_frozen and self._aisle_road_overlay:
            return [dict(ln) for ln in self._aisle_road_overlay]

        sides = {ln.get('side'): ln for ln in (lines or []) if ln.get('side') in ('left', 'right')}
        if 'left' not in sides or 'right' not in sides:
            return list(lines or [])

        frozen = []
        for side in ('left', 'right'):
            ln = sides[side]
            pts = [(int(x), int(y)) for x, y in (ln.get('points') or [])]
            if len(pts) < 2:
                return list(lines or [])
            arr = np.array(pts, dtype=np.int32)
            arr = arr[np.argsort(arr[:, 1])]
            anchor = (int(arr[int(len(arr) * 0.52)][0]), int(arr[int(len(arr) * 0.52)][1]))
            label = f"Aisle Road Way ({side.capitalize()})"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.78, 2)
            if side == 'left':
                tag_x = max(8, int(anchor[0] - tw - 36))
            else:
                tag_x = min(w - tw - 16, int(anchor[0] + 28))
            tag_y = int(np.clip(anchor[1], th + 40, int(h * 0.70)))
            item = dict(ln)
            item['points'] = [(int(x), int(y)) for x, y in arr.tolist()]
            item['label_anchor'] = anchor
            item['label_tag'] = (tag_x, tag_y, tw, th, label)
            item['locked'] = True
            frozen.append(item)

        self._aisle_road_overlay = frozen
        self._aisle_road_frozen = True
        print("Aisle Road Way locked (Left + Right) — lines/labels frozen")
        return [dict(ln) for ln in frozen]

    def _rebuild_safe_route_from_lock(self, h, w):
        """Rebuild polylines from locked slope/intercept (stable draw)."""
        y_min = max(int(h * 0.08), int(h * 0.14))
        y_max = h - 4
        mid = w // 2
        out = []
        for side in ('left', 'right'):
            st = self._safe_route_locked.get(side)
            if not st:
                continue
            # Prefer exact frozen integer points (zero jitter)
            if st.get('points'):
                pts = [(int(x), int(y)) for x, y in st['points']]
                out.append({
                    'points': pts,
                    'polyline': True,
                    'bbox': np.array([
                        float(min(p[0] for p in pts)), float(min(p[1] for p in pts)),
                        float(max(p[0] for p in pts)), float(max(p[1] for p in pts)),
                    ], dtype=float),
                    'conf': float(st.get('conf', 0.9)),
                    'raw_name': 'safe_route_line',
                    'side': side,
                    'slope': float(st.get('slope', 0.0)),
                    'intercept': float(st.get('intercept', 0.0)),
                    'synthetic': bool(st.get('synthetic', False)),
                    'locked': True,
                    'label_anchor': st.get('label_anchor'),
                    'label_tag': st.get('label_tag'),
                })
                continue

            a = float(st['slope'])
            b = float(st['intercept'])
            y0 = y_min
            if abs(a) > 1e-6:
                y_cross = (mid - b) / a
                if y0 < y_cross < y_max:
                    y0 = max(y0, float(y_cross) + 55)
            ys = np.linspace(y0, y_max, num=48)
            xs = np.clip(a * ys + b, 0, w - 1)
            pts = [(int(round(x)), int(round(y))) for x, y in zip(xs, ys)]
            out.append({
                'points': pts,
                'polyline': True,
                'bbox': np.array([
                    float(np.min(xs)), float(np.min(ys)),
                    float(np.max(xs)), float(np.max(ys)),
                ], dtype=float),
                'conf': float(st.get('conf', 0.9)),
                'raw_name': 'safe_route_line',
                'side': side,
                'slope': a,
                'intercept': b,
                'synthetic': bool(st.get('synthetic', False)),
                'locked': True,
                'label_anchor': st.get('label_anchor'),
                'label_tag': st.get('label_tag'),
            })
        return out

    def _freeze_safe_route_labels(self, lines, h, w):
        """Fix Left/Right labels once — same layout as Aisle Road Way (never move)."""
        frozen = []
        for ln in lines:
            side = ln.get('side')
            pts = [(int(x), int(y)) for x, y in (ln.get('points') or [])]
            if side not in ('left', 'right') or len(pts) < 2:
                continue
            arr = np.array(pts, dtype=np.int32)
            arr = arr[np.argsort(arr[:, 1])]
            idx = int(len(arr) * 0.55)
            anchor = (int(arr[idx][0]), int(arr[idx][1]))
            label = f"Safe Route ({side.capitalize()})"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.78, 2)
            # Outside corridor: left tag left of line, right tag right of line
            if side == 'left':
                tag_x = max(8, int(anchor[0] - tw - 36))
            else:
                tag_x = min(w - tw - 16, int(anchor[0] + 28))
            tag_y = int(np.clip(anchor[1], th + 40, int(h * 0.70)))

            item = {
                'points': [(int(x), int(y)) for x, y in arr.tolist()],
                'polyline': True,
                'bbox': np.array([
                    float(arr[:, 0].min()), float(arr[:, 1].min()),
                    float(arr[:, 0].max()), float(arr[:, 1].max()),
                ], dtype=float),
                'conf': float(ln.get('conf', 0.9)),
                'raw_name': 'safe_route_line',
                'side': side,
                'slope': float(ln.get('slope', 0.0)),
                'intercept': float(ln.get('intercept', 0.0)),
                'synthetic': bool(ln.get('synthetic', False)),
                'locked': True,
                'label_anchor': (int(anchor[0]), int(anchor[1])),
                'label_tag': (int(tag_x), int(tag_y), int(tw), int(th), label),
            }
            frozen.append(item)
            st = self._safe_route_locked.setdefault(side, {})
            st['points'] = list(item['points'])
            st['label_anchor'] = item['label_anchor']
            st['label_tag'] = item['label_tag']
            st['slope'] = item['slope']
            st['intercept'] = item['intercept']
            st['conf'] = item['conf']
            st['synthetic'] = item['synthetic']
            st['stable'] = 99
            st['miss'] = 0
        return frozen

    def _stabilize_safe_route_lines(self, detected, h, w):
        """
        Acquire Left/Right once, then hard-freeze — static CCTV must not blink.
        """
        if self._safe_route_frozen and self._safe_route_overlay:
            return [dict(ln) for ln in self._safe_route_overlay]

        det = {ln.get('side'): ln for ln in (detected or []) if ln.get('side') in ('left', 'right')}

        for side in ('left', 'right'):
            cur = det.get(side)
            prev = self._safe_route_locked.get(side)

            if cur is None:
                if prev is not None:
                    prev['miss'] = int(prev.get('miss', 0)) + 1
                continue

            a = float(cur.get('slope', 0.0))
            b = float(cur.get('intercept', 0.0))
            if ('slope' not in cur or 'intercept' not in cur) and cur.get('points'):
                pts_fit = np.array(cur['points'], dtype=np.float32)
                if len(pts_fit) >= 2:
                    a, b = np.polyfit(pts_fit[:, 1], pts_fit[:, 0], deg=1)

            pts = [(int(round(x)), int(round(y))) for x, y in (cur.get('points') or [])]

            if prev is None:
                self._safe_route_locked[side] = {
                    'slope': a,
                    'intercept': b,
                    'points': pts,
                    'conf': float(cur.get('conf', 0.85)),
                    'synthetic': bool(cur.get('synthetic', False)),
                    'miss': 0,
                    'stable': 1,
                    'jump': 0,
                }
                continue

            # Keep first solid geometry — blending makes labels drift
            x_new = a * float(h - 6) + b
            x_old = float(prev['slope']) * float(h - 6) + float(prev['intercept'])
            dx = abs(x_new - x_old)
            prev['miss'] = 0
            if dx <= 80.0:
                if not prev.get('points') and pts:
                    prev['points'] = pts
                prev['stable'] = int(prev.get('stable', 0)) + 1
                prev['conf'] = float(cur.get('conf', prev.get('conf', 0.85)))
            else:
                prev['stable'] = int(prev.get('stable', 0)) + 1

        lines = self._rebuild_safe_route_from_lock(h, w)

        def _quality_ok(ln):
            if not ln or not ln.get('points') or len(ln['points']) < 4:
                return False
            pts = ln['points']
            x_bot, _ = pts[-1]
            x_top, _ = pts[0]
            if abs(int(x_bot) - int(x_top)) < int(w * 0.045):
                return False  # vertical rack upright — reject
            a = float(ln.get('slope', 0.0))
            side = ln.get('side')
            if side == 'left':
                if a > -0.04:
                    return False
                # Must sit on left road-way at rack toe (floor), not boxes / mid-aisle
                if not (w * 0.27 < int(x_bot) < w * 0.36):
                    return False
            if side == 'right':
                if a < 0.04:
                    return False
                if not (w * 0.60 < int(x_bot) < w * 0.86):
                    return False
            return True

        # Freeze only when BOTH sides look like floor paint (not shelves)
        left_ln = next((ln for ln in lines if ln.get('side') == 'left'), None)
        right_ln = next((ln for ln in lines if ln.get('side') == 'right'), None)
        left_ok = (
            left_ln is not None
            and _quality_ok(left_ln)
            and int(self._safe_route_locked.get('left', {}).get('stable', 0)) >= 2
        )
        right_ok = (
            right_ln is not None
            and _quality_ok(right_ln)
            and int(self._safe_route_locked.get('right', {}).get('stable', 0)) >= 2
        )
        if left_ok and right_ok:
            self._safe_route_overlay = self._freeze_safe_route_labels(lines, h, w)
            self._safe_route_frozen = True
            print("Safe Route locked (Left + Right) — floor lines FROZEN (will not move)")
            return [dict(ln) for ln in self._safe_route_overlay]

        if len(lines) == 1:
            side = lines[0].get('side')
            if (
                side
                and _quality_ok(lines[0])
                and int(self._safe_route_locked.get(side, {}).get('stable', 0)) >= 3
            ):
                self._safe_route_overlay = self._freeze_safe_route_labels(lines, h, w)
                self._safe_route_frozen = True
                print(f"Safe Route locked ({side}) — floor line FROZEN (will not move)")
                return [dict(ln) for ln in self._safe_route_overlay]

        return lines

    def _process_frame_safe_route(self, frame):
        """GODOWN NO-3 only: Safe Route lines + worker PPE (no forklift FPs)."""
        from .dashboard_safe_route import render_safe_route_dashboard
        from .utils import detect_safe_route_lines

        results = self.model(
            frame,
            conf=min(self.config.MODEL_CONFIDENCE, self.config.PERSON_CONFIDENCE),
            imgsz=getattr(self.config, 'INFER_IMGSZ', 960),
            verbose=False,
        )[0]
        dets = self._extract_detections(results)
        people = dets.get('person', [])
        helmets = dets.get('helmet', [])
        vests = dets.get('vest', [])
        boxes = dets.get('box', [])

        workers = self._annotate_workers(frame, people, helmets, vests)
        # Distant aisle workers: vest heuristic is noisy — Safe Route mockup focuses on helmet
        fh = frame.shape[0]
        for worker in workers:
            _x1, y1, _x2, y2 = map(float, worker['bbox'])
            bh = y2 - y1
            if bh < fh * 0.18:
                worker['no_vest'] = False
            if worker.get('no_helmet') and bh < fh * 0.28:
                worker['no_vest'] = False

        h, w = frame.shape[:2]
        self._safe_route_frame_i += 1

        # HARD FREEZE: after lock, never re-detect — lines/labels stay put
        if self._safe_route_frozen and self._safe_route_overlay:
            yellow_lines = [dict(ln) for ln in self._safe_route_overlay]
        else:
            raw_lines = detect_safe_route_lines(frame, max_lines=2)
            yellow_lines = self._stabilize_safe_route_lines(raw_lines, h, w)

        no_helmet = sum(1 for w in workers if w.get('no_helmet'))
        no_vest = sum(1 for w in workers if w.get('no_vest'))
        compliant = sum(
            1 for w in workers if not w.get('no_helmet') and not w.get('no_vest')
        )
        ppe_pct = int(100 * compliant / len(workers)) if workers else 100

        if workers:
            cx, cy = get_bbox_center(workers[0]['bbox'])
            if self._route_last_center is not None:
                dx = cx - self._route_last_center[0]
                dy = cy - self._route_last_center[1]
                self._route_distance_m += float(np.hypot(dx, dy)) / 80.0
            self._route_last_center = (cx, cy)
            if self._route_t0 is None:
                self._route_t0 = time.time()
        route_ok = len(yellow_lines) >= 1
        elapsed = time.time() - self._route_t0 if self._route_t0 else 0.0
        remain_m = max(0.0, 60.0 - self._route_distance_m)
        speed = (self._route_distance_m / elapsed) if elapsed > 1 else 1.2
        eta_s = int(remain_m / max(speed, 0.3))
        eta = f"00:{eta_s:02d} sec" if eta_s < 60 else f"{eta_s // 60:02d}:{eta_s % 60:02d}"

        side = "Both"
        if len(yellow_lines) == 1:
            side = f"{(yellow_lines[0].get('side') or 'path').capitalize()} Side"
        elif len(yellow_lines) >= 2:
            side = "Left + Right"

        violations = []
        if no_helmet:
            violations.append({
                'type': 'NO_HELMET',
                'count': no_helmet,
                'timestamp': datetime.now().isoformat(),
            })
            if self.logger:
                self.logger.warning(f"VIOLATION: {no_helmet} worker(s) without helmet")
        if no_vest:
            violations.append({
                'type': 'NO_VEST',
                'count': no_vest,
                'timestamp': datetime.now().isoformat(),
            })

        stats = {
            'total': len(workers) + len(yellow_lines) + (len(boxes) if workers else 0),
            'workers': len(workers),
            'forklifts': 0,
            'boxes': len(boxes) if workers else 0,
            'yellow_lines': len(yellow_lines),
            'no_helmet': no_helmet,
            'no_vest': no_vest,
            'unsafe_zones': 1 if no_helmet else 0,
            'ppe_pct': ppe_pct,
            'route_ok': route_ok,
            'route_path': side if route_ok else '—',
            'distance_m': round(self._route_distance_m, 1),
            'eta': eta if route_ok else '—',
        }

        alert = None
        loc = self.profile.get('location', 'Zone B - Aisle 4')
        if no_helmet:
            alert = {
                'title': 'No Helmet Detected',
                'location': loc,
                'time': datetime.now().strftime('%H:%M:%S'),
            }
        elif no_vest:
            alert = {
                'title': 'No Vest Detected',
                'location': loc,
                'time': datetime.now().strftime('%H:%M:%S'),
            }

        result = render_safe_route_dashboard(
            frame,
            workers=workers,
            boxes=boxes if workers else [],
            yellow_lines=yellow_lines,
            stats=stats,
            alert=alert,
        )
        self.violations.extend(violations)
        self.last_stats = dict(stats)
        self.last_stats['aisle_locked'] = bool(self._safe_route_frozen)
        self.last_overlay = {
            'workers': [dict(w) for w in workers],
            'forklifts': [],
            'boxes': [dict(b) for b in (boxes if workers else [])],
            'stats': dict(stats),
            'alert': dict(alert) if alert else None,
            'yellow_lines': [dict(ln) for ln in yellow_lines],
            'draw_zones': False,
        }
        return result, violations

    def _process_frame_project16(self, frame):
        """Video Project 16 only: PERSON + DANGER ZONE + PRODUCT TOUCH labels."""
        from .dashboard_project16 import (
            render_project16_dashboard,
            point_in_poly,
            _poly_px,
        )

        h, w = frame.shape[:2]
        danger_poly = _poly_px(self.profile['danger_zone'], w, h)
        product_poly = _poly_px(self.profile['product_zone'], w, h)

        people = []
        if self.pose_model is not None:
            pr = self.pose_model(frame, conf=0.15, imgsz=960, verbose=False)[0]
            if pr.boxes is not None and len(pr.boxes):
                kxy = pr.keypoints.xy.cpu().numpy() if pr.keypoints is not None else None
                kconf = None
                if pr.keypoints is not None and getattr(pr.keypoints, 'conf', None) is not None:
                    kconf = pr.keypoints.conf.cpu().numpy()
                for i, box in enumerate(pr.boxes):
                    xyxy = box.xyxy[0].cpu().numpy()
                    conf = float(box.conf[0])
                    kpts = kxy[i] if kxy is not None and i < len(kxy) else None
                    kc = kconf[i] if kconf is not None and i < len(kconf) else None
                    people.append({
                        'bbox': xyxy,
                        'conf': conf,
                        'keypoints': kpts,
                        'kp_conf': kc,
                    })

        if not people:
            results = self.model(
                frame,
                conf=max(0.20, float(getattr(self.config, 'PERSON_CONFIDENCE', 0.35))),
                imgsz=getattr(self.config, 'INFER_IMGSZ', 960),
                verbose=False,
            )[0]
            dets = self._extract_detections(results)
            for p in dets.get('person', []):
                people.append({
                    'bbox': p['bbox'],
                    'conf': float(p['conf']),
                    'keypoints': None,
                    'kp_conf': None,
                })

        def _body_center(person):
            """Torso absorb point: shoulders+hips mean (green tracking point)."""
            x1, y1, x2, y2 = map(float, person['bbox'])
            kpts = person.get('keypoints')
            kc = person.get('kp_conf')
            if kpts is not None and len(kpts) >= 13:
                pts = []
                for i in (5, 6, 11, 12):  # shoulders + hips
                    pt = kpts[i]
                    if pt[0] > 1 and pt[1] > 1:
                        if kc is not None and float(kc[i]) < 0.10:
                            continue
                        pts.append(pt)
                if pts:
                    arr = np.asarray(pts, dtype=np.float32)
                    return float(arr[:, 0].mean()), float(arr[:, 1].mean())
            return (x1 + x2) / 2.0, y1 + 0.55 * (y2 - y1)

        # Attach body-center tracking point on every person (for green absorb point)
        for p in people:
            p['body_center'] = _body_center(p)

        def _product_blobs():
            """Product fiber pile only — inside product_zone, not platform/rails."""
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            # Tobacco / straw product (muted brown–tan)
            brown = cv2.inRange(hsv, (6, 40, 40), (28, 170, 190))
            straw = cv2.inRange(hsv, (14, 35, 60), (36, 120, 210))
            raw = cv2.bitwise_or(brown, straw)
            # Bright yellow / orange paint (rails, posts) → exclude
            paint = cv2.inRange(hsv, (8, 100, 90), (42, 255, 255))
            raw = cv2.bitwise_and(raw, cv2.bitwise_not(paint))
            # Strict: product pile poly only (do NOT use full danger zone)
            zone = np.zeros((h, w), dtype=np.uint8)
            cv2.fillPoly(zone, [product_poly], 255)
            raw = cv2.bitwise_and(raw, zone)
            raw = cv2.morphologyEx(raw, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
            raw = cv2.morphologyEx(raw, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
            n, labels, stats, cents = cv2.connectedComponentsWithStats(raw, connectivity=8)
            blobs = []
            min_area = max(3000, int(0.0025 * w * h))
            for i in range(1, n):
                area = int(stats[i, cv2.CC_STAT_AREA])
                bw_ = int(stats[i, cv2.CC_STAT_WIDTH])
                bh_ = int(stats[i, cv2.CC_STAT_HEIGHT])
                if area < min_area:
                    continue
                aspect = max(bw_, bh_) / max(1.0, min(bw_, bh_))
                if aspect > 5.0:
                    continue
                blobs.append({
                    'cx': float(cents[i][0]),
                    'cy': float(cents[i][1]),
                    'area': area,
                    'label': i,
                })
            if blobs:
                blobs.sort(key=lambda b: -b['area'])
                top = blobs[0]['area']
                blobs = [b for b in blobs if b['area'] >= max(min_area * 2, 0.30 * top)][:4]
            return raw, labels, blobs

        fiber_mask, fiber_labels, fiber_blobs = _product_blobs()
        # Small dilate so fingertip on pile edge still counts
        fiber_contact = cv2.dilate(fiber_mask, np.ones((7, 7), np.uint8), iterations=1)
        snap_r = int(getattr(self, '_p16_touch_snap_px', 20))

        def _wrists(person):
            """Wrist keypoints with quality flag (collapsed arms marked bad)."""
            out = []
            kpts = person.get('keypoints')
            kc = person.get('kp_conf')
            x1, y1, x2, y2 = map(float, person['bbox'])
            bw, bh = max(1.0, x2 - x1), max(1.0, y2 - y1)
            if kpts is None or len(kpts) < 11:
                return out
            for shoulder_i, elbow_i, wrist_i in ((5, 7, 9), (6, 8, 10)):
                wr = kpts[wrist_i]
                if wr[0] <= 1 or wr[1] <= 1:
                    continue
                if kc is not None and float(kc[wrist_i]) < 0.12:
                    continue
                wx, wy = float(wr[0]), float(wr[1])
                sh = kpts[shoulder_i]
                el = kpts[elbow_i]
                ex = ey = sx = sy = None
                good = True
                if sh[0] > 1 and sh[1] > 1:
                    sx, sy = float(sh[0]), float(sh[1])
                    d_sh = ((wx - sx) ** 2 + (wy - sy) ** 2) ** 0.5
                    if d_sh < max(18.0, 0.08 * max(bw, bh)):
                        good = False
                    if abs(wy - sy) < 18 and d_sh < max(40.0, 0.18 * max(bw, bh)):
                        good = False
                if el[0] > 1 and el[1] > 1:
                    ex, ey = float(el[0]), float(el[1])
                    forearm = ((wx - ex) ** 2 + (wy - ey) ** 2) ** 0.5
                    if forearm < max(14.0, 0.08 * max(bw, bh)):
                        good = False
                    if sy is not None and wy < sy - 12:
                        good = False
                out.append({
                    'xy': (wx, wy),
                    'elbow': (ex, ey),
                    'shoulder': (sx, sy),
                    'good': good,
                    'side': 'L' if wrist_i == 9 else 'R',
                })
            return out

        def _fiber_density(ix, iy, r=10):
            patch = fiber_mask[
                max(0, iy - r) : min(h, iy + r + 1),
                max(0, ix - r) : min(w, ix + r + 1),
            ]
            return float(np.count_nonzero(patch)) / float(max(1, patch.size))

        def _snap_to_fiber(px, py, max_dist):
            """If hand is just above pile edge, snap to nearest fiber pixel."""
            ix, iy = int(round(px)), int(round(py))
            if ix < 2 or iy < 2 or ix >= w - 2 or iy >= h - 2:
                return None, 0.0
            best = None
            best_d2 = max_dist * max_dist + 1
            y0, y1 = max(0, iy - max_dist), min(h, iy + max_dist + 1)
            x0, x1 = max(0, ix - max_dist), min(w, ix + max_dist + 1)
            roi = fiber_contact[y0:y1, x0:x1]
            ys, xs = np.where(roi > 0)
            if len(xs) == 0:
                return None, 0.0
            for x, y in zip(xs, ys):
                gx, gy = int(x + x0), int(y + y0)
                if not point_in_poly(float(gx), float(gy), product_poly):
                    continue
                d2 = (gx - ix) ** 2 + (gy - iy) ** 2
                if d2 < best_d2:
                    best_d2 = d2
                    best = (gx, gy)
            if best is None:
                return None, 0.0
            local = _fiber_density(best[0], best[1], r=10)
            if local < 0.16:
                return None, local
            return best, local

        def _hand_contact(px, py):
            """True when wrist/fingertip is on (or within snap_r of) the product pile."""
            ix, iy = int(round(px)), int(round(py))
            if ix < 2 or iy < 2 or ix >= w - 2 or iy >= h - 2:
                return False, 0.0, None
            # Direct hit on fiber inside product zone
            if point_in_poly(float(ix), float(iy), product_poly) and fiber_contact[iy, ix]:
                local = _fiber_density(ix, iy, r=10)
                if local >= 0.16:
                    return True, local, (ix, iy)
            # Hand slightly above pile — snap to nearest fiber within snap_r
            hit, local = _snap_to_fiber(px, py, snap_r)
            if hit is not None:
                return True, local, hit
            return False, 0.0, None

        in_danger = False
        product_touch = False
        touch_point = None
        touch_score = -1e9
        touch_owner = None

        for pi, p in enumerate(people):
            x1, y1, x2, y2 = map(float, p['bbox'])
            bw, bh = max(1.0, x2 - x1), max(1.0, y2 - y1)
            samples = [
                ((x1 + x2) / 2.0, y2 - 4),
                ((x1 + x2) / 2.0, y1 + bh * 0.75),
                ((x1 + x2) / 2.0, y1 + bh * 0.45),
                (x1 + bw * 0.35, y2 - 4),
                (x1 + bw * 0.65, y2 - 4),
            ]
            if any(point_in_poly(sx, sy, danger_poly) for sx, sy in samples):
                in_danger = True
            cx, cy = _body_center(p)
            if point_in_poly(cx, cy, danger_poly):
                in_danger = True

            # PRODUCT TOUCH = wrist/fingertip on or at edge of product pile
            best_local = None
            best_local_sc = -1e9
            for winfo in _wrists(p):
                # Prefer good wrists; still allow weak wrists if contact is strong
                wx, wy = winfo['xy']
                ex, ey = winfo['elbow']
                candidates = [(wx, wy, 1.0 if winfo['good'] else 0.75)]
                if ex is not None and ey is not None:
                    fvx, fvy = wx - ex, wy - ey
                    fn = max(1e-3, (fvx * fvx + fvy * fvy) ** 0.5)
                    if fn >= 16.0:
                        for tip in (12.0, 24.0, 36.0):
                            if tip > min(40.0, 0.45 * fn):
                                break
                            candidates.append((
                                wx + fvx / fn * tip,
                                wy + fvy / fn * tip,
                                1.2 if winfo['good'] else 0.9,
                            ))
                for px, py, bonus in candidates:
                    ok, local, hit = _hand_contact(px, py)
                    if not ok or hit is None:
                        continue
                    if not winfo['good'] and local < 0.28:
                        continue
                    sc = local * 100.0 * bonus
                    if sc > best_local_sc:
                        best_local_sc = sc
                        best_local = hit

            if best_local is not None and best_local_sc > touch_score:
                touch_score = best_local_sc
                touch_point = best_local
                product_touch = True
                touch_owner = pi
                p['touch_point'] = touch_point

        # Debounce: confirm PRODUCT TOUCH (default 1 = immediate on contact)
        raw_touch = bool(product_touch)
        if raw_touch:
            self._p16_touch_streak = int(getattr(self, '_p16_touch_streak', 0)) + 1
        else:
            self._p16_touch_streak = 0
            touch_point = None
        need = int(getattr(self, '_p16_touch_confirm_frames', 1))
        product_touch = self._p16_touch_streak >= need
        if not product_touch:
            touch_point = None

        # Prefer video/motion clock when live 1× playback sets it
        if getattr(self, '_motion_clock', None) is not None:
            now = float(self._motion_clock)
        else:
            now = time.time()

        # Zone absorb time — continuous presence in danger zone
        if in_danger:
            if self._p16_zone_enter_t is None:
                self._p16_zone_enter_t = now
            if not self._p16_was_in_danger:
                self._p16_alert_count += 1
            self._p16_was_in_danger = True
            elapsed = max(0, int(now - self._p16_zone_enter_t))
        else:
            self._p16_zone_enter_t = None
            self._p16_was_in_danger = False
            elapsed = 0

        # Product touch absorb time — starts the moment contact is confirmed
        touch_elapsed = 0
        if product_touch:
            if self._p16_touch_enter_t is None:
                self._p16_touch_enter_t = now
            self._p16_was_touching = True
            touch_elapsed = max(0, int(now - self._p16_touch_enter_t))
        else:
            self._p16_touch_enter_t = None
            self._p16_was_touching = False
            self._p16_touch_alert_latched = False
            self._p16_touch_start_latched = False
            touch_elapsed = 0
            touch_point = None

        def _fmt(sec: int) -> str:
            hh, mm, ss = sec // 3600, (sec % 3600) // 60, sec % 60
            return f"{hh:02d}:{mm:02d}:{ss:02d}"

        duration_str = _fmt(elapsed)
        touch_duration_str = _fmt(touch_elapsed)

        pose_points = 0
        for p in people:
            kpts = p.get('keypoints')
            kc = p.get('kp_conf')
            if kpts is None:
                continue
            for i, pt in enumerate(kpts):
                if pt[0] <= 1 or pt[1] <= 1:
                    continue
                if kc is not None and float(kc[i]) < 0.10:
                    continue
                pose_points += 1

        violations = []
        if in_danger:
            violations.append({
                'type': 'PERSON_IN_DANGER_ZONE',
                'product_touch': product_touch,
                'zone_absorb_sec': elapsed,
                'timestamp': datetime.now().isoformat(),
            })
            if self.logger:
                self.logger.warning(
                    "VIOLATION: PERSON IN DANGER ZONE"
                    + (" + PRODUCT TOUCH" if product_touch else "")
                    + f" (absorb {duration_str})"
                )

        # Immediate alert the moment product is touched
        if product_touch and not self._p16_touch_start_latched:
            self._p16_touch_start_latched = True
            self._p16_alert_count += 1
            violations.append({
                'type': 'PERSON_PRODUCT_TOUCH',
                'touch_sec': touch_elapsed,
                'timestamp': datetime.now().isoformat(),
            })
            if self.logger:
                self.logger.warning("VIOLATION: PERSON PRODUCT TOUCH (contact)")

        # Duration alert when product touch is sustained
        touch_thr = float(getattr(self, '_p16_touch_alert_sec', 1.0))
        if product_touch and touch_elapsed >= touch_thr and not self._p16_touch_alert_latched:
            self._p16_touch_alert_latched = True
            self._p16_alert_count += 1
            violations.append({
                'type': 'PERSON_PRODUCT_TOUCH_TIME',
                'touch_sec': touch_elapsed,
                'threshold_sec': touch_thr,
                'timestamp': datetime.now().isoformat(),
            })
            if self.logger:
                self.logger.warning(
                    f"VIOLATION: PERSON PRODUCT TOUCH TIME ({touch_elapsed}s >= {touch_thr:.0f}s)"
                )

        location = self.profile.get('location', 'Production Line - Zone B')
        alerts_today = max(
            self._p16_alert_count,
            len([
                v for v in self.violations
                if v.get('type') in (
                    'PERSON_IN_DANGER_ZONE',
                    'PERSON_PRODUCT_TOUCH',
                    'PERSON_PRODUCT_TOUCH_TIME',
                )
            ]),
        )
        result = render_project16_dashboard(
            frame,
            people=people,
            danger_poly=danger_poly,
            product_poly=product_poly,
            in_danger=in_danger,
            product_touch=product_touch,
            touch_point=touch_point,
            duration_str=duration_str,
            location=location,
            alerts_today=alerts_today,
            touch_duration_str=touch_duration_str,
            pose_points=pose_points,
        )
        self.violations.extend(violations)
        self.last_stats = {
            'workers': len(people),
            'forklifts': 0,
            'yellow_lines': 0,
            'boxes': 0,
            'total': len(people),
            'product_touch': bool(product_touch),
            'in_danger': bool(in_danger),
            'zone_absorb_sec': elapsed,
            'touch_absorb_sec': touch_elapsed,
            'pose_points': pose_points,
        }
        # Sticky overlay for 1× live — without this, UI shows raw source only
        sticky_people = []
        for p in people:
            item = {
                'bbox': np.asarray(p['bbox'], dtype=np.float32).copy(),
                'conf': float(p.get('conf', 0)),
                'body_center': p.get('body_center'),
                'keypoints': None,
                'kp_conf': None,
            }
            if p.get('keypoints') is not None:
                item['keypoints'] = np.asarray(p['keypoints'], dtype=np.float32).copy()
            if p.get('kp_conf') is not None:
                item['kp_conf'] = np.asarray(p['kp_conf'], dtype=np.float32).copy()
            sticky_people.append(item)
        self.last_overlay = {
            'mode': 'project16',
            'people': sticky_people,
            'danger_poly': danger_poly.copy(),
            'product_poly': product_poly.copy(),
            'in_danger': bool(in_danger),
            'product_touch': bool(product_touch),
            'touch_point': touch_point,
            'duration_str': duration_str,
            'touch_duration_str': touch_duration_str,
            'location': location,
            'alerts_today': int(alerts_today),
            'pose_points': int(pose_points),
        }
        return result, violations

    def _check_conveyor_safety(self, frame, people, conveyors):
        """Check 1: Man Near Conveyor"""
        violations = []
        if not people or not conveyors:
            return violations

        for person in people:
            for conveyor in conveyors:
                dist = calculate_distance(
                    get_bbox_center(person['bbox']),
                    get_bbox_center(conveyor['bbox'])
                )
                if dist < self.config.CONVEYOR_DANGER_DISTANCE:
                    violations.append({
                        'type': 'MAN_NEAR_CONVEYOR',
                        'distance': float(dist),
                        'timestamp': datetime.now().isoformat()
                    })
                    self.logger.warning(
                        f"VIOLATION: Person near conveyor (distance: {dist:.1f}px)"
                    )
        return violations

    def _check_harness_compliance(self, frame, people, harnesses):
        """Check 2: Safety Harness Compliance"""
        violations = []
        if harnesses and len(people) > len(harnesses):
            missing = len(people) - len(harnesses)
            violations.append({
                'type': 'NO_HARNESS',
                'count': missing,
                'timestamp': datetime.now().isoformat()
            })
            self.logger.warning(f"VIOLATION: {missing} person(s) without harness")
        return violations

    def _check_forklift_safety(self, frame, forklifts):
        """Track forklifts across frames and estimate speed (km/h).

        Annotates each forklift with:
          track_id, speed_kmh, speed_px_s, overspeed
        and emits FORKLIFT_OVERSPEED when above the aisle limit.

        Prefers video/motion clock (set by live 1× playback) so sparse YOLO
        still measures speed over real video time instead of wall-clock gaps.
        """
        violations = []
        # Video time (seconds) when available — critical for 1× display + slow AI
        if getattr(self, '_motion_clock', None) is not None:
            now = float(self._motion_clock)
            using_video_clock = True
        else:
            now = time.time()
            using_video_clock = False

        limit_kmh = float(getattr(self.config, 'FORKLIFT_SPEED_LIMIT_KMH', 8.0))
        ref_h_m = float(self.profile.get(
            'forklift_ref_height_m',
            getattr(self.config, 'FORKLIFT_REF_HEIGHT_M', 2.2),
        ))
        ema = float(getattr(self.config, 'FORKLIFT_SPEED_EMA', 0.35))
        max_dist = float(self.profile.get(
            'forklift_track_max_dist',
            getattr(self.config, 'FORKLIFT_TRACK_MAX_DIST', 160),
        ))
        # Slow AI / skipped frames: keep tracks alive longer
        default_ttl = 12.0 if using_video_clock else 1.5
        ttl = float(self.profile.get(
            'forklift_track_ttl',
            getattr(self.config, 'FORKLIFT_TRACK_TTL', default_ttl),
        ))
        if using_video_clock:
            ttl = max(ttl, 8.0)

        # Drop stale tracks
        self._forklift_tracks = {
            tid: tr for tid, tr in self._forklift_tracks.items()
            if (now - tr['time']) <= ttl
        }

        # Greedy nearest-neighbor match: detection ↔ existing track
        unused = set(self._forklift_tracks.keys())
        assignments = []  # (det_idx, tid, dist)

        centers = []
        for fl in forklifts:
            centers.append(get_bbox_center(fl['bbox']))

        for i, center in enumerate(centers):
            best_tid, best_d = None, None
            for tid in unused:
                tr = self._forklift_tracks[tid]
                dt_guess = max(now - float(tr['time']), 1e-3)
                # Allow larger match radius when frames are far apart in video time
                radius = max_dist * float(min(max(dt_guess / 0.2, 1.0), 10.0))
                d = calculate_distance(center, tr['center'])
                if d <= radius and (best_d is None or d < best_d):
                    best_d, best_tid = d, tid
            if best_tid is not None:
                unused.discard(best_tid)
                assignments.append((i, best_tid, best_d or 0.0))
            else:
                assignments.append((i, None, 0.0))

        max_speed = 0.0
        any_overspeed = False

        for i, tid, _dist in assignments:
            fl = forklifts[i]
            center = centers[i]
            x1, y1, x2, y2 = fl['bbox']
            bbox_h = max(8.0, float(y2 - y1))
            # meters per pixel from assumed forklift height in frame
            m_per_px = ref_h_m / bbox_h

            if tid is None:
                tid = self._next_forklift_tid
                self._next_forklift_tid += 1
                self._forklift_tracks[tid] = {
                    'center': center,
                    'time': now,
                    'speed_kmh': 0.0,
                    'speed_px_s': 0.0,
                    'bbox_h': bbox_h,
                }
                speed_kmh = 0.0
                speed_px = 0.0
            else:
                prev = self._forklift_tracks[tid]
                dt = max(now - prev['time'], 1e-3)
                dist_px = calculate_distance(center, prev['center'])
                jump_lim = max_dist * float(min(max(dt / 0.2, 1.8), 12.0))
                # Ignore huge jumps (ID swaps / detection flicker)
                if dist_px > jump_lim:
                    speed_px = prev.get('speed_px_s', 0.0)
                    speed_kmh = prev.get('speed_kmh', 0.0)
                else:
                    speed_px = dist_px / dt
                    speed_m_s = (dist_px * m_per_px) / dt
                    raw_kmh = speed_m_s * 3.6
                    # Clamp absurd spikes from tracking noise
                    raw_kmh = float(min(max(raw_kmh, 0.0), 40.0))
                    prev_kmh = float(prev.get('speed_kmh', 0.0))
                    # First real sample after a zero track: trust raw more
                    if prev_kmh < 0.15 and raw_kmh > 0.3:
                        speed_kmh = raw_kmh
                    else:
                        speed_kmh = (ema * raw_kmh) + ((1.0 - ema) * prev_kmh)
                    speed_px = (ema * speed_px) + ((1.0 - ema) * float(prev.get('speed_px_s', 0.0)))

                self._forklift_tracks[tid] = {
                    'center': center,
                    'time': now,
                    'speed_kmh': speed_kmh,
                    'speed_px_s': speed_px,
                    'bbox_h': bbox_h,
                }

            overspeed = speed_kmh > limit_kmh and speed_kmh > 0.5
            fl['track_id'] = tid
            fl['speed_kmh'] = round(speed_kmh, 1)
            fl['speed_px_s'] = round(speed_px, 1)
            fl['overspeed'] = bool(overspeed)
            fl['speed_limit_kmh'] = limit_kmh

            max_speed = max(max_speed, speed_kmh)
            if overspeed:
                any_overspeed = True
                last_alert = self._forklift_overspeed_cooldown.get(tid, 0.0)
                cooldown_ref = time.time()  # wall clock for alert spam control
                if (cooldown_ref - last_alert) >= 2.0:
                    self._forklift_overspeed_cooldown[tid] = cooldown_ref
                    violations.append({
                        'type': 'FORKLIFT_OVERSPEED',
                        'speed': float(round(speed_kmh, 1)),
                        'speed_kmh': float(round(speed_kmh, 1)),
                        'limit_kmh': limit_kmh,
                        'track_id': tid,
                        'timestamp': datetime.now().isoformat(),
                    })
                    if self.logger:
                        self.logger.warning(
                            f"VIOLATION: Forklift overspeed {speed_kmh:.1f} km/h "
                            f"(limit {limit_kmh:.1f})"
                        )

        # Expose aggregate for dashboard / live API (set by caller into stats)
        if not forklifts and self._forklift_tracks:
            # Brief miss: keep last track speed so UI doesn't flicker to 0.0
            coast = max(
                (float(tr.get('speed_kmh', 0.0)) for tr in self._forklift_tracks.values()),
                default=0.0,
            )
            max_speed = max(max_speed, coast)
        self._last_forklift_speed = {
            'forklift_speed_kmh': round(max_speed, 1),
            'forklift_speed_limit_kmh': limit_kmh,
            'forklift_overspeed': any_overspeed or (max_speed > limit_kmh and max_speed > 0.5),
        }
        return violations

    def save_report(self):
        """Save violations report"""
        os.makedirs(self.config.REPORT_DIR, exist_ok=True)
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_violations': len(self.violations),
            'violations': self.violations
        }
        report_file = os.path.join(self.config.REPORT_DIR, 'gls_report.json')
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"Report saved: {report_file}")
