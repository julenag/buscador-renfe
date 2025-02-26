import requests
import time
import asyncio
import signal
import os
import logging
import sys
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
import asyncpg
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

BOT_TOKEN = '8088144724:AAEAhC1CZbq6Dtd_hJEZoNdKml58z0h0vlM' 
LOCK_FILE = os.path.join('data', 'renfe_search.lock')

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/renfe_search.log')
    ]
)
logger = logging.getLogger(__name__)

async def get_db_connection():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise Exception("DATABASE_URL no está configurada")
    return await asyncpg.create_pool(dsn=db_url)

async def load_preferences():
    """Carga las preferencias de los usuarios desde la base de datos."""
    try:
        db_pool = await get_db_connection()
        async with db_pool.acquire() as connection:
            result = await connection.fetch('''
                SELECT chat_id, origen, destino, fecha FROM user_preferences
            ''')
            prefs = {}
            for row in result:
                if row['chat_id'] not in prefs:
                    prefs[row['chat_id']] = []
                prefs[row['chat_id']].append({
                    'origen': row['origen'],
                    'destino': row['destino'],
                    'fecha': row['fecha'].strftime("%d/%m/%Y")
                })
            return prefs
    except Exception as e:
        logger.error(f"Error cargando preferencias: {e}")
        return {}

async def save_preferences(prefs):
    """Guardar las preferencias en la base de datos."""
    try:
        db_pool = await get_db_connection()
        async with db_pool.acquire() as connection:
            for chat_id, solicitudes in prefs.items():
                for solicitud in solicitudes:
                    # Aquí puedes guardar o actualizar las preferencias si es necesario
                    await connection.execute('''
                        INSERT INTO user_preferences (chat_id, origen, destino, fecha)
                        VALUES ($1, $2, $3, $4)
                        ON CONFLICT (chat_id, origen, destino, fecha) DO NOTHING
                    ''', chat_id, solicitud['origen'], solicitud['destino'], solicitud['fecha'])
            return True
    except Exception as e:
        logger.error(f"Error guardando preferencias: {e}")
        return False

def terminate_other_instances():
    """Terminate other instances of this script"""
    current_pid = os.getpid()
    try:
        import psutil
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] == 'python' and 'renfe_search.py' in ' '.join(proc.info['cmdline'] or []):
                    if proc.info['pid'] != current_pid:
                        logger.info(f"Terminating other instance with PID {proc.info['pid']}")
                        try:
                            proc.terminate()
                            proc.wait(timeout=3)  # Wait for graceful termination
                        except psutil.TimeoutExpired:
                            logger.warning(f"Force killing process {proc.info['pid']}")
                            proc.kill()  # Force kill if graceful termination fails
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                logger.error(f"Error handling process: {e}")
                continue
    except ImportError:
        logger.warning("psutil not available, skipping process termination")

def check_lock():
    """Check if another instance is running"""
    try:
        if os.path.exists(LOCK_FILE):
            with open(LOCK_FILE, 'r') as f:
                stored_pid = int(f.read().strip())
                current_pid = os.getpid()

                if stored_pid == current_pid:
                    logger.info("Lock file belongs to current process")
                    return True

                try:
                    os.kill(stored_pid, 0)
                    logger.warning(f"Another instance is running with PID {stored_pid}")
                    return False
                except OSError:
                    logger.info(f"Removing stale lock file for PID {stored_pid}")
                    os.remove(LOCK_FILE)
        return True
    except Exception as e:
        logger.error(f"Error checking lock file: {e}")
        return False

def create_lock():
    """Create lock file with current PID"""
    try:
        os.makedirs(os.path.dirname(LOCK_FILE), exist_ok=True)
        current_pid = os.getpid()
        with open(LOCK_FILE, 'w') as f:
            f.write(str(current_pid))
        logger.info(f"Created lock file with PID {current_pid}")
        return True
    except Exception as e:
        logger.error(f"Error creating lock file: {e}")
        return False

def cleanup(signo=None, frame=None):
    """Cleanup function for graceful shutdown"""
    try:
        if os.path.exists(LOCK_FILE):
            with open(LOCK_FILE, 'r') as f:
                stored_pid = int(f.read().strip())
                if stored_pid == os.getpid():
                    logger.info("Removing lock file during cleanup")
                    os.remove(LOCK_FILE)
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
    finally:
        sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGTERM, cleanup)
signal.signal(signal.SIGINT, cleanup)

def send_telegram_notification(chat_id, origen, destino, fecha):
    try:
        fecha_formateada = fecha.strftime("%d/%m/%Y")
        message = f"🚄 ¡Hay trenes disponibles!\n\nOrigen: {origen}\nDestino: {destino}\nFecha: {fecha_formateada}"
        response = requests.get(f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage?chat_id={chat_id}&text={message}')
        if response.status_code != 200:
            logger.error(f"Error sending Telegram notification: {response.text}")
    except Exception as e:
        logger.error(f"Error in send_telegram_notification: {e}")

def create_driver():
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Ejecutar sin interfaz gráfica
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")

        # Usar webdriver-manager para gestionar el chromedriver
        service = Service(ChromeDriverManager().install())

        driver = webdriver.Chrome(service=service, options=chrome_options)
        return driver
    except Exception as e:
        logger.error(f"Error creando el WebDriver: {e}")
        return None

async def consultar_renfe(origen, destino, fecha_deseada):
    driver = None
    try:
        driver = create_driver()
        if not driver:
            return False

        driver.get("https://www.renfe.com/es/es")

        try:
            # Cerrar el mensaje de cookies, si aparece
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "onetrust-reject-all-handler"))
            ).click()
            logger.info("Cookies rechazadas.")
        except Exception as e:
            logger.warning(f"Cookies message not found or could not be closed: {e}")


        # Escribir en el input de origen
        origen_input = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "origin")))
        origen_input.clear()
        origen_input.send_keys(origen)
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "(//li[@role='option'])[1]"))).click()
        logger.info("Origen seleccionado.")

        # Ingresar destino
        destino_input = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "destination")))
        destino_input.clear()
        destino_input.send_keys(destino)
        time.sleep(0.5)
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "awesomplete_list_2_item_0"))).click()
        logger.info("Destino seleccionado.")

        # Seleccionar la fecha usando flechas
        fecha_input = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "first-input")))
        fecha_input.click()
        time.sleep(1)

        # Calcular la diferencia de días entre hoy y la fecha deseada
        hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        fecha_obj = datetime.strptime(fecha_deseada, "%d/%m/%Y")
        dias_faltantes = (fecha_obj - hoy).days

        for _ in range(dias_faltantes):
            fecha_input.send_keys(Keys.ARROW_RIGHT)
            time.sleep(0.1)
        fecha_input.send_keys(Keys.ARROW_UP)
        logger.info("Fecha seleccionada.")

        # Clic en "Aceptar"
        try:
            aceptar_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@type='button' and text()='Aceptar']"))
            )
            ActionChains(driver).move_to_element(aceptar_btn).click().perform()
            logger.info("Botón 'Aceptar' clicado.")
        except Exception as e:
            logger.warning(f"Error al hacer clic en 'Aceptar': {e}")

        # Buscar billetes
        try:
            buscar_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@title='Buscar billete']"))
            )
            ActionChains(driver).move_to_element(buscar_btn).click().perform()
            logger.info("Botón 'Buscar billete' clicado.")
        except Exception as e:
            logger.error(f"Error al hacer clic en 'Buscar billete': {e}")

        # Esperar a que cargue la página de resultados
        time.sleep(5)

        # Verificar la disponibilidad
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "noDispoIda"))
            )
            logger.info("No hay billetes disponibles para estos parámetros.")
            return False
        except Exception:
            logger.info("¡Billetes disponibles!")
            return True

    except Exception as e:
        logger.error(f"Error in consultar_renfe: {e}")
        return False
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

async def run_search_loop():
    """Main search loop with error handling and recovery"""
    while True:
        try:
            prefs = await load_preferences()
            users = list(prefs.items())

            for chat_id, solicitudes in users:
                for solicitud in list(solicitudes):  # Make a copy of the list for iteration
                    origen = solicitud.get("origen")
                    destino = solicitud.get("destino")
                    fecha_deseada = solicitud.get("fecha")

                    if not all([origen, destino, fecha_deseada]):
                        logger.warning(f"Invalid search parameters for user {chat_id}")
                        continue

                    logger.info(f"Checking for user {chat_id}: {origen} - {destino} - {fecha_deseada}")

                    try:
                        if await consultar_renfe(origen, destino, fecha_deseada):
                            send_telegram_notification(chat_id, origen, destino, 
                                                        datetime.strptime(fecha_deseada, "%d/%m/%Y"))
                            solicitudes.remove(solicitud)
                            await save_preferences(prefs)
                    except Exception as e:
                        logger.error(f"Error processing search for user {chat_id}: {e}")
                        continue

            logger.info("Completed search cycle, waiting for next iteration...")
            await asyncio.sleep(60)  # 10 minutes

        except Exception as e:
            logger.error(f"Error in search loop: {e}")
            await asyncio.sleep(300)  # 5 minutes on error

async def main():
    """Main function with improved startup checks"""
    try:
        # Try to terminate other instances first
        terminate_other_instances()

        # Wait for other instances to fully terminate
        await asyncio.sleep(5)  # Increased wait time

        if not check_lock():
            logger.error("Another instance is still running. Exiting.")
            return

        if not create_lock():
            logger.error("Could not create lock file. Exiting.")
            return

        logger.info(f"Starting Renfe search service with PID {os.getpid()}")

        try:
            await run_search_loop()
        except Exception as e:
            logger.error(f"Search loop error: {e}")
        finally:
            cleanup()

    except Exception as e:
        logger.error(f"Fatal error in main: {e}")
    finally:
        cleanup()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Unhandled error: {e}")
    finally:
        cleanup()
