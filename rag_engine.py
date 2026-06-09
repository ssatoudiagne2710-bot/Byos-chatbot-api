import chromadb
from chromadb.utils import embedding_functions
import os
import time

class RAGEngine:
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        self.persist_directory = "./chroma_db"
        self.client = chromadb.PersistentClient(path=self.persist_directory)
        
        self.emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=model_name
        )
        self.collection = self.client.get_or_create_collection(
            name="tickets_sonatel",
            embedding_function=self.emb_fn
        )

    def is_index_stale(self, hours=24):
        """Vérifie si la base de données n'a pas été mise à jour depuis X heures."""
        # On se base sur le fichier de métadonnées de sqlite
        sqlite_path = os.path.join(self.persist_directory, "chroma.sqlite3")
        if not os.path.exists(sqlite_path):
            return True
        
        file_age_seconds = time.time() - os.path.getmtime(sqlite_path)
        return file_age_seconds > (hours * 3600)

    def build_index(self, data_records):
        """Met à jour ChromaDB par petits lots en utilisant l'ID unique du ticket."""
        if not data_records:
            print("Aucune donnée fournie pour l'indexation.")
            return
            
        print(f"Préparation de la mise à jour pour {len(data_records)} documents...")
        
        # Extraction des textes et des IDs réels des tickets
        texts = [record["document_text"] for record in data_records]
        # On force le format string pour les IDs (ex: "ticket_41836")
        ids = [f"ticket_{record['ticket']}" for record in data_records]
        
        batch_size = 4000 
        
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i : i + batch_size]
            batch_ids = ids[i : i + batch_size]
            
            print(f"Indexation du lot {i//batch_size + 1}...")
            
            # Grâce aux vrais IDs de tickets, upsert va :
            # - Insérer le ticket s'il est nouveau
            # - Mettre à jour ses stats/détails s'il existait déjà
            self.collection.upsert(
                documents=batch_texts,
                ids=batch_ids
            )
            
        print(f"Base de données ChromaDB synchronisée. Total : {self.collection.count()} documents.")

    def search(self, query, k=3):
        """Recherche les documents les plus proches."""
        results = self.collection.query(
            query_texts=[query],
            n_results=k
        )
        retrieved_chunks = results['documents'][0]