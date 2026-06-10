# BYOS Chatbot - Expert Data Analyst API 🚀

**BYOS (Build Your Own Solution)** est un assistant virtuel intelligent basé sur une architecture RAG (*Retrieval-Augmented Generation*), développé sur-mesure pour les équipes techniques et réseau de la **Sonatel**. 

Il agit comme un collègue expert capable d'analyser en temps réel les données opérationnelles issues d'**Elasticsearch** (tickets d'intervention sur site, statistiques par zones et régions) et de restituer des analyses fluides, précises et contextuelles via une interface API streaming.

---

## 🏗️ Architecture & Choix Techniques

Le projet s'appuie sur une infrastructure conteneurisée et optimisée pour s'exécuter localement (notamment validée sur architecture Apple Silicon M4) sans dépendance cloud externe pour la partie LLM.

* **Framework API :** FastAPI (Python 3.10) avec gestion du streaming asynchrone (Server-Sent Events).
* **Orchestration LLM :** LangChain / LangChain-Ollama.
* **Moteur d'IA Local :** Ollama exécutant le modèle `llama3.1:latest` (4.9 GB).
* **Optimisation Infra (Production Ready) :** Utilisation des **Docker Network Aliases** (`ollama-backend-alias`) permettant un découplage total entre le code applicatif et l'infrastructure réseau de conteneurs.
* **Base de connaissances :** Pipeline de données connecté à un cluster Elasticsearch distant.

---

## 🛠️ Configuration du Projet

1. Variables d'environnement (`.env`)
Créez un fichier `.env` à la racine du projet sur le modèle suivant :

Configuration de la source de données (Elasticsearch)
ES_HOST=https://your-secure-elasticsearch-cluster.com:443
ES_USER=api_data_user
ES_PASSWORD=YourSuperSecurePassword123!
ES_INDEX=production_tickets_index

Configuration du Modèle de Langage (LLM)
OLLAMA_MODEL=llama3.1:latest

Configuration Réseau Docker 
OLLAMA_HOST=http://ollama-server:11434


2. Déploiement avec Docker Compose
L'orchestration des services est automatisée. Le conteneur de l'API attend intelligemment que le service Ollama soit pleinement opérationnel (via un healthcheck natif ollama list) avant de démarrer son propre pipeline.
Pour lancer l'application :

docker compose up -d --build

3. Structure des Fichiers Clés

main.py              # Point d'entrée de l'application FastAPI
data_loader.py       # Récuperation et ingestion des données
rag_engine.py        # Mémoire sémantiqque du système
chatbot.py           # Logique métier, invite système (Prompt) et streaming LangChain
Dockerfile           # Build de l'image de l'API (Optimisé CPU/Torch)
docker-compose.yml   # Orchestration multi-conteneurs
nginx.conf           # Reverse proxy pour la sécurisation du API
chatbot.py           # Logique métier, invite système (Prompt) et streaming LangChain
Dockerfile           # Build de l'image de l'API (Optimisé CPU/Torch)
docker-compose.yml   # Orchestration multi-conteneurs avec Alias Réseau
.dockerignore        # Exclusion des fichiers inutiles (ex: logs, configurations locales)
requirements.txt     # Dépendances Python du projet
chroma.db            # Base de données vectorielle
.gitignore           # Exclusion des fichiers inutiles

