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


# ========================================
# VARIABLES DE ENTORNO
# ========================================

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

ACCESS_CODE = os.getenv("ACCESS_CODE", "SOCENTEL2026")

AUTHORIZED_USER_IDS_ENV = os.getenv("AUTHORIZED_USER_IDS", "")
ADMIN_USER_IDS_ENV = os.getenv("ADMIN_USER_IDS", "")

ALLOW_ALL_USERS = os.getenv("ALLOW_ALL_USERS", "false").lower() == "true"

USERS_FILE = "usuarios_autorizados.json"


# ========================================
# SEGURIDAD
# ========================================

SESSION_FILE = "sesiones.json"

def cargar_sesiones():
    try:
        if os.path.exists(SESSION_FILE):
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
    except:
        pass

    return set()

def guardar_sesiones():
    with open(SESSION_FILE, "w", encoding="utf-8") as f:
        json.dump(list(usuarios_logueados), f)

usuarios_logueados = cargar_sesiones()


def convertir_ids_env(valor):
    ids = set()

    if valor:
        for item in valor.split(","):
            item = item.strip()

            if item.isdigit():
                ids.add(int(item))

    return ids


USUARIOS_BASE = convertir_ids_env(AUTHORIZED_USER_IDS_ENV)
ADMIN_USERS = convertir_ids_env(ADMIN_USER_IDS_ENV)

if not ADMIN_USERS:
    ADMIN_USERS = set(USUARIOS_BASE)


def cargar_usuarios_dinamicos():
    try:
        if os.path.exists(USERS_FILE):
            with open(USERS_FILE, "r", encoding="utf-8") as archivo:
                data = json.load(archivo)

            return set(int(x) for x in data.get("usuarios", []))

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
# LIMPIEZA DE TEXTO
# ========================================

def limpiar_mensaje(texto):
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


# ========================================
# BASE DE CONOCIMIENTO
# ========================================

BASE_CONOCIMIENTO = {}

try:
    with open("docs/base_conocimiento.txt", "r", encoding="utf-8") as archivo:
        contenido = archivo.read()

    # Convierte entidades HTML si existieran
    contenido = html.unescape(contenido)

    # Limpieza de saltos HTML
    contenido = contenido.replace("<br>", "\n\n")
    contenido = contenido.replace("<br/>", "\n\n")
    contenido = contenido.replace("<br />", "\n\n")
    contenido = contenido.replace("&lt;br&gt;", "\n\n")

    bloques = contenido.split("\n\n")

    for bloque in bloques:
        bloque = bloque.strip()

        if ":" in bloque:
            clave_original = bloque.split(":")[0].strip()
            clave_limpia = limpiar_mensaje(clave_original)
            BASE_CONOCIMIENTO[clave_limpia] = bloque

    print("Base de conocimiento cargada correctamente")

except Exception as e:
    print("Error cargando base de conocimiento:", e)


# ========================================
# VALIDACIÓN DE ACCESO
# ========================================

async def validar_acceso(update: Update, mensaje_original: str):

    user_id = update.effective_user.id
    usuarios_autorizados = obtener_usuarios_autorizados()

    print(f"Mensaje recibido de usuario {user_id}: {mensaje_original}")

    # Validar ID solo si ALLOW_ALL_USERS está en false
    if not ALLOW_ALL_USERS:

        if user_id not in usuarios_autorizados:

            await update.message.reply_text(
                "⛔ Usuario no autorizado.\n\n"
                f"Tu ID de Telegram es:\n{user_id}\n\n"
                "Solicita al administrador que te agregue con:\n"
                f"/agregarusuario {user_id}"
            )
            return False

    # Validar contraseña
    if user_id not in usuarios_logueados:

        if mensaje_original.strip() == ACCESS_CODE:

            usuarios_logueados.add(user_id)

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

    await update.message.reply_text(
        "👋 Hola.\n\n"
        "Soy el Assistant del SOC."
    )

    if ALLOW_ALL_USERS:

        if user_id not in usuarios_logueados:
            await update.message.reply_text(
                "🔐 Ingresa la contraseña de acceso."
            )

        return

    usuarios_autorizados = obtener_usuarios_autorizados()

    if user_id not in usuarios_autorizados:

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

        await update.message.reply_text(
            "🔒 Sesión cerrada correctamente."
        )

    else:

        await update.message.reply_text(
            "No tienes una sesión activa."
        )


# ========================================
# RESPUESTAS LIBRES
# ========================================

async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):

    mensaje_original = update.message.text.strip()
    mensaje = limpiar_mensaje(mensaje_original)
    user_id = update.effective_user.id

    # Evitar que la contraseña SOCENTEL2026 se interprete como SOC
    if mensaje_original.strip() == ACCESS_CODE and user_id in usuarios_logueados:

        await update.message.reply_text(
            "✅ Ya tienes una sesión activa en el SOC Assistant."
        )
        return

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

        return

    acceso_ok = await validar_acceso(update, mensaje_original)

    if not acceso_ok:
        return

    # Coincidencia exacta
    if mensaje in BASE_CONOCIMIENTO:

        await update.message.reply_text(
            BASE_CONOCIMIENTO[mensaje]
        )
        return

    # Coincidencia flexible
    for clave in sorted(BASE_CONOCIMIENTO.keys(), key=len, reverse=True):

        clave_limpia = limpiar_mensaje(clave)

        if clave_limpia == mensaje or clave_limpia in mensaje or mensaje in clave_limpia:

            await update.message.reply_text(
                BASE_CONOCIMIENTO[clave]
            )
            return

    await update.message.reply_text(
        "🤖 No encontré información en la base de conocimiento.\n\n"
        "Prueba con:\n"
        "SOC\n"
        "GPON\n"
        "OLT\n"
        "HELIX\n"
        "NCE\n"
        "SMARTWIFI\n"
        "FAN SHARING\n"
        "POTENCIA\n"
        "COMO VALIDAR POTENCIA\n"
        "HELIX CREAR TICKET\n"
        "NCE TROUBLESHOOTING"
    )


# ========================================
# COMANDOS DIRECTOS
# ========================================

async def helix(update: Update, context: ContextTypes.DEFAULT_TYPE):

    acceso_ok = await validar_acceso(update, "helix")

    if not acceso_ok:
        return

    clave = "helix"

    if clave in BASE_CONOCIMIENTO:
        await update.message.reply_text(BASE_CONOCIMIENTO[clave])
    else:
        await update.message.reply_text("HELIX no encontrado en la base de conocimiento.")


async def nce(update: Update, context: ContextTypes.DEFAULT_TYPE):

    acceso_ok = await validar_acceso(update, "nce")

    if not acceso_ok:
        return

    clave = "nce"

    if clave in BASE_CONOCIMIENTO:
        await update.message.reply_text(BASE_CONOCIMIENTO[clave])
    else:
        await update.message.reply_text("NCE no encontrado en la base de conocimiento.")


async def smartwifi(update: Update, context: ContextTypes.DEFAULT_TYPE):

    acceso_ok = await validar_acceso(update, "smartwifi")

    if not acceso_ok:
        return

    clave = "smartwifi"

    if clave in BASE_CONOCIMIENTO:
        await update.message.reply_text(BASE_CONOCIMIENTO[clave])
    else:
        await update.message.reply_text("SMARTWIFI no encontrado en la base de conocimiento.")


async def masivas(update: Update, context: ContextTypes.DEFAULT_TYPE):

    acceso_ok = await validar_acceso(update, "evento masivo")

    if not acceso_ok:
        return

    clave = "evento masivo"

    if clave in BASE_CONOCIMIENTO:
        await update.message.reply_text(BASE_CONOCIMIENTO[clave])
    else:
        await update.message.reply_text("EVENTO MASIVO no encontrado en la base de conocimiento.")


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

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("id", mi_id))
app.add_handler(CommandHandler("logout", logout))

app.add_handler(CommandHandler("agregarusuario", agregar_usuario))
app.add_handler(CommandHandler("eliminarusuario", eliminar_usuario))
app.add_handler(CommandHandler("usuarios", listar_usuarios))

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

app.run_polling(drop_pending_updates=True)
