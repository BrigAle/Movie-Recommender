# Movie Recommender Pipeline - Phase 1: Asynchronous Data Ingestion

An event-driven, microservices-based data pipeline designed to ingest, store, and process movie metadata in real-time. This project leverages **Docker Compose** to orchestrate isolated containers running **Python**, **MongoDB**, and **RabbitMQ**, implementing a decoupled architectural pattern.

## 🏗️ Architecture Overview

The system is split into independent, decoupled components to ensure high scalability, fault tolerance, and separation of concerns:

1. **Ingestion Service (Publisher)**: A Python service that fetches popular movie metadata from the TMDb (The Movie Database) API at regular intervals (every 60 seconds).
2. **Raw Data Store (MongoDB)**: A NoSQL database that acts as a staging area, storing the raw JSON payloads using an `upsert` strategy to prevent duplicates.
3. **Message Broker (RabbitMQ)**: A resilient message queue that receives lightweight events (`movie_id`) from the Ingestion Service, ensuring asynchronous communication.
4. **Processing Service (Consumer)**: A worker service that stays connected to RabbitMQ, consumes incoming events, fetches the corresponding full payload from MongoDB, and prepares the data for the recommendation engine.

---

## 🛠️ Tech Stack

* **Language:** Python 3.11
* **Containerization & Orchestration:** Docker / Docker Compose
* **Database (NoSQL):** MongoDB 6.0
* **Message Broker:** RabbitMQ 3.13 (with Management Plugin)
* **Libraries:** `requests`, `pymongo`, `pika`, `python-dotenv`

---

## 📂 Project Structure

```text
movie-recommender-pipeline/
│
├── ingestion_service/
│   ├── .env                 # Local API Keys (Git ignored)
│   ├── Dockerfile           # Python Ingestion environment
│   ├── requirements.txt     # Ingestion dependencies
│   └── fetch_movies.py      # Publisher script
│
├── processing_service/
│   ├── Dockerfile           # Python Worker environment
│   ├── requirements.txt     # Worker dependencies
│   └── process_movies.py    # Consumer script
│
├── .gitignore               # Safe-guard for credentials and caches
└── docker-compose.yml       # Infrastructure orchestration recipe# Movie-Recommender
