# Usar la imagen oficial de Selenium con Chrome preinstalado
FROM selenium/standalone-chrome:latest

# Cambiar a usuario root para instalar paquetes del sistema
USER root

# Actualizar e instalar python3-pip, herramientas de compilación y librerías de desarrollo
RUN apt-get update && apt-get install -y \
    python3-pip \
    build-essential \
    python3-dev \
    libffi-dev \
    libssl-dev \
    libxml2-dev \
    libxslt1-dev \
    && apt-get clean

# Actualizar pip a la versión más reciente
RUN python3 -m pip install --upgrade pip

# Establecer el directorio de trabajo
WORKDIR /app

# Copiar el archivo requirements.txt y el código fuente a la imagen
COPY requirements.txt /app/requirements.txt
COPY . /app

# (Opcional) Mostrar el contenido de requirements.txt para ver qué se está instalando
RUN cat requirements.txt

# Instalar las dependencias de Python (modo verbose para mayor detalle en los logs)
RUN python3 -m pip install --no-cache-dir -v -r requirements.txt

# Comando para ejecutar el script principal
CMD ["python3", "renfe_search.py"]
