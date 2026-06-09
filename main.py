import os
import time
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from data_loader import DataLoader
from rag_engine import RAGEngine
from chatbot import BYOSChatbot

load_dotenv()

def ensure_ollama_model():
    """Vérifie si le modèle Ollama est présent, sinon le télécharge automatiquement."""
    ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    model_name = os.getenv("OLLAMA_MODEL", "gpt-oss:latest")
    
    print(f"🔄 Connexion à Ollama sur {ollama_host}...")
    
    # ÉTAPE CLÉ : Boucle d'attente pour laisser le temps au conteneur Ollama de démarrer
    response = None
    for attempt in range(10):
        try:
            response = requests.get(f"{ollama_host}/api/tags", timeout=5)
            if response.status_code == 200:
                break
        except requests.exceptions.ConnectionError:
            print(f"⏳ En attente du démarrage du service Ollama (tentative {attempt + 1}/10)...")
            time.sleep(3)
    else:
        print("❌ Impossible de joindre le serveur Ollama après plusieurs tentatives.")
        return

    # Vérification et téléchargement (pull) du modèle gpt-oss
    try:
        models = [m["name"] for m in response.json().get("models", [])]
        
        if model_name not in models and f"{model_name}:latest" not in models:
            print(f"⚠️ Modèle '{model_name}' introuvable sur le serveur Ollama. Téléchargement en cours...")
            
            pull_response = requests.post(
                f"{ollama_host}/api/pull",
                json={"name": model_name},
                timeout=600  # Laisse le temps au gros fichier de se télécharger
            )
            if pull_response.status_code == 200:
                print(f"✅ Modèle '{model_name}' récupéré avec succès dans Docker !")
            else:
                print(f"❌ Échec du téléchargement automatique d'Ollama : {pull_response.text}")
        else:
            print(f"✅ Modèle Ollama '{model_name}' détecté et prêt.")
            
    except Exception as e:
        print(f"⚠️ Erreur lors de l'initialisation du modèle : {e}")

# Lancer la vérification automatique au démarrage
ensure_ollama_model()

app = FastAPI(title="BYOS RAG API", description="API d'analyse de tickets Sonatel en mode Streaming")

# Configuration du CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialisation globale au démarrage
loader = DataLoader(
    host=os.getenv("ES_HOST"),
    user=os.getenv("ES_USER"),
    password=os.getenv("ES_PASSWORD"),
    index_id=os.getenv("ES_INDEX")
)
raw_texts = loader.fetch_and_process()
engine = RAGEngine()
engine.build_index(raw_texts)
bot = BYOSChatbot(engine, model_ollama=os.getenv("OLLAMA_MODEL"))

# Modèle de données pour la requête
class ChatRequest(BaseModel):
    query: str
    history: list = []  # Liste de dictionnaires {"role": "user", "content": "..."}

@app.get("/")
def home():
    return {"status": "online", "message": "API BYOS prête et configurée pour le Streaming"}

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        # On récupère le générateur asynchrone de tokens
        stream_generator = bot.generate_stream(request.query, request.history)
        
        # On renvoie le flux continu au client avec le type approprié
        return StreamingResponse(stream_generator, media_type="text/event-stream")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))