FROM python:3.12-slim

# Instalación de dependencias y Google Chrome
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    gnupg2 \
    ca-certificates \
    libx11-dev \
    libx11-xcb1 \
    libxcomposite1 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libnss3 \
    libxss1 \
    libappindicator3-1 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libgtk-3-0 \
    libdbus-1-3 \
    libxtst6 \
    libgbm-dev \
    xdg-utils \
    --no-install-recommends \
    && wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] https://dl.google.com/linux/chrome/deb/ stable main" | tee -a /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable

# Establecer el directorio de trabajo
WORKDIR /app

# Copiar los archivos de dependencias
COPY requirements.txt .

# Instalar dependencias de Python
RUN python3 -m pip install --no-cache-dir -r requirements.txt

# Copiar el código del proyecto
COPY . .

# Crear el directorio de logs
RUN mkdir -p /app/logs

# Establecer el comando para ejecutar el script
CMD ["python3", "renfe_search.py"]
