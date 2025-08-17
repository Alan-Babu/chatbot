from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os, json, glob, re
import numpy as np

# Embeddings
from sentence_transformers import SentenceTransformer
import faiss

app = FastAPI(title="Custom Data Chatbot - Python Service",
              description="Simple RAG: data ingestion + semantic search + answer assembly",
              version="0.1.0")

DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "data"))
MODEL_NAME = os.environ.get("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

# Globals (simple in-memory store for demo)
embedder = None
index = None
chunk_store: List[Dict[str, Any]] = []  # [{id, source, text}]
dim = None

class ChatRequest(BaseModel):
    query: str
    k: int = 3
    return_snippets: bool = True

def read_text_file(path: str) -> str:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()

def load_corpus(data_dir: str) -> List[Dict[str, Any]]:
    """
    Load .txt/.md as raw text documents, and faq.json as Q/A concatenated text units.
    Returns a list[ {source, text} ].
    """
    corpus: List[Dict[str, Any]] = []
    for path in glob.glob(os.path.join(data_dir, "*.txt")) + glob.glob(os.path.join(data_dir, "*.md")):
        corpus.append({"source": os.path.basename(path), "text": read_text_file(path)})
    # faq.json support
    faq_path = os.path.join(data_dir, "faq.json")
    if os.path.exists(faq_path):
        try:
            faqs = json.loads(read_text_file(faq_path))
            for qa in faqs:
                q, a = qa.get("question","").strip(), qa.get("answer","").strip()
                if q and a:
                    corpus.append({"source": "faq.json", "text": f"Q: {q}\nA: {a}"})
        except Exception as e:
            print("Error reading faq.json:", e)
    return corpus

def simple_chunk(text: str, chunk_size: int = 500, overlap: int = 100) -> List[str]:
    """
    Split text into overlapping chunks by characters, keeping sentence boundaries when possible.
    """
    # Prefer splitting on paragraphs/sentences first
    sentences = re.split(r'(?<=[.!?])\s+|\n{2,}', text)
    chunks = []
    current = ""
    for s in sentences:
        if len(current) + len(s) + 1 <= chunk_size:
            current = (current + " " + s).strip()
        else:
            if current:
                chunks.append(current.strip())
            # start new chunk possibly overlapping last part
            if len(s) > chunk_size:
                # hard wrap very long sentence
                for i in range(0, len(s), chunk_size - overlap):
                    chunks.append(s[i:i+chunk_size])
                current = ""
            else:
                current = s
    if current:
        chunks.append(current.strip())

    # Add overlaps
    with_overlap = []
    for i, c in enumerate(chunks):
        if i == 0:
            with_overlap.append(c)
        else:
            prev = chunks[i-1]
            tail = prev[-overlap:] if len(prev) > overlap else prev
            merged = (tail + " " + c).strip()
            with_overlap.append(merged[:chunk_size])
    return with_overlap

def build_index(data_dir: str):
    global embedder, index, chunk_store, dim
    print(f"Loading embedder: {MODEL_NAME}")
    embedder = SentenceTransformer(MODEL_NAME)

    print("Loading corpus from", data_dir)
    corpus = load_corpus(data_dir)

    chunk_store = []
    for doc_id, doc in enumerate(corpus):
        for chunk in simple_chunk(doc["text"]):
            chunk_store.append({
                "id": len(chunk_store),
                "source": doc["source"],
                "text": chunk
            })

    print(f"Total chunks: {len(chunk_store)}")
    texts = [c["text"] for c in chunk_store]
    embs = embedder.encode(texts, convert_to_numpy=True, show_progress_bar=True)
    dim = embs.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embs.astype(np.float32))
    print("Index built.")

def search(query: str, k: int = 3):
    if index is None or embedder is None:
        raise RuntimeError("Index not built. Call /ingest first.")
    q_emb = embedder.encode([query], convert_to_numpy=True).astype(np.float32)
    D, I = index.search(q_emb, k)
    results = []
    for dist, idx in zip(D[0], I[0]):
        if idx == -1: 
            continue
        item = chunk_store[idx]
        # Convert L2 distance to a simple similarity score for display
        sim = float(1.0 / (1.0 + dist))
        results.append({
            "score": sim,
            "text": item["text"],
            "source": item["source"]
        })
    return results

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/ingest")
def ingest():
    try:
        build_index(DATA_DIR)
        return {"status": "indexed", "chunks": len(chunk_store), "data_dir": DATA_DIR}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
def chat(req: ChatRequest):
    if index is None:
        raise HTTPException(status_code=400, detail="Index not ready. Call /ingest first.")
    matches = search(req.query, k=req.k)
    if not matches:
        return {"answer": "Sorry, I couldn't find anything relevant.", "matches": []}

    # Simple answer assembly (no LLM): stitch top snippets
    context = "\n\n".join([m["text"] for m in matches])
    answer = f"Based on our knowledge base:\n\n{context}"
    resp = {"answer": answer}
    if req.return_snippets:
        resp["matches"] = matches
    return resp

# Optional: You could integrate an LLM (OpenAI/HF) here to summarize `context` into a nicer answer.
# We skip it in this starter project to keep dependencies light and avoid API keys.
# If you want this, add an endpoint /chat_llm that calls your provider using the retrieved context.
