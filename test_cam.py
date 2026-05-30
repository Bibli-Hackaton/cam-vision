import cv2

print("Testando câmeras conectadas...")
for i in range(5):
    cap = cv2.VideoCapture(i, cv2.CAP_DSHOW) # CAP_DSHOW ajuda no Windows
    if cap.isOpened():
        ret, frame = cap.read()
        if ret:
            # Verifica se o frame é totalmente preto (todas as cores == 0)
            is_black = frame.max() == 0
            status = "IMAGEM PRETA (provavelmente bloqueada ou tampa fechada)" if is_black else "IMAGEM OK!"
            print(f"[OK] Camera {i} encontrada: {status}")
        else:
            print(f"[WARN] Camera {i} abre, mas nao retorna frame.")
        cap.release()
    else:
        print(f"[ERROR] Camera {i} indisponivel.")
