#config cell 
!pip install -q nltk
import json
SERVICE_ACCOUNT_JSON = "/content/introtocloudcomputing-fcb85-firebase-adminsdk-fbsvc-9b3fe969d0.json"
import os
os.environ["SERVICE_ACCOUNT_JSON"] = SERVICE_ACCOUNT_JSON

from __future__ import annotations
from typing import Optional, List, Dict, Any
import os
import datetime as _dt
import firebase_admin
from firebase_admin import credentials, firestore

_APP_INITIALIZED: bool = False # a flag to tell the system if the firebase has been initialized or not 
_DB = None #to hold the firestore client object after initialization -> to ensure consistent DB context

SENSORS_COL  = "sensors"    #iot readings: the name of the firestore collection where Iot readings are stored
ARTICLES_COL = "articles"   #RAG articles: the firestore collection for the RAG articles 


#init the firebase
def init_firebase(path_to_json=None, project_id=None):
    global _APP_INITIALIZED, _DB
    try:
        if firebase_admin._apps:
            _DB = firestore.client()
            _APP_INITIALIZED = True
            return
    except Exception:
        pass
    if path_to_json is None:
        path_to_json = os.environ.get("SERVICE_ACCOUNT_JSON")
    if not path_to_json:
        raise ValueError("Missing service account JSON path. "
                         "Set SERVICE_ACCOUNT_JSON or pass path_to_json.")

    cred = credentials.Certificate(path_to_json)
    if project_id:
        firebase_admin.initialize_app(cred, {"projectId": project_id})
    else:
        firebase_admin.initialize_app(cred)

    _DB = firestore.client()
    _APP_INITIALIZED = True



#lazy getter --> will init if needed!
def get_db():
    global _DB
    if _DB is None:
        init_firebase(os.environ.get("SERVICE_ACCOUNT_JSON"))
    return _DB




#timestamp to store in the firestore
def _server_ts():
    try:
        return firestore.SERVER_TIMESTAMP
    except Exception:
        return _dt.datetime.utcnow().isoformat()


#normalization -> convert firestore doc to plain dict
def _doc_to_dict(doc):
    d = doc.to_dict() if hasattr(doc, "to_dict") else dict(doc)
    d["id"] = doc.id if hasattr(doc, "id") else d.get("id") #attach id

    #normalize time fields
    for k in ("created_at", "updated_at", "timestamp"): 
        v = d.get(k)
        if hasattr(v, "isoformat"):
            d[k] = v.isoformat()

    #returns a dict that represent firestore doc
    return d 


#SENSORS (IOT) - CRUD menu 

#create a new reading doc
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

    #returns new doc id
    return ref.id 



#READ readings for a plant: newest first
def get_sensor_history(plant_id: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    db = get_db()
    q = (db.collection(SENSORS_COL)
           .where("plant_id", "==", plant_id)
           .order_by("timestamp", direction=firestore.Query.DESCENDING))
    if limit:
        q = q.limit(int(limit))
    return [_doc_to_dict(doc) for doc in q.stream()]


#READ the most recent reading for a plant --> for the dashboard cards
def get_latest_reading(plant_id: str) -> Optional[Dict[str, Any]]:
    rows = get_sensor_history(plant_id, limit=1)
    return rows[0] if rows else None


  
#READ recent readings across all plants - the newest ones first 
def get_all_readings(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    db = get_db()
    q = db.collection(SENSORS_COL).order_by("timestamp", direction=firestore.Query.DESCENDING)
    if limit:
        q = q.limit(int(limit))
    return [_doc_to_dict(doc) for doc in q.stream()]



#UPDATE specific fields on an existing reading (update by id)
def update_reading(reading_id: str, **fields: Any) -> bool:
    #reading_id : doc's id in the SENSOR_COL
    #fields : "keyword" fields to update (temp =.. ,  humidity= .. blah blah blah)
    db = get_db()
    fields = {**fields, "updated_at": _server_ts()}
    db.collection(SENSORS_COL).document(reading_id).update(fields)
    return True


#DELETE a reading doc by it's id
def delete_reading(reading_id: str) -> bool:
    db = get_db()
    db.collection(SENSORS_COL).document(reading_id).delete()
    return True




#CRUD for articles

#functoin to create a new article doc in the firestore
def add_article(title, content, url=None, metadata=None):
    db = get_db()
    #creating a dict that contains all the fields to save in firestore
    doc = {
        "title": title,
        "content": content,
        "url": url,
        "metadata": metadata or {},
        "created_at": _server_ts(),
        "updated_at": _server_ts(),
    }
    ref = db.collection(ARTICLES_COL).add(doc)[1]

    #returns the id of the new article 
    return ref.id

#function to get all the articles from the "articles" collection in the firestore
def get_all_articles(limit=None):
    db = get_db()
    collection_ref = db.collection("articles") # start a query on the "articles" collection
    query = collection_ref.order_by(
        "created_at",
        direction=firestore.Query.DESCENDING
    )

    if limit is not None:
        query = query.limit(int(limit))

    docs = query.stream()# run query and get documents

    # convert each Firestore document to a normal Python dict
    articles = []
    for doc in docs:
        articles.append(_doc_to_dict(doc))

    return articles #returns as a list


#function that fitches one atricle from the firestore by its doc id
def get_article_by_id(article_id):
    db = get_db()
    col = db.collection("articles")
    # Get the document with this id
    doc_snapshot = col.document(article_id).get()

    # If the document exists, convert it to a dict
    if doc_snapshot.exists:
        return _doc_to_dict(doc_snapshot)

    # If it doesn't exist, return None
    else:
        return None


#function to update an existing article in firestore
def update_article(article_id, **fields):
    db = get_db()

    # Add a timestamp for when the update happens
    fields["updated_at"] = _server_ts()
    collection_ref = db.collection("articles")

    # Pick the specific document and update its fields
    doc_ref = collection_ref.document(article_id)
    doc_ref.update(fields)

    # Return True if the update is done successfully 
    return True

#function to delete an atricle from the firestore
#helper func
def delete_article(article_id):
    db = get_db()
    collection_ref = db.collection("articles")
    doc_ref = collection_ref.document(article_id) #get the doc by its id
    doc_ref.delete()
    #return true if the doc was successfully deleted 
    return True


#function that reads a .txt file from Colab and uploads it as an article to firestore
def add_article_from_txt(file_path, title, url=None, metadata=None):
    # Read file content
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    article_id = add_article(
        title=title,
        content=text, 
        url=url,
        metadata=None,
    )

    return article_id

#building the index
import re
from nltk.stem import PorterStemmer  #for stemming
stemmer = PorterStemmer()

#the name of the firestore collection that will store the index
INDEX_COL = "index"

#words we want to igonre  in search
STOPWORDS = {"a","an","the","and","or","in","on","at","of","for","to","is","are","as","by","with","from","this","that","it","be","was","were"}

def _tokenize(text):
    if text is None:
        text = ""
    # Find all groups of letters/numbers in the text
    words = re.findall(r"\w+", text)
    # Convert them to lowercase
    words = [w.lower() for w in words]
    return words

#function that removes the stopwords ans stems the rest -> the tesxt becomes clean and searchable
def _normalize(tokens):
    cleaned_tokens = []  # list to store final words

    for word in tokens:
        # skip stopwords (ignore them completely)
        if word in STOPWORDS:
            continue
        stemmed_word = stemmer.stem(word)
        cleaned_tokens.append(stemmed_word)
    #returns 'clean'list
    return cleaned_tokens




#function that builds the index for the RAG search engine
def build_index_from_articles():

    db = get_db()

    #Clear old index
    index_ref = db.collection("index")
    for old_doc in index_ref.stream():
        old_doc.reference.delete()

    inverted_index = {}

    #Loop through all article documents
    articles = get_all_articles()
    for article in articles:
        doc_id = article["id"]
        text = (article.get("title","") + " " + article.get("content",""))

        # tokenize and normalize text
        words = _tokenize(text)
        words = _normalize(words)

        # count term frequency
        term_freq = {}
        for word in words:
            term_freq[word] = term_freq.get(word, 0) + 1

        # add to the index
        for term, count in term_freq.items():
            if term not in inverted_index:
                inverted_index[term] = {}
            inverted_index[term][doc_id] = count

    #Write the final index to firestore
    batch = db.batch()
    for term, posting in inverted_index.items():
        doc_ref = index_ref.document(term)
        batch.set(doc_ref, {"postings": posting})

    batch.commit()

    return True


#function that searches through the indexed atricles -> returns the beast matching docs
def rag_search(query, top_k=5):
    db = get_db()
    words = _tokenize(query)        
    terms = _normalize(words)           
    scores = {}

    #Look up each search term in the index
    for term in terms:
        term_doc = db.collection("index").document(term).get()
        if not term_doc.exists:
            continue
        postings = term_doc.to_dict().get("postings", {})

        for doc_id, count in postings.items():
            if doc_id not in scores:
                scores[doc_id] = 0
            scores[doc_id] += count

    #Rank documents by score -> highest first
    ranked_docs = sorted(
        scores.items(),
        key=lambda item: item[1],
        reverse=True
    )[:top_k]

    #Build the final list of results
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



#adding articles from the 7th tutorial
#article 1
article_id = add_article_from_txt(
    "/content/1-s2.0-S2772899424000417-main.txt",
    title="A real time monitoring system for accurate plant leaves disease detection using deep learning",
    url="https://doi.org/10.1016/j.cropd.2024.100092"
)
print("Added article id:", article_id)


article_id = add_article_from_txt(
    "/content/s41598-025-98454-6.txt",
    title="AI-IoT based smart agriculture  pivot for plant diseases detection  and treatment",
    url="https://doi.org/10.1038/s41598-025-98454-6"
)
print("Added article id:", article_id)


article_id = add_article_from_txt(
    "/content/s41598-024-52038-y.txt",
    title="A novel smartphone application  for early detection of habanero  disease",
    url="https://www.nature.com/articles/s41598-024-52038-y"
)
print("Added article id:", article_id)


article_id = add_article_from_txt(
    "/content/pdis-03-15-0340-fe.txt",
    title="Plant Disease Detection by Imaging Sensors – Parallels and Specific Demands for Precision Agriculture and Plant Phenotyping",
    url="https://doi.org/10.1094/PDIS-03-15-0340-FE"
)
print("Added article id:", article_id)


article_id = add_article_from_txt(
    "/content/1-s2.0-S2772899424000417-main.txt",
    title="Using Deep Learning for Image-Based Plant Disease Detection",
    url="https://www.frontiersin.org/articles/10.3389/fpls.2016.01419/full"
)
print("Added article id:", article_id)




build_index_from_articles()

rag_search("tomato leaf disease detection", top_k=3)

rid = add_sensor_reading("plant_001", temp=24.7, humidity=61.2, soil=0.44)
print("new reading:", rid)
print("latest:", get_latest_reading("plant_001"))
print("history(3):", get_sensor_history("plant_001", limit=3))





