# 1. Utiliser une image Python officielle légère
FROM python:3.10-slim

# 2. Définir le dossier de travail dans le conteneur
WORKDIR /app

# 3. Installer les outils système essentiels (nécessaires pour compiler ChromaDB et certaines libs)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 4. Copier le fichier des dépendances
COPY requirements.txt .

# 5. MODIFICATION ICI : Installer d'abord la version CPU de Torch, puis le reste
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

# 6. Copier tout le reste du code du projet
COPY . .

# 7. Exposer le port qu'utilise FastAPI
EXPOSE 8000

# 8. Commande pour lancer l'fastAPI avec uvicorn au démarrage du conteneur et autoriser tous les ip avec le port
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]

