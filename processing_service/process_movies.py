import pika
import json
import os
import sys
from pymongo import MongoClient

# Connessione a MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017")
mongo_client = MongoClient(MONGO_URI)
raw_db = mongo_client["movie_raw_db"]
raw_collection = raw_db["popular_movies"]

def process_movie_data(movie_id):
    """Va a prendere il film grezzo su MongoDB e lo analizza"""
    # Cerchiamo il film nel database NoSQL tramite il suo ID
    movie = raw_collection.find_one({"id": movie_id})
    
    if movie:
        print(f"\n🎬 [Elaborazione] Analizzo il film: {movie.get('title')}")
        print(f"📈 Punteggio medio: {movie.get('vote_average')}")
        print(f"📝 Sinonimo di trama (anteprima): {movie.get('overview')[:80]}...")
        # Qui in futuro scatterà l'algoritmo di raccomandazione!
    else:
        print(f"⚠️ [Attenzione] Film con ID {movie_id} non trovato in MongoDB grezzo.")

def callback(ch, method, properties, body):
    """Funzione che si attiva ogni volta che arriva un messaggio nella coda"""
    try:
        # Decodifichiamo il JSON del messaggio
        message = json.loads(body.decode())
        movie_id = message.get("movie_id")
        
        print(f"📥 [RabbitMQ] Ricevuto segnale per il film ID: {movie_id}")
        
        # Elaboriamo il dato
        process_movie_data(movie_id)
        
        # Diciamo a RabbitMQ che abbiamo elaborato il messaggio con successo.
        # Questo rimuove definitivamente il messaggio dalla coda (Acknowledge)
        ch.basic_ack(delivery_tag=method.delivery_tag)
        
    except Exception as e:
        print(f"❌ Errore durante l'elaborazione del messaggio: {e}")

def main():
    # Connessione a RabbitMQ
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
        channel = connection.channel()
        
        # Dichiariamo la stessa coda dell'ingestion
        channel.queue_declare(queue='movie_queue', durable=True)
        
        # Diciamo a RabbitMQ di non inviare più di un messaggio alla volta a questo worker
        # se non ha ancora finito di elaborare il precedente (Fair Dispatch)
        channel.basic_qos(prefetch_count=1)
        
        # Associano la coda alla nostra funzione di callback
        channel.basic_consume(queue='movie_queue', on_message_callback=callback)
        
        print("🚀 [Processing Service] In ascolto su RabbitMQ. In attesa di messaggi... Per uscire premi CTRL+C")
        channel.start_consuming()
        
    except Exception as e:
        print(f"❌ Errore di connessione al broker: {e}")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('👋 Servizio interrotto.')
        try:
            sys.exit(0)
        except SystemExit:
            os._exit(0)