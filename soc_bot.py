from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters
)

import os
import re
import json
import html
from io import BytesIO


try:
    from PyPDF2 import PdfReader
except Exception:
    PdfReader = None


# ========================================
# VARIABLES DE ENTORNO
# ========================================

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ACCESS_CODE = os.getenv("ACCESS_CODE", "SOCENTEL2026")

AUTHORIZED_USER_IDS_ENV = os.getenv("AUTHORIZED_USER_IDS", "")
ADMIN_USER_IDS_ENV = os.getenv("ADMIN_USER_IDS", "")

ALLOW_ALL_USERS = os.getenv("ALLOW_ALL_USERS", "false").lower().strip() == "true"

DOCS_PATH = os.getenv("DOCS_PATH", "docs/manuales_pdf")
MAX_RESULTS = int(os.getenv("MAX_RESULTS", "1"))

USERS_FILE = "usuarios_autorizados.json"
SESSION_FILE = "sesiones.json"
CONSULTAS_FILE = "consultas.json"
PDF_FILE_IDS_FILE = "pdf_file_ids.json"

BASE_TXT_PATH = "docs/base_conocimiento.txt"


# ========================================
# FUNCIONES GENERALES
# ========================================

def limpiar_mensaje(texto):
    if not texto:
        return ""

    texto = str(texto)
    texto = html.unescape(texto)
    texto = re.sub(r"<br\s*/?>", " ", texto, flags=re.IGNORECASE)

    texto = texto.lower().strip()
    texto = texto.replace("¿", "")
    texto = texto.replace("?", "")
    texto = texto.replace("á", "a")
    texto = texto.replace("é", "e")
    texto = texto.replace("í", "i")
    texto = texto.replace("ó", "o")
    texto = texto.replace("ú", "u")
    texto = texto.replace("ñ", "n")
    texto = re.sub(r"\s+", " ", texto)

    return texto


def limpiar_texto_visible(texto):
    if not texto:
        return ""

    texto = str(texto)
    texto = html.unescape(texto)
    texto = re.sub(r"<br\s*/?>", "\n", texto, flags=re.IGNORECASE)
    texto = texto.replace("\r", "\n")
    texto = re.sub(r"\n{3,}", "\n\n", texto)

    return texto.strip()


def convertir_ids_env(valor):
    ids = set()

    if valor:
        for item in valor.split(","):
            item = item.strip()

            if item.isdigit():
                ids.add(int(item))

    return ids


async def enviar_texto_largo(update: Update, texto, limite=3900):
    if not texto:
        return

    texto = str(texto).strip()

    if len(texto) <= limite:
        await update.message.reply_text(texto)
        return

    partes = []

    while len(texto) > limite:
        corte = texto.rfind("\n", 0, limite)

        if corte == -1:
            corte = limite

        partes.append(texto[:corte].strip())
        texto = texto[corte:].strip()

    if texto:
        partes.append(texto)

    for parte in partes:
        if parte:
            await update.message.reply_text(parte)


def teclado_principal():
    botones = [
        ["📡 GPON", "🌐 NCE"],
        ["🎫 HELIX", "📶 SMARTWIFI"],
        ["⚡ POTENCIA", "🚨 MASIVAS"],
        ["📚 MANUALES", "📊 ESTADISTICAS"],
        ["🆔 MI ID", "🚪 LOGOUT"]
    ]

    return ReplyKeyboardMarkup(
        botones,
        resize_keyboard=True,
        one_time_keyboard=False
    )


def normalizar_boton(texto):
    texto_limpio = limpiar_mensaje(texto)

    reemplazos = {
        "📡 gpon": "gpon",
        "gpon": "gpon",
        "olt": "gpon",
        "ont": "gpon",
        "onu": "gpon",
        "nce gpon": "gpon",

        "🌐 nce": "nce",
        "nce": "nce",

        "🎫 helix": "helix",
        "helix": "helix",

        "📶 smartwifi": "smartwifi",
        "smartwifi": "smartwifi",
        "smart wifi": "smartwifi",

        "⚡ potencia": "potencia",
        "potencia": "potencia",
        "validar potencia": "potencia",

        "🚨 masivas": "evento masivo",
        "masivas": "evento masivo",
        "masiva": "evento masivo",
        "evento masivo": "evento masivo",
        "falla masiva": "evento masivo",
        "fallas masivas": "evento masivo",

        "📚 manuales": "manuales",
        "manuales": "manuales",

        "📊 estadisticas": "estadisticas",
        "estadisticas": "estadisticas",

        "🆔 mi id": "id",
        "mi id": "id",
        "id": "id",

        "🚪 logout": "logout",
        "logout": "logout",
        "salir": "logout"
    }

    return reemplazos.get(texto_limpio, texto_limpio)


# ========================================
# SESIONES
# ========================================

def cargar_sesiones():
    try:
        if os.path.exists(SESSION_FILE):
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, list):
                return set(int(x) for x in data)

    except Exception as e:
        print("Error cargando sesiones:", e)

    return set()


def guardar_sesiones():
    try:
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump(
                sorted(list(usuarios_logueados)),
                f,
                indent=4
            )

        print("Sesiones guardadas correctamente")

    except Exception as e:
        print("Error guardando sesiones:", e)


usuarios_logueados = cargar_sesiones()
ULTIMO_MENSAJE = {}

# ========================================
# CONSULTAS / ESTADÍSTICAS
# ========================================

def cargar_consultas():
    try:
        if os.path.exists(CONSULTAS_FILE):
            with open(CONSULTAS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, list):
                return data

    except Exception as e:
        print("Error cargando consultas:", e)

    return []


def guardar_consultas(data):
    try:
        with open(CONSULTAS_FILE, "w", encoding="utf-8") as f:
            json.dump(
                data,
                f,
                indent=4,
                ensure_ascii=False
            )

        print("Consultas guardadas correctamente")

    except Exception as e:
        print("Error guardando consultas:", e)


def registrar_consulta(user_id, consulta):
    try:
        data = cargar_consultas()

        data.append(
            {
                "usuario": str(user_id),
                "consulta": consulta
            }
        )

        guardar_consultas(data)

    except Exception as e:
        print("Error registrando consulta:", e)


def obtener_top_consultas():
    data = cargar_consultas()
    conteo = {}

    for item in data:
        consulta = limpiar_mensaje(item.get("consulta", ""))

        if consulta:
            conteo[consulta] = conteo.get(consulta, 0) + 1

    top = sorted(
        conteo.items(),
        key=lambda x: x[1],
        reverse=True
    )

    return top[:5]


# ========================================
# USUARIOS
# ========================================

USUARIOS_BASE = convertir_ids_env(AUTHORIZED_USER_IDS_ENV)
ADMIN_USERS = convertir_ids_env(ADMIN_USER_IDS_ENV)

if not ADMIN_USERS:
    ADMIN_USERS = set(USUARIOS_BASE)


def cargar_usuarios_dinamicos():
    try:
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, "r", encoding="utf-8") as archivo:
                data = json.load(archivo)

            if isinstance(data, dict):
                return set(int(x) for x in data.get("usuarios", []))

            if isinstance(data, list):
                return set(int(x) for x in data)

    except Exception as e:
        print("Error cargando usuarios dinámicos:", e)

    return set()


def guardar_usuarios_dinamicos(usuarios):
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as archivo:
            json.dump(
                {"usuarios": sorted(list(usuarios))},
                archivo,
                indent=4
            )

        print("Usuarios dinámicos guardados correctamente")

    except Exception as e:
        print("Error guardando usuarios dinámicos:", e)


USUARIOS_DINAMICOS = cargar_usuarios_dinamicos()


def obtener_usuarios_autorizados():
    return USUARIOS_BASE.union(USUARIOS_DINAMICOS)


def es_admin(user_id):
    return user_id in ADMIN_USERS


# ========================================
# CACHE FILE_ID TELEGRAM
# ========================================

def cargar_pdf_file_ids():
    try:
        if os.path.exists(PDF_FILE_IDS_FILE):
            with open(PDF_FILE_IDS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, dict):
                return data

    except Exception as e:
        print("Error cargando file_id de PDFs:", e)

    return {}


def guardar_pdf_file_ids():
    try:
        with open(PDF_FILE_IDS_FILE, "w", encoding="utf-8") as f:
            json.dump(
                PDF_FILE_IDS,
                f,
                indent=4,
                ensure_ascii=False
            )

        print("File IDs de PDFs guardados correctamente")

    except Exception as e:
        print("Error guardando file_id de PDFs:", e)


PDF_FILE_IDS = cargar_pdf_file_ids()


def claves_pdf(pdf):
    claves = []

    archivo = pdf.get("archivo", "")
    archivo_limpio = limpiar_mensaje(archivo)

    if archivo_limpio:
        claves.append(archivo_limpio)
        claves.append(archivo_limpio.replace(".pdf", "").strip())
        claves.append(archivo_limpio.replace("manual", "").replace(".pdf", "").strip())

    objetivo = obtener_manual_objetivo(archivo)

    if objetivo:
        claves.append(objetivo)

    claves_limpias = []

    for clave in claves:
        clave = limpiar_mensaje(clave)

        if clave and clave not in claves_limpias:
            claves_limpias.append(clave)

    return claves_limpias


# ========================================
# BASE DE CONOCIMIENTO TXT
# ========================================

BASE_CONOCIMIENTO = {}


def cargar_base_txt():
    try:
        if not os.path.exists(BASE_TXT_PATH):
            print("No se encontró base_conocimiento.txt")
            return

        with open(BASE_TXT_PATH, "r", encoding="utf-8") as archivo:
            contenido = archivo.read()

        contenido = limpiar_texto_visible(contenido)

        bloques = contenido.split("\n\n")

        for bloque in bloques:
            bloque = bloque.strip()

            if ":" in bloque:
                clave_original = bloque.split(":")[0].strip()
                clave_limpia = limpiar_mensaje(clave_original)
                BASE_CONOCIMIENTO[clave_limpia] = bloque

        print(f"Base TXT cargada correctamente: {len(BASE_CONOCIMIENTO)} entradas")

    except Exception as e:
        print("Error cargando base TXT:", e)


def buscar_en_txt(consulta):
    consulta_limpia = limpiar_mensaje(consulta)

    if not consulta_limpia:
        return None

    if consulta_limpia in BASE_CONOCIMIENTO:
        return BASE_CONOCIMIENTO[consulta_limpia]

    for clave in sorted(BASE_CONOCIMIENTO.keys(), key=len, reverse=True):
        clave_limpia = limpiar_mensaje(clave)

        if (
            clave_limpia == consulta_limpia
            or clave_limpia in consulta_limpia
            or consulta_limpia in clave_limpia
        ):
            return BASE_CONOCIMIENTO[clave]

    return None


# ========================================
# BASE DE CONOCIMIENTO PDF
# ========================================

BASE_PDFS = []


def extraer_texto_pdf(ruta_pdf):
    texto_total = ""

    if PdfReader is None:
        print("PyPDF2 no está instalado. No se pueden leer PDFs.")
        return texto_total

    try:
        reader = PdfReader(ruta_pdf)

        if getattr(reader, "is_encrypted", False):
            try:
                reader.decrypt("")
                print(f"PDF cifrado desbloqueado sin contraseña: {ruta_pdf}")
            except Exception as e:
                print(f"PDF cifrado no desbloqueable: {ruta_pdf} - {e}")
                return texto_total

        for numero_pagina, pagina in enumerate(reader.pages, start=1):
            try:
                texto = pagina.extract_text()

                if texto:
                    texto_total += f"\n\n[Página {numero_pagina}]\n{texto}"

            except Exception as e:
                print(f"Error leyendo página {numero_pagina} de {ruta_pdf}: {e}")

    except Exception as e:
        print(f"Error leyendo PDF {ruta_pdf}: {e}")

    return texto_total


def cargar_bytes_pdf(ruta_pdf):
    try:
        with open(ruta_pdf, "rb") as archivo:
            return archivo.read()

    except Exception as e:
        print(f"Error cargando PDF en memoria {ruta_pdf}: {e}")
        return None


def cargar_pdfs():
    try:
        print(f"Buscando PDFs en ruta: {DOCS_PATH}")

        if not os.path.exists(DOCS_PATH):
            print(f"No existe la ruta de PDFs: {DOCS_PATH}")
            return

        total_pdfs = 0

        for raiz, carpetas, archivos in os.walk(DOCS_PATH):
            for archivo in archivos:
                if archivo.lower().endswith(".pdf"):
                    total_pdfs += 1
                    ruta_pdf = os.path.join(raiz, archivo)

                    print(f"Cargando PDF: {ruta_pdf}")

                    texto_pdf = extraer_texto_pdf(ruta_pdf)
                    pdf_bytes = cargar_bytes_pdf(ruta_pdf)

                    try:
                        tamano_mb = round(os.path.getsize(ruta_pdf) / (1024 * 1024), 2)
                    except Exception:
                        tamano_mb = 0

                    BASE_PDFS.append(
                        {
                            "archivo": archivo,
                            "ruta": ruta_pdf,
                            "texto": texto_pdf,
                            "texto_limpio": limpiar_mensaje(texto_pdf),
                            "archivo_limpio": limpiar_mensaje(archivo),
                            "bytes": pdf_bytes,
                            "tamano_mb": tamano_mb
                        }
                    )

                    if texto_pdf and texto_pdf.strip():
                        print(f"PDF cargado correctamente: {archivo} - {tamano_mb} MB")
                    else:
                        print(f"PDF sin texto extraíble o escaneado: {archivo} - {tamano_mb} MB")

        pdfs_con_texto = len([p for p in BASE_PDFS if p["texto"].strip()])
        pdfs_con_bytes = len([p for p in BASE_PDFS if p.get("bytes")])

        print(f"PDFs encontrados: {total_pdfs}")
        print(f"PDFs con texto cargado: {pdfs_con_texto}")
        print(f"PDFs cargados en memoria: {pdfs_con_bytes}")
        print(f"PDFs con file_id guardado: {len(PDF_FILE_IDS)}")

    except Exception as e:
        print("Error cargando PDFs:", e)


def listar_manuales_texto():
    if not BASE_PDFS:
        return "⚠️ No hay manuales PDF cargados."

    texto = "📚 Manuales PDF disponibles:\n\n"

    for pdf in BASE_PDFS:
        archivo = pdf.get("archivo", "")
        tamano = pdf.get("tamano_mb", 0)

        cache_ok = "⚡" if any(clave in PDF_FILE_IDS for clave in claves_pdf(pdf)) else "📤"

        texto += f"• {cache_ok} {archivo} ({tamano} MB)\n"

    texto += "\nLeyenda:\n"
    texto += "⚡ Envío rápido por file_id\n"
    texto += "📤 Se enviará subiendo el PDF\n\n"

    texto += "Puedes solicitar uno así:\n"
    texto += "/manual gpon\n"
    texto += "/manual helix\n"
    texto += "/manual nce\n"
    texto += "/manual smartwifi\n"
    texto += "/manual schaman\n"
    texto += "/manual aaa\n"
    texto += "/manual acs\n"
    texto += "/manual broadsoft\n"
    texto += "/manual fan\n"

    return texto


def obtener_manual_objetivo(consulta):
    consulta_limpia = limpiar_mensaje(consulta)

    reglas = {
        "gpon": "ncegpon",
        "olt": "ncegpon",
        "ont": "ncegpon",
        "onu": "ncegpon",
        "nce": "ncegpon",
        "potencia": "ncegpon",
        "rx": "ncegpon",
        "tx": "ncegpon",
        "dbm": "ncegpon",
        "masiva": "ncegpon",
        "masivas": "ncegpon",
        "evento masivo": "ncegpon",
        "falla masiva": "ncegpon",
        "fallas masivas": "ncegpon",

        "helix": "helix",

        "smartwifi": "smartwifi",
        "smart wifi": "smartwifi",

        "schaman": "schaman",
        "shaman": "schaman",

        "fan sharing": "fan",
        "fan": "fan",

        "acs": "acs",
        "genie": "acs",

        "aaa": "aaa",

        "broadsoft": "broadsoft",
        "broad soft": "broadsoft"
    }

    for clave, manual in reglas.items():
        if clave in consulta_limpia:
            return manual

    for pdf in BASE_PDFS:
        archivo_limpio = pdf.get("archivo_limpio", "")
        archivo_sin_pdf = archivo_limpio.replace(".pdf", "").replace("manual", "").strip()
        palabras_archivo = archivo_sin_pdf.split()

        for palabra in palabras_archivo:
            if len(palabra) >= 3 and palabra in consulta_limpia:
                return palabra

    return None


def buscar_pdf_relacionado(consulta):
    consulta_limpia = limpiar_mensaje(consulta)

    if not consulta_limpia:
        return None

    manual_objetivo = obtener_manual_objetivo(consulta_limpia)

    if manual_objetivo:
        for pdf in BASE_PDFS:
            archivo_limpio = pdf.get("archivo_limpio", "")

            if manual_objetivo in archivo_limpio:
                return pdf

    palabras = consulta_limpia.split()
    candidatos = []

    for pdf in BASE_PDFS:
        archivo_limpio = pdf.get("archivo_limpio", "")
        texto_limpio = pdf.get("texto_limpio", "")
        puntaje = 0

        if consulta_limpia in archivo_limpio:
            puntaje += 40

        if consulta_limpia in texto_limpio:
            puntaje += 15

        for palabra in palabras:
            if len(palabra) >= 3:
                if palabra in archivo_limpio:
                    puntaje += 10

                if palabra in texto_limpio:
                    puntaje += 1

        if "gpon" in consulta_limpia and "aaa" in archivo_limpio:
            puntaje -= 100

        if "gpon" in consulta_limpia and "acs" in archivo_limpio:
            puntaje -= 100

        if "gpon" in consulta_limpia and "broadsoft" in archivo_limpio:
            puntaje -= 100

        if "nce" in consulta_limpia and "aaa" in archivo_limpio:
            puntaje -= 100

        if puntaje > 0:
            candidatos.append((puntaje, pdf))

    if not candidatos:
        return None

    candidatos = sorted(
        candidatos,
        key=lambda x: x[0],
        reverse=True
    )

    return candidatos[0][1]


def buscar_fragmentos_pdf(consulta):
    consulta_limpia = limpiar_mensaje(consulta)

    if not consulta_limpia:
        return None

    palabras = [
        palabra for palabra in consulta_limpia.split()
        if len(palabra) >= 4
    ]

    if not palabras:
        return None

    resultados = []

    for pdf in BASE_PDFS:
        texto = pdf.get("texto", "")
        texto_limpio = pdf.get("texto_limpio", "")

        if not texto or not texto_limpio:
            continue

        puntaje = 0

        for palabra in palabras:
            if palabra in texto_limpio:
                puntaje += 1

        if puntaje == 0:
            continue

        posicion = -1

        for palabra in palabras:
            posicion = texto_limpio.find(palabra)
            if posicion != -1:
                break

        if posicion == -1:
            continue

        inicio = max(0, posicion - 800)
        fin = min(len(texto), posicion + 2200)

        fragmento = texto[inicio:fin].strip()

        resultados.append(
            {
                "archivo": pdf.get("archivo", ""),
                "puntaje": puntaje,
                "fragmento": fragmento
            }
        )

    if not resultados:
        return None

    resultados = sorted(
        resultados,
        key=lambda x: x["puntaje"],
        reverse=True
    )

    respuesta = (
        "📚 SOC Assistant\n\n"
        "He encontrado información en los manuales operativos:\n\n"
    )

    for item in resultados[:MAX_RESULTS]:
        respuesta += f"📄 Manual: {item['archivo']}\n"
        respuesta += f"{item['fragmento']}\n\n"
        respuesta += "────────────────────\n\n"

    return respuesta.strip()


async def enviar_pdf_seguro(update: Update, pdf):
    if not pdf:
        return

    archivo = pdf.get("archivo")
    pdf_bytes = pdf.get("bytes")
    tamano_mb = pdf.get("tamano_mb", 0)
    ruta = pdf.get("ruta")

    if not archivo:
        await update.message.reply_text(
            "⚠️ No pude identificar el nombre del manual."
        )
        return

    # 1. Intentar envío rápido con file_id
    for clave in claves_pdf(pdf):
        file_id = PDF_FILE_IDS.get(clave)

        if file_id:
            try:
                await update.message.reply_text(
                    f"⚡ Enviando manual rápido: {archivo}..."
                )

                await update.message.reply_document(
                    document=file_id,
                    filename=archivo,
                    caption=f"📄 {archivo}",
                    protect_content=True,
                    read_timeout=300,
                    write_timeout=300,
                    connect_timeout=300,
                    pool_timeout=300
                )

                print(f"PDF enviado por file_id: {archivo} - clave: {clave}")
                return

            except Exception as e:
                print(f"Error usando file_id para {archivo}: {e}")

                if clave in PDF_FILE_IDS:
                    del PDF_FILE_IDS[clave]
                    guardar_pdf_file_ids()

    # 2. Si no hay file_id, subir PDF desde memoria o disco
    await update.message.reply_text(
        f"📤 Preparando envío del manual: {archivo} ({tamano_mb} MB)..."
    )

    try:
        mensaje_pdf = None

        if pdf_bytes:
            pdf_file = BytesIO(pdf_bytes)
            pdf_file.name = archivo

            mensaje_pdf = await update.message.reply_document(
                document=pdf_file,
                filename=archivo,
                caption=f"📄 {archivo}",
                protect_content=True,
                read_timeout=300,
                write_timeout=300,
                connect_timeout=300,
                pool_timeout=300
            )

            print(f"PDF enviado desde memoria: {archivo}")

        elif ruta and os.path.exists(ruta):
            with open(ruta, "rb") as f:
                mensaje_pdf = await update.message.reply_document(
                    document=f,
                    filename=archivo,
                    caption=f"📄 {archivo}",
                    protect_content=True,
                    read_timeout=300,
                    write_timeout=300,
                    connect_timeout=300,
                    pool_timeout=300
                )

            print(f"PDF enviado desde disco: {archivo}")

        else:
            await update.message.reply_text(
                "⚠️ Encontré el manual, pero no pude ubicar el archivo en el servidor."
            )
            return

        # 3. Guardar file_id automáticamente para próximos envíos rápidos
        if mensaje_pdf and mensaje_pdf.document:
            file_id = mensaje_pdf.document.file_id

            for clave in claves_pdf(pdf):
                PDF_FILE_IDS[clave] = file_id

            guardar_pdf_file_ids()

            print(f"FILE_ID guardado para {archivo}: {file_id}")

    except Exception as e:
        print(f"Error enviando PDF {archivo}: {e}")
        await update.message.reply_text(
            "⚠️ Encontré el manual, pero Telegram demoró demasiado en enviarlo.\n\n"
            "Puedes consultar directamente el tema escribiendo, por ejemplo:\n"
            "GPON\n"
            "NCE\n"
            "HELIX\n"
            "POTENCIA\n"
            "MASIVAS"
        )


# ========================================
# CARGA INICIAL
# ========================================

cargar_base_txt()
cargar_pdfs()

print("Base de conocimiento inicializada")
print(f"Entradas TXT: {len(BASE_CONOCIMIENTO)}")
print(f"Manuales PDF cargados: {len(BASE_PDFS)}")


# ========================================
# VALIDACIÓN DE ACCESO
# ========================================

async def validar_acceso(update: Update, mensaje_original: str):
    user_id = update.effective_user.id
    usuarios_autorizados = obtener_usuarios_autorizados()

    print(f"Mensaje recibido de usuario {user_id}: {mensaje_original}")

    if user_id in usuarios_autorizados or user_id in ADMIN_USERS:
        if user_id not in usuarios_logueados:
            usuarios_logueados.add(user_id)
            guardar_sesiones()

        return True

    if not ALLOW_ALL_USERS:
        await update.message.reply_text(
            "⛔ Usuario no autorizado.\n\n"
            f"Tu ID de Telegram es:\n{user_id}\n\n"
            "Solicita al administrador que te agregue con:\n"
            f"/agregarusuario {user_id}"
        )
        return False

    if user_id not in usuarios_logueados:
        if mensaje_original.strip() == ACCESS_CODE:
            usuarios_logueados.add(user_id)
            guardar_sesiones()

            await update.message.reply_text(
                "✅ Acceso autorizado.\n\n"
                "Bienvenido al SOC Assistant.",
                reply_markup=teclado_principal()
            )

            return False

        await update.message.reply_text(
            "🔒 Acceso restringido.\n\n"
            "Ingrese la contraseña para utilizar el SOC Assistant."
        )

        return False

    return True


# ========================================
# COMANDOS BÁSICOS
# ========================================

async def mi_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    await update.message.reply_text(
        f"Tu ID de Telegram es:\n\n{user_id}"
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    usuarios_autorizados = obtener_usuarios_autorizados()

    await update.message.reply_text(
        "👋 Hola.\n\n"
        "Soy el Assistant del SOC."
    )

    if user_id in usuarios_autorizados or user_id in ADMIN_USERS:
        usuarios_logueados.add(user_id)
        guardar_sesiones()

        await update.message.reply_text(
            "✅ Acceso validado.\n\n"
            "Puedes usar /menu para ver las opciones disponibles.",
            reply_markup=teclado_principal()
        )
        return

    if not ALLOW_ALL_USERS:
        await update.message.reply_text(
            "🔒 Para usar el bot, primero debes estar autorizado.\n\n"
            f"Tu ID de Telegram es:\n{user_id}\n\n"
            "Solicita al administrador que te agregue."
        )
        return

    if user_id not in usuarios_logueados:
        await update.message.reply_text(
            "🔐 Ingresa la contraseña de acceso."
        )
        return

    await update.message.reply_text(
        "Puedes usar /menu para ver las opciones disponibles.",
        reply_markup=teclado_principal()
    )


async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id in usuarios_logueados:
        usuarios_logueados.remove(user_id)
        guardar_sesiones()

        await update.message.reply_text(
            "🔒 Sesión cerrada correctamente."
        )

    else:
        await update.message.reply_text(
            "No tienes una sesión activa."
        )


# ========================================
# ADMIN USUARIOS
# ========================================

async def agregar_usuario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_id = update.effective_user.id

    if not es_admin(admin_id):
        await update.message.reply_text(
            "⛔ No tienes permisos de administrador para agregar usuarios."
        )
        return

    if not context.args:
        await update.message.reply_text(
            "Uso correcto:\n\n"
            "/agregarusuario ID_TELEGRAM\n\n"
            "Ejemplo:\n"
            "/agregarusuario 123456789"
        )
        return

    nuevo_id = context.args[0].strip()

    if not nuevo_id.isdigit():
        await update.message.reply_text(
            "⚠️ El ID debe ser numérico."
        )
        return

    nuevo_id = int(nuevo_id)

    USUARIOS_DINAMICOS.add(nuevo_id)
    guardar_usuarios_dinamicos(USUARIOS_DINAMICOS)

    usuarios_logueados.add(nuevo_id)
    guardar_sesiones()

    await update.message.reply_text(
        "✅ Usuario agregado correctamente.\n\n"
        f"ID autorizado:\n{nuevo_id}"
    )


async def eliminar_usuario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_id = update.effective_user.id

    if not es_admin(admin_id):
        await update.message.reply_text(
            "⛔ No tienes permisos de administrador para eliminar usuarios."
        )
        return

    if not context.args:
        await update.message.reply_text(
            "Uso correcto:\n\n"
            "/eliminarusuario ID_TELEGRAM"
        )
        return

    eliminar_id = context.args[0].strip()

    if not eliminar_id.isdigit():
        await update.message.reply_text(
            "⚠️ El ID debe ser numérico."
        )
        return

    eliminar_id = int(eliminar_id)

    if eliminar_id in USUARIOS_DINAMICOS:
        USUARIOS_DINAMICOS.remove(eliminar_id)
        guardar_usuarios_dinamicos(USUARIOS_DINAMICOS)

    if eliminar_id in usuarios_logueados:
        usuarios_logueados.remove(eliminar_id)
        guardar_sesiones()

    await update.message.reply_text(
        "✅ Usuario eliminado correctamente.\n\n"
        f"ID eliminado:\n{eliminar_id}"
    )


async def listar_usuarios(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_id = update.effective_user.id

    if not es_admin(admin_id):
        await update.message.reply_text(
            "⛔ No tienes permisos de administrador para listar usuarios."
        )
        return

    usuarios_autorizados = obtener_usuarios_autorizados()

    if not usuarios_autorizados:
        await update.message.reply_text(
            "No hay usuarios autorizados."
        )
        return

    texto = "👥 Usuarios autorizados:\n\n"

    for user_id in sorted(usuarios_autorizados):
        tipo = "Admin" if user_id in ADMIN_USERS else "Usuario"
        texto += f"- {user_id} ({tipo})\n"

    await enviar_texto_largo(update, texto)


# ========================================
# MENÚ / MANUALES / ESTADÍSTICAS
# ========================================

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    acceso_ok = await validar_acceso(update, "menu")

    if not acceso_ok:
        return

    texto = """
📡 SOC Assistant

═══════════════════════

COMANDOS

/menu
/id
/logout
/estadisticas
/manuales
/manual palabra_clave

═══════════════════════

CONSULTAS DISPONIBLES

✅ SOC
✅ GPON
✅ OLT
✅ ONT
✅ HELIX
✅ NCE
✅ SMARTWIFI
✅ FAN SHARING
✅ POTENCIA
✅ MASIVAS
✅ ACS
✅ BROADSOFT
✅ SCHAMAN
✅ AAA

═══════════════════════

COMANDOS DIRECTOS

/helix
/nce
/smartwifi
/masivas

═══════════════════════

EJEMPLOS

GPON
manual gpon
/manual helix
/manual nce
/manual potencia
/manual smartwifi
/manual schaman
validar potencia
evento masivo
"""

    await update.message.reply_text(
        texto,
        reply_markup=teclado_principal()
    )


async def manuales(update: Update, context: ContextTypes.DEFAULT_TYPE):
    acceso_ok = await validar_acceso(update, "manuales")

    if not acceso_ok:
        return

    texto = listar_manuales_texto()
    await enviar_texto_largo(update, texto)


async def manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    acceso_ok = await validar_acceso(update, "manual")

    if not acceso_ok:
        return

    if not context.args:
        texto = (
            "Uso correcto:\n\n"
            "/manual palabra_clave\n\n"
            "Ejemplos:\n"
            "/manual gpon\n"
            "/manual helix\n"
            "/manual nce\n"
            "/manual potencia\n"
            "/manual smartwifi\n"
            "/manual schaman\n\n"
        )

        texto += listar_manuales_texto()

        await enviar_texto_largo(update, texto)
        return

    consulta = " ".join(context.args).strip()

    registrar_consulta(update.effective_user.id, f"manual {consulta}")

    pdf = buscar_pdf_relacionado(consulta)

    if not pdf:
        await update.message.reply_text(
            f"No encontré manual relacionado con: {consulta}\n\n"
            "Usa /manuales para ver la lista disponible."
        )
        return

    await enviar_pdf_seguro(update, pdf)


async def estadisticas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    acceso_ok = await validar_acceso(update, "estadisticas")

    if not acceso_ok:
        return

    data = cargar_consultas()
    total = len(data)
    ultimas = data[-5:]
    top = obtener_top_consultas()

    mensaje = (
        "📊 ESTADÍSTICAS SOC\n\n"
        f"Consultas registradas: {total}\n"
        f"Entradas TXT cargadas: {len(BASE_CONOCIMIENTO)}\n"
        f"Manuales PDF cargados: {len(BASE_PDFS)}\n\n"
        "Últimas consultas:\n"
    )

    if not ultimas:
        mensaje += "Aún no hay consultas registradas.\n"
    else:
        for item in ultimas:
            consulta = item.get("consulta", "")
            mensaje += f"• {consulta}\n"

    mensaje += "\nTop consultas:\n"

    if not top:
        mensaje += "Aún no hay ranking de consultas.\n"
    else:
        for consulta, cantidad in top:
            mensaje += f"• {consulta}: {cantidad}\n"

    await enviar_texto_largo(update, mensaje)


# ========================================
# RESPONDER CONOCIMIENTO
# ========================================

def detectar_tema_inteligente(mensaje):
    mensaje = limpiar_mensaje(mensaje)

    if not mensaje:
        return None

    if "potencia" in mensaje or "rx" in mensaje or "tx" in mensaje or "dbm" in mensaje:
        return "potencia"

    if "evento masivo" in mensaje or "masiva" in mensaje or "masivas" in mensaje:
        return "evento masivo"

    if "helix" in mensaje or "ticket" in mensaje or "incidente" in mensaje:
        return "helix"

    if "smartwifi" in mensaje or "smart wifi" in mensaje:
        return "smartwifi"

    if "schaman" in mensaje or "shaman" in mensaje:
        return "schaman"

    if "nce" in mensaje:
        return "nce"

    if "gpon" in mensaje or "olt" in mensaje or "ont" in mensaje or "onu" in mensaje:
        return "gpon"

    if "fan" in mensaje or "fan sharing" in mensaje:
        return "fan sharing"

    if "acs" in mensaje or "genie" in mensaje:
        return "acs"

    if "aaa" in mensaje:
        return "aaa"

    if "broadsoft" in mensaje or "broad soft" in mensaje:
        return "broadsoft"

    return None


async def responder_conocimiento(update: Update, consulta):
    respuesta_txt = buscar_en_txt(consulta)

    if respuesta_txt:
        await enviar_texto_largo(update, respuesta_txt)
        return

    tema_detectado = detectar_tema_inteligente(consulta)

    if tema_detectado and tema_detectado != limpiar_mensaje(consulta):
        respuesta_txt = buscar_en_txt(tema_detectado)

        if respuesta_txt:
            await enviar_texto_largo(update, respuesta_txt)
            return

    respuesta_pdf = buscar_fragmentos_pdf(consulta)

    if respuesta_pdf:
        await enviar_texto_largo(update, respuesta_pdf)
        return

    await update.message.reply_text(
        "No encontré información relacionada.\n\n"
        "Puedes intentar con:\n"
        "GPON\n"
        "NCE\n"
        "HELIX\n"
        "POTENCIA\n"
        "MASIVAS\n"
        "SMARTWIFI\n"
        "SCHAMAN\n\n"
        "O puedes usar /manuales para ver los PDFs disponibles."
    )


# ========================================
# COMANDOS DIRECTOS
# ========================================

async def helix(update: Update, context: ContextTypes.DEFAULT_TYPE):
    acceso_ok = await validar_acceso(update, "helix")

    if not acceso_ok:
        return

    registrar_consulta(update.effective_user.id, "helix")
    await responder_conocimiento(update, "helix")


async def nce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    acceso_ok = await validar_acceso(update, "nce")

    if not acceso_ok:
        return

    registrar_consulta(update.effective_user.id, "nce")
    await responder_conocimiento(update, "nce")


async def smartwifi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    acceso_ok = await validar_acceso(update, "smartwifi")

    if not acceso_ok:
        return

    registrar_consulta(update.effective_user.id, "smartwifi")
    await responder_conocimiento(update, "smartwifi")


async def masivas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    acceso_ok = await validar_acceso(update, "evento masivo")

    if not acceso_ok:
        return

    registrar_consulta(update.effective_user.id, "evento masivo")
    await responder_conocimiento(update, "evento masivo")


# ========================================
# RESPUESTAS LIBRES
# ========================================

async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    mensaje_original = update.message.text.strip()
    mensaje = normalizar_boton(mensaje_original)
    user_id = update.effective_user.id

    saludos = [
        "hola",
        "buenos dias",
        "buen dia",
        "buenas tardes",
        "buenas noches"
    ]

    if mensaje in saludos:
        await update.message.reply_text(
            "👋 Hola.\n\n"
            "Soy el Assistant del SOC.",
            reply_markup=teclado_principal()
        )

        acceso_ok = await validar_acceso(update, mensaje_original)

        if not acceso_ok:
            return

        registrar_consulta(user_id, mensaje_original)
        return

    if mensaje == "id":
        await mi_id(update, context)
        return

    if mensaje == "logout":
        await logout(update, context)
        return

    if mensaje == "manuales":
        await manuales(update, context)
        return

    if mensaje == "estadisticas":
        await estadisticas(update, context)
        return

    acceso_ok = await validar_acceso(update, mensaje_original)

    if not acceso_ok:
        return

    registrar_consulta(user_id, mensaje_original)

    if mensaje_original.strip() == ACCESS_CODE:
        await update.message.reply_text(
            "✅ Ya tienes una sesión activa en el SOC Assistant.",
            reply_markup=teclado_principal()
        )
        return

    if mensaje == "manual":
        texto = (
            "Uso correcto:\n\n"
            "/manual palabra_clave\n\n"
            "Ejemplos:\n"
            "/manual gpon\n"
            "/manual helix\n"
            "/manual nce\n"
            "/manual potencia\n"
            "/manual smartwifi\n"
            "/manual schaman\n\n"
        )

        texto += listar_manuales_texto()

        await enviar_texto_largo(update, texto)
        return

    if mensaje.startswith("manual "):
        consulta_manual = mensaje.replace("manual ", "", 1).strip()

        pdf = buscar_pdf_relacionado(consulta_manual)

        if not pdf:
            await update.message.reply_text(
                f"No encontré manual relacionado con: {consulta_manual}\n\n"
                "Usa /manuales para ver la lista disponible."
            )
            return

        await enviar_pdf_seguro(update, pdf)
        return

    tema_detectado = detectar_tema_inteligente(mensaje)

    if tema_detectado:
        await responder_conocimiento(update, tema_detectado)
        return

    await responder_conocimiento(update, mensaje)


# ========================================
# MANEJO DE ERRORES
# ========================================

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    print("Error detectado:", context.error)


# ========================================
# APP
# ========================================

if not TOKEN:
    raise ValueError("No se encontró TELEGRAM_BOT_TOKEN en las variables de entorno.")


async def post_init(application):
    try:
        await application.bot.delete_webhook(
            drop_pending_updates=True
        )
        print("✅ Webhook eliminado correctamente")
    except Exception as e:
        print(f"Error eliminando webhook: {e}")


app = (
    ApplicationBuilder()
    .token(TOKEN)
    .post_init(post_init)
    .build()
)

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("menu", menu))
app.add_handler(CommandHandler("id", mi_id))
app.add_handler(CommandHandler("logout", logout))

app.add_handler(CommandHandler("agregarusuario", agregar_usuario))
app.add_handler(CommandHandler("eliminarusuario", eliminar_usuario))
app.add_handler(CommandHandler("usuarios", listar_usuarios))

app.add_handler(CommandHandler("estadisticas", estadisticas))
app.add_handler(CommandHandler("manuales", manuales))
app.add_handler(CommandHandler("manual", manual))

app.add_handler(CommandHandler("helix", helix))
app.add_handler(CommandHandler("nce", nce))
app.add_handler(CommandHandler("smartwifi", smartwifi))
app.add_handler(CommandHandler("masivas", masivas))

app.add_handler(
    MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        responder
    )
)

app.add_error_handler(error_handler)

print("Bot iniciado...")

app.run_polling(
    poll_interval=2,
    timeout=30,
    drop_pending_updates=True,
    allowed_updates=Update.ALL_TYPES
)
