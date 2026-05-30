# 🚀 Fluxo de Devolução com Visão Computacional (Manual para o Front-end)

Com a chegada da **2ª Camada de Segurança** (Validação Visual por IA), o processo de devolver um livro deixou de ser uma requisição instantânea e síncrona. Agora temos um fluxo **assíncrono** de segurança.

Este guia serve para alinhar como a equipe de Front-end deve orquestrar as chamadas e a interface visual durante uma devolução.

---

## 📌 1. O que mudou? (Resumo da Ópera)
Antigamente: O Front-end chamava o `POST /return-book`, o backend processava tudo e respondia `"Sucesso, livro devolvido"`.
**Agora:** O Front-end chama o `POST /return-book`, o backend apenas avisa a câmera para ligar e responde `"Aguardando Câmera"`. A devolução *real* só acontece segundos depois, de forma invisível, quando a Câmera enviar um *Webhook* de aprovação para o backend.

---

## 🛠️ 2. Passo a Passo do Novo Fluxo (Para o Front-end)

### Passo 1: O Gatilho (Passar o livro no leitor RFID)
O usuário passa o livro no leitor e o Front-end dispara a mesma requisição de sempre:
```http
POST /api/sessions/{id_da_sessao}/return-book
Body: { "rfid_tag": "RFID-12345" }
```
Se a requisição retornar **200/201 OK**, isso **não significa** que o livro foi devolvido ainda! Significa apenas que o backend acordou a câmera de segurança.

### Passo 2: Mudança de Tela (Aguardando Câmera)
Imediatamente após receber o `200 OK`, o Front-end deve:
1. Esconder o botão de "Devolver".
2. Mostrar um Modal ou Tela de Carregamento bonita dizendo: 
   > 📸 *"Por favor, posicione o livro na frente da câmera de segurança."*
3. Começar a fazer um **Polling** (perguntar para a API a cada X segundos se já acabou).

### Passo 3: O Polling Mágico (Como saber se a IA já validou?)
Como a validação visual leva cerca de 10 segundos ininterruptos, o Front-end não ficará travado esperando o HTTP. Ele deve fazer pequenas requisições a cada **2 segundos** na rota da sessão atual para verificar se o livro foi desvinculado.

**Rota a ser chamada repetidamente:**
```http
GET /api/sessions/current
```

**O que o Front-end deve verificar?**
O Front deve olhar a chave `linkedBookId` ou `linkedBook` dentro da resposta da sessão.
- Se `linkedBook` **ainda existir** = A câmera ainda está contando os 10s. O Front continua esperando e mantendo a tela de *"Posicione o livro"*.
- Se `linkedBook` **retornar `null`** = Bingo! 🎉 O Webhook da IA já chegou no backend, o livro foi guardado e a devolução acabou! O Front pode cancelar o Polling.

### Passo 4: O Sucesso Visual
Assim que o Polling detectar que o `linkedBook` é nulo, o Front-end deve:
1. Matar a função de Polling (clearInterval).
2. Tocar um som agradável (opcional).
3. Mostrar a tela verde de sucesso: *"Devolução Concluída! O livro já está disponível para o próximo leitor."*

---

## 💻 3. Exemplo de Código (React / Fetch)

```javascript
// 1. O usuário bipou o livro
async function handleReturnBook(rfidTag) {
  try {
    // Dispara a devolução (Acorda a Câmera)
    await api.post(`/api/sessions/${sessionId}/return-book`, { rfid_tag: rfidTag });
    
    // 2. Mostra tela de carregamento da câmera
    setUiState('AWAITING_CAMERA'); 
    
    // 3. Inicia o Polling
    const pollingId = setInterval(async () => {
      const response = await api.get('/api/sessions/current');
      const session = response.data;
      
      // 4. Checa se o livro foi desvinculado pelo Webhook
      if (session.linkedBook === null || session.linkedBookId === null) {
        clearInterval(pollingId); // Para de perguntar
        setUiState('RETURN_SUCCESS'); // Mostra o sucesso pro usuário!
      }
    }, 2000); // Pergunta a cada 2 segundos
    
  } catch (error) {
    console.error("Erro ao devolver:", error);
    setUiState('ERROR');
  }
}
```

---
> **Dica de UX:** Coloque uma animação circular simulando a câmera analisando o livro para preencher o vazio durante os 10 segundos de espera na tela do usuário!
