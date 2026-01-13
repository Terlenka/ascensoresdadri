FROM python:3.11-slim

WORKDIR /app

# Instalamos solo lo estrictamente necesario para compilar paquetes de Python
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY . .

# Instalamos las librerías de Python (streamlit y pandas)
RUN pip3 install --no-cache-dir -r requirements.txt

EXPOSE 8501

# Comando para arrancar la app
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
