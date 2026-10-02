"""RAG engine — embed emails + transcripts into ChromaDB, retrieve relevant context."""
import os
import chromadb
from chromadb.config import Settings as ChromaSettings
from config import settings as app_settings


def get_chroma_client():
    return chromadb.Client(ChromaSettings(
        persist_directory=app_settings.CHROMA_PERSIST_DIR,
        anonymized_telemetry=False,
    ))


def get_or_create_collection(client, name: str = "revos_docs"):
    return client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )


def index_emails(emails: list[dict]):
    """Index email bodies into ChromaDB for RAG retrieval."""
    client = get_chroma_client()
    collection = get_or_create_collection(client)

    docs, metas, ids = [], [], []
    for email in emails:
        doc = (
            f"Subject: {email.get('subject', '')}\n"
            f"From: {email.get('from_addr', '')}\n"
            f"To: {email.get('to_addr', '')}\n"
            f"Date: {email.get('date', '')}\n"
            f"Deal ID: {email.get('deal_id', '')}\n\n"
            f"{email.get('body', '')}"
        )
        docs.append(doc)
        metas.append({
            "deal_id": str(email.get("deal_id", "")),
            "type": "email",
            "date": email.get("date", ""),
            "sentiment": float(email.get("sentiment", 0)),
        })
        ids.append(f"email_{email['id']}")

    # Batch upsert (ChromaDB limit: 41666 per batch)
    batch_size = 5000
    for i in range(0, len(docs), batch_size):
        collection.upsert(
            documents=docs[i:i+batch_size],
            metadatas=metas[i:i+batch_size],
            ids=ids[i:i+batch_size],
        )
    print(f"  [+] Indexed {len(docs)} emails into ChromaDB", flush=True)


def index_transcripts(transcripts: list[dict]):
    """Index call transcripts into ChromaDB."""
    client = get_chroma_client()
    collection = get_or_create_collection(client)

    docs, metas, ids = [], [], []
    for t in transcripts:
        doc = (
            f"Call Transcript — Deal ID: {t.get('deal_id', '')}\n"
            f"Date: {t.get('date', '')}\n"
            f"Duration: {t.get('duration_minutes', '')} min\n"
            f"Summary: {t.get('summary', '')}\n"
            f"Objections: {t.get('objections', '')}\n"
            f"Commitments: {t.get('commitments', '')}\n\n"
            f"{t.get('transcript', '')}"
        )
        docs.append(doc)
        metas.append({
            "deal_id": str(t.get("deal_id", "")),
            "type": "transcript",
            "date": t.get("date", ""),
        })
        ids.append(f"transcript_{t['id']}")

    batch_size = 5000
    for i in range(0, len(docs), batch_size):
        collection.upsert(
            documents=docs[i:i+batch_size],
            metadatas=metas[i:i+batch_size],
            ids=ids[i:i+batch_size],
        )
    print(f"  [+] Indexed {len(docs)} transcripts into ChromaDB", flush=True)


def retrieve(query: str, deal_id: int | None = None, top_k: int = 5) -> list[dict]:
    """Retrieve relevant documents for a query, optionally filtered by deal_id."""
    client = get_chroma_client()
    collection = get_or_create_collection(client)

    where_filter = {"deal_id": str(deal_id)} if deal_id else None

    results = collection.query(
        query_texts=[query],
        n_results=top_k,
        where=where_filter,
    )

    docs = []
    if results and results["documents"]:
        for i, doc in enumerate(results["documents"][0]):
            meta = results["metadatas"][0][i] if results["metadatas"] else {}
            dist = results["distances"][0][i] if results["distances"] else 0
            docs.append({
                "content": doc,
                "metadata": meta,
                "relevance": round(1 - dist, 3),  # cosine similarity
            })
    return docs
