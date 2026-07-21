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


# ========================================
# VARIABLES DE ENTORNO
# ========================================

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

ACCESS_CODE = os.getenv("ACCESS_CODE", "SOCENTEL2026")

AUTHORIZED_USER_IDS_ENV = os.getenv("AUTHORIZED_USER_IDS", "")
ADMIN_USER_IDS_ENV = os.getenv("ADMIN_USER_IDS", "")

USERS_FILE = "usuarios_autorizados.json"


# ========================================
# SEGURIDAD - USUARIOS
# ========================================

usuarios_logueados = set()


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

# Si no configuras ADMIN_USER_IDS, se tomarán como admin los AUTHORIZED_USER_IDS
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
                {
                    "usuarios": sorted(list(usuarios))
                },
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
# BASE DE CONOCIMIENTO
# ========================================

BASE_CONOCIMIENTO = {}

try:
    with open("docs/base_conocimiento.txt", "r", encoding="utf-8") as archivo:
        contenido = archivo.read()

    # Limpieza por si quedó algún <br>
    contenido = contenido.replace("<br>", "\n\n")

    bloques = contenido.split("\n\n")

    for bloque in bloques:
        bloque = bloque.strip()

        if ":" in bloque:
            clave = bloque.split(":")[0].strip().lower()
            BASE_CONOCIMIENTO[clave] = bloque

    print("Base de conocimiento cargada correctamente")

except Exception as e:
    print("Error cargando base de conocimiento:", e)


# ========================================
# FUNCIONES AUXILIARES
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


async def validar_acceso(update: Update, mensaje_original: str):

    user_id = update.effective_user.id
    usuarios_autorizados = obtener_usuarios_autorizados()

    # Validar si el usuario está autorizado
    if user_id not in usuarios_autorizados:

        await update.message.reply_text(
            "⛔ Usuario no autorizado.\n\n"
            f"Tu ID de Telegram es:\n{user_id}\n\n"
            "Solicita al administrador del SOC Assistant que te agregue con:\n"
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

