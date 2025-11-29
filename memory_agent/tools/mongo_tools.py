import os
from typing import List, Optional
from langchain_core.tools import tool
from pymongo import MongoClient
from datetime import datetime

# MongoDB Connection
MONGO_URI = os.environ.get("MONGODB_URL", "mongodb://localhost:18070")
DB_NAME = os.environ.get("MONGODB_DATABASE", "teamadapt")
COLLECTION_NAME = "agent_documents"


def get_mongo_collection():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    return db[COLLECTION_NAME]


@tool
def save_document(title: str, content: str, tags: List[str] = []) -> str:
    """Saves a document to MongoDB with title, content, and optional tags."""
    try:
        collection = get_mongo_collection()
        doc = {
            "title": title,
            "content": content,
            "tags": tags,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        result = collection.insert_one(doc)
        return f"Document saved successfully with ID: {result.inserted_id}"
    except Exception as e:
        return f"Error saving document: {e}"


@tool
def read_document(query: str) -> str:
    """Searches for documents in MongoDB by title or tags."""
    try:
        collection = get_mongo_collection()
        # Simple regex search for title or tags
        regex_query = {"$regex": query, "$options": "i"}
        filter_query = {"$or": [{"title": regex_query}, {"tags": regex_query}]}
        docs = list(collection.find(filter_query).limit(5))

        if not docs:
            return "No documents found."

        results = []
        for doc in docs:
            results.append(
                f"Title: {doc['title']}\nTags: {doc['tags']}\nContent: {doc['content'][:200]}..."
            )

        return "\n---\n".join(results)
    except Exception as e:
        return f"Error reading documents: {e}"


def get_mongo_tools():
    return [save_document, read_document]
