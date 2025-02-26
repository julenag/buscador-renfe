# Usar la imagen oficial de Selenium con Chrome preinstalado
FROM selenium/standalone-chrome:latest

# Cambiar a usuario root para instalar paquetes del sistema
USER root

# Actualizar e instalar python3-pip, herramientas de compilación y librerías de desarrollo necesarias
RUN apt-get update && apt-get install -y \
    python3-pip \
    build-essential \
    python3-dev \
    libffi-dev \
    libssl-dev \
    libxml2-dev \
    libxslt1-dev \
    lsb-release \
    && apt-get clean

# (Omitir la actualización de pip, ya que puede generar errores en este entorno)
# RUN python3 -m pip install --upgrade pip setuptools wheel

# Establecer el directorio de trabajo
WORKDIR /app

# Copiar el archivo requirements.txt y el código fuente a la imagen
COPY requirements.txt /app/requirements.txt
COPY . /app

# Instalar las dependencias de Python (modo verbose para obtener más detalles en los logs)
RUN python3 -m pip install --no-cache-dir -v -r requirements.txt

# Comando para ejecutar el script principal
CMD ["python3", "renfe_search.py"]
