from __future__ import annotations
import nltk
import json
import time
import requests
import os
import glob
from config import get_db as _get_central_db
from typing import Optional, List, Dict, Any
import datetime as _dt
import firebase_admin
from firebase_admin import credentials, firestore
import re
from nltk.stem import PorterStemmer

# --- בדיקה שהספרייה מותקנת ---
try:
    from docx import Document
except ImportError:
    print("Warning: python-docx not installed. Run 'pip install python-docx'")

# ==========================================
# הגדרות ראשוניות (SETUP)
# ==========================================

try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    print("Downloading NLTK stopwords...")
    nltk.download('stopwords')
    nltk.download('punkt')

SENSORS_COL  = "sensors"    
ARTICLES_COL = "articles"   
INDEX_COL = "index"

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
# פונקציות חיישנים (IOT)
# ==========================================

def add_sensor_reading(plant_id ,temp=None, humidity=None, soil=None, light=None, extra=None):
    db = get_db()
    payload = {
        "plant_id": plant_id,
        "timestamp": _server_ts(),
        "created_at": _server_ts(),
    }
    if temp      is not None: payload["temp"] = float(temp)
    if humidity  is not None: payload["humidity"] = float(humidity)
    if soil      is not None: payload["soil"] = float(soil)
    if light     is not None: payload["light"] = float(light)
    if extra:                 payload.update(extra)

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

def sync_iot_data(plant_id):
    """
    Fetches real data from the lecturer's server (Render)
    and saves it to our Firebase Firestore.
    """
    print("--- Connecting to IoT Server... (This might take time if server is sleeping) ---")
    
    # We need to fetch 3 different feeds
    feeds = ["temperature", "humidity", "soil"]
    sensor_data = {}

    try:
        for feed in feeds:
            # Send GET request
            response = requests.get(IOT_SERVER_URL, params={"feed": feed, "limit": 1})
            
            if response.status_code == 200:
                data = response.json()
                if "data" in data and len(data["data"]) > 0:
                    # Get the most recent value
                    latest_entry = data["data"][0]
                    value = float(latest_entry["value"])
                    sensor_data[feed] = value
                    print(f"[IOT] Fetched {feed}: {value}")
                else:
                    print(f"[IOT] No data for {feed}")
            else:
                print(f"[IOT] Error fetching {feed}: {response.status_code}")

        # If we got data, save it to our Firestore
        if sensor_data:
            # Normalize keys to match our database schema (temp, humidity, soil)
            # The server returns "temperature", we use "temp"
            final_temp = sensor_data.get("temperature")
            final_hum = sensor_data.get("humidity")
            final_soil = sensor_data.get("soil")

            # Save to Firestore using existing function
            new_id = add_sensor_reading(
                plant_id, 
                temp=final_temp, 
                humidity=final_hum, 
                soil=final_soil
            )
            print(f"[IOT] Data synced to Firestore successfully. ID: {new_id}")
            return True
            
    except Exception as e:
        print(f"[IOT] Connection failed: {e}")
        return False

# ==========================================
# פונקציות מאמרים ו-RAG (תומך DOCX)
# ==========================================

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

def add_article(title, content, url=None, metadata=None):
    db = get_db()
    # בדיקה למניעת כפילויות: אם הכותרת קיימת, לא מעלים שוב
    existing = db.collection(ARTICLES_COL).where("title", "==", title).limit(1).stream()
    if list(existing):
        print(f"Skipping duplicate: {title}")
        return None

    doc = {
        "title": title,
        "content": content,
        "url": url,
        "metadata": metadata or {},
        "created_at": _server_ts(),
        "updated_at": _server_ts(),
    }
    ref = db.collection(ARTICLES_COL).add(doc)[1]
    return ref.id

def get_all_articles(limit=None):
    db = get_db()
    docs = db.collection(ARTICLES_COL).stream()
    return [_doc_to_dict(doc) for doc in docs]

def get_article_by_id(article_id):
    db = get_db()
    doc = db.collection(ARTICLES_COL).document(article_id).get()
    return _doc_to_dict(doc) if doc.exists else None

# --- מנוע החיפוש והאינדקס ---

stemmer = PorterStemmer()
STOPWORDS = {
    "a", "an", "the", "and", "or", "in", "on", "at", "of", "for", "to", 
    "is", "are", "as", "by", "with", "from", "this", "that", "it", "be", 
    "was", "were", "which", "how", "what", "where", "when", "who", "can", 
    "will", "not", "but", "has", "have", "had", "do", "does", "did"
}

def _tokenize(text):
    if text is None: text = ""
    # אופטימיזציה 1: לוקחים רק את ה-4000 תווים הראשונים (כותרת + תקציר + מבוא)
    # זה מונע עומס מטורף על האינדקס במאמרים ארוכים
    text = text[:4000] 
    
    words = re.findall(r"\w+", text)
    # סינון מילים קצרות מדי (פחות מ-3 אותיות)
    words = [w.lower() for w in words if len(w) > 2]
    return words

def _normalize(tokens):
    cleaned_tokens = []
    for word in tokens:
        if word in STOPWORDS: continue
        # בדיקה שהמילה היא לא סתם מספרים
        if word.isdigit(): continue 
        
        try:
            stemmed_word = stemmer.stem(word)
            cleaned_tokens.append(stemmed_word)
        except:
            continue
    return cleaned_tokens

def build_index_from_articles():
    print("Optimization: Starting index build in batches...")
    db = get_db()
    index_ref = db.collection(INDEX_COL)
    
    # 1. מחיקת אינדקס ישן (במנות קטנות כדי לא לחרוג)
    try:
        deleted = 0
        for old_doc in index_ref.limit(50).stream(): 
            old_doc.reference.delete()
            deleted += 1
        if deleted > 0: print(f"Cleaned {deleted} old index terms...")
    except Exception as e:
        print(f"Warning during cleanup: {e}")

    inverted_index = {}
    articles = get_all_articles()
    
    print(f"Indexing {len(articles)} articles...")
    
    for article in articles:
        doc_id = article["id"]
        # חיבור כותרת ותוכן
        text = (article.get("title","") + " " + article.get("content",""))
        words = _normalize(_tokenize(text))
        
        term_freq = {}
        for word in words:
            term_freq[word] = term_freq.get(word, 0) + 1

        for term, count in term_freq.items():
            if term not in inverted_index: inverted_index[term] = {}
            inverted_index[term][doc_id] = count

    # 2. כתיבה לדאטה-בייס במנות (Batches)
    # Firestore מאפשר מקסימום 500 פעולות ב-Batch. אנחנו נעשה 400 ליתר ביטחון.
    batch = db.batch()
    count = 0
    total_terms = len(inverted_index)
    print(f"Total unique terms to index: {total_terms}")

    for i, (term, posting) in enumerate(inverted_index.items()):
        doc_ref = index_ref.document(term)
        batch.set(doc_ref, {"postings": posting})
        count += 1
        
        # כשהגענו ל-400, שולחים ומנקים
        if count >= 400:
            print(f"Saving batch... ({i}/{total_terms})")
            batch.commit()
            batch = db.batch() # בטש חדש
            count = 0
            time.sleep(1) # נותנים ל-Firebase לנשום שנייה

    # שליחת מה שנשאר
    if count > 0:
        batch.commit()
    
    print("Index built successfully.")
    return True

def rag_search(query, top_k=5):
    db = get_db()
    words = _tokenize(query)        
    terms = _normalize(words)           
    scores = {}

    for term in terms:
        term_doc = db.collection("index").document(term).get()
        if not term_doc.exists: continue
        postings = term_doc.to_dict().get("postings", {})

        for doc_id, count in postings.items():
            if doc_id not in scores: scores[doc_id] = 0
            scores[doc_id] += count

    ranked_docs = sorted(scores.items(), key=lambda item: item[1], reverse=True)[:top_k]
    results = []

    for doc_id, score in ranked_docs:
        article = get_article_by_id(doc_id)
        if article:
            snippet = article["content"][:200] + "..."
            results.append({
                "id": doc_id,
                "title": article["title"],
                "score": score,
                "snippet": snippet,
                "url": article.get("url")
            })
    return results

# ==========================================
# פונקציית הטעינה האוטומטית
# ==========================================

def seed_database_with_articles():
    """
    סורקת את התיקייה 'articles_data',
    קוראת קבצי docx ו-txt, ומעלה אותם ל-Firestore.
    """
    print("--- Seeding Database with REAL Data ---")
    
    # שם התיקייה שבה שמת את הקבצים
    folder_path = "articles_data" 
    
    if not os.path.exists(folder_path):
        print(f"Warning: Folder '{folder_path}' not found. Creating it now...")
        os.makedirs(folder_path)
        print(f"Please put your .docx files in '{folder_path}' and restart.")
        return

    # מציאת כל הקבצים מסוג docx ו-txt
    files = glob.glob(os.path.join(folder_path, "*.docx")) + glob.glob(os.path.join(folder_path, "*.txt"))
    
    if not files:
        print(f"No files found in {folder_path}.")
        return

    print(f"Found {len(files)} files. Processing...")

    for file_path in files:
        filename = os.path.basename(file_path)
        # שימוש בשם הקובץ בתור כותרת (בלי הסיומת)
        title = os.path.splitext(filename)[0].replace("_", " ").title()
        
        print(f"Reading: {filename}...")
        content = read_text_from_file(file_path)
        
        if content:
            # הוספה לדאטה-בייס (יש בדיקת כפילויות בפנים)
            add_article(title=title, content=content)
        else:
            print(f"Skipped empty or unreadable file: {filename}")
    
    print("Building Search Index...")
    build_index_from_articles()
    print("Seeding Complete.")