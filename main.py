import os
import time
import asyncio
import requests
from enum import Enum
from pydantic import BaseModel
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from detector import BookDetector
from dotenv import load_dotenv

load_dotenv()

PORT = int(os.getenv("PORT", "8000"))
CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", "0"))

class AppState(str, Enum):
    IDLE = "IDLE"
    AWAITING = "AWAITING"
    VALIDATING = "VALIDATING"
    DONE = "DONE"

class GlobalState:
    status = AppState.IDLE
    session_id = None
    webhook_url = None
    validation_start = None
    time_left = 10

app = FastAPI(title="Visão Computacional - 2a Camada", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

detector = BookDetector(camera_index=CAMERA_INDEX)

# ------------------------------------------------------------------ #
#  Endpoints de Controle de Estado                                   #
# ------------------------------------------------------------------ #

class StartVisionRequest(BaseModel):
    session_id: str
    webhook_url: str

@app.post("/start-vision", tags=["Controle"])
def start_vision(req: StartVisionRequest):
    """Acorda a câmera e inicia a validação da 2a camada."""
    GlobalState.status = AppState.AWAITING
    GlobalState.session_id = req.session_id
    GlobalState.webhook_url = req.webhook_url
    GlobalState.validation_start = None
    GlobalState.time_left = 10
    detector.clear_results()
    return {"success": True, "message": "Visão computacional ativada e aguardando livro."}

@app.post("/reset-vision", tags=["Controle"])
def reset_vision():
    """Força o sistema a voltar para IDLE (Standby)."""
    GlobalState.status = AppState.IDLE
    GlobalState.session_id = None
    GlobalState.webhook_url = None
    GlobalState.validation_start = None
    GlobalState.time_left = 10
    detector.clear_results()
    return {"success": True, "message": "Sistema em Standby."}

@app.get("/health", tags=["GUI"])
def health():
    return {
        "status": "ok",
        "app_state": GlobalState.status.value,
        "time_left": GlobalState.time_left,
        "camera_index": detector.camera_index,
    }

# ------------------------------------------------------------------ #
#  GUI e Configurações                                                 #
# ------------------------------------------------------------------ #

@app.get("/", response_class=HTMLResponse, tags=["GUI"])
def serve_gui():
    html_path = os.path.join(os.path.dirname(__file__), "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()

@app.get("/video_feed", tags=["GUI"])
def video_feed():
    return StreamingResponse(
        detector.generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )

class CameraConfig(BaseModel):
    camera_index: int

@app.post("/config/camera", tags=["GUI"])
def change_camera(config: CameraConfig):
    detector.set_camera(config.camera_index)
    return {"success": True, "message": f"Câmera alterada para {config.camera_index}"}

# ------------------------------------------------------------------ #
#  Máquina de Estados em Background                                    #
# ------------------------------------------------------------------ #

async def state_machine_loop():
    """Loop isolado que faz a inferência apenas quando necessário e aciona o webhook."""
    while True:
        await asyncio.sleep(0.3)  # Frequência de verificação: 330ms
        
        if GlobalState.status in [AppState.AWAITING, AppState.VALIDATING]:
            result = detector.verify()
            
            if result["book_detected"]:
                if GlobalState.status == AppState.AWAITING:
                    GlobalState.status = AppState.VALIDATING
                    GlobalState.validation_start = time.time()
                
                elapsed = time.time() - GlobalState.validation_start
                GlobalState.time_left = max(10 - int(elapsed), 0)
                
                if elapsed >= 10:
                    GlobalState.status = AppState.DONE
                    GlobalState.time_left = 0
                    
                    # Dispara o Webhook para a API NestJS informando o sucesso
                    print(f"[*] Validado! Disparando Webhook para {GlobalState.webhook_url}...")
                    try:
                        requests.post(GlobalState.webhook_url, json={
                            "sessionId": GlobalState.session_id,
                            "visionVerified": True
                        }, timeout=5)
                        print("[*] Webhook enviado com sucesso.")
                    except Exception as e:
                        print(f"[!] Erro no Webhook: {e}")
                        
            else:
                # Se o livro sumir ou o rosto atrapalhar, a contagem reseta!
                if GlobalState.status == AppState.VALIDATING:
                    GlobalState.status = AppState.AWAITING
                    GlobalState.validation_start = None
                    GlobalState.time_left = 10

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(state_machine_loop())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=PORT)
