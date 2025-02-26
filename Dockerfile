# Usar una imagen base de Python
FROM python:3.11-slim

# Instalación de dependencias del sistema
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
    gnupg2 \
    lsb-release \
    && apt-get clean

# Instalar Google Chrome directamente desde el repositorio de Google
RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    apt-get update && \
    apt-get install -y ./google-chrome-stable_current_amd64.deb && \
    rm google-chrome-stable_current_amd64.deb && \
    apt-get clean

# Verificar la versión de Google Chrome instalada
RUN google-chrome-stable --version

# Descargar e instalar ChromeDriver compatible con la versión actual de Google Chrome
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

# Ejecutar el script principal con Python
CMD ["python", "renfe_search.py"]
