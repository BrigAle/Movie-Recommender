import os
import time
import json
import pika
from pymongo import MongoClient
from neo4j import GraphDatabase

# --- CONFIGURAZIONI ---
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongodb:27017")   # Connessione a MongoDB (default: mongodb://mongodb:27017)
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")         # Connessione a Neo4j (default: bolt://neo4j:7687)
NEO4J_USER = "neo4j"                                            # Username per Neo4j (deve coincidere con il docker-compose)
NEO4J_PASSWORD = "password_sicurissima"                         # Deve coincidere con il docker-compose

# Connessione a MongoDB
mongo_client = MongoClient(MONGO_URI)                           # Apertura connessione verso MongoDB
mongo_db = mongo_client["movie_raw_db"]                         # Selezione del database, se non esiste, MongoDB lo crea automaticamente
mongo_collection = mongo_db["popular_movies"]                   # Selezione della collezione, se non esiste, MongoDB la crea automaticamente

# Connessione a Neo4j
neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))       # Apertura connessione verso Neo4j

def save_to_graph(movie_data):
    """Estrae i dati utili dal JSON di Mongo e li mappa nel Grafo Neo4j con i Nomi dei Generi"""
    movie_id = movie_data.get("id")
    title = movie_data.get("title", "Titolo Sconosciuto")
    vote_average = movie_data.get("vote_average", 0.0)
    overview = movie_data.get("overview", "")
    genre_ids = movie_data.get("genre_ids", [])

    # --- RECUPERO NOMI DEI GENERI DA MONGO ---
    genres_list_for_neo4j = []
    for g_id in genre_ids:
        # Cerchiamo il nome del genere nella collezione 'genres' che ha popolato l'ingestion
        genre_doc = mongo_db["genres"].find_one({"id": g_id})
        genre_name = genre_doc["name"] if genre_doc else "Sconosciuto"
        
        # Creiamo un dizionarietto con ID e Nome da passare a Neo4j
        genres_list_for_neo4j.append({"id": g_id, "name": genre_name})
    # ------------------------------------------------------

    # Aggiorniamo la query Cypher per accettare la lista di oggetti (ID + Nome)
    query = """
    MERGE (m:Movie {id: $movie_id})
    SET m.title = $title,
        m.vote_average = $vote_average,
        m.overview = $overview
    WITH m
    UNWIND $genres_list AS g_data
    MERGE (g:Genre {id: g_data.id})
    SET g.name = g_data.name
    MERGE (m)-[:BELONGS_TO]->(g)
    """

    with neo4j_driver.session() as session:
        try:
            # Passiamo 'genres_list_for_neo4j' alla query
            session.run(query, movie_id=movie_id, title=title, vote_average=vote_average, 
                        overview=overview, genres_list=genres_list_for_neo4j)
            print(f"🌲 [Neo4j] Mappato nel grafo: '{title}' con i rispettivi generi testuali.")
        except Exception as e:
            print(f"❌ Errore durante l'inserimento in Neo4j: {e}")
            
def callback(ch, method, properties, body):
    try:
        # 1. Riceve e decodifica il messaggio da RabbitMQ
        data = json.loads(body.decode())
        movie_id = data.get("movie_id")
        print(f"\n📥 [RabbitMQ] Ricevuto segnale per il film ID: {movie_id}")

        # 2. Interroga MongoDB per estrarre il JSON grezzo completo
        movie_data = mongo_collection.find_one({"id": movie_id})

        if movie_data:
            # 3. Mappa il film e i generi nel Grafo Neo4j
            save_to_graph(movie_data)
        else:
            print(f"⚠️ Film ID {movie_id} non trovato su MongoDB.")

        # 4. Invia la ricevuta di ritorno a RabbitMQ
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        print(f"❌ Errore nell'elaborazione del messaggio: {e}")

def main():
    print("🚀 [Processing Service] In ascolto su RabbitMQ. In attesa di messaggi...")
    
    # Connessione a RabbitMQ
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='rabbitmq'))
    channel = connection.channel()
    
    channel.queue_declare(queue='movie_queue', durable=True)
    
    # Dice a RabbitMQ di non dare più di un messaggio alla volta a questo worker
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue='movie_queue', on_message_callback=callback)

    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        channel.stop_consuming()
        connection.close()
        neo4j_driver.close()

if __name__ == "__main__":
    main()