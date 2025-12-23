
from __future__ import annotations

import nltk
import time
import json
import requests
import os
import glob
import re
import concurrent.futures
from config import get_db as _get_central_db
import datetime as _dt
from typing import Optional, List, Dict, Any
from collections import defaultdict

import firebase_admin
from firebase_admin import firestore

from nltk.stem import PorterStemmer


try:
    from docx import Document
except ImportError:
    Document = None
    print("Warning: python-docx not installed. Run: pip install python-docx")

# ==========================================
# SETUP
# ==========================================

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    print("Downloading NLTK stopwords...")
    nltk.download('stopwords')
    nltk.download('punkt')

SENSORS_COL = "sensors"
ARTICLES_COL = "articles"

def get_db():
    return _get_central_db()

def _server_ts():
    try:
        return firestore.SERVER_TIMESTAMP
    except Exception:
        return _dt.datetime.utcnow().isoformat()

def _doc_to_dict(doc):
    d = doc.to_dict() if hasattr(doc, "to_dict") else dict(doc)
    d["id"] = doc.id if hasattr(doc, "id") else d.get("id")
    for k in ("created_at", "updated_at", "timestamp"):
        v = d.get(k)
        if hasattr(v, "isoformat"):
            d[k] = v.isoformat()
    return d

# ==========================================
# SENSORS (IoT)
# ==========================================

def add_sensor_reading(plant_id, temp=None, humidity=None, soil=None, light=None, extra=None):
    db = get_db()
    payload = {
        "plant_id": plant_id,
        "timestamp": _server_ts(),
        "created_at": _server_ts(),
    }
    if temp is not None:     payload["temp"] = float(temp)
    if humidity is not None: payload["humidity"] = float(humidity)
    if soil is not None:     payload["soil"] = float(soil)
    if light is not None:    payload["light"] = float(light)
    if extra:                payload.update(extra)

    ref = db.collection(SENSORS_COL).add(payload)[1]
    return ref.id

def get_sensor_history(plant_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    db = get_db()
    q = (db.collection(SENSORS_COL)
           .where("plant_id", "==", plant_id)
           .order_by("timestamp", direction=firestore.Query.DESCENDING))
    if limit:
        q = q.limit(int(limit))
    return [_doc_to_dict(doc) for doc in q.stream()]

def get_latest_reading(plant_id: str) -> Optional[Dict[str, Any]]:
    rows = get_sensor_history(plant_id, limit=1)
    return rows[0] if rows else None

def get_all_readings(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    db = get_db()
    q = db.collection(SENSORS_COL).order_by("timestamp", direction=firestore.Query.DESCENDING)
    if limit:
        q = q.limit(int(limit))
    return [_doc_to_dict(doc) for doc in q.stream()]

# ==========================================
# EXTERNAL IOT SERVER INTEGRATION
# ==========================================

IOT_SERVER_URL = "https://server-cloud-v645.onrender.com/history"

def sync_iot_data(plant_id: str) -> bool:
    print("--- Connecting to IoT Server... (Parallel Fetch) ---")

    feeds = ["temperature", "humidity", "soil"]
    sensor_data: Dict[str, float] = {}

    def _fetch(feed):
        try:
            # Short timeout to ensure speed
            resp = requests.get(IOT_SERVER_URL, params={"feed": feed, "limit": 1}, timeout=5)
            if resp.status_code == 200:
                d = resp.json()
                if "data" in d and len(d["data"]) > 0:
                    val = float(d["data"][0]["value"])
                    print(f"[IOT] Fetched {feed}: {val}")
                    return feed, val
        except Exception as e:
            print(f"[IOT] Err {feed}: {e}")
        return feed, None

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            # Start all requests
            futures = [executor.submit(_fetch, f) for f in feeds]
            
            # Collect results
            for future in concurrent.futures.as_completed(futures):
                f, val = future.result()
                if val is not None:
                    sensor_data[f] = val

        if sensor_data:
            final_temp = sensor_data.get("temperature")
            final_hum = sensor_data.get("humidity")
            final_soil = sensor_data.get("soil")

            new_id = add_sensor_reading(
                plant_id,
                temp=final_temp,
                humidity=final_hum,
                soil=final_soil
            )
            print(f"[IOT] Data synced to Firestore successfully. ID: {new_id}")
            return True

        return False

    except Exception as e:
        print(f"[IOT] Connection failed: {e}")
        return False

# ==========================================
# ARTICLES (TXT/DOCX) + CRUD
# ==========================================


def extract_article_metadata(title: str, content: str, url: str | None = None) -> dict:
    """
    Best-effort metadata extraction (simple, lecturer-friendly).
    Returns keys: authors, journal, year, doi
    """
    text = (content or "")
    t = (title or "")

    # DOI (common pattern)
    doi_match = re.search(r"\b10\.\d{4,9}/[-._;()/:A-Za-z0-9]+\b", text)
    doi = doi_match.group(0) if doi_match else None

    # Year (pick first reasonable year)
    year_match = re.search(r"\b(19\d{2}|20\d{2})\b", text)
    year = year_match.group(0) if year_match else None

    # Journal (very heuristic)
    journal = None
    j_match = re.search(r"(?:Journal|Proceedings|Conference)\s*[:\-]\s*([^\n\r]{3,120})", text, re.IGNORECASE)
    if j_match:
        journal = j_match.group(1).strip()

    # Authors (heuristic)
    authors = None
    a_match = re.search(r"(?:Authors?)\s*[:\-]\s*([^\n\r]{3,180})", text, re.IGNORECASE)
    if a_match:
        authors = a_match.group(1).strip()

    # Fallback: if title looks like "X et al 2022" etc.
    if not authors:
        etal = re.search(r"([A-Z][A-Za-z\-]+)\s+et\s+al\.?", t)
        if etal:
            authors = f"{etal.group(1)} et al."

    meta = {
        "authors": authors,
        "journal": journal,
        "year": year,
        "doi": doi,
    }

    # optional: store url too (not required)
    if url:
        meta["url"] = url

    # clean Nones
    return {k: v for k, v in meta.items() if v}



def read_text_from_file(file_path):
    """
    פונקציה חכמה שקוראת טקסט מקובץ לפי הסוג שלו (docx או txt).
    """
    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".docx":
        try:
            doc = Document(file_path)
            full_text = []
            for para in doc.paragraphs:
                full_text.append(para.text)
            return "\n".join(full_text)
        except Exception as e:
            print(f"Error reading DOCX {file_path}: {e}")
            return ""

    else: # ברירת מחדל: קובץ טקסט רגיל
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception as e:
            print(f"Error reading TXT {file_path}: {e}")
            return ""

def add_article(title: str, content: str, url: Optional[str] = None, metadata: Optional[dict] = None):
    db = get_db()

    existing = db.collection(ARTICLES_COL).where("title", "==", title).limit(1).stream()
    if list(existing):
        print(f"Skipping duplicate: {title}")
        return None

    
    auto_meta = extract_article_metadata(title, content, url)
    final_meta = {**auto_meta, **(metadata or {})}

    doc = {
        "title": title,
        "content": content,
        "url": url,
        "metadata": final_meta,
        "created_at": _server_ts(),
        "updated_at": _server_ts(),
    }

    ref = db.collection(ARTICLES_COL).add(doc)[1]
    return ref.id


def get_all_articles(limit: Optional[int] = None):
    db = get_db()
    q = db.collection(ARTICLES_COL).order_by("created_at", direction=firestore.Query.DESCENDING)
    if limit is not None:
        q = q.limit(int(limit))
    return [_doc_to_dict(doc) for doc in q.stream()]

def get_article_by_id(article_id: str):
    db = get_db()
    doc = db.collection(ARTICLES_COL).document(article_id).get()
    return _doc_to_dict(doc) if doc.exists else None

def add_article_from_txt(file_path: str, title: str, url: Optional[str] = None, metadata: Optional[dict] = None):
    text = read_text_from_file(file_path)
    if not text.strip():
        print(f"Skipped empty/unreadable file: {file_path}")
        return None
    return add_article(title=title, content=text, url=url, metadata=metadata)




#=============================================
#INDEX (term + DocIDs)
#=============================================




stemmer = PorterStemmer()

INDEX_COL = "index"

STOPWORDS = {
    "a","an","the","and","or","in","on","at","of","for","to",
    "is","are","as","by","with","from","this","that","it","be","was","were",
    "which","how","what","where","when","who","can","will","not","but",
    "has","have","had","do","does","did"
}

def _tokenize(text: str):
    if not text:
        return []
    return re.findall(r"\w+", text.lower())

def _normalize(tokens, use_stem: bool = True):
    out = []
    for t in tokens:
        if len(t) < 3:
            continue
        if t in STOPWORDS:
            continue
        if t.isdigit():
            continue
        if use_stem:
            try:
                t = stemmer.stem(t)
            except Exception:
                pass
        out.append(t)
    return out

def build_index(max_docs: int = 5, use_stem: bool = True, include_title: bool = True):
    db = get_db()
    
    # [OPTIMIZATION] Skip if index already exists
    try:
        # Check if we have at least one document in the 'index' collection
        if next(db.collection(INDEX_COL).limit(1).stream(), None):
            print(f"[OPTIMIZATION] Index '{INDEX_COL}' already exists. Skipping rebuild.")
            return {}
    except Exception:
        pass # If check fails, safe to proceed with build

    articles = get_all_articles(limit=max_docs)
    if not articles:
        print("No articles found. Seed articles first.")
        return {}

    docnum_to_articleid: Dict[str, str] = {}
    numbered = []
    for i, a in enumerate(articles, start=1):
        doc_num = f"doc_{i}"
        docnum_to_articleid[doc_num] = a["id"]
        numbered.append((doc_num, a))

    term_to_docids = defaultdict(set)

    for doc_num, a in numbered:
        title = a.get("title", "") if include_title else ""
        content = a.get("content", "")
        text = (title + " " + content).strip()

        tokens = _tokenize(text)
        terms = _normalize(tokens, use_stem=use_stem)

        for term in set(terms):
            term_to_docids[term].add(doc_num)

    col = db.collection(INDEX_COL)

    # clear previous index
    batch = db.batch()
    ops = 0
    for d in col.stream():
        batch.delete(d.reference)
        ops += 1
        if ops >= 400:
            batch.commit()
            batch = db.batch()
            ops = 0
    if ops:
        batch.commit()

    # write required schema
    batch = db.batch()
    ops = 0
    for term, docids_set in term_to_docids.items():
        ref = col.document(term)
        batch.set(ref, {
            "term": term,
            "DocIDs": sorted(docids_set),
        })
        ops += 1
        if ops >= 400:
            batch.commit()
            batch = db.batch()
            ops = 0
    if ops:
        batch.commit()

    print(f"Built index in '{INDEX_COL}' with {len(term_to_docids)} terms.")
    print("DocIDs mapping:")
    for k, v in docnum_to_articleid.items():
        print(f"  {k} -> article_id={v}")

    return docnum_to_articleid





#============================
# RAG
#============================

import numpy as np

# Dependency checks (like lecturer)
try:
    import chromadb
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class SimpleVectorStore:
    """Fallback vector store when ChromaDB is not available."""
    def __init__(self):
        self.documents = []
        self.embeddings = []
        self.metadatas = []
        self.ids = []

    def add(self, embeddings, documents, metadatas, ids):
        self.embeddings.extend(list(embeddings))
        self.documents.extend(list(documents))
        self.metadatas.extend(list(metadatas))
        self.ids.extend(list(ids))

    def query(self, query_embeddings, n_results=5):
        if not self.embeddings:
            return {'ids':[[]], 'documents':[[]], 'metadatas':[[]], 'distances':[[]]}

        X = np.array(self.embeddings, dtype=np.float32)
        q = np.array(query_embeddings, dtype=np.float32)

        # cosine similarity
        q_norm = np.linalg.norm(q, axis=1, keepdims=True) + 1e-12
        X_norm = np.linalg.norm(X, axis=1, keepdims=True) + 1e-12
        qn = q / q_norm
        Xn = X / X_norm
        sims = (Xn @ qn.T).reshape(-1)

        top = np.argsort(sims)[::-1][:n_results]
        distances = [float(1 - sims[i]) for i in top]  # 1 - similarity

        return {
            "ids": [[self.ids[i] for i in top]],
            "documents": [[self.documents[i] for i in top]],
            "metadatas": [[self.metadatas[i] for i in top]],
            "distances": [distances],
        }

    def count(self):
        return len(self.documents)


class PlantRAG:
    """
    Lecturer-style RAG:
    - Embeddings: SentenceTransformer OR TF-IDF fallback
    - Vector store: ChromaDB OR SimpleVectorStore fallback
    - Generation: OpenAI OR Template fallback
    """

    def __init__(self, openai_api_key: str | None = None):
        # Embeddings setup
        self.use_transformers = False
        self.use_tfidf = False
        self.fitted = False

        if TRANSFORMERS_AVAILABLE:
            try:
                self.embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
                self.use_transformers = True
            except Exception:
                self.use_transformers = False

        if (not self.use_transformers):
            if not SKLEARN_AVAILABLE:
                raise RuntimeError("No SentenceTransformers and no sklearn TF-IDF available. Install sentence-transformers or scikit-learn.")
            self.tfidf = TfidfVectorizer(max_features=2000, stop_words="english")
            self.use_tfidf = True

        # Vector store setup
        self.use_chromadb = False
        if CHROMADB_AVAILABLE:
            try:
                client = chromadb.Client()
                try:
                    self.collection = client.get_collection("plant_articles")
                except Exception:
                    self.collection = client.create_collection("plant_articles")
                self.use_chromadb = True
            except Exception:
                self.collection = SimpleVectorStore()
                self.use_chromadb = False
        else:
            self.collection = SimpleVectorStore()
            self.use_chromadb = False

        # OpenAI setup (optional)
        self.use_openai = False
        if openai_api_key and OPENAI_AVAILABLE:
            openai.api_key = openai_api_key
            self.use_openai = True

        self.loaded = False


    def preprocess_text(self, text: str) -> str:
        if not text:
            return ""
        text = re.sub(r"\s+", " ", text)
        return text.strip()


    def generate_embeddings(self, texts: list[str]):
        if self.use_transformers:
            return self.embedding_model.encode(texts, show_progress_bar=False)

        # TF-IDF fallback
        if not self.fitted:
            self.tfidf.fit(texts)
            self.fitted = True
        return self.tfidf.transform(texts).toarray()


    def load_from_firestore(self, limit: int | None = None):
        if self.loaded:
            return 0

        papers = get_all_articles(limit=limit)
        documents, metadatas, ids = [], [], []

        for i, a in enumerate(papers):
            title = a.get("title", "Unknown")
            content = a.get("content", "")
            text = self.preprocess_text(f"{title}\n{content}")
            if len(text) < 30:
                continue

            documents.append(text)
            metadatas.append({
            "title": title,
            "article_id": a.get("id"),
            "url": a.get("url"),
            "metadata": a.get("metadata") or {},
            })

            ids.append(f"article_{i}")

        if not documents:
            raise RuntimeError("No articles with content found in Firestore.")

        emb = self.generate_embeddings(documents)


        if self.use_chromadb:
            try:
                existing = self.collection.get()
                if existing and existing.get("ids"):
                    self.collection.delete(ids=existing["ids"])
            except Exception:
                pass


        if self.use_chromadb:
            self.collection.add(
                embeddings=[e.tolist() for e in emb],
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
        else:
            self.collection.add(
                embeddings=emb,
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )

        self.loaded = True
        return len(documents)


    def search(self, query: str, n_results: int = 5):
        q = self.preprocess_text(query)
        q_emb = self.generate_embeddings([q])

        if self.use_chromadb:
            return self.collection.query(query_embeddings=q_emb.tolist(), n_results=n_results)
        else:
            return self.collection.query(query_embeddings=q_emb, n_results=n_results)


    def _template_response(self, question: str, docs: list[str], metas: list[dict], sims: list[float]) -> str:
        # Instead of printing "found papers", return only an answer-like text
        if not docs:
            return "No results found. Try different keywords."

        # take a few snippets as “context” but don't print a ranked list
        snippets = []
        for d in docs[:3]:
            if not d:
                continue
            snippets.append(d[:350].replace("\n", " ").strip())

        # simple “lecturer-friendly” answer (no duplication)
        return (
            f"Based on the retrieved papers, here are key points related to **{question}**:\n\n"
            + "\n".join([f"- {s}..." for s in snippets if s])
          ).strip()



    def generate_response(self, question: str, docs: list[str], metas: list[dict], sims: list[float]) -> str:

        if self.use_openai:
            context = "\n\n".join(
                [f"Title: {m.get('title')}\nContent: {d[:600]}..." for m, d in zip(metas, docs)]
            )
            prompt = f"""Answer the question using ONLY the provided sources.

Question: {question}

Sources:
{context}

Return a short helpful answer and mention the most relevant sources."""
            try:
                resp = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a helpful plant-care assistant."},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=350,
                    temperature=0.3
                )
                return resp.choices[0].message.content
            except Exception:
                return self._template_response(question, docs, metas, sims)

        return self._template_response(question, docs, metas, sims)


    def query(self, question: str, top_k: int = 5, fallback_threshold: float = 0.20) -> dict:
        if not self.loaded:
            self.load_from_firestore()

        res = self.search(question, n_results=top_k)

        docs = res["documents"][0]
        metas = res["metadatas"][0]
        dists = res["distances"][0]

        if not docs:
            return {
                "response": "No results found. Try different keywords.",
                "papers_found": 0,
                "used_fallback": True,
                "best_sim": 0.0,
                "sources": [],
                "chunks": []
            }

        # Convert distances to similarities (1 - distance)
        sims = []
        for d in dists:
            try:
                d = float(d)
            except Exception:
                d = 999.0
            sim = 1.0 - d
            sims.append(sim)

        best_sim = max(sims) if sims else 0.0
        used_fallback = best_sim < fallback_threshold

        # Build chunks for UI
        chunks = []
        for m, doc, sim in zip(metas, docs, sims):
            chunks.append({
                "title": m.get("title") or "Untitled",
                "url": m.get("url"),
                "snippet": (doc[:320].replace("\n", " ") + "...") if doc else "",
                "article_id": m.get("article_id"),
                "metadata": (m.get("metadata") or {}),
            })

        response_text = self.generate_response(question, docs, metas, sims)

        return {
            "response": response_text,
            "papers_found": len(docs),
            "used_fallback": used_fallback,
            "best_sim": float(best_sim),
            "sources": metas,
            "chunks": chunks
        }



# SEED ARTICLES FROM LOCAL FOLDER + BUILD INDEX


def seed_database_with_articles(folder_path: str = "articles_data", do_build_index: bool = True):

    print("--- Seeding Database with REAL Data ---")

    if not os.path.exists(folder_path):
        print(f"Warning: Folder '{folder_path}' not found. Creating it now...")
        os.makedirs(folder_path)
        print(f"Please put your .docx/.txt files in '{folder_path}' and restart.")
        return

    files = glob.glob(os.path.join(folder_path, "*.docx")) + glob.glob(os.path.join(folder_path, "*.txt"))
    if not files:
        print(f"No files found in {folder_path}.")
        return

    print(f"Found {len(files)} files. Processing...")
    for file_path in files:
        filename = os.path.basename(file_path)
        title = os.path.splitext(filename)[0].replace("_", " ").title()

        print(f"Reading: {filename}...")
        content = read_text_from_file(file_path)
        if content:
            add_article(title=title, content=content)
        else:
            print(f"Skipped empty or unreadable file: {filename}")

    if do_build_index:
        print("Building Index")
        build_index(max_docs=5, use_stem=True)

def generate_vacation_report(username, days_away):
    """
    Generates a survival report with DYNAMIC drying rates based on plant type.
    Thirsty plants (high threshold) dry faster than hardy plants (low threshold).
    """
    import plants_manager 
    from data_manager import get_latest_reading
    
    user_plants = plants_manager.list_plants(username)
    report = []
    
    MAX_SOIL_CAPACITY = 100.0
    GLOBAL_MAX_DAYS = 21 

    for plant in user_plants:
        plant_id = plant.get("plant_id")
        plant_name = plant.get("name", "Unknown Plant")
        
        # 1. Get Threshold
        plant_threshold = plant.get('min_soil',30)

        # 2. --- SMART LOGIC: Determine Drying Rate ---
        # If the plant needs a lot of water (threshold > 20%), assumes it dries fast.
        if plant_threshold > 20:
            drying_rate = 10.0  # Fast drying (e.g. Basil) - loses 10% per day
        else:
            drying_rate = 2.0   # Slow drying (e.g. Cactus) - loses 2% per day
        # ---------------------------------------------

        # 3. Get Sensor Data
        latest_data = get_latest_reading(plant_id)
        current_soil = float(latest_data.get("soil", 0)) if latest_data else 0

        try:
            days = int(days_away)
        except (ValueError, TypeError):
            days = 0

        # Calculate limits based on the SPECIFIC drying rate
        max_possible_days = (MAX_SOIL_CAPACITY - plant_threshold) / drying_rate
        predicted_soil = current_soil - (days * drying_rate)
        
        status = ""
        msg = ""

        if not latest_data:
            status = "Unknown ❓"
            msg = "No sensor data available."

        # Case A: Physically impossible to survive this long
        elif days > max_possible_days:
            status = "CRITICAL 💀"
            msg = f"Cannot survive {days} days. Max capacity is ~{int(max_possible_days)} days. Need a sitter."
            
        elif days > GLOBAL_MAX_DAYS:
            status = "CRITICAL 💀"
            msg = "Vacation too long. System limit exceeded."

        # Case B: Possible, but needs water NOW
        elif predicted_soil < plant_threshold:
            status = "NEEDS WATER 💧"
            # How much to water?
            days_left_current = max(0, int((current_soil - plant_threshold) / drying_rate))
            msg = f"Will dry in {days_left_current} days. Water to 100% BEFORE leaving!"

        else:
            status = "SAFE ✅"
            msg = f"Predicted: {int(predicted_soil)}% (Min: {plant_threshold}%). Have fun!"

        report.append([plant_name, f"{current_soil}%", status, msg])

    return report