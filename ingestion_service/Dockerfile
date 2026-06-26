# 1. Usa un'immagine base ufficiale di Python leggera (basata su Alpine Linux)
FROM python:3.11-slim

# 2. Imposta la cartella di lavoro interna al container
WORKDIR /app

# 3. Copia il file dei requisiti nel container
COPY requirements.txt .

# 4. Installa le dipendenze dentro il container
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copia il resto del codice della cartella corrente dentro /app
COPY . .

# 6. Comando di avvio: esegue lo script quando il container parte
CMD ["python", "fetch_movies.py"]