# Usar una imagen base de Python
FROM python:3.11-slim

# Instalación de dependencias del sistema para Google Chrome y ChromeDriver
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    unzip \
    ca-certificates \
    fonts-liberation \
    libappindicator3-1 \
    libasound2 \
    libxss1 \
    libgdk-pixbuf2.0-0 \
    libnss3 \
    libxtst6 \
    xdg-utils \
    google-chrome-stable \
    && apt-get clean

# Instalar ChromeDriver
RUN CHROME_DRIVER_VERSION=$(curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE) && \
    wget https://chromedriver.storage.googleapis.com/${CHROME_DRIVER_VERSION}/chromedriver_linux64.zip && \
    unzip chromedriver_linux64.zip && \
    mv chromedriver /usr/bin/ && \
    chmod +x /usr/bin/chromedriver

# Crear y establecer el directorio de trabajo
WORKDIR /app

# Copiar el archivo requirements.txt y el código fuente
COPY requirements.txt /app/requirements.txt
COPY . /app

# Instalar las dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Crear un directorio de logs para la aplicación
RUN mkdir /app/logs

# Exponer el puerto si es necesario (en caso de que tengas algún servicio web, como Flask o FastAPI)
# EXPOSE 8000

# Establecer las variables de entorno necesarias
# Aquí se asume que DATABASE_URL se establece en el entorno o archivo .env
# ENV DATABASE_URL=postgres://usuario:contraseña@localhost:5432/renfe_db

# Ejecutar el script principal con Python
CMD ["python", "renfe_search.py"]
