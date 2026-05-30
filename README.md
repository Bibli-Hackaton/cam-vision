# 👁️ BIBLI — Visão Computacional (2ª Camada de Segurança)

Este microserviço é o coração da **2ª camada de segurança** da biblioteca inteligente. Ele utiliza inteligência artificial avançada (**YOLOv8**) para garantir fisicamente que o aluno devolveu o livro na mesa após bipar a tag RFID.

Ele foi construído de forma **Stateful e Assíncrona**, o que significa que ele hiberna para não consumir CPU da máquina, ligando a IA e a câmera **apenas** quando a API principal autoriza, aguarda a validação ininterrupta de 10 segundos, e responde via Webhook.

---

## 🛠️ Stack Tecnológica

- **FastAPI** — Motor HTTP assíncrono super veloz.
- **YOLOv8 (Ultralytics)** — Rede neural de detecção de objetos (treinada em nano scale para rodar sem GPU).
- **OpenCV** — Captura e processamento do feed da webcam.
- **Asyncio / Threading** — Máquina de estados executando em loop limpo.

---

## 🚀 Como Iniciar Localmente

### 1. Pré-requisitos
- Python 3.10+
- Webcam conectada (pode ser configurada via `.env`)

### 2. Instalação
Clone o projeto e instale as dependências.
```bash
pip install -r requirements.txt
```

### 3. Rodando o Servidor
Execute com o Uvicorn. O servidor subirá na porta 8000.
```bash
python -m uvicorn main:app --port 8000
```
> **Dica:** Abra `http://localhost:8000` no navegador para ver a interface gráfica do estado da câmera!

---

## 🔌 Guia de Integração para a API (Backend)

O fluxo de comunicação entre a API Principal (ex: NestJS) e este Serviço de Visão acontece em três etapas:

### Passo 1: O Despertar da Câmera
Quando o aluno bipa a tag RFID para devolução, a API Principal **NÃO** deve finalizar o empréstimo ainda. A API deve chamar o nosso serviço para acordar a IA:

`POST /start-vision`
```json
{
  "session_id": "uuid-da-sessao",
  "webhook_url": "http://sua-api-principal:3000/api/sessions/webhook/vision-confirm"
}
```
**O que acontece?** A tela da câmera destrava, o YOLOv8 acorda e fica esperando o livro aparecer na mesa.

### Passo 2: O Cronômetro de Validação (Fluxo Físico)
O aluno coloca o livro na frente da câmera. O YOLOv8 detecta o objeto e inicia uma **contagem ininterrupta de 10 segundos**. 
> 🚨 **Sistema Antifraude:** Se o aluno tirar o livro ou tapar a câmera no segundo 9, o timer zera! O livro precisa ficar **10 segundos parados e visíveis**.

### Passo 3: O Webhook de Sucesso (A Confirmação)
Quando os 10 segundos expiram de forma limpa, este serviço Python faz uma requisição HTTP automaticamente para a URL que a sua API enviou no Passo 1:

`POST {webhook_url}`
```json
{
  "session_id": "uuid-da-sessao",
  "visionVerified": true,
  "timestamp": "2026-05-30T10:00:00Z"
}
```
**O que a API Principal deve fazer?** Ao receber esse POST, a API Principal finalmente altera o status do livro no banco para devolvido e finaliza o empréstimo da sessão. O serviço Python volta a dormir (IDLE).

---

## 🎛️ Referência Rápida de Endpoints

- **`GET /`** → Interface web amigável com a câmera ao vivo (HTML puro).
- **`GET /health`** → Verifica se o servidor está rodando.
- **`GET /video_feed`** → Stream de vídeo MJPEG (usado pelo Front-end).
- **`POST /start-vision`** → Acorda o sistema e passa os dados do Webhook.
- **`POST /config/camera`** → Troca o índice da câmera em tempo de execução (Ex: de `0` para `1`).

## ⚙️ Variáveis de Ambiente (`.env`)

Crie um arquivo `.env` na raiz caso queira mudar os padrões:
```env
PORT=8000
CAMERA_INDEX=1
```
