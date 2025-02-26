# Usar la imagen oficial de Selenium con Chrome preinstalado
FROM selenium/standalone-chrome:latest

# Cambiar a usuario root para instalar paquetes del sistema
USER root

# Actualizar e instalar python3-pip, herramientas de compilación y dependencias necesarias
RUN apt-get update && apt-get install -y \
    python3-pip \
    build-essential \
    python3-dev \
    && apt-get clean

# Actualizar pip y setuptools
RUN pip install --upgrade pip setuptools

# Establecer el directorio de trabajo
WORKDIR /app

# Copiar el archivo requirements.txt y el código fuente
COPY requirements.txt /app/requirements.txt
COPY . /app

# Instalar las dependencias de Python en modo verbose para más detalles en los logs
RUN echo "Instalando dependencias de Python..." && \
    pip install --no-cache-dir -v -r requirements.txt

# Comando para ejecutar el script principal
CMD ["python", "renfe_search.py"]

