from multiprocessing import Manager, Process
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import sqlite3
import random
from datetime import datetime
import os


def crear_tabla_si_no_existe(cursor):
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS convocatorias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cuce TEXT NOT NULL UNIQUE,
                entidad TEXT,
                tipo_contratacion TEXT,
                modalidad TEXT,
                objeto_contratacion TEXT,
                subasta TEXT,
                fecha_publicacion TEXT,
                fecha_presentacion TEXT,
                estado TEXT
            )
        """)

def scrapear(pagina_inicial, pagina_final, paso):
        options = webdriver.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        driver = webdriver.Chrome(options=options)
        wait = WebDriverWait(driver, 2)
        try:
            driver.get("https://www.sicoes.gob.bo/")
            try:
                close_btn = wait.until(EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "#modalComunicados .close[data-dismiss='modal']")))
                close_btn.click()
            except:
                pass

            convocatorias = wait.until(EC.presence_of_element_located(
                (By.XPATH, "//a[.//h4[text()='Convocatorias']]")))
            convocatorias.click()
            wait.until(EC.presence_of_element_located((By.ID, "tablaSimple")))

            conn = sqlite3.connect("convocatorias.db", check_same_thread=False)
            cursor = conn.cursor()
            crear_tabla_si_no_existe(cursor)
            conn.commit()

            for pagina in range(pagina_inicial, pagina_final + paso, paso):
                if pagina != 1:
                    try:
                        siguiente = wait.until(EC.element_to_be_clickable(
                            (By.XPATH, f"//a[contains(@onclick, \"busquedadraw('{pagina}')\")]")))
                        driver.execute_script("arguments[0].click();", siguiente)
                        time.sleep(random.uniform(1.0, 2.0))
                    except:
                        break

                wait.until(EC.presence_of_element_located((By.ID, "tablaSimple")))
                filas = driver.find_elements(By.CSS_SELECTOR, "#tablaSimple tbody tr")

                for fila in filas:
                    columnas = fila.find_elements(By.TAG_NAME, "td")
                    if len(columnas) >= 9:
                        cuce = columnas[0].text.strip()
                        cursor.execute("SELECT 1 FROM convocatorias WHERE cuce = ?", (cuce,))
                        if cursor.fetchone():
                            continue

                        fecha_publicacion_str = columnas[6].text.strip()
                        fecha_presentacion_str = columnas[7].text.strip()

                        try:
                            fecha_publicacion = datetime.strptime(fecha_publicacion_str, "%d/%m/%Y").strftime("%Y-%m-%d")
                        except Exception:
                            fecha_publicacion = fecha_publicacion_str  # Si falla, se guarda como está

                        try:
                            fecha_presentacion = datetime.strptime(fecha_presentacion_str, "%d/%m/%Y").strftime("%Y-%m-%d")
                        except Exception:
                            fecha_presentacion = fecha_presentacion_str


                        datos = [
                            cuce,
                            columnas[1].text.strip(),
                            columnas[2].text.strip(),
                            columnas[3].text.strip(),
                            columnas[4].text.strip(),
                            columnas[5].text.strip(),
                            fecha_publicacion,
                            fecha_presentacion,
                            columnas[8].text.strip()
                        ]
                        cursor.execute("""
                            INSERT INTO convocatorias (
                                cuce, entidad, tipo_contratacion, modalidad, objeto_contratacion,
                                subasta, fecha_publicacion, fecha_presentacion, estado
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, datos)
                        print(f"[+] CUCE registrado: {cuce}")
                conn.commit()
            conn.close()
        finally:
            driver.quit()
def cargar_datos_base():
    if not os.path.exists("convocatorias.db"):
        conn = sqlite3.connect("convocatorias.db")
        cursor = conn.cursor()
        crear_tabla_si_no_existe(cursor)
        conn.commit()
        conn.close()

        driver_tmp = webdriver.Chrome()
        driver_tmp.get("https://www.sicoes.gob.bo/")
        wait_tmp = WebDriverWait(driver_tmp, 15)
        try:
            wait_tmp.until(EC.element_to_be_clickable(
                (By.XPATH, "//a[.//h4[text()='Convocatorias']]"))).click()
            wait_tmp.until(EC.presence_of_element_located((By.ID, "tablaSimple")))
            total_paginas = obtener_total_paginas(driver_tmp)
        except:
            total_paginas = 170
        finally:
            driver_tmp.quit()

        p1 = Process(target=scrapear, args=(1, total_paginas, 1))
        p2 = Process(target=scrapear, args=(total_paginas, 1, -1))
        p1.start()
        p2.start()
        p1.join()
        p2.join()
    else:
        scrapear(1, 2, 1)

def obtener_total_paginas(driver):
    try:
        elementos = driver.find_elements(By.XPATH, "//a[contains(@onclick, 'busquedadraw')]")
        paginas = []
        for el in elementos:
            try:
                num = int(el.get_attribute("onclick").split("'")[1])
                paginas.append(num)
            except:
                continue
        return max(paginas) if paginas else 1
    except:
        return 1

def buscar_desde(pagina_inicial, pagina_final, paso, cuce_a_buscar, resultado_compartido, nombre_proceso):
    options = webdriver.ChromeOptions()
    driver = webdriver.Chrome(options=options)
    wait = WebDriverWait(driver, 15)
    try:
        driver.get("https://www.sicoes.gob.bo/")
        try:
            close_btn = wait.until(EC.element_to_be_clickable(
                (By.CSS_SELECTOR, "#modalComunicados .close[data-dismiss='modal']")))
            close_btn.click()
        except:
            pass
        convocatorias = wait.until(EC.presence_of_element_located(
            (By.XPATH, "//a[.//h4[text()='Convocatorias']]")))
        convocatorias.click()
        wait.until(EC.presence_of_element_located((By.ID, "tablaSimple")))
        for pagina in range(pagina_inicial, pagina_final + paso, paso):
            if resultado_compartido["encontrado"] and resultado_compartido.get("proceso") != nombre_proceso:
                break
            if pagina != 1:
                try:
                    siguiente = wait.until(EC.element_to_be_clickable(
                        (By.XPATH, f"//a[contains(@onclick, \"busquedadraw('{pagina}')\")]")))
                    driver.execute_script("arguments[0].click();", siguiente)
                except:
                    continue
            wait.until(EC.presence_of_element_located((By.ID, "tablaSimple")))
            script_busqueda = f"""
                let filas = document.querySelectorAll('#tablaSimple tbody tr');
                for (let fila of filas) {{
                    let cuce = fila.cells[0].innerText.trim();
                    if (cuce === "{cuce_a_buscar}") {{
                        fila.style.backgroundColor = 'yellow';
                        fila.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                        return true;
                    }}
                }}
                return false;
            """
            encontrado = driver.execute_script(script_busqueda)
            if encontrado:
                resultado_compartido["encontrado"] = True
                resultado_compartido["pagina"] = pagina
                resultado_compartido["proceso"] = nombre_proceso
                print(f"CUCE {cuce_a_buscar} encontrado en página {pagina}. Navegador abierto para inspección.")
                while True:
                    time.sleep(5)
    finally:
        pass

def buscar_cuce(cuce_a_buscar):
    total_paginas = 170
    manager = Manager()
    resultado = manager.dict()
    resultado["encontrado"] = False
    resultado["pagina"] = -1
    p1 = Process(target=buscar_desde, args=(1, total_paginas, 1, cuce_a_buscar, resultado, "Proceso Inicio->Fin"))
    p2 = Process(target=buscar_desde, args=(total_paginas, 1, -1, cuce_a_buscar, resultado, "Proceso Fin->Inicio"))
    p1.start()
    p2.start()
    p1.join()
    p2.join()
    if resultado["encontrado"]:
        return f"CUCE {cuce_a_buscar} encontrado en página {resultado['pagina']}."
    else:
        return f"CUCE {cuce_a_buscar} no fue encontrado."
