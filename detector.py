"""
Módulo de detecção de livros por visão computacional usando YOLOv8.
"""

import os
import cv2
import numpy as np
import threading
import time
from ultralytics import YOLO

class BookDetector:
    """Detecta a presença de um livro usando YOLOv8."""

    def __init__(self, camera_index: int = 0):
        self.camera_index = camera_index
        self.current_frame: np.ndarray | None = None
        self.last_results = None
        self.running = True
        self.paused = False
        
        # Carrega o modelo nano (se não tiver baixado, ele baixa ~6MB automaticamente)
        print("[Detector] Carregando modelo YOLOv8n...")
        self.model = YOLO('yolov8n.pt')
        print("[Detector] Modelo carregado!")

        # Inicia a thread de captura contínua de vídeo
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()

    def set_camera(self, index: int):
        """Altera a câmera em tempo real."""
        print(f"[Detector] Trocando para a câmera {index}...")
        self.camera_index = index
        self.current_frame = None

    def pause(self, state: bool):
        self.paused = state
        if state:
            self.clear_results()

    def clear_results(self):
        self.last_results = None

    def _capture_loop(self):
        """Loop em background para manter a câmera sempre pronta."""
        cap = None
        last_index = -1

        while self.running:
            if cap is None or last_index != self.camera_index:
                if cap is not None:
                    cap.release()
                cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
                if not cap.isOpened():
                    cap = cv2.VideoCapture(self.camera_index)
                last_index = self.camera_index

            if cap and cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    self.current_frame = frame

            time.sleep(0.03)

    def stop(self):
        """Para a thread de captura."""
        self.running = False

    def capture_frame(self) -> np.ndarray | None:
        """Retorna o frame mais recente em BGR."""
        return self.current_frame

    def generate_frames(self):
        """Generator para streaming MJPEG (Video Feed) com YOLO boxes."""
        while self.running:
            frame = self.current_frame
            if frame is not None:
                display_frame = frame.copy()
                
                # Desenha os bounding boxes da última inferência
                if self.last_results is not None:
                    for box in self.last_results:
                        x1, y1, x2, y2 = box['coords']
                        label = box['label']
                        conf = box['conf']
                        
                        # Desenha a caixa verde
                        cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 255, 0), 3)
                        # Fundo para o texto
                        (w, h), _ = cv2.getTextSize(f"{label} {conf:.2f}", cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                        cv2.rectangle(display_frame, (x1, y1 - 25), (x1 + w, y1), (0, 255, 0), -1)
                        # Texto
                        cv2.putText(display_frame, f"{label} {conf:.2f}", (x1, y1 - 5), 
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

                _, buffer = cv2.imencode(".jpg", display_frame)
                frame_bytes = buffer.tobytes()
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
                )
            time.sleep(0.05)

    def verify(self) -> dict:
        """Processa o frame atual no YOLOv8 e retorna se achou um livro."""
        frame = self.capture_frame()
        if frame is None:
            return {
                "book_detected": False,
                "confidence": 0.0,
                "objects_found": 0,
                "message": "Câmera indisponível.",
            }

        # Roda a inferência (classes 73 = book, 67 = cell phone para testar)
        results = self.model.predict(source=frame, classes=[67, 73], verbose=False)
        
        detected_objects = []
        highest_conf = 0.0
        
        for result in results:
            boxes = result.boxes
            for box in boxes:
                # Extrai coordenadas, confiança e classe
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = float(box.conf[0])
                cls = int(box.cls[0])
                
                if conf > highest_conf:
                    highest_conf = conf
                    
                label = "Livro" if cls == 73 else "Celular (Teste)"
                
                detected_objects.append({
                    "coords": (x1, y1, x2, y2),
                    "conf": conf,
                    "label": label
                })

        self.last_results = detected_objects
        book_detected = len(detected_objects) > 0

        return {
            "book_detected": book_detected,
            "confidence": round(highest_conf, 2),
            "contours_found": len(detected_objects),
            "message": f"Objeto detectado ({len(detected_objects)} encontrados)."
            if book_detected
            else "Nenhum livro detectado na mesa.",
        }

    @property
    def is_calibrated(self) -> bool:
        # YOLO não precisa de calibração de baseline
        return True
