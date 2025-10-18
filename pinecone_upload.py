# pinecone_upload.py
import json
import time
from tqdm import tqdm
from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec
import config

# Config
DATA_FILE = "vietnam_travel_database.json"
BATCH_SIZE = 32

INDEX_NAME = config.PINECONE_INDEX_NAME
VECTOR_DIM = 384  # 384 for sentence-transformers all-MiniLM-L6-v2

# Initialize - clients
# Use OpenRouter if available, otherwise OpenAI
if config.OPENROUTER_API_KEY:
    client = OpenAI(
        api_key=config.OPENROUTER_API_KEY,
        base_url=config.OPENROUTER_BASE_URL
    )
    print("Using OpenRouter for embeddings")
else:
    client = OpenAI(api_key=config.OPENAI_API_KEY)
    print("Using OpenAI for embeddings")

# Initialize Pinecone v3.0.0
pc = Pinecone(api_key=config.PINECONE_API_KEY)

# Create index if it doesn't exist
try:
    existing_indexes = [idx.name for idx in pc.list_indexes()]
    if INDEX_NAME not in existing_indexes:
        print(f"Creating index: {INDEX_NAME}")
        pc.create_index(
            name=INDEX_NAME,
            dimension=VECTOR_DIM,
            metric="cosine",
            spec=ServerlessSpec(
                cloud="aws",
                region="us-east-1"
            )
        )
    else:
        print(f"Index {INDEX_NAME} already exists.")
    
    # Connect to the index
    index = pc.Index(INDEX_NAME)
    print(f"Connected to Pinecone index: {INDEX_NAME}")
    
except Exception as e:
    print(f"Pinecone setup error: {e}")
    print("Please check your Pinecone API key")
    exit(1)

# Helper functions
def get_embeddings(texts, model="all-MiniLM-L6-v2"):
    """Generate embeddings using local sentence transformer."""
    from sentence_transformers import SentenceTransformer
    embedding_model = SentenceTransformer(model)
    embeddings = embedding_model.encode(texts)
    return embeddings.tolist()

def get_embeddings_http(texts, model="text-embedding-3-small"):
    """Fallback HTTP method for embeddings"""
    import requests
    
    url = f"{config.OPENROUTER_BASE_URL}/embeddings"
    headers = {
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:3000",  # Required by OpenRouter
        "X-Title": "Vietnam Travel RAG"  
    }
    
    data = {
        "model": model,
        "input": texts
    }
    
    response = requests.post(url, headers=headers, json=data)
    
    if response.status_code == 200:
        try:
            result = response.json()
            return [item['embedding'] for item in result['data']]
        except Exception as e:
            print(f"[ERROR] JSON decode failed: {e}")
            print(f"[ERROR] Full response: {response.text}")
            raise e
    else:
        raise Exception(f"HTTP {response.status_code}: {response.text}")

def chunked(iterable, n):
    for i in range(0, len(iterable), n):
        yield iterable[i:i+n]


def main():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        nodes = json.load(f)

    items = []
    for node in nodes:
        semantic_text = node.get("semantic_text") or (node.get("description") or "")[:1000]
        if not semantic_text.strip():
            continue
        meta = {
            "id": node.get("id"),
            "type": node.get("type"),
            "name": node.get("name"),
            "city": node.get("city", node.get("region", "")),
            "tags": node.get("tags", [])
        }
        items.append((node["id"], semantic_text, meta))
    print(f"Preparing to upsert {len(items)} items to Pinecone...")
    for batch in tqdm(list(chunked(items, BATCH_SIZE)), desc="Uploading batches"):
        ids = [item[0] for item in batch]
        texts = [item[1] for item in batch]
        metas = [item[2] for item in batch]
        embeddings = get_embeddings(texts, model="all-MiniLM-L6-v2")
        vectors = [
            {"id": _id, "values": emb, "metadata": meta}
            for _id, emb, meta in zip(ids, embeddings, metas)
        ]

        try:
            index.upsert(vectors=vectors)
        except Exception as e:
            print(f"[ERROR] Upsert failed: {e}")
            # Continue with next batch
            continue
        time.sleep(0.2)

    print("All items uploaded successfully.")

# -----------------------------
if __name__ == "__main__":
    main()
