from fastapi import FastAPI, HTTPException
from sentence_transformers import SentenceTransformer
from pydantic import BaseModel
from PyPDF2 import PdfReader
import faiss
import json
import os
#import openai

#openai.api_key =  

class ChatRequest(BaseModel):
    query: str
    k: int = 3

app = FastAPI()

# Load embedding model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Globals
index = None
docs = []


def load_text(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_pdf(path):
    reader = PdfReader(path)
    return "".join([page.extract_text() for page in reader.pages if page.extract_text()])

def load_docx(file_path: str):
    doc = Document(file_path)
    return "\n".join([para.text for para in doc.paragraphs])

def load_xlsx(file_path: str):
    wb = openpyxl.load_workbook(file_path)
    text = ""
    for sheet in wb.sheetnames:
        ws = wb[sheet]
        for row in ws.iter_rows(values_only=True):
            text += " ".join([str(cell) for cell in row if cell]) + "\n"
    return text

def chunked_text(text, chunk_size=500, overlap=50):
    """Split text into chunks with overlap"""
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end]
        chunks.append(chunk)
        if end == len(text):
            break
        start += chunk_size - overlap
    return chunks


@app.on_event("startup")
def load_data():
    """Automatically ingest multiple files at startup"""
    global index, docs
    try:
        file_paths = ["data/policies.md", "data/faq.json", "data/product_guide.md"]

        all_chunks = []

        for path in file_paths:
            ext = os.path.splitext(path)[1].lower()

            if ext == ".json":
                data = load_json(path)
                for item in data:
                    all_chunks.append(item.get("question", "") + " " + item.get("answer", ""))
            
            elif ext == ".pdf":
                text = load_pdf(path)
                all_chunks.extend(chunked_text(text))
            
            elif ext in [".md", ".txt"]:
                text = load_text(path)
                all_chunks.extend(chunked_text(text))
            elif ext == ".docx":
                text = load_docx(path)
                all_chunks.extend(chunked_text(text))
            elif ext == ".xlsx":
                text = load_xlsx(path)
                all_chunks.extend(chunked_text(text))

        # Store chunks in docs
        docs = all_chunks  

        # Create embeddings
        embeddings = model.encode(docs)
        dim = embeddings.shape[1]

        # Build FAISS index
        index = faiss.IndexFlatL2(dim)
        index.add(embeddings)

        print(f"Index built at startup with {len(docs)} chunks from {len(file_paths)} files")

    except Exception as e:
        print(f"Failed to load dataset at startup: {e}")


@app.post("/chat")
def chat(request: ChatRequest):
    global index, docs
    if index is None:
        raise HTTPException(status_code=500, detail="Index not initialized")

    q_emb = model.encode([request.query])
    D, I = index.search(q_emb, request.k)
    results = [docs[i] for i in I[0]]

    # Prepare answer
    answer = "Based on your question, here are the top results:\n"
    for r in results:
        answer += f"- {r}\n\n"

    return {"query": request.query, "answer": answer.strip(), "results": results}
