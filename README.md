# Bibli — Serviço de Reconhecimento de Livros 📷

Microserviço de **visão computacional** para validação de devolutiva de livros na biblioteca.

Funciona como **segunda camada de segurança**: após o aluno bipar a tag RFID, a câmera verifica se o livro foi realmente deixado na mesa de devolução.

---

## Como Funciona

1. **Calibração**: Com a mesa **vazia**, chame `POST /calibrate`. Isso salva uma foto da mesa limpa como referência.
2. **Verificação**: Quando o aluno coloca o livro na mesa, chame `POST /verify`. O serviço compara o frame atual com a referência usando **detecção de contornos (OpenCV)**.
3. **Resultado**: Se um objeto retangular grande apareceu na imagem → `book_detected: true`.

---

## Pré-requisitos

- Python 3.10+
- Webcam conectada à máquina

## Instalação

```bash
cd recocnize-livros
pip install -r requirements.txt
```

## Rodar

```bash
python main.py
```

O serviço inicia em `http://localhost:8000`.

**Swagger:** [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| `GET` | `/health` | Health check + status da calibração |
| `POST` | `/calibrate` | Captura mesa vazia como baseline |
| `POST` | `/verify` | Verifica se há livro na mesa |
| `GET` | `/snapshot` | Frame atual da câmera (JPEG, para debug) |

### Exemplo de resposta (`POST /verify`)

```json
{
  "book_detected": true,
  "confidence": 0.87,
  "contours_found": 1,
  "message": "Livro detectado na mesa (1 objeto(s) encontrado(s))."
}
```

---

## Variáveis de Ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `CAMERA_INDEX` | `0` | Índice da webcam |
| `PORT` | `8000` | Porta do servidor |
| `MIN_CONTOUR_AREA` | `5000` | Área mínima (px²) para considerar um objeto |
| `DIFF_THRESHOLD` | `30` | Sensibilidade da detecção (0-255) |
| `API_BASE_URL` | `http://localhost:3000` | URL da API NestJS |

---

## Stack

- **FastAPI** — servidor HTTP
- **OpenCV** — visão computacional
- **NumPy** — processamento de arrays
