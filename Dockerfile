# Usar la imagen oficial de Selenium con Chrome preinstalado
FROM selenium/standalone-chrome:latest

# Cambiar a usuario root para instalar paquetes del sistema
USER root

# Instalar dependencias de Python y herramientas de compilación
RUN apt-get update && apt-get install -y python3-pip build-essential python3-dev && apt-get clean

# Establecer el directorio de trabajo
WORKDIR /app

# Copiar el archivo requirements.txt y el código fuente a la imagen
COPY requirements.txt /app/requirements.txt
COPY . /app

# Instalar las dependencias de Python (usa python3 para evitar confusiones)
RUN python3 -m pip install --no-cache-dir -r requirements.txt

# Comando para ejecutar el script principal
CMD ["python3", "renfe_search.py"]
