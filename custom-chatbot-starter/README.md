# Custom-Data Chatbot Starter (Python + Node)

This is a **beginner-friendly** Retrieval-Augmented Generation (RAG) starter you can run locally.
It uses:
- **Python FastAPI** + **Sentence-Transformers** + **FAISS** for embeddings & semantic search
- **Node.js Express** as a small API gateway for your frontend (e.g., Angular)

> No external LLMs required. The Python service assembles answers from retrieved snippets.
> You can later plug in OpenAI/Hugging Face to generate more natural answers.

---

## 📦 Project Structure

```
custom-chatbot-starter/
├── python_service/
│   ├── data/
│   │   ├── faq.json
│   │   ├── policies.md
│   │   └── product_guide.md
│   ├── main.py
│   ├── requirements.txt
│   └── run.sh
└── node_backend/
    ├── index.js
    ├── package.json
    └── .env.example
```

---

## 🧭 Architecture Diagram

```
Angular UI (chat box)
        |
        v
Node.js Backend  (routes: /api/ingest, /api/chat)
        |
        v
Python Service (FastAPI)
  - Ingests data/ into chunks
  - Embeds with all-MiniLM-L6-v2
  - Stores in FAISS index
  - On /chat: retrieves top-k chunks and assembles an answer
```

---

## 🚀 Getting Started

### 1) Python service
```bash
cd python_service
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt

# First time (or after changing files in data/):
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
# In another terminal, call ingest to build the index:
curl -X POST http://localhost:8000/ingest
```

### 2) Node backend
```bash
cd ../node_backend
cp .env.example .env
npm install
npm start
# Node will run on http://localhost:3000
```

---

## ✅ Test with curl

**Check health**
```bash
curl http://localhost:3000/api/health
```

**Ingest (build index)**
```bash
curl -X POST http://localhost:3000/api/ingest
```

**Ask a question**
```bash
curl -X POST http://localhost:3000/api/chat   -H "Content-Type: application/json"   -d '{"query":"What is your refund policy?", "k": 3}'
```

Try variations like:
```bash
# semantic match example (no exact words 'refund policy' here)
curl -X POST http://localhost:3000/api/chat   -H "Content-Type: application/json"   -d '{"query":"Can I get my money back?", "k": 3}'
```

---

## 🗂️ Add your own data

- Put `.txt` or `.md` files into `python_service/data/`
- Update `faq.json` with Q/A pairs if you have them
- Then re-run:
```bash
curl -X POST http://localhost:8000/ingest
```

---

## 🧩 Angular example (service)

```ts
// chat.service.ts
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';

@Injectable({ providedIn: 'root' })
export class ChatService {
  private base = 'http://localhost:3000';

  constructor(private http: HttpClient) {}

  ingest() {
    return this.http.post(`${this.base}/api/ingest`, {});
  }

  chat(query: string, k = 3) {
    return this.http.post(`${this.base}/api/chat`, { query, k });
  }
}
```

---

## 🧠 How it works (quick recap)

1. **Ingest**: Python loads files from `data/`, splits them into chunks, embeds with `all-MiniLM-L6-v2`, and builds a FAISS index.
2. **Search**: On `/chat`, the query is embedded and used to retrieve top-k similar chunks.
3. **Answer**: The service returns a stitched answer + the snippets it used.

> Upgrade path: Replace the final answer assembly with an LLM call that takes the retrieved `context` and the `query` to generate a concise answer in your brand tone.
