import os
import requests
import time
import json
import pika  # <-- Nuovo Import
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

API_KEY = os.getenv("TMDB_API_KEY")
BASE_URL = "https://api.themoviedb.org/3"

# Configurazione MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017")
client = MongoClient(MONGO_URI)
db = client["movie_raw_db"]
collection = db["popular_movies"]

# Funzione per inviare un messaggio a RabbitMQ
def send_to_queue(movie_id):
    try:
        # Ci connettiamo a RabbitMQ usando il nome del servizio nel compose
        connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
        channel = connection.channel()
        
        # Dichiariamo la coda (se non esiste, viene creata)
        channel.queue_declare(queue='movie_queue', durable=True)
        
        # Creiamo il payload del messaggio (inviamo l'ID e l'azione)
        payload = {"movie_id": movie_id, "action": "PROCESS"}
        message = json.dumps(payload)
        
        # Pubblichiamo il messaggio nella coda
        channel.basic_publish(
            exchange='',
            routing_key='movie_queue',
            body=message,
            properties=pika.BasicProperties(
                delivery_mode=2,  # Rende il messaggio persistente sul disco di RabbitMQ
            )
        )
        print(f"📨 [RabbitMQ] Messaggio inviato per il film ID: {movie_id}")
        connection.close()
    except Exception as e:
        print(f"❌ Errore nell'invio a RabbitMQ: {e}")

def fetch_and_save_movies():
    if not API_KEY:
        print("❌ Errore: TMDB_API_KEY non trovata!")
        return

    endpoint = f"{BASE_URL}/movie/popular"
    params = {"api_key": API_KEY, "language": "it-IT", "page": 1}

    try:
        print("\n🔄 Richiesta dati a TMDb...")
        response = requests.get(endpoint, params=params)
        
        if response.status_code == 200:
            data = response.json()
            movies = data.get("results", [])
            
            print(f"📥 Ricevuti {len(movies)} film. Inizio salvataggio e accodamento...")
            
            for movie in movies:
                # 1. Salva/Aggiorna su MongoDB
                collection.update_one(
                    {"id": movie["id"]},
                    {"$set": movie},
                    upsert=True
                )
                
                # 2. Invia l'ID del film a RabbitMQ per la successiva elaborazione
                send_to_queue(movie["id"])
            
            print("✅ Ciclo completato con successo!")
                
        else:
            print(f"❌ Errore TMDb: {response.status_code}")

    except Exception as e:
        print(f"❌ Errore durante la pipeline: {e}")

if __name__ == "__main__":
    print("🚀 Ingestion Service con MongoDB e RabbitMQ avviato!")
    while True:
        fetch_and_save_movies()
        print("😴 Prossimo aggiornamento tra 60 secondi...")
        time.sleep(60)