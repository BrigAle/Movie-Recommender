FROM python:3.10-slim

WORKDIR /app

# Copia e installa le dipendenze per sfruttare la cache di Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia il resto del codice sorgente
COPY . .

# Comunichiamo che il container ascolterà sulla porta 8000
EXPOSE 8000

# Avviamo uvicorn con il --reload attivo (si aggiorna da solo se modifichi il file main.py!)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
