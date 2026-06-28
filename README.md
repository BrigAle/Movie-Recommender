# Movie Recommender Pipeline & Real-Time Matcher

An event-driven, microservices-based data pipeline and real-time synchronization platform designed to ingest, process, and vote on movie metadata. This ecosystem leverages **Docker Compose** to orchestrate isolated containers running **Python (FastAPI)**, **Node.js (React)**, **MongoDB**, **Neo4j**, and **RabbitMQ**, implementing a decoupled and polyglot persistence architectural pattern.

## 🏗️ Architecture Overview

The system is split into independent, decoupled microservices to ensure high scalability, fault tolerance, and clear separation of concerns:

1. **Ingestion Service (Publisher)**: A Python service that fetches popular movie metadata from the TMDb (The Movie Database) API at regular intervals and handles scheduling.
2. **Raw Data Store (MongoDB)**: A NoSQL database acting as a staging area, storing the raw JSON payloads using an `upsert` strategy to prevent duplicates.
3. **Message Broker (RabbitMQ)**: A resilient message queue that receives lightweight events (`movie_id`) from the Ingestion Service, ensuring asynchronous communication.
4. **Processing Service (Consumer)**: A worker service connected to RabbitMQ that consumes incoming events, fetches payloads from MongoDB, and populates the graph engine.
5. **Graph Database (Neo4j)**: A graph-oriented database used to map complex relationships between movies, genres, users, and real-time matches.
6. **API Gateway (FastAPI)**: The central brain of the ecosystem. It connects to MongoDB and Neo4j, exposes standard REST endpoints for data consumption, and implements **WebSockets** with a stateful `ConnectionManager` to handle real-time, bidirectional communication for room-based swiping sessions.
7. **Client Application (React + Vite)**: A dynamic user interface that fetches standard data via HTTP and hooks into the API Gateway's WebSocket server to synchronize real-time voting sessions across users.

---

## 🛠️ Tech Stack Expansion

* **Languages & Runtimes:** Python 3.11, Node.js 20 (Alpine)
* **Containerization & Orchestration:** Docker / Docker Compose
* **Polyglot Persistence:** MongoDB 8.0 & Neo4j 5.12 (Community Edition)
* **Message Broker:** RabbitMQ 3.13 (with Management Plugin)
* **Web Framework & Server:** FastAPI / Uvicorn
* **Frontend Setup:** React / Vite / Tailwind CSS

---

## 📂 Project Structure

```text
Movie-Recommender/
│
├── api_gateway/
│   ├── Dockerfile           # FastAPI environment
│   ├── requirements.txt     # Uvicorn, FastAPI, Pymongo, Neo4j, Websockets
│   └── main.py              # Central Gateway & WebSocket logic
│
├── movie-frontend/
│   ├── Dockerfile           # Node production/dev image
│   ├── package.json         # React dependencies (Vite, Tailwind)
│   ├── src/                 # Application components and styles
│   └── index.html           
│
├── ingestion_service/
│   ├── Dockerfile           # Python Ingestion environment
│   ├── requirements.txt     # Ingestion dependencies
│   └── fetch_movies.py      # Publisher script
│
├── processing_service/
│   ├── Dockerfile           # Python Worker environment
│   ├── requirements.txt     # Worker dependencies
│   └── process_movies.py    # Consumer script
│
└── docker-compose.yml       # Infrastructure orchestration recipe (8 services total)