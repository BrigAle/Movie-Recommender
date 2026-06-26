import os           #lettura chiavi API in env o docker-compose
import requests     #libreria per fare richieste HTTP
import time         
import json         #Modulo per lavorare con JSON
import pika         #driver python per connessione a RabbitMQ 
from dotenv import load_dotenv  #import per leggere le variabili d'ambiente da un file .env
from pymongo import MongoClient #driver python per connessione a MongoDB

load_dotenv()       #Carica le variabili d'ambiente dal file .env

API_KEY = os.getenv("TMDB_API_KEY")         #Chiave API per TMDb
BASE_URL = "https://api.themoviedb.org/3"   #Indirizzo base per le richieste all'API di TMDb

# Configurazione MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017")   # Connessione a MongoDB (default: mongodb://mongodb:27017)
client = MongoClient(MONGO_URI)     #Apertura connessione verso MongoDB
db = client["movie_raw_db"]         #Selezione del database, se non esiste, MongoDB lo crea automaticamente
collection = db["popular_movies"]   #Selezione della collezione, se non esiste, MongoDB la crea automaticamente   

# Funzione per inviare l'id del film nella coda di RabbitMQ
def send_to_queue(movie_id):
    try:
        # Ci connettiamo a RabbitMQ usando il nome del servizio nel compose
        connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq')) #Apre una connessione sincrona verso RabbitMQ
        channel = connection.channel()  #Crea un canale di comunicazione con RabbitMQ
        
        # Dichiariamo la coda (se non esiste, viene creata)
        channel.queue_declare(queue='movie_queue', durable=True) #Significa che la coda sopravvive al riavvio del broker
        
        # Creiamo il payload del messaggio (inviamo l'ID e l'azione)
        payload = {"movie_id": movie_id, "action": "PROCESS"}  #In questo caso, inviamo solo l'ID del film e un'azione da eseguire, PROCESS significa che il film deve essere processato dal servizio di elaborazione
        message = json.dumps(payload)   #Convertiamo il payload in una stringa JSON per l'invio a RabbitMQ
        
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
    
    print("🏷️ [Ingestion] Recupero della mappa dei generi da TMDb...")
    genres_collection = db["genres"]

    genres_url = f"{BASE_URL}/genre/movie/list?api_key={API_KEY}&language=it-IT"
    try:
        genres_response = requests.get(genres_url)
        genres_data = genres_response.json()
        
        # Salviamo ogni genere su MongoDB
        for genre in genres_data.get("genres", []):
            # genre è un dizionario tipo: {"id": 28, "name": "Azione"}
            genres_collection.update_one({"id": genre["id"]}, {"$set": genre}, upsert=True)
        print("✅ [Ingestion] Mappa dei generi salvata con successo su MongoDB.")
    except Exception as e:
        print(f"❌ Errore durante il recupero dei generi: {e}")
   
    endpoint = f"{BASE_URL}/movie/popular"
    params = {"api_key": API_KEY, "language": "it-IT", "page": 1}

    try:
        print("\n🔄 Richiesta dati a TMDb...")
        response = requests.get(endpoint, params=params)    #Effettua la richiesta HTTP alla API di TMDb
        
        if response.status_code == 200:
            data = response.json()  #Decodifica la risposta JSON in un dizionario Python
            movies = data.get("results", [])    #movies è una lista di dizionari, ognuno rappresenta un film con i suoi dettagli
            
            print(f"📥 Ricevuti {len(movies)} film. Inizio salvataggio e accodamento...")
            
            for movie in movies:
                # 1. Salva/Aggiorna su MongoDB
                collection.update_one(
                    {"id": movie["id"]},
                    {"$set": movie},
                    upsert=True #Se il documento con l'ID del film non esiste, lo crea; altrimenti, aggiorna i campi esistenti
                )
                
                # 2. Invia l'ID del film a RabbitMQ per la successiva elaborazione
                send_to_queue(movie["id"])
            
            print("✅ Ciclo completato con successo!")
                
        else:
            print(f"❌ Errore TMDb: {response.status_code}")

    except Exception as e:
        print(f"❌ Errore durante la pipeline: {e}")

if __name__ == "__main__": #Se il file è eseguito come script principale, allora esegue il codice sottostante
    print("🚀 Ingestion Service con MongoDB e RabbitMQ avviato!")
    while True: #Ciclo infinito per eseguire periodicamente ogni 60 secondi la funzione di fetch e salvataggio dei film
        fetch_and_save_movies()
        print("😴 Prossimo aggiornamento tra 60 secondi...")
        time.sleep(60)