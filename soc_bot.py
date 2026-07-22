from telegram import Update
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

        contenido = contenido.replace("&lt;br&gt;", "\n\n")
        contenido = contenido.replace("&lt;br/&gt;", "\n\n")
        contenido = contenido.replace("&lt;br /&gt;", "\n\n")
        contenido = contenido.replace("<br>", "\n\n")
        contenido = contenido.replace("<br/>", "\n\n")
        contenido = contenido.replace("<br />", "\n\n")

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

        for numero_pagina, pagina in enumerate(reader.pages, start=1):
            try:
                texto = pagina.extract_text()

                if texto:
                    texto_total += f"\n\n[Página {numero_pagina}]\n{texto}"

            except Exception as e:
                print(f"Error leyendo página {numero_pagina} de {ruta_pdf}:", e)

    except Exception as e:
        print(f"Error leyendo PDF {ruta_pdf}:", e)

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

                    if texto_pdf and texto_pdf.strip():
                        BASE_PDFS.append(
                            {
                                "archivo": archivo,
                                "ruta": ruta_pdf,
                                "texto": texto_pdf,
                                "texto_limpio": limpiar_mensaje(texto_pdf)
                            }
                        )

                        print(f"PDF cargado correctamente: {archivo}")
                    else:
                        print(f"PDF sin texto extraíble o escaneado: {archivo}")

        print(f"PDFs encontrados: {total_pdfs}")
        print(f"PDFs con texto cargado: {len(BASE_PDFS)}")

    except Exception as e:
        print("Error cargando PDFs:", e)


def buscar_en_pdfs(consulta):
    resultados = []
    consulta_limpia = limpiar_mensaje(consulta)

    if not consulta_limpia:
        return resultados

    palabras = consulta_limpia.split()

    for pdf in BASE_PDFS:
        texto_limpio = pdf["texto_limpio"]

        coincidencia = False

        if consulta_limpia in texto_limpio:
            coincidencia = True
        else:
            coincidencias_palabras = 0

            for palabra in palabras:
                if len(palabra) >= 3 and palabra in texto_limpio:
                    coincidencias_palabras += 1

            if coincidencias_palabras >= 1:
                coincidencia = True

        if coincidencia:
            texto_original = pdf["texto"]

            posicion = texto_limpio.find(consulta_limpia)

            if posicion >= 0:
                inicio = max(0, posicion - 500)
                fin = min(len(texto_original), posicion + 1000)
                fragmento = texto_original[inicio:fin]
            else:
                fragmento = texto_original[:1300]

            resultados.append(
                {
                    "archivo": pdf["archivo"],
                    "fragmento": cortar_texto(fragmento, 1000)
                }
            )

        if len(resultados) >= MAX_RESULTS:
            break

    return resultados


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

    # Si el usuario está autorizado por ENV o es admin, se loguea automático.
    # Esto evita que a tu usuario principal le pida contraseña después de cada deploy.
    if user_id in usuarios_autorizados or user_id in ADMIN_USERS:
        if user_id not in usuarios_logueados:
            usuarios_logueados.add(user_id)
            guardar_sesiones()
        return True

    # Si ALLOW_ALL_USERS está en false, bloquear usuarios no autorizados
    if not ALLOW_ALL_USERS:
        await update.message.reply_text(
            "⛔ Usuario no autorizado.\n\n"
            f"Tu ID de Telegram es:\n{user_id}\n\n"
            "Solicita al administrador que te agregue con:\n"
            f"/agregarusuario {user_id}"
        )
        return False

    # Si ALLOW_ALL_USERS está en true, permitir acceso con contraseña
    if user_id not in usuarios_logueados:
        if mensaje_original.strip() == ACCESS_CODE:
            usuarios_logueados.add(user_id)
            guardar_sesiones()

            await update.message.reply_text(
                "✅ Acceso autorizado.\n\n"
                "Bienvenido al SOC Assistant."
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
            "Puedes usar /menu para ver las opciones disponibles."
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
        "Puedes usar /menu para ver las opciones disponibles."
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
"""

    await update.message.reply_text(texto)


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

    await update.message.reply_text(texto)


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

    await update.message.reply_text(mensaje)


# ========================================
# COMANDOS DIRECTOS
# ========================================

async def helix(update: Update, context: ContextTypes.DEFAULT_TYPE):
    acceso_ok = await validar_acceso(update, "helix")

    if not acceso_ok:
        return

    await responder_por_clave(update, "helix")


async def nce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    acceso_ok = await validar_acceso(update, "nce")

    if not acceso_ok:
        return

    await responder_por_clave(update, "nce")


async def smartwifi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    acceso_ok = await validar_acceso(update, "smartwifi")

    if not acceso_ok:
        return

    await responder_por_clave(update, "smartwifi")


async def masivas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    acceso_ok = await validar_acceso(update, "evento masivo")

    if not acceso_ok:
        return

    await responder_por_clave(update, "evento masivo")


async def responder_por_clave(update: Update, clave):
    clave_limpia = limpiar_mensaje(clave)

    if clave_limpia in BASE_CONOCIMIENTO:
        await update.message.reply_text(BASE_CONOCIMIENTO[clave_limpia])
        return

    resultados_pdf = buscar_en_pdfs(clave)

    if resultados_pdf:
        respuesta = "📚 Encontré información en manuales PDF:\n\n"

        for resultado in resultados_pdf:
            respuesta += f"📄 Manual: {resultado['archivo']}\n"
            respuesta += f"{resultado['fragmento']}\n\n"

        await update.message.reply_text(respuesta[:3900])
        return

    await update.message.reply_text(
        f"🤖 No encontré información relacionada con: {clave}"
    )


# ========================================
# RESPUESTAS LIBRES
# ========================================

async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensaje_original = update.message.text.strip()
    mensaje = limpiar_mensaje(mensaje_original)
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
            "Soy el Assistant del SOC."
        )

        acceso_ok = await validar_acceso(update, mensaje_original)

        if not acceso_ok:
            return

        registrar_consulta(user_id, mensaje_original)
        return

    acceso_ok = await validar_acceso(update, mensaje_original)

    if not acceso_ok:
        return

    registrar_consulta(user_id, mensaje_original)

    # Evitar que la contraseña se interprete como consulta
    if mensaje_original.strip() == ACCESS_CODE:
        await update.message.reply_text(
            "✅ Ya tienes una sesión activa en el SOC Assistant."
        )
        return

    # Coincidencia exacta TXT
    if mensaje in BASE_CONOCIMIENTO:
        await update.message.reply_text(
            BASE_CONOCIMIENTO[mensaje]
        )
        return

    # Coincidencia flexible TXT
    for clave in sorted(BASE_CONOCIMIENTO.keys(), key=len, reverse=True):
        clave_limpia = limpiar_mensaje(clave)

        if clave_limpia == mensaje or clave_limpia in mensaje or mensaje in clave_limpia:
            await update.message.reply_text(
                BASE_CONOCIMIENTO[clave]
            )
            return

    # Búsqueda en PDFs
    resultados_pdf = buscar_en_pdfs(mensaje_original)

    if resultados_pdf:
        respuesta = "📚 Encontré información en manuales PDF:\n\n"

        for resultado in resultados_pdf:
            respuesta += f"📄 Manual: {resultado['archivo']}\n"
            respuesta += f"{resultado['fragmento']}\n\n"

        await update.message.reply_text(respuesta[:3900])
        return

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
        "BROADS0FT\n"
        "MASIVAS\n"
        "COMO VALIDAR POTENCIA\n"
        "HELIX CREAR TICKET\n"
        "NCE TROUBLESHOOTING"
    )


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

