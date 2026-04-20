import chromadb
from chromadb.utils import embedding_functions
from openai import OpenAI

client = OpenAI()

chroma_client = chromadb.Client()

collection = chroma_client.create_collection(name="laws")

def add_document(text, doc_id):
    collection.add(
        documents=[text],
        ids=[doc_id]
    )

def search_docs(query):
    results = collection.query(
        query_texts=[query],
        n_results=5
    )
    return results["documents"][0]
