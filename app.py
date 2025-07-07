from datetime import datetime, timedelta
from multiprocessing import Manager
from threading import Thread
from flask import Flask, render_template, jsonify, request, redirect, url_for
import sqlite3
import pandas as pd
import os
import re
from scraping import cargar_datos_base, buscar_cuce

app = Flask(__name__)
manager = Manager()
resultado_global = manager.dict()
resultado_global["continuar"] = True
resultado_global["encontrado"] = False
resultado_global["pagina"] = -1
scraping_en_progreso = False

def tarea_scraping():
    global scraping_en_progreso
    scraping_en_progreso = True
    cargar_datos_base()
    scraping_en_progreso = False

@app.route("/", methods=["GET", "POST"])
def index():
    page = request.args.get("page", default=1, type=int)
    mostrar_ultimos = request.args.get("ultimos_dias") == "true"
    per_page = 7
    offset = (page - 1) * per_page

    conn = sqlite3.connect("convocatorias.db")
    cursor = conn.cursor()

    if mostrar_ultimos:
        hace_3_dias = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
        cursor.execute("""
            SELECT COUNT(*) FROM convocatorias 
            WHERE tipo_contratacion = 'Bienes' 
            AND fecha_publicacion >= ?
        """, (hace_3_dias,))
        total = cursor.fetchone()[0]

        cursor.execute("""
            SELECT * FROM convocatorias 
            WHERE tipo_contratacion = 'Bienes' 
            AND fecha_publicacion >= ?
            ORDER BY fecha_publicacion DESC 
            LIMIT ? OFFSET ?
        """, (hace_3_dias, per_page, offset))
    else:
        cursor.execute("""
            SELECT COUNT(*) FROM convocatorias 
            WHERE tipo_contratacion = 'Bienes'
        """)
        total = cursor.fetchone()[0]

        cursor.execute("""
            SELECT * FROM convocatorias 
            WHERE tipo_contratacion = 'Bienes' 
            ORDER BY fecha_publicacion DESC 
            LIMIT ? OFFSET ?
        """, (per_page, offset))

    datos = cursor.fetchall()
    conn.close()

    total_pages = (total + per_page - 1) // per_page

    return render_template("index.html",
                           convocatorias=datos,
                           page=page,
                           total_pages=total_pages,
                           mostrar_ultimos=mostrar_ultimos,
                           palabras_clave=[])

@app.route("/scrapear")
def scrapear():
    global scraping_en_progreso
    if not scraping_en_progreso:
        hilo = Thread(target=tarea_scraping)
        hilo.start()
    return render_template("loading.html")

@app.route("/estado_scraping")
def estado_scraping():
    global scraping_en_progreso
    return jsonify({"scraping": scraping_en_progreso})

@app.route("/buscar/<cuce>")
def buscar(cuce):
    resultado = buscar_cuce(cuce)
    return f"<p>{resultado}</p><a href='/'>Volver</a>"

def resaltar_palabras(texto, palabras):
    def reemplazar(match):
        return f'<mark style="background:yellow;">{match.group(0)}</mark>'
    patron = re.compile(r'\b(' + '|'.join(re.escape(p) for p in palabras) + r')\b', re.IGNORECASE)
    return patron.sub(reemplazar, texto)

@app.route("/filtrar_excel", methods=["GET", "POST"])
def filtrar_excel():
    per_page = 7
    page = request.args.get("page", default=1, type=int)

    if request.method == "POST":
        archivo = request.files.get("archivo_excel")
        if not archivo:
            return "No se subió ningún archivo.", 400

        mostrar_ultimos = request.form.get("ultimos_dias") == "true"
        ruta_temporal = "palabras_clave.xlsx"
        archivo.save(ruta_temporal)
        df = pd.read_excel(ruta_temporal)
        palabras = df.iloc[:, 0].dropna().astype(str).str.strip().str.lower().tolist()
        os.remove(ruta_temporal)

        if not palabras:
            return "El archivo Excel no contiene palabras clave válidas.", 400

        palabras_query = ",".join(palabras)
        ultimos_str = "true" if mostrar_ultimos else "false"

        return redirect(url_for('filtrar_excel', palabras=palabras_query, ultimos_dias=ultimos_str, page=1))

    else:
        palabras_query = request.args.get("palabras")
        mostrar_ultimos = request.args.get("ultimos_dias") == "true"

        if not palabras_query:
            return "No se enviaron palabras clave para filtrar.", 400

        palabras = [p.strip() for p in palabras_query.split(",") if p.strip()]
        if not palabras:
            return "Palabras clave inválidas.", 400

        palabras_like = [f"%{p}%" for p in palabras]
        condiciones = ["LOWER(objeto_contratacion) LIKE ?" for _ in palabras_like]

        if mostrar_ultimos:
            hace_3_dias = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
            condiciones.append("fecha_publicacion >= ?")

        if mostrar_ultimos:
            where_clause = "(" + " OR ".join(condiciones[:-1]) + ") AND " + condiciones[-1]
        else:
            where_clause = " OR ".join(condiciones)

        offset = (page - 1) * per_page

        consulta_count = f"""
            SELECT COUNT(*) FROM convocatorias
            WHERE tipo_contratacion = 'Bienes' AND {where_clause}
        """

        consulta = f"""
            SELECT * FROM convocatorias
            WHERE tipo_contratacion = 'Bienes' AND {where_clause}
            ORDER BY fecha_publicacion DESC
            LIMIT ? OFFSET ?
        """

        parametros = palabras_like.copy()
        if mostrar_ultimos:
            parametros.append(hace_3_dias)

        conn = sqlite3.connect("convocatorias.db")
        cursor = conn.cursor()
        cursor.execute(consulta_count, parametros)
        total = cursor.fetchone()[0]
        cursor.execute(consulta, parametros + [per_page, offset])
        datos = cursor.fetchall()
        conn.close()

        datos_resaltados = []
        for fila in datos:
            texto_resaltado = resaltar_palabras(fila[5] or "", palabras)
            fila_lista = list(fila)
            fila_lista[5] = texto_resaltado
            datos_resaltados.append(tuple(fila_lista))

        total_pages = (total + per_page - 1) // per_page

        return render_template("index.html",
                               convocatorias=datos_resaltados,
                               page=page,
                               total_pages=total_pages,
                               mostrar_ultimos=mostrar_ultimos,
                               palabras_clave=palabras,
                               palabras_query=palabras_query)

@app.route("/buscando/<cuce>")
def buscando(cuce):
    return render_template("buscando.html", cuce=cuce)

@app.route("/buscar_api/<cuce>")
def buscar_api(cuce):
    resultado = buscar_cuce(cuce)
    return jsonify({"resultado": resultado})

if __name__ == "__main__":
    cargar_datos_base()
    app.run(debug=True, port=5012)
