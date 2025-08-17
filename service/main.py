from fastapi import FastAPI, HTTPException
from sentence_transformers import SentenceTransformer
from pydantic import BaseModel
import faiss, os
from dotenv import load_dotenv

# File readers
from PyPDF2 import PdfReader
from docx import Document
import openpyxl
import logging as log

# OpenAI client
from openai import OpenAI

# -------------------------
# Config
# -------------------------
load_dotenv()  # Set to False if you don't want to load .env
app = FastAPI()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set. Please set it in your .env file.")
client = OpenAI(api_key=api_key)  # <- set your API key in env
embedder = SentenceTransformer("all-MiniLM-L6-v2")

index = None
docs = []
doc_sources = []

class ChatRequest(BaseModel):
    query: str
    k: int = 3


# -------------------------
# File loaders
# -------------------------
def load_txt(file_path): 
    with open(file_path, "r", encoding="utf-8") as f: 
        return f.read()

def load_md(file_path): return load_txt(file_path)

def load_pdf(file_path):
    reader = PdfReader(file_path)
    return "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])

def load_docx(file_path):
    doc = Document(file_path)
    return "\n".join([para.text for para in doc.paragraphs])

def load_xlsx(file_path):
    wb = openpyxl.load_workbook(file_path)
    text = ""
    for sheet in wb.sheetnames:
        ws = wb[sheet]
        for row in ws.iter_rows(values_only=True):
            text += " ".join([str(cell) for cell in row if cell]) + "\n"
    return text


# -------------------------
# Chunking
# -------------------------
def chunk_text(text, chunk_size=500, overlap=50):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


# -------------------------
# Startup: Scan folder + index
# -------------------------
@app.on_event("startup")
def load_data():
    global index, docs, doc_sources

    file_dir = "data/"
    if not os.path.exists(file_dir):
        print("⚠️ Data folder not found.")
        return

    for file in os.listdir(file_dir):
        file_path = os.path.join(file_dir, file)
        ext = os.path.splitext(file)[1].lower()

        try:
            if ext == ".txt": text = load_txt(file_path)
            elif ext == ".md": text = load_md(file_path)
            elif ext == ".pdf": text = load_pdf(file_path)
            elif ext == ".docx": text = load_docx(file_path)
            elif ext == ".xlsx": text = load_xlsx(file_path)
            else:
                print(f"Skipping unsupported file: {file}")
                continue

            chunks = chunk_text(text)
            docs.extend(chunks)
            doc_sources.extend([file] * len(chunks))
            print(f"✅ Loaded {file} with {len(chunks)} chunks")

        except Exception as e:
            print(f"❌ Failed to load {file}: {e}")

    if not docs:
        print("⚠️ No documents loaded.")
        return

    # Build FAISS index
    embeddings = embedder.encode(docs)
    dim = embeddings.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(embeddings)

    print(f"📚 Index built with {len(docs)} chunks from {len(set(doc_sources))} files")


# -------------------------
# Chat Endpoint (RAG with GPT-4o)
# -------------------------
@app.post("/chat")
def chat(request: ChatRequest):
    global index, docs, doc_sources
    if index is None:
        raise HTTPException(status_code=500, detail="Index not initialized")

    q_emb = embedder.encode([request.query])
    D, I = index.search(q_emb, request.k)
    retrieved_chunks = [(docs[i], doc_sources[i]) for i in I[0]]

    context = "\n".join([f"From {src}:\n{chunk}" for chunk, src in retrieved_chunks])

    prompt = f"""You are a helpful assistant.
Use the following context to answer the question.

Context:
{context}

Question: {request.query}
Answer:"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",   # ✅ You can use "gpt-4o" too if available in your plan
        messages=[
            {"role": "system", "content": "You are a knowledgeable assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=300
    )

    answer = response.choices[0].message.content

    return {
        "query": request.query,
        "context": [f"{src}: {chunk[:200]}..." for chunk, src in retrieved_chunks],
        "answer": answer
    }
