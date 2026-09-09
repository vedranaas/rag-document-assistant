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

      <div class="upload-section">
        <input type="file" id="pdfInput" accept=".pdf" />
        <button id="uploadButton">Upload PDF</button>
      </div>

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

const input = document.querySelector<HTMLInputElement>('.input-area input')!
const button = document.querySelector<HTMLButtonElement>('.input-area button')!
const chat = document.querySelector<HTMLDivElement>('.chat')!
const pdfInput = document.querySelector<HTMLInputElement>('#pdfInput')!
const uploadButton = document.querySelector<HTMLButtonElement>('#uploadButton')!


uploadButton.addEventListener('click', async () => {
  const file = pdfInput.files?.[0]

  if (!file) {
    alert('Please select a PDF file.')
    return
  }

  const formData = new FormData()
  formData.append('file', file)

  uploadButton.disabled = true
  uploadButton.textContent = 'Uploading...'

  try {
    const response = await fetch('http://127.0.0.1:8000/upload', {
      method: 'POST',
      body: formData
    })

    const data = await response.json()

    if (!response.ok || data.error) {
      alert(data.error || 'Upload failed.')
      return
    }

    history =[]
    chat.innerHTML = ''
    input.value = ''
    alert('${data.filename} uploaded successfully!')

  } catch (error) {
    console.error(error)
    alert('Could not connect to the server.')
  } finally {
    uploadButton.disabled = false
    uploadButton.textContent = 'Upload PDF'
  }
})


let history: { role: string; content: string }[] = [];

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
      question: question,
      history: history
    })
  })

  if (!response.ok) {
    throw new Error('Server error')
  }

  const data = await response.json()

  history.push({
    role: 'user',
    content: question
  })

  history.push({
    role: 'assistant',
    content: data.answer
  })

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