import json
import requests
import time
import csv
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from pathlib import Path

# Token del bot ocultado por seguridad
BOT_TOKEN = 'TU_TOKEN_DE_TELEGRAM_AQUI'

# URL pública del CSV exportado de Google Sheets (puedes dejarla si es pública)
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/TU_ID_DE_HOJA_DE_CALCULO/export?format=csv"

USERS_PREF_FILE = Path("user_preferences.json")
NOTIFICADOS_FILE = Path("notificados.json")

def download_csv(url, filename):
    print("Descargando CSV desde Google Sheets...")
    r = requests.get(url)
    r.raise_for_status()
    with open(filename, 'wb') as f:
        f.write(r.content)
    print("CSV descargado.")

def csv_to_json(csv_path, json_path):
    print("Convirtiendo CSV a JSON...")
    data = {}
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            chat_id = row['chat_id'].strip()
            origen = row['origen'].strip()
            destino = row['destino'].strip()
            fecha = row['fecha'].strip()
            if chat_id not in data:
                data[chat_id] = []
            data[chat_id].append({"origen": origen, "destino": destino, "fecha": fecha})
    with open(json_path, 'w', encoding='utf-8') as jsonfile:
        json.dump(data, jsonfile, indent=2, ensure_ascii=False)
    print("Conversión completada.")

def load_notificados():
    if NOTIFICADOS_FILE.exists():
        with open(NOTIFICADOS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_notificados(data):
    with open(NOTIFICADOS_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def viaje_key(chat_id, origen, destino, fecha):
    return f"{chat_id}_{origen}_{destino}_{fecha}"

def send_telegram_notification(chat_id, origen, destino, fecha):
    fecha_formateada = fecha.strftime("%d/%m/%Y")
    renfe_url = "https://www.renfe.com/es/es"  # URL pública y genérica

    message = (
        f"🚄 ¡Hay trenes disponibles!\n\n"
        f"🔹 Origen: {origen}\n"
        f"🔹 Destino: {destino}\n"
        f"🔹 Fecha: {fecha_formateada}\n\n"
        f"🔗 Compra tus billetes en Renfe: {renfe_url}")
    requests.get(f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage', params={
        'chat_id': chat_id,
        'text': message
    })

def create_driver():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(options=chrome_options)

def consultar_renfe(origen, destino, fecha_deseada):
    driver = create_driver()
    try:
        driver.get("https://www.renfe.com/es/es")

        try:
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "onetrust-reject-all-handler"))
            ).click()
        except:
            pass

        WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "origin"))).send_keys(origen)
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "(//li[@role='option'])[1]"))).click()

        destino_input = WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.ID, "destination")))
        destino_input.clear()
        destino_input.send_keys(destino)
        time.sleep(1)
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "awesomplete_list_2_item_0"))).click()

        fecha_input = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "first-input")))
        fecha_input.click()
        time.sleep(1)

        hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        fecha_obj = datetime.strptime(fecha_deseada, "%d/%m/%Y")
        dias_faltantes = (fecha_obj - hoy).days
        for _ in range(dias_faltantes):
            fecha_input.send_keys(Keys.ARROW_RIGHT)
            time.sleep(0.1)
        fecha_input.send_keys(Keys.ARROW_UP)

        try:
            WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, "//button[text()='Aceptar']"))).click()
        except:
            pass

        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//button[@title='Buscar billete']"))).click()
        time.sleep(5)

        try:
            driver.find_element(By.ID, "noDispoIda")
            return False
        except:
            return True
    finally:
        driver.quit()

def main():
    csv_file = Path("usuarios.csv")
    download_csv(SHEET_CSV_URL, csv_file)
    csv_to_json(csv_file, USERS_PREF_FILE)

    notificados = load_notificados()

    try:
        with open(USERS_PREF_FILE, 'r', encoding='utf-8') as f:
            prefs = json.load(f)
    except Exception as e:
        print(f"Error al cargar preferencias: {e}")
        return

    for chat_id, solicitudes in prefs.items():
        for solicitud in solicitudes:
            origen = solicitud.get("origen")
            destino = solicitud.get("destino")
            fecha = solicitud.get("fecha")
            if origen and destino and fecha:
                key = viaje_key(chat_id, origen, destino, fecha)
                if key in notificados:
                    print(f"⏭ Ya notificado: {key}")
                    continue

                print(f"Buscando: {origen} -> {destino} ({fecha})")
                if consultar_renfe(origen, destino, fecha):
                    send_telegram_notification(chat_id, origen, destino, datetime.strptime(fecha, "%d/%m/%Y"))
                    print(f"✅ Billetes disponibles. Notificación enviada para {key}.")
                    notificados[key] = True
                    save_notificados(notificados)
                else:
                    print(f"❌ No hay billetes disponibles para {key}.")

if __name__ == '__main__':
    main()

