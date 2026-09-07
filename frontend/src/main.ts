import './style.css'
const app = document.querySelector<HTMLDivElement>('#app')!

app.innerHTML = `
    <div class="app">

      <header class="header">
        <div class="logo">🤖</div>

        <div>
          <h1>RAG Document Assistant</h1>
          <p>Ask questions about your document</p>
        </div>
      </header>

    <div class="chat">
      

    
    </div>

    <div class="input-area">
      <input
        type="text"
        placeholder="Ask a question..."
      />

      <button>Send</button>
    </div>
  </div>
`

const input = document.querySelector<HTMLInputElement>('input')!
const button = document.querySelector<HTMLButtonElement>('button')!
const chat = document.querySelector<HTMLDivElement>('.chat')!

async function askQuestion() {
  const question = input.value.trim()

  if (!question) return

  button.disabled = true

  chat.innerHTML += `
    <div class="message user">
      <div class="message-label">You</div>
      <div>${question}</div>
    </div>
  `

  input.value = ''

  chat.innerHTML += `
    <div class="message assistant loading">
      <div class="message-label">Assistant</div>
      <div>Thinking...</div>
    </div>
  `
try {
  const response = await fetch('http://127.0.0.1:8000/ask', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      question: question
    })
  })

  if (!response.ok) {
    throw new Error('Server error')
  }

  const data = await response.json()

  chat.querySelector('.loading')?.remove()

let sourcesHtml = ''

if (data.sources && data.sources.length > 0) {
  sourcesHtml = `
    <div class="sources">
      <div class="sources-title">Sources</div>

      ${data.sources.map((source: any) => `
        <div class="source">
          📄 Page ${source.page + 1}
        </div>
      `).join('')}
    </div>
  `
}

chat.innerHTML += `
  <div class="message assistant">
    <div class="message-label">Assistant</div>

    <div class="answer">
      ${data.answer}
    </div>

    ${sourcesHtml}
  </div>
`

} catch (error) {
  chat.querySelector('.loading')?.remove()

  chat.innerHTML += `
    <div class="message assistant">
      Sorry, something went wrong. Please try again.
    </div>
  `
} finally {
  button.disabled = false
}
}

button.addEventListener('click', askQuestion)

input.addEventListener('keydown', (event) => {
  if (event.key === 'Enter') {
    askQuestion()
  }
})