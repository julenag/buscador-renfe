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

# (Omitir la actualización de pip, setuptools y wheel si falla)
# RUN python3 -m pip install --upgrade pip setuptools wheel

# Establecer el directorio de trabajo
WORKDIR /app

# Copiar el archivo requirements.txt y el código fuente a la imagen
COPY requirements.txt /app/requirements.txt
COPY . /app

# Instalar las dependencias de Python (modo verbose para más detalles en los logs)
RUN python3 -m pip install --no-cache-dir -v -r requirements.txt

# Comando para ejecutar el script principal
CMD ["python3", "renfe_search.py"]
