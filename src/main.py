# """Main Entry Point"""
# import argparse
# import cv2
# import time
# from .config import Config
# from .trainer import YOLOv8Trainer
# from .monitor import ComplianceMonitor
# from .utils import ensure_directories

# def train_command(args):
#     """Execute training"""
#     ensure_directories()
#     trainer = YOLOv8Trainer()
#     trainer.train(
#         data_path=args.data_path,
#         model_size=args.model,
#         epochs=args.epochs,
#         batch_size=args.batch,
#         imgsz=args.imgsz,
#         device=args.device
#     )

# def monitor_command(args):
#     """Execute monitoring"""
#     ensure_directories()
    
#     monitor = ComplianceMonitor(args.model)
    
#     source = int(args.source) if args.source.isdigit() else args.source
#     cap = cv2.VideoCapture(source)
    
#     if not cap.isOpened():
#         print(f"ERROR: Cannot open source: {source}")
#         return
    
#     fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
#     width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
#     height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
#     video_writer = None
#     if args.save_video:
#         fourcc = cv2.VideoWriter_fourcc(*'mp4v')
#         video_writer = cv2.VideoWriter(args.output, fourcc, fps, (width, height))
    
#     frame_count = 0
#     start_time = time.time()
    
#     print("Monitoring started... (q=quit, s=screenshot)")
    
#     while True:
#         ret, frame = cap.read()
#         if not ret:
#             break
        
#         result_frame, violations = monitor.process_frame(frame)
        
#         if video_writer:
#             video_writer.write(result_frame)
        
#         frame_count += 1
#         elapsed = time.time() - start_time
#         fps_display = frame_count / elapsed if elapsed > 0 else 0
        
#         cv2.putText(result_frame, f'FPS: {fps_display:.1f}', (width - 150, 30),
#                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
        
#         cv2.imshow('GLS Warehouse Safety Monitor', result_frame)
        
#         if frame_count % 30 == 0:
#             print(f'Frame {frame_count} | FPS {fps_display:.1f} | Violations {len(violations)}')
        
#         key = cv2.waitKey(1) & 0xFF
#         if key == ord('q'):
#             break
#         elif key == ord('s'):
#             cv2.imwrite(f'screenshot_{frame_count}.png', result_frame)
    
#     cap.release()
#     if video_writer:
#         video_writer.release()
#     cv2.destroyAllWindows()
    
#     monitor.save_report()
#     print(f"\nMonitoring complete!")
#     print(f"Total violations: {len(monitor.violations)}")

# def main():
#     """Main entry point"""
#     parser = argparse.ArgumentParser(
#         description='GLS Warehouse Safety Compliance System',
#         formatter_class=argparse.RawDescriptionHelpFormatter
#     )
    
#     subparsers = parser.add_subparsers(dest='command', help='Command')
    
#     # Training command
#     train_parser = subparsers.add_parser('train', help='Train model')
#     train_parser.add_argument('--data-path', default='data/dataset', help='Dataset path')
#     train_parser.add_argument('--model', default='m', choices=['n','s','m','l','x'], help='Model size')
#     train_parser.add_argument('--epochs', type=int, default=150, help='Epochs')
#     train_parser.add_argument('--batch', type=int, default=16, help='Batch size')
#     train_parser.add_argument('--imgsz', type=int, default=640, help='Image size')
#     # train_parser.add_argument('--device', type=int, default=0, help='GPU device')
#     train_parser.add_argument('--device', type=str, default='cpu', help='Device: cpu or GPU device ID (0,1,2...)')
#     train_parser.set_defaults(func=train_command)
    
#     # Monitoring command
#     monitor_parser = subparsers.add_parser('monitor', help='Real-time monitoring')
#     monitor_parser.add_argument('--model', default=Config.MODEL_PATH, help='Model path')
#     monitor_parser.add_argument('--source', default='0', help='Video source')
#     monitor_parser.add_argument('--output', default='outputs/videos/gls_output.mp4', help='Output video')
#     monitor_parser.add_argument('--save-video', action='store_true', help='Save video')
#     monitor_parser.set_defaults(func=monitor_command)
    
#     args = parser.parse_args()
    
#     if args.command:
#         args.func(args)
#     else:
#         parser.print_help()

# if __name__ == '__main__':
#     main()

"""Main Entry Point"""
import argparse
import cv2
import os
import time
from .config import Config
from .monitor import ComplianceMonitor
from .utils import ensure_directories

def train_command(args):
    """Execute training - import trainer only when needed"""
    from .trainer import YOLOv8Trainer  # ← Import ONLY when training
    
    ensure_directories()
    trainer = YOLOv8Trainer()
    trainer.train(
        data_path=args.data_path,
        model_size=args.model,
        epochs=args.epochs,
        batch_size=args.batch,
        imgsz=args.imgsz,
        device=args.device
    )

def monitor_command(args):
    """Execute monitoring"""
    ensure_directories()

    source = int(args.source) if args.source.isdigit() else args.source
    if isinstance(source, str) and not os.path.isfile(source):
        print(f"ERROR: Video file not found: {source}")
        print(f"Copy the .mp4 into data/videos/ then run again.")
        print(f"Current videos: {os.path.join('data', 'videos')}")
        return

    from .camera_profiles import resolve_profile
    profile = resolve_profile(source, camera_id=getattr(args, 'camera_id', None))
    monitor = ComplianceMonitor(args.model, profile=profile)

    cap = cv2.VideoCapture(source)
    
    if not cap.isOpened():
        print(f"ERROR: Cannot open source: {source}")
        print("File exists but OpenCV cannot decode it. Try re-exporting as H.264 .mp4.")
        return
    
    fps = int(cap.get(cv2.CAP_PROP_FPS)) or 30
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    video_fps = float(cap.get(cv2.CAP_PROP_FPS) or 25.0)
    if video_fps < 1.0:
        video_fps = 25.0
    is_file = not str(source).isdigit()
    
    video_writer = None
    if args.save_video:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        video_writer = cv2.VideoWriter(args.output, fourcc, fps, (width, height))
    
    frame_count = 0
    file_frame_i = 0
    start_time = time.time()
    playback_t0 = time.time()
    
    window_title = profile.get('title', 'Hypervis Warehouse Safety Monitor - AI Powered')
    print(
        f"Monitoring started... profile={profile.get('name')} "
        f"playback=1x@{video_fps:.0f}fps (q=quit, s=screenshot)"
    )
    
    while True:
        # Keep OpenCV window at ~normal video speed (skip when YOLO is slow)
        if is_file:
            target = int((time.time() - playback_t0) * video_fps)
            max_skip = max(1, target - file_frame_i)
            skipped = 0
            while file_frame_i < target and skipped < max_skip:
                if not cap.grab():
                    break
                file_frame_i += 1
                skipped += 1

        ret, frame = cap.read()
        if not ret:
            break
        file_frame_i += 1
        
        result_frame, violations = monitor.process_frame(frame)
        
        if video_writer:
            video_writer.write(result_frame)
        
        frame_count += 1
        elapsed = time.time() - start_time
        fps_display = frame_count / elapsed if elapsed > 0 else 0

        display = result_frame
        if width > 1600:
            scale = 1600 / float(width)
            display = cv2.resize(result_frame, (1600, int(height * scale)))

        cv2.putText(display, f'FPS: {fps_display:.1f}', (display.shape[1] - 140, 28),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        cv2.imshow(window_title, display)

        if frame_count % 30 == 0:
            print(f'Frame {frame_count} | FPS {fps_display:.1f} | Violations {len(violations)}')

        # Pace to video clock if we got ahead
        if is_file:
            ideal = playback_t0 + (file_frame_i / video_fps)
            delay = ideal - time.time()
            wait_ms = 1
            if delay > 0.002:
                wait_ms = min(40, max(1, int(delay * 1000)))
            key = cv2.waitKey(wait_ms) & 0xFF
        else:
            key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            cv2.imwrite(f'screenshot_{frame_count}.png', result_frame)

    cap.release()
    if video_writer:
        video_writer.release()
    cv2.destroyAllWindows()
    
    monitor.save_report()
    print(f"\nMonitoring complete!")
    print(f"Total violations: {len(monitor.violations)}")

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='GLS Warehouse Safety Compliance System',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command')
    
    # Training command
    train_parser = subparsers.add_parser('train', help='Train model')
    train_parser.add_argument('--data-path', default='data/dataset', help='Dataset path')
    train_parser.add_argument('--model', default='m', choices=['n','s','m','l','x'], help='Model size')
    train_parser.add_argument('--epochs', type=int, default=150, help='Epochs')
    train_parser.add_argument('--batch', type=int, default=16, help='Batch size')
    train_parser.add_argument('--imgsz', type=int, default=640, help='Image size')
    train_parser.add_argument('--device', type=str, default='cpu', help='Device: cpu or GPU device ID')
    train_parser.set_defaults(func=train_command)
    
    # Monitoring command
    monitor_parser = subparsers.add_parser('monitor', help='Real-time monitoring')
    monitor_parser.add_argument('--model', default=Config.MODEL_PATH, help='Model path')
    monitor_parser.add_argument('--source', default='0', help='Video source')
    monitor_parser.add_argument('--output', default='outputs/videos/gls_output.mp4', help='Output video')
    monitor_parser.add_argument('--save-video', action='store_true', help='Save video')
    monitor_parser.add_argument(
        '--camera-id', default=None,
        help='Stable camera identity to look up in config/cameras.json '
             '(e.g. loading_dock_1). Defaults to the source filename.',
    )
    monitor_parser.set_defaults(func=monitor_command)
    
    args = parser.parse_args()
    
    if args.command:
        args.func(args)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()