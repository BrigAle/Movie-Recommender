import os
from pyclbr import Class
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import json
from pymongo import MongoClient
from neo4j import GraphDatabase

app = FastAPI(title="Movie Recommender API Gateway")
## Configurazione CORS per permettere al front-end React di comunicare con questo gateway
origins = [
    "http://localhost:5173",        # L'indirizzo locale dove gira React (Vite)
    "http://127.0.0.1:5173",        # Variante standard dell'IP locale
]
# il front end e' un client non un microservizio, quindi non ha bisogno di autenticazione, ma solo di accesso alle rotte GET e POST

# Aggiunta del middleware CORS per permettere al front-end React di comunicare con questo gateway
# senza autenticazione, ma solo di accesso alle rotte GET e POST
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,          
    allow_credentials=True,
    allow_methods=["GET", "POST"],  # Se l'app deve solo leggere e inviare dati, blocca PUT e DELETE per sicurezza
    allow_headers=["*"],
)
# --- CONFIGURAZIONI CONNESSIONI ---
# Le variabili di ambiente MONGO_URI e NEO4J_URI possono essere impostate nel file .env o nel sistema operativo. Se non sono impostate, verranno utilizzati i valori di default.
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017")
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password_sicurissima"

# Connessione a MongoDB
# per connettersi a MongoDB, utilizziamo la libreria pymongo. La connessione viene stabilita utilizzando l'URI di MongoDB, che può essere configurato tramite variabile di ambiente o impostato di default.
# MongoClient è la classe principale per connettersi a MongoDB. Creiamo un'istanza di MongoClient passando l'URI di connessione. Successivamente, accediamo al database "movie_raw_db" e alla collezione "popular_movies" che contiene i film popolari.
mongo_client = MongoClient(MONGO_URI)
mongo_db = mongo_client["movie_raw_db"]
mongo_collection = mongo_db["popular_movies"]

# Connessione a Neo4j
# creo un istanza del driver di Neo4j utilizzando l'URI, l'utente e la password. Questo driver sarà utilizzato per eseguire query sul database Neo4j.
neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

# Implemento le websockets. Sono utili per la comunicazione in tempo reale tra il front-end e il back-end. 
# In questo caso, potrebbero essere utilizzate per notificare al front-end eventuali aggiornamenti sui film o sui generi senza dover fare richieste HTTP continue real-time. 
# Tuttavia, per semplicità, in questa implementatione iniziale non sono state incluse funzionalità specifiche di websocket.

# Creo un gestore che tiene traccia di chi e' connesso in una specifica stanza di websocket. 
# Il server deve sapere quali sono i loro 3 canali per poter inviare i messaggi a tutti contemporaneamente

# I Dunder methods __init__, __enter__, __exit__ sono metodi speciali in Python 
# che permettono di definire il comportamento di un oggetto quando viene creato,
# utilizzato in un contesto (con la parola chiave "with") e quando viene distrutto.

class ConnectionManager:
    def __init__(self):
        # dizionario per memorizzare le stanze.
        # La struttura della  stanza e': {"Codice_Stanza": [lista di websocket attive]}
        self.active_connections: dict[str,list[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        """Accetta la connessione WebSocket e la aggiunge alla lista delle 
            connessioni attive per la stanza specificata."""
        await websocket.accept() 
        # Se la stanza non esiste nella memotira del server, la creiamo vuota
        if session_id not in self.active_connections:
            self.active_connections[session_id] = []
        # Aggiugno il cancale dell'utente alla lista della stan\a
        self.active_connections[session_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, session_id: str):
        """Rimuovo l'utente dalla stanza quando chiude l'applicazione o si disconnette."""
        if session_id in self.active_connections:
            self.active_connections[session_id].remove(websocket)
            # Se la stanza è vuota, la rimuoviamo dal dizionario
            if not self.active_connections[session_id]:
                del self.active_connections[session_id]

    async def broadcast_to_session(self,session_id: str,message:dict):
        """Prende un messaggio e lo invia a TUTTI a1uelli dentro la stanza"""
        if session_id in self.active_connections:
            for connection in self.active_connections[session_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    pass  # Gestione degli errori di invio, ad esempio se un client si è disconnesso

## Creo un oggetto manager che usero' nell'endpoint
manager = ConnectionManager()


# --- ENDPOINTS ---
@app.get("/")
def read_root():
    """Rotta di controllo per verificare se il gateway è vivo"""
    return {"status": "online", "message": "API Gateway pronto per servire React!"}

@app.get("/api/movies")
def get_movies():
    """Estrae i film popolari da MongoDB da mostrare nella home di React"""
    try:
        # Cerchiamo tutti i film, escludendo il campo '_id' di MongoDB che non è serializzabile in JSON
        movies = list(mongo_collection.find({}, {"_id": 0}).limit(20))
        return movies
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore nel recupero dei film da Mongo: {e}")

@app.get("/api/genres")
def get_genres():
    """Estrae la mappa dei generi testuali che l'ingestion ha salvato su Mongo"""
    try:
        genres = list(mongo_db["genres"].find({}, {"_id": 0}))
        return genres
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Errore nel recupero dei generi: {e}")
    
@app.websocket("/ws/session/{session_id}") 
async def session_websocket(websocket: WebSocket, session_id: str):
    # Quando un utente si connette, lo aggiungiamo alla stanza
    await manager.connect(websocket, session_id)
    # Poi inviamo un messaggio di benvenuto a tutti nella stanza
    await manager.broadcast_to_session(session_id, {
        "event": "USER_JOINED",
        "message": f"Un utente si è unito alla sessione {session_id}."
    })
    
    try:
        while True:
            data = await websocket.receive_text()
            # trasformo in json
            event_data = json.loads(data)
            # In base al tipo di evento, possiamo decidere cosa fare
            if event_data.get("action") == "VOTE":
                movie_id = event_data.get("movie_id")
                vote_type = event_data.get("vote_type")  # "like" o "dislike"
                username = event_data.get("username")
                
                # stampo su docker logs per debug
                print(f"Ricevuto voto: {vote_type} per il film {movie_id} da {username} nella sessione/stanza {session_id}")
                
                # invio il voto a tutti nella stanza
                await manager.broadcast_to_session(session_id, {
                    "event": "VOTE_RECEIVED",
                    "movie_id": movie_id,
                    "vote_type": vote_type,
                    "username": username
                })
                
    except WebSocketDisconnect:
        # Quando un utente si disconnette, lo rimuoviamo dalla stanza
        manager.disconnect(websocket, session_id)
        # Poi inviamo un messaggio a tutti nella stanza che l'utente si è disconnesso
        await manager.broadcast_to_session(session_id, {
            "event": "USER_LEFT",
            "message": "Un amico si è disconnesso dalla stanza."
        })