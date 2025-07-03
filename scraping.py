from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import sqlite3

driver = webdriver.Chrome()
driver.get("https://www.sicoes.gob.bo/")
wait = WebDriverWait(driver, 15)

conn = sqlite3.connect("convocatorias.db")
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='convocatorias'")
tabla_existente = cursor.fetchone()

if tabla_existente:
    cursor.execute("SELECT COUNT(*) FROM convocatorias")
    total_registros = cursor.fetchone()[0]
else:
    total_registros = 0

print(f"\n Total de registros existentes en la tabla: {total_registros}")

if not tabla_existente:
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS convocatorias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cuce TEXT  NOT NULL UNIQUE,
        entidad TEXT,
        tipo_contratacion TEXT,
        modalidad TEXT,
        objeto_contratacion TEXT,
        subasta TEXT,
        fecha_publicacion TEXT,
        fecha_presentacion TEXT,
        estado TEXT,
        archivos TEXT,
        formularios TEXT
    )
    """)
    conn.commit()
    print("Tabla 'convocatorias' creada.")

try:
    close_btn = wait.until(EC.element_to_be_clickable(
        (By.CSS_SELECTOR, "#modalComunicados .close[data-dismiss='modal']")
    ))
    close_btn.click()
    wait.until(EC.invisibility_of_element_located((By.ID, "modalComunicados")))
    print("Modal cerrado.")
except Exception:
    print("Modal no visible o ya cerrado.")

try:
    convocatorias = wait.until(EC.presence_of_element_located(
        (By.XPATH, "//a[.//h4[text()='Convocatorias']]")
    ))
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", convocatorias)
    try:
        convocatorias.click()
    except:
        driver.execute_script("arguments[0].click();", convocatorias)
    wait.until(EC.presence_of_element_located((By.ID, "tablaSimple")))
    print("Accediste a Convocatorias.")
except Exception as e:
    print(f"Error al acceder a Convocatorias: {e}")
    driver.quit()
    exit()

def obtener_total_paginas():
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

total_paginas = obtener_total_paginas()
print(f"\n Total de páginas detectadas: {total_paginas}\n")

if total_registros > 0:
    pagina_inicio = 1
    total_paginas = min(total_paginas, 5)
    print(f"Tabla con datos existente. Se scrapean solo las primeras 5 páginas.")
else:
    pagina_inicio = 1
    print("Tabla vacía o no existente. Se scrapea desde página 1 hasta la última.")

print(f"\nComenzando scraping desde la página {pagina_inicio} hasta {total_paginas}...\n")

for pagina in range(pagina_inicio, total_paginas + 1):
    print(f"\n Página {pagina}/{total_paginas}")
    try:
        wait.until(EC.presence_of_element_located((By.ID, "tablaSimple")))

        filas = driver.find_elements(By.CSS_SELECTOR, "#tablaSimple tbody tr")
        for i, fila in enumerate(filas, 1):
            columnas = fila.find_elements(By.TAG_NAME, "td")
            if len(columnas) >= 11:
                cuce = columnas[0].text.strip()
                entidad = columnas[1].text.strip()
                tipo_contratacion = columnas[2].text.strip()
                modalidad = columnas[3].text.strip()
                objeto_contratacion = columnas[4].text.strip()
                subasta = columnas[5].text.strip()
                fecha_publicacion = columnas[6].text.strip()
                fecha_presentacion = columnas[7].text.strip()
                estado = columnas[8].text.strip()
                archivos = columnas[9].text.strip().replace("\n", " | ")
                formularios = columnas[10].text.strip().replace("\n", " | ")

                cursor.execute("SELECT 1 FROM convocatorias WHERE cuce = ?", (cuce,))
                if cursor.fetchone():
                    print(f"{i}. CUCE: {cuce} ya existe. Saltando.")
                    continue

              
                cursor.execute("""
                    INSERT INTO convocatorias (
                        cuce, entidad, tipo_contratacion, modalidad, objeto_contratacion,
                        subasta, fecha_publicacion, fecha_presentacion, estado, archivos, formularios
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    cuce, entidad, tipo_contratacion, modalidad, objeto_contratacion,
                    subasta, fecha_publicacion, fecha_presentacion, estado, archivos, formularios
                ))
        conn.commit()

    except Exception as e:
        print(f" Error leyendo tabla en página {pagina}: {e}")

    if pagina < total_paginas:
        try:
            siguiente = wait.until(EC.element_to_be_clickable(
                (By.XPATH, f"//a[contains(@onclick, \"busquedadraw('{pagina + 1}')\")]")
            ))
            driver.execute_script("arguments[0].click();", siguiente)
            
        except Exception as e:
            print(f"No se pudo ir a la página {pagina + 1}: {e}")
            break

print("\nScraping finalizado.")
conn.close()
print("Conexión a la base de datos cerrada.")
input("\nPresiona ENTER para cerrar el navegador...")
driver.quit()
