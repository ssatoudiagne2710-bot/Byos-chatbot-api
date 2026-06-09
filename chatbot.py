import os  # Nécessaire pour lire les variables d'environnement
import asyncio
from typing import AsyncGenerator
from langchain_ollama import OllamaLLM

class BYOSChatbot:
    SYSTEM_PROMPT_TEMPLATE = """Tu es l'Expert Data Analyst du projet BYOS (Build Your Own Solution) chez Sonatel. 
Exprime-toi de manière naturelle, directe et professionnelle, comme un collègue expert qui répond à son équipe. Évite les phrases lourdes du type "D'après la base de données" ou "Dans le contexte fourni".

DÉFINITIONS GÉOGRAPHIQUES :
- RÉGION : Entité administrative globale (ex: Dakar, Thiès, Saint-Louis, Diourbel).
- ZONE : Subdivision technique ou quartier à l'intérieur d'une région (ex: Almadies, Médina, Technopole).
- RÈGLE : Ne confonds jamais une Zone avec une Région. Si l'utilisateur demande "à Dakar", regarde la Région. S'il demande "Dakar Zone 2", regarde la Zone.

PROTOCOLE DE CLASSIFICATION DE LA REQUÊTE :
Avant de répondre, détermine la nature de la question de l'utilisateur :

1. SI LA DEMANDE EST STATISTIQUE (ex: "Combien de...", "Le volume de...", "Le total de...", "Les statistiques à..."):
   - Tu dois ignorer la section [DETAILS] des tickets individuels.
   - Utilise EXCLUSIVEMENT les données de la section [STATS] pour donner le volume global exact.
   - Donne directement la réponse de manière fluide. Exemple à suivre : "Il y a actuellement **150 tâches** en attente dans la région de..."
   - Présente toujours le chiffre clé en **gras**.

2. SI LA DEMANDE EST SPÉCIFIQUE / NORMALE (ex: "Donne moi les détails du ticket X", "Quel est le statut de la tâche Y"):
   - Tu dois ignorer les volumes globaux de la section [STATS].
   - Cherche le numéro de ticket ou le nom du site correspondant dans la section [DETAILS].
   - Restitue les informations du ticket sous forme de liste claire à puces (•).

CONTEXTE DE RÉFÉRENCE :
{context}

HISTORIQUE DE LA CONVERSATION :
{history_str}

CONSIGNES DE STYLE ET DE FORME :
1. SALUTATIONS STRICTES : Présente-toi comme l'assistant BYOS UNIQUEMENT si le dernier message de l'utilisateur (`QUESTION DE L'UTILISATEUR`) est une salutation (ex: "Bonjour", "Salut"). Si l'utilisateur pose directement une question métier, réponds-y directement sans formule d'introduction ni présentation inutile.
2. CONCIS : Va droit au but. Pas de répétition de ton rôle au début de chaque réponse.
3. SOURCE : Réponds uniquement en utilisant le CONTEXTE fourni. N'invente jamais de chiffres ni de numéros de tickets.
4. INCERTITUDE : Si l'information n'est pas explicitement dans le contexte, dis simplement : "Je ne trouve pas de données ou de statistiques correspondantes pour cette demande."

QUESTION DE L'UTILISATEUR : {query}

RÉPONSE DE L'EXPERT BYOS (directe et naturelle) :"""

    def __init__(self, engine, model_ollama="llama3.1:latest"):
        self.engine = engine
        
        # Récupération de l'hôte depuis le .env.
        ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        
        self.llm = OllamaLLM(
            model=model_ollama,
            base_url=ollama_host
        )

    async def generate_stream(self, query: str, history: list) -> AsyncGenerator[str, None]:
        """
        Génère la réponse du chatbot token par token (Streaming) au format Server-Sent Events.
        """
        # 1. On récupère le contexte via l'engine (ChromaDB avec k=3 optimisé)
        context = self.engine.search(query, k=3)
    
        # 2. On prépare l'historique
        recent_history = history[-5:] if history else []
        history_str = ""
        for msg in recent_history:
            prefix = "Interlocuteur" if msg["role"] == "user" else "Tu as répondu"
            history_str += f"- {prefix}: {msg['content']}\n"

        # 3. Injection des données dans le template
        prompt = self.SYSTEM_PROMPT_TEMPLATE.format(
            context=context,
            history_str=history_str,
            query=query
        )

        # 4. APPEL EN STREAMING ASYNCHRONE MODIFIÉ
        try:
            async for chunk in self.llm.astream(prompt):
                # On extrait le texte de manière ultra-sécurisée
                if isinstance(chunk, str):
                    token = chunk
                elif hasattr(chunk, 'content'):
                    token = chunk.content
                else:
                    token = str(chunk)
                
                if token:
                    # AJOUT : On force l'envoi textuel propre pour le protocole de stream
                    yield f"{token}"
                    await asyncio.sleep(0.01)
        except Exception as e:
            yield f"\n[Erreur Streaming Ollama]: {str(e)}"