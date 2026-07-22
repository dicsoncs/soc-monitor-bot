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

ALLOW_ALL_USERS = os.getenv("ALLOW_ALL_USERS", "false").lower() == "true"

DOCS_PATH = os.getenv("DOCS_PATH", "docs/manuales_pdf")
MAX_RESULTS = int(os.getenv("MAX_RESULTS", "4"))

USERS_FILE = "usuarios_autorizados.json"
SESSION_FILE = "sesiones.json"
CONSULTAS_FILE = "consultas.json"

BASE_TXT_PATH = "docs/base_conocimiento.txt"


# ========================================
# FUNCIONES GENERALES
# ========================================

def limpiar_mensaje(texto):
    if not texto:
        return ""

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


def cortar_texto(texto, limite=900):
    texto = texto.strip()

    if len(texto) <= limite:
        return texto

    return texto[:limite].strip() + "..."


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

    texto = texto.strip()

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
        "🌐 nce": "nce",
        "🎫 helix": "helix",
        "📶 smartwifi": "smartwifi",
        "⚡ potencia": "potencia",
        "🚨 masivas": "evento masivo",
        "📚 manuales": "manuales",
        "📊 estadisticas": "estadisticas",
        "🆔 mi id": "id",
        "🚪 logout": "logout"
    }

    return reemplazos.get(texto_limpio, texto_limpio)


# ========================================
# FUNCIONES DE SESIÓN
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
# FUNCIONES DE USUARIOS
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

        contenido = html.unescape(contenido)

        contenido = contenido.replace("<br>", "\n\n")
        contenido = contenido.replace("<br/>", "\n\n")
        contenido = contenido.replace("<br />", "\n\n")
        contenido = contenido.replace("&lt;br&gt;", "\n\n")
        contenido = contenido.replace("&lt;br/&gt;", "\n\n")
        contenido = contenido.replace("&lt;br /&gt;", "\n\n")

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

                    BASE_PDFS.append(
                        {
                            "archivo": archivo,
                            "ruta": ruta_pdf,
                            "texto": texto_pdf,
                            "texto_limpio": limpiar_mensaje(texto_pdf),
                            "archivo_limpio": limpiar_mensaje(archivo)
                        }
                    )

                    if texto_pdf and texto_pdf.strip():
                        print(f"PDF cargado correctamente: {archivo}")
                    else:
                        print(f"PDF sin texto extraíble o escaneado: {archivo}")

        print(f"PDFs encontrados: {total_pdfs}")
        print(f"PDFs con texto cargado: {len([p for p in BASE_PDFS if p['texto'].strip()])}")

    except Exception as e:
        print("Error cargando PDFs:", e)


def puntuar_pdf(pdf, consulta_limpia, palabras):
    puntaje = 0

    archivo_limpio = pdf.get("archivo_limpio", "")
    texto_limpio = pdf.get("texto_limpio", "")

    if consulta_limpia in archivo_limpio:
        puntaje += 10

    if consulta_limpia in texto_limpio:
        puntaje += 6

    for palabra in palabras:
        if len(palabra) >= 3:
            if palabra in archivo_limpio:
                puntaje += 4

            if palabra in texto_limpio:
                puntaje += 1

    sinonimos = {
        "gpon": ["gpon", "ncegpon", "olt", "ont", "fibra"],
        "helix": ["helix", "ticket", "incidente"],
        "nce": ["nce", "troubleshooting", "diagnostico"],
        "smartwifi": ["smartwifi", "smart wifi", "wifi"],
        "fan sharing": ["fan sharing", "fan"],
        "potencia": ["potencia", "rx", "tx", "dbm", "ont", "olt"],
        "masivas": ["masiva", "masivas", "evento masivo", "clientes caidos"],
        "evento masivo": ["masiva", "masivas", "evento masivo", "clientes caidos"],
        "acs": ["acs", "genie"],
        "broadsoft": ["broadsoft"]
    }

    for clave, valores in sinonimos.items():
        if clave in consulta_limpia:
            for valor in valores:
                valor_limpio = limpiar_mensaje(valor)

                if valor_limpio in archivo_limpio:
                    puntaje += 5

                if valor_limpio in texto_limpio:
                    puntaje += 2

    return puntaje


def buscar_en_pdfs(consulta, limite=None):
    resultados = []
    consulta_limpia = limpiar_mensaje(consulta)

    if not consulta_limpia:
        return resultados

    if limite is None:
        limite = MAX_RESULTS

    palabras = consulta_limpia.split()

    candidatos = []

    for pdf in BASE_PDFS:
        puntaje = puntuar_pdf(pdf, consulta_limpia, palabras)

        if puntaje > 0:
            candidatos.append((puntaje, pdf))

    candidatos = sorted(
        candidatos,
        key=lambda x: x[0],
        reverse=True
    )

    for puntaje, pdf in candidatos[:limite]:
        texto_original = pdf.get("texto", "")
        texto_limpio = pdf.get("texto_limpio", "")

        fragmento = ""

        if texto_original.strip():
            posicion = texto_limpio.find(consulta_limpia)

            if posicion >= 0:
                inicio = max(0, posicion - 500)
                fin = min(len(texto_original), posicion + 1200)
                fragmento = texto_original[inicio:fin]
            else:
                fragmento = texto_original[:1300]
        else:
            fragmento = "El manual fue encontrado, pero parece ser escaneado o no tiene texto extraíble."

        resultados.append(
            {
                "archivo": pdf["archivo"],
                "ruta": pdf["ruta"],
                "fragmento": cortar_texto(fragmento, 1000),
                "puntaje": puntaje
            }
        )

    return resultados


async def enviar_documentos_pdf(update: Update, resultados_pdf, limite=2):
    enviados = 0
    archivos_enviados = set()

    for resultado in resultados_pdf:
        if enviados >= limite:
            break

        ruta = resultado.get("ruta")
        archivo = resultado.get("archivo")

        if not ruta or not os.path.exists(ruta):
            continue

        if archivo in archivos_enviados:
            continue

        try:
            with open(ruta, "rb") as f:
                await update.message.reply_document(
                    document=f,
                    filename=archivo,
                    caption=f"📄 Manual relacionado: {archivo}"
                )

            archivos_enviados.add(archivo)
            enviados += 1

        except Exception as e:
            print(f"Error enviando PDF {archivo}: {e}")


# ========================================
# CARGA INICIAL DE CONOCIMIENTO
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
# COMANDO /ID
# ========================================

async def mi_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    await update.message.reply_text(
        f"Tu ID de Telegram es:\n\n{user_id}"
    )


# ========================================
# COMANDO /START
# ========================================

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


# ========================================
# COMANDO /AGREGARUSUARIO
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
            "⚠️ El ID debe ser numérico.\n\n"
            "Ejemplo:\n"
            "/agregarusuario 123456789"
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


# ========================================
# COMANDO /ELIMINARUSUARIO
# ========================================

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
            "/eliminarusuario ID_TELEGRAM\n\n"
            "Ejemplo:\n"
            "/eliminarusuario 123456789"
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


# ========================================
# COMANDO /USUARIOS
# ========================================

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

    await update.message.reply_text(texto)


# ========================================
# COMANDO /LOGOUT
# ========================================

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
# COMANDO /MENU
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

═══════════════════════

COMANDOS DIRECTOS

/helix
/nce
/smartwifi
/masivas

═══════════════════════

EJEMPLOS

manual gpon
manual helix
manual potencia
como crear ticket helix
nce troubleshooting
validar potencia ont
evento masivo gpon
"""

    await update.message.reply_text(
        texto,
        reply_markup=teclado_principal()
    )


# ========================================
# COMANDO /MANUALES
# ========================================

async def manuales(update: Update, context: ContextTypes.DEFAULT_TYPE):
    acceso_ok = await validar_acceso(update, "manuales")

    if not acceso_ok:
        return

    if not BASE_PDFS:
        await update.message.reply_text(
            "⚠️ No hay manuales PDF cargados.\n\n"
            "Verifica lo siguiente:\n"
            "1. Que DOCS_PATH sea docs/manuales_pdf\n"
            "2. Que los PDF estén subidos a GitHub\n"
            "3. Que PyPDF2 esté en requirements.txt"
        )
        return

    texto = "📚 Manuales PDF cargados:\n\n"

    for pdf in BASE_PDFS:
        texto += f"• {pdf['archivo']}\n"

    texto += "\nPara buscar un manual usa:\n"
    texto += "/manual gpon\n"
    texto += "/manual helix\n"
    texto += "/manual nce\n"
    texto += "/manual potencia\n"

    await update.message.reply_text(texto)


# ========================================
# COMANDO /MANUAL
# ========================================

async def manual(update: Update, context: ContextTypes.DEFAULT_TYPE):
    acceso_ok = await validar_acceso(update, "manual")

    if not acceso_ok:
        return

    if not context.args:
        await update.message.reply_text(
            "Uso correcto:\n\n"
            "/manual palabra_clave\n\n"
            "Ejemplos:\n"
            "/manual gpon\n"
            "/manual helix\n"
            "/manual nce\n"
            "/manual potencia"
        )
        return

    consulta = " ".join(context.args).strip()

    registrar_consulta(update.effective_user.id, f"manual {consulta}")

    resultados_pdf = buscar_en_pdfs(consulta, limite=3)

    if not resultados_pdf:
        await update.message.reply_text(
            f"🤖 No encontré manual relacionado con: {consulta}"
        )
        return

    respuesta = f"📚 Manuales relacionados con: {consulta}\n\n"

    for resultado in resultados_pdf:
        respuesta += f"📄 Manual: {resultado['archivo']}\n"
        respuesta += f"{resultado['fragmento']}\n\n"

    await enviar_texto_largo(update, respuesta)

    await enviar_documentos_pdf(
        update,
        resultados_pdf,
        limite=2
    )


# ========================================
# COMANDO /ESTADISTICAS
# ========================================

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

    await update.message.reply_text(mensaje)


# ========================================
# RESPONDER CON TXT + PDF
# ========================================

async def responder_conocimiento(update: Update, consulta):
    respuesta_txt = buscar_en_txt(consulta)
    resultados_pdf = buscar_en_pdfs(consulta, limite=MAX_RESULTS)

    hubo_respuesta = False

    if respuesta_txt:
        await enviar_texto_largo(
            update,
            f"📌 Información encontrada en base SOC:\n\n{respuesta_txt}"
        )
        hubo_respuesta = True

    if resultados_pdf:
        respuesta_pdf = "📚 Información relacionada en manuales PDF:\n\n"

        for resultado in resultados_pdf:
            respuesta_pdf += f"📄 Manual: {resultado['archivo']}\n"
            respuesta_pdf += f"{resultado['fragmento']}\n\n"

        await enviar_texto_largo(update, respuesta_pdf)
        await enviar_documentos_pdf(update, resultados_pdf, limite=2)

        hubo_respuesta = True

    if not hubo_respuesta:
        await update.message.reply_text(
            "🤖 No encontré información en la base de conocimiento ni en los manuales PDF.\n\n"
            "Prueba con:\n"
            "SOC\n"
            "GPON\n"
            "OLT\n"
            "ONT\n"
            "HELIX\n"
            "NCE\n"
            "SMARTWIFI\n"
            "FAN SHARING\n"
            "POTENCIA\n"
            "ACS\n"
            "BROADSOFT\n"
            "MASIVAS\n"
            "COMO VALIDAR POTENCIA\n"
            "HELIX CREAR TICKET\n"
            "NCE TROUBLESHOOTING\n\n"
            "También puedes usar:\n"
            "/manual gpon\n"
            "/manual helix\n"
            "/manual potencia"
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

    if mensaje.startswith("manual "):
        consulta_manual = mensaje.replace("manual ", "", 1).strip()

        resultados_pdf = buscar_en_pdfs(consulta_manual, limite=3)

        if not resultados_pdf:
            await update.message.reply_text(
                f"🤖 No encontré manual relacionado con: {consulta_manual}"
            )
            return

        respuesta = f"📚 Manuales relacionados con: {consulta_manual}\n\n"

        for resultado in resultados_pdf:
            respuesta += f"📄 Manual: {resultado['archivo']}\n"
            respuesta += f"{resultado['fragmento']}\n\n"

        await enviar_texto_largo(update, respuesta)
        await enviar_documentos_pdf(update, resultados_pdf, limite=2)
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
    drop_pending_updates=True,
    allowed_updates=Update.ALL_TYPES
)
