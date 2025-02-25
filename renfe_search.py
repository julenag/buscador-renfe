import os
import sys
import requests
import asyncio
import signal
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import asyncpg  # Para acceder a PostgreSQL


# --- Configuración de logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(script_dir, 'logs/renfe_search.log'))
    ]
)
logger = logging.getLogger(__name__)

# Variable global para el pool de conexiones a la BD
DB_POOL = None

# --- Funciones para la Base de Datos ---
async def init_db():
    global DB_POOL
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise Exception("DATABASE_URL no está configurada")
    DB_POOL = await asyncpg.create_pool(dsn=db_url)
    async with DB_POOL.acquire() as connection:
        await connection.execute('''
            CREATE TABLE IF NOT EXISTS user_preferences (
                id SERIAL PRIMARY KEY,
                chat_id TEXT NOT NULL,
                origen TEXT NOT NULL,
                destino TEXT NOT NULL,
                fecha DATE NOT NULL
            );
        ''')

        await connection.execute('''
            CREATE TABLE IF NOT EXISTS notifications (
                id SERIAL PRIMARY KEY,
                chat_id TEXT NOT NULL,
                origen TEXT NOT NULL,
                destino TEXT NOT NULL,
                fecha DATE NOT NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notificacion_enviada BOOLEAN DEFAULT false  -- Agregamos la columna
            );
        ''')


async def get_all_preferences():
    """
    Recupera todas las preferencias de la BD y las agrupa por chat_id.
    Cada registro se formatea para incluir el ID y la fecha en formato dd/mm/aaaa.
    """
    global DB_POOL
    prefs = {}
    try:
        async with DB_POOL.acquire() as connection:
            rows = await connection.fetch("SELECT id, chat_id, origen, destino, fecha FROM user_preferences")
            for row in rows:
                chat_id = row['chat_id']
                if chat_id not in prefs:
                    prefs[chat_id] = []
                prefs[chat_id].append({
                    'id': row['id'],
                    'origen': row['origen'],
                    'destino': row['destino'],
                    'fecha': row['fecha'].strftime("%d/%m/%Y") if row['fecha'] else ""
                })
    except Exception as e:
        logger.error(f"Error al obtener preferencias de la BD: {e}")
    return prefs

async def delete_preference_by_id(pref_id: int) -> bool:
    """Elimina de la BD una preferencia según su ID."""
    global DB_POOL
    try:
        async with DB_POOL.acquire() as connection:
            await connection.execute("DELETE FROM user_preferences WHERE id = $1", pref_id)
        return True
    except Exception as e:
        logger.error(f"Error al eliminar la preferencia ID {pref_id}: {e}")
        return False

async def save_notification_to_db(chat_id, origen, destino, fecha):
    """Guarda una notificación en la base de datos."""
    global DB_POOL
    try:
        fecha_formateada = fecha.strftime("%d/%m/%Y")
        message = f"🚄 ¡Hay trenes disponibles!\n\nOrigen: {origen}\nDestino: {destino}\nFecha: {fecha_formateada}"
        async with DB_POOL.acquire() as connection:
            await connection.execute('''
                INSERT INTO notifications (chat_id, origen, destino, fecha, message)
                VALUES ($1, $2, $3, $4, $5)
            ''', chat_id, origen, destino, fecha, message)
        logger.info(f"Notificación guardada para {chat_id}: {message}")
    except Exception as e:
        logger.error(f"Error al guardar notificación en la BD: {e}")

# --- Funciones relacionadas con Selenium ---
def create_driver():
    """Crea y configura el WebDriver de Chrome."""
    try:
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--window-size=1920,1080")

        chrome_options.binary_location = "/usr/bin/google-chrome"
        chromedriver_path = "/usr/bin/chromedriver"
        if not os.path.exists(chromedriver_path):
            raise FileNotFoundError("Chromedriver no encontrado en /usr/bin/chromedriver")

        service = Service(executable_path=chromedriver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        return driver
    except Exception as e:
        print(f"Error al crear webdriver: {e}")
        return None


async def consultar_renfe(origen, destino, fecha_deseada):
    """Realiza la consulta en Renfe y retorna True si hay billetes disponibles."""
    driver = None
    try:
        driver = create_driver()
        if not driver:
            return False

        driver.get("https://www.renfe.com/es/es")

        # Manejo de cookies
        try:
            cookie_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "onetrust-reject-all-handler"))
            )
            cookie_btn.click()
            logger.info("Cookies rechazadas.")
            await asyncio.sleep(1)
        except Exception as e:
            logger.warning(f"Error al manejar cookies: {e}")

        # Input de origen
        origen_input = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "origin"))
        )
        origen_input.clear()
        origen_input.send_keys(origen)
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "(//li[@role='option'])[1]"))
        ).click()
        logger.info("Origen seleccionado.")

        # Input de destino
        destino_input = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.ID, "destination"))
        )
        destino_input.clear()
        destino_input.send_keys(destino)
        await asyncio.sleep(0.5)
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "awesomplete_list_2_item_0"))
        ).click()
        logger.info("Destino seleccionado.")

        # Selección de fecha
        fecha_input = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "first-input"))
        )
        fecha_input.click()
        await asyncio.sleep(1)

        hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        fecha_obj = datetime.strptime(fecha_deseada, "%d/%m/%Y")
        dias_faltantes = (fecha_obj - hoy).days

        for _ in range(dias_faltantes):
            fecha_input.send_keys(Keys.ARROW_RIGHT)
            await asyncio.sleep(0.1)
        fecha_input.send_keys(Keys.ARROW_UP)
        logger.info("Fecha seleccionada.")

        # Botón Aceptar
        try:
            aceptar_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Aceptar')]"))
            )
            ActionChains(driver).move_to_element(aceptar_btn).click().perform()
            logger.info("Botón 'Aceptar' clicado.")
        except Exception as e:
            logger.warning(f"Error al clicar 'Aceptar': {e}")

        # Botón Buscar billete
        try:
            buscar_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@title='Buscar billete']"))
            )
            ActionChains(driver).move_to_element(buscar_btn).click().perform()
            logger.info("Botón 'Buscar billete' clicado.")
        except Exception as e:
            logger.error(f"Error al buscar billete: {e}")
            return False

        await asyncio.sleep(5)

        # Verificar disponibilidad
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "noDispoIda"))
            )
            logger.info("No hay billetes disponibles.")
            return False
        except Exception:
            logger.info("¡Billetes disponibles!")
            return True

    except Exception as e:
        logger.error(f"Error en consultar_renfe: {e}")
        return False
    finally:
        if driver:
            try:
                driver.quit()
            except Exception as e:
                logger.error(f"Error al cerrar driver: {e}")

async def run_search_loop():
    """Bucle principal que consulta periódicamente la disponibilidad."""
    while True:
        try:
            prefs = await get_all_preferences()
            for chat_id, solicitudes in prefs.items():
                for solicitud in solicitudes:
                    origen = solicitud.get("origen")
                    destino = solicitud.get("destino")
                    fecha_deseada = solicitud.get("fecha")

                    if not all([origen, destino, fecha_deseada]):
                        logger.warning(f"Parámetros inválidos para {chat_id}")
                        continue

                    logger.info(f"Verificando {chat_id}: {origen} - {destino} - {fecha_deseada}")

                    try:
                        # Consultar disponibilidad de billetes
                        if await consultar_renfe(origen, destino, fecha_deseada):
                            # Si hay billetes disponibles, guardar la notificación en la BD
                            await save_notification_to_db(
                                chat_id,
                                origen,
                                destino,
                                datetime.strptime(fecha_deseada, "%d/%m/%Y")
                            )
                            # Eliminar la preferencia una vez que se ha encontrado un billete
                            await delete_preference_by_id(solicitud['id'])
                    except Exception as e:
                        logger.error(f"Error procesando {chat_id}: {e}")

            logger.info("Ciclo de búsqueda completado.")
            await asyncio.sleep(30)

        except Exception as e:
            logger.error(f"Error en el bucle principal: {e}")
            await asyncio.sleep(300)


async def main():
    try:
        terminate_other_instances()
        await asyncio.sleep(5)

        if not check_lock():
            logger.error("Otra instancia en ejecución. Saliendo.")
            return

        if not create_lock():
            logger.error("Error creando lock file. Saliendo.")
            return

        # Inicializar la conexión a la BD
        await init_db()

        logger.info(f"Iniciando servicio con PID {os.getpid()}")
        await run_search_loop()

    except Exception as e:
        logger.error(f"Error fatal: {e}")
    finally:
        cleanup()

if __name__ == '__main__':
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(main())  # Agregar la tarea principal al bucle de eventos actual
        loop.run_forever()  # Mantener el ciclo de eventos ejecutándose
    except (KeyboardInterrupt, SystemExit):
        logger.info("Interrupción recibida, saliendo...")
    finally:
        cleanup()
