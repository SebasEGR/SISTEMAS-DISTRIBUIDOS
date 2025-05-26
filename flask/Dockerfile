# Usa Python 3.10 con Debian 11 (bullseye) como base
FROM python:3.10-bullseye

# 1. Instala dependencias del sistema
RUN apt-get update && apt-get install -y \
    g++ \
    unixodbc-dev \
    unixodbc \
    curl \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# 2. Configura el repositorio de Microsoft (método actualizado sin apt-key)
RUN curl -sSL https://packages.microsoft.com/keys/microsoft.asc > /etc/apt/trusted.gpg.d/microsoft.asc \
    && echo "deb [arch=amd64] https://packages.microsoft.com/debian/11/prod bullseye main" > /etc/apt/sources.list.d/mssql-release.list

# 3. Instala el driver ODBC
RUN apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
    && apt-get clean

# 4. Configura el entorno de la aplicación
WORKDIR /app
COPY requirements.txt .

# Instalar las dependencias de Python (asegúrate de que 'requirements.txt' tenga las librerías necesarias como flask, flask-jwt-extended, etc.)
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo el código de la aplicación al contenedor
COPY . .

# Configuración de uWSGI (si usas uWSGI como servidor)
CMD ["uwsgi", "app.ini"]
