# Usar la imagen oficial de Python 3.11
FROM python:3.11-slim

# Cambiar a usuario root para instalar paquetes del sistema
USER root

# Actualizar e instalar python3-pip, herramientas de compilación y librerías de desarrollo necesarias
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    libffi-dev \
    libssl-dev \
    libxml2-dev \
    libxslt1-dev \
    lsb-release \
    && apt-get clean

# Establecer el directorio de trabajo
WORKDIR /app

# Copiar el archivo requirements.txt y el resto del código fuente a la imagen
COPY requirements.txt /app/requirements.txt
COPY . /app

# Verificar que pip está instalado correctamente y qué versiones de Python y pip están disponibles
RUN python3 --version
RUN python3 -m pip --version

# Crear un archivo de log vacío antes de intentar instalar las dependencias
RUN touch install.log

# Instalar las dependencias de Python y redirigir los logs a install.log
RUN python3 -m pip install --no-cache-dir -v -r requirements.txt > install.log 2>&1 || (cat install.log && exit 1)

# Comando para ejecutar el script principal
CMD ["python3", "renfe_search.py"]
