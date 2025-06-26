from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

driver = webdriver.Chrome()
driver.get("https://www.sicoes.gob.bo/")
wait = WebDriverWait(driver, 15)

#Cerrar ventana emergente
try:
    close_btn = wait.until(EC.element_to_be_clickable(
        (By.CSS_SELECTOR, "#modalComunicados .close[data-dismiss='modal']")
    ))
    close_btn.click()
    wait.until(EC.invisibility_of_element_located((By.ID, "modalComunicados")))
    print("Modal cerrado.")
except Exception:
    print(" Modal no visible o ya cerrado.")

#Convovatorias

try:
    convocatorias = wait.until(EC.presence_of_element_located(
        (By.XPATH, "//a[.//h4[text()='Convocatorias']]")
    ))
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", convocatorias)
    time.sleep(1)
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

# Obtiene el total de las paginas
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
        return max(paginas)
    except:
        return 1

total_paginas = obtener_total_paginas()
print(f"\n Total de páginas detectadas: {total_paginas}\n")

# scraping de las paginas
for pagina in range(1, total_paginas + 1):
    print(f"\n Página {pagina}/{total_paginas}")
    try:
        wait.until(EC.presence_of_element_located((By.ID, "tablaSimple")))
        time.sleep(1)
        
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

                print(f"{i}. CUCE: {cuce}")
                print(f"   Entidad: {entidad}")
                print(f"   Tipo Contratación: {tipo_contratacion}")
                print(f"   Modalidad: {modalidad}")
                print(f"   Objeto de Contratación: {objeto_contratacion}")
                print(f"   Subasta: {subasta}")
                print(f"   Fecha Publicación: {fecha_publicacion}")
                print(f"   Fecha Presentación: {fecha_presentacion}")
                print(f"   Estado: {estado}")
                print(f"   Archivos: {archivos}")
                print(f"   Formularios: {formularios}")
                print("-" * 80)

    except Exception as e:
        print(f" Error leyendo tabla en página {pagina}: {e}")

    if pagina < total_paginas:
        try:
            siguiente = wait.until(EC.element_to_be_clickable(
                (By.XPATH, f"//a[contains(@onclick, \"busquedadraw('{pagina + 1}')\")]")
            ))
            driver.execute_script("arguments[0].click();", siguiente)
            time.sleep(2)
        except Exception as e:
            print(f" No se pudo ir a la página {pagina+1}: {e}")
            break

input("\nPresiona ENTER para cerrar el navegador...")
driver.quit()
