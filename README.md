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

> ⚠️ **Atenção ao payload do Webhook:** o serviço envia os campos **`sessionId`** (camelCase) e **`visionVerified: true`**. Ele **não** envia `timestamp`. Configure o handler da API Principal para ler exatamente esses nomes.

---

## 🖥️ Guia de Integração para o Front-end

O front-end **não dispara** a verificação (isso é responsabilidade da API Principal / leitura RFID). O papel do front-end é **exibir o feed da câmera ao vivo** e **refletir o estado** da máquina de visão em tempo real. A comunicação é feita por dois recursos simples: um `<img>` de vídeo e um *polling* no `/health`.

> ✅ **CORS liberado:** o serviço responde com `Access-Control-Allow-Origin: *`, então pode ser consumido de qualquer origem (React, Vue, Angular, HTML puro) sem proxy.

### 1. Exibindo o vídeo ao vivo (MJPEG)
O endpoint `/video_feed` devolve um stream **MJPEG** (`multipart/x-mixed-replace`). A forma mais simples de exibi-lo é apontar uma tag `<img>` diretamente para ele — o navegador renderiza o stream nativamente, sem `<video>` nem WebRTC:

```html
<img id="videoFeed" src="http://localhost:8000/video_feed" alt="Câmera ao vivo" />
```

> 💡 Para **forçar a recarga** do stream (ex.: após trocar a câmera), basta acrescentar um parâmetro único na URL:
> `videoFeed.src = "http://localhost:8000/video_feed?t=" + Date.now();`

### 2. Lendo o estado em tempo real (Polling do `/health`)
O front-end deve consultar o `GET /health` em intervalos curtos (recomendado: **300 ms**) para saber o que desenhar na tela. A resposta é:

```json
{
  "status": "ok",
  "app_state": "VALIDATING",
  "time_left": 7,
  "camera_index": 0
}
```

O campo `app_state` controla **toda** a interface. São 4 estados possíveis:

| `app_state`  | Significado                                  | O que o front-end deve mostrar                                  |
|--------------|----------------------------------------------|----------------------------------------------------------------|
| `IDLE`       | IA dormindo, aguardando a API liberar.       | Tela de "Sistema Bloqueado" / Standby. Esconder o vídeo.       |
| `AWAITING`   | Câmera ligada, procurando o livro na mesa.   | Mostrar o vídeo + status "Procurando objeto...".               |
| `VALIDATING` | Livro detectado, contando 10s ininterruptos. | Mostrar o vídeo + overlay do cronômetro usando `time_left`.    |
| `DONE`       | 10s concluídos, Webhook já disparado.        | Mensagem de "Devolução Concluída!". O sistema volta a `IDLE`.  |

> 🚨 **Antifraude na tela:** enquanto o estado for `VALIDATING`, atualize o cronômetro com `time_left`. Se o aluno remover o livro, o estado volta para `AWAITING` e o `time_left` reseta para `10` automaticamente — o front-end só precisa refletir o que vier no `/health`.

### 3. Exemplo de consumo (JavaScript puro)
```javascript
const API = "http://localhost:8000";

async function pollState() {
  try {
    const data = await (await fetch(`${API}/health`)).json();

    switch (data.app_state) {
      case "IDLE":
        // mostrar tela de standby, esconder vídeo
        break;
      case "AWAITING":
        // mostrar vídeo, status "Procurando objeto..."
        break;
      case "VALIDATING":
        // mostrar overlay com o cronômetro
        document.getElementById("timer").innerText = data.time_left;
        break;
      case "DONE":
        // mostrar "Devolução Concluída!"
        break;
    }
  } catch (e) {
    console.error("Serviço de visão offline?", e);
  }
}

setInterval(pollState, 300); // polling a cada 300ms
```

### 4. Exemplo de consumo (React)
```jsx
import { useEffect, useState } from "react";

const API = "http://localhost:8000";

export function VisionPanel() {
  const [state, setState] = useState({ app_state: "IDLE", time_left: 10 });

  useEffect(() => {
    const id = setInterval(async () => {
      try {
        const res = await fetch(`${API}/health`);
        setState(await res.json());
      } catch (_) { /* serviço offline */ }
    }, 300);
    return () => clearInterval(id);
  }, []);

  const { app_state, time_left } = state;

  return (
    <div>
      {app_state === "IDLE" ? (
        <p>🔒 Sistema bloqueado — aguardando liberação da API.</p>
      ) : (
        <img src={`${API}/video_feed`} alt="Câmera ao vivo" />
      )}

      {app_state === "VALIDATING" && <div className="timer">{time_left}</div>}
      {app_state === "DONE" && <p>✅ Devolução concluída!</p>}
    </div>
  );
}
```

### 5. (Opcional) Trocar a câmera pela interface
Se a UI oferecer um seletor de câmeras, basta um `POST /config/camera`:

```javascript
await fetch("http://localhost:8000/config/camera", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ camera_index: 1 }),
});
// depois, recarregue o stream:
videoFeed.src = "http://localhost:8000/video_feed?t=" + Date.now();
```

---

## 🎛️ Referência Rápida de Endpoints

| Método & Rota          | Quem usa        | Descrição                                                              |
|------------------------|-----------------|------------------------------------------------------------------------|
| `GET /`                | Navegador       | Interface web de demonstração com a câmera ao vivo (HTML puro).        |
| `GET /health`          | **Front-end**   | Retorna `app_state`, `time_left` e `camera_index` (base do polling).   |
| `GET /video_feed`      | **Front-end**   | Stream de vídeo MJPEG para exibir em uma tag `<img>`.                  |
| `POST /config/camera`  | **Front-end**   | Troca o índice da câmera em tempo de execução (ex.: de `0` para `1`).  |
| `POST /start-vision`   | API Principal   | Acorda o sistema e passa `session_id` + `webhook_url`.                 |
| `POST /reset-vision`   | API Principal   | Força o retorno ao estado `IDLE` (Standby), cancelando a validação.   |

## ⚙️ Variáveis de Ambiente (`.env`)

Crie um arquivo `.env` na raiz caso queira mudar os padrões:
```env
PORT=8000
CAMERA_INDEX=1
```
