# Renfe Ticket Availability Notifier

Este script automatiza la búsqueda de billetes disponibles en Renfe para varios usuarios, leyendo sus preferencias desde un CSV público de Google Sheets. 
Esto permite compartir el archivo de Google Sheets para que otras personas lo modifiquen y puedan recibir alertas para los trenes que les interesan.
Si detecta disponibilidad para alguna ruta y fecha, envía una notificación vía Telegram a los usuarios correspondientes.

---
## Cómo funciona

- El script descarga un CSV público que debe estar alojado en Google Sheets y compartido con las personas que quieras que puedan usar las alertas.
- Cada persona que tenga acceso al CSV puede agregar sus preferencias de viajes con su `chat_id` de Telegram para recibir alertas personalizadas.
- El script procesa todas las solicitudes, consulta disponibilidad y notifica solo si hay billetes.
- Está pensado para ejecutarse de forma periódica (por ejemplo, cada hora o cada día) usando un programador de tareas, de modo que las alertas se actualicen y envíen automáticamente.

---
## Características del script

- Descarga un CSV público con las preferencias de viaje de los usuarios.
- Convierte el CSV a JSON para facilitar la gestión interna.
- Automatiza la consulta en la web de Renfe usando Selenium en modo headless.
- Envía notificaciones por Telegram cuando hay billetes disponibles.
- Evita notificaciones repetidas para la misma búsqueda.

---

# Configuración

1. **Token de Telegram**

   Crea un bot en Telegram con [@BotFather](https://t.me/BotFather) y copia el token.

2. **Google Sheets público**

   Crea un Google Sheets con las columnas:

   - `chat_id`: ID del chat Telegram del usuario.
   - `origen`: ciudad o estación de origen.
   - `destino`: ciudad o estación de destino.
   - `fecha`: fecha del viaje en formato `DD/MM/YYYY`.

   Publica la hoja y copia la URL para exportar en formato CSV:
    https://docs.google.com/spreadsheets/d/ID_DE_TU_HOJA/export?format=csv

3. **Editar el script**

En el script `renfe_notifier.py`, modifica:

```python
BOT_TOKEN = 'TU_TOKEN_DE_TELEGRAM_AQUI'
SHEET_CSV_URL = "URL_PUBLICA_DE_TU_CSV"```


---

## Requisitos

- Python 3.8+
- Google Chrome instalado (compatible con el ChromeDriver)
- ChromeDriver en el PATH (o ruta configurada)
- Librerías Python:
  - `selenium`
  - `requests`

Instalación rápida de dependencias:

```bash
pip install selenium requests
