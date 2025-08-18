from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from sentence_transformers import SentenceTransformer
from pydantic import BaseModel
import faiss, os, re, logging
from dotenv import load_dotenv
from typing import Generator

# File readers
from PyPDF2 import PdfReader
from docx import Document
import openpyxl
from sklearn.preprocessing import normalize
from sklearn.feature_extraction.text import TfidfVectorizer

import ollama

# -------------------------
# Config
# -------------------------
load_dotenv()
app = FastAPI()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

embedder = SentenceTransformer("all-MiniLM-L6-v2")

# Use app.state instead of globals
app.state.index = None
app.state.docs = []
app.state.doc_sources = []

class ChatRequest(BaseModel):
    query: str
    k: int = 3


# -------------------------
# File loaders
# -------------------------
def load_txt(file_path): 
    with open(file_path, "r", encoding="utf-8") as f: 
        return f.read()

def load_md(file_path): 
    return load_txt(file_path)

def load_pdf(file_path):
    reader = PdfReader(file_path)
    texts = [page.extract_text() for page in reader.pages if page.extract_text()]
    return "\n".join(texts)

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
    """Split text into chunks with overlap."""
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
    file_dir = os.getenv("DATA_DIR", "data/")

    if not os.path.exists(file_dir):
        logger.warning("⚠️ Data folder not found.")
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
                logger.info(f"Skipping unsupported file: {file}")
                continue

            chunks = chunk_text(text)
            app.state.docs.extend(chunks)
            app.state.doc_sources.extend([file] * len(chunks))
            logger.info(f"✅ Loaded {file} with {len(chunks)} chunks")

        except Exception as e:
            logger.error(f"❌ Failed to load {file}: {e}")

    if not app.state.docs:
        logger.warning("⚠️ No documents loaded.")
        return

    # Build FAISS index (cosine similarity)
    embeddings = embedder.encode(app.state.docs)
    embeddings = normalize(embeddings)  # normalize for cosine similarity
    dim = embeddings.shape[1]
    app.state.index = faiss.IndexFlatIP(dim)
    app.state.index.add(embeddings)

    logger.info(
        f"📚 Index built with {len(app.state.docs)} chunks from {len(set(app.state.doc_sources))} files"
    )


# -------------------------
# Chat Endpoint (RAG with ollama)
# -------------------------
@app.post("/chat")
def chat(request: ChatRequest):
    if app.state.index is None:
        raise HTTPException(status_code=500, detail="Index not initialized")

    q_emb = embedder.encode([request.query])
    q_emb = normalize(q_emb)  # normalize query too

    D, I = app.state.index.search(q_emb, request.k)
    retrieved_chunks = [(app.state.docs[i], app.state.doc_sources[i]) for i in I[0]]

    context = "\n".join([f"From {src}:\n{chunk}" for chunk, src in retrieved_chunks])

    prompt = f"""You are a helpful assistant.
Use the following context to answer the question.

Context:
{context}

Question: {request.query}
Answer:"""

    def generate() -> Generator[str, None, None]:
        try:
            for chunk in ollama.chat(
                model="phi3",
                messages=[
                    {"role": "system", "content": "You are a knowledgeable assistant."},
                    {"role": "user", "content": prompt}
                ],
                stream=True
            ):
                if chunk.get("message") and "content" in chunk["message"]:
                    yield chunk["message"]["content"]
        except Exception as e:
            yield f"Error generating response: {str(e)}"

    return StreamingResponse(generate(), media_type="text/plain")


# -------------------------
# Menu Endpoint
# -------------------------
@app.get("/menu", response_model=list[str])
def get_menu():
    if not app.state.doc_sources:
        raise HTTPException(status_code=404, detail="No documents loaded")

    menu_items = []
    for doc in app.state.docs:
        headings = re.findall(r"^(#+\s.*)", doc, flags=re.MULTILINE)
        if headings:
            menu_items.extend([h.strip("# ").strip() for h in headings])

    if not menu_items:
        vectorizer = TfidfVectorizer(stop_words="english", max_features=10)
        X = vectorizer.fit_transform(app.state.docs)
        keywords = vectorizer.get_feature_names_out()
        menu_items.extend(keywords.tolist())

    # Deduplicate and return top 15
    unique_items = list(dict.fromkeys(menu_items))[:15]
    return unique_items


# -------------------------
# Healthcheck Endpoint
# -------------------------
@app.get("/health")
def health():
    return {
        "status": "ok",
        "docs_loaded": len(app.state.docs),
        "files_loaded": len(set(app.state.doc_sources)),
    }
