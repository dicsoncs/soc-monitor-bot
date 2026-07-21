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


# ========================================
# VARIABLES DE ENTORNO
# ========================================

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Contraseña del bot
# Recomendado configurarlo en Render como variable:
# ACCESS_CODE = SOCENTEL2026
ACCESS_CODE = os.getenv("ACCESS_CODE", "SOCENTEL2026")

# IDs autorizados separados por coma en Render:
# AUTHORIZED_USER_IDS = 123456789,987654321
AUTHORIZED_USER_IDS_ENV = os.getenv("AUTHORIZED_USER_IDS", "")


# ========================================
# SEGURIDAD
# ========================================

USUARIOS_AUTORIZADOS = set()

if AUTHORIZED_USER_IDS_ENV:
    for user_id in AUTHORIZED_USER_IDS_ENV.split(","):
        user_id = user_id.strip()

        if user_id.isdigit():
            USUARIOS_AUTORIZADOS.add(int(user_id))


usuarios_logueados = set()


# ========================================
# BASE DE CONOCIMIENTO
# ========================================

BASE_CONOCIMIENTO = {}

try:
    with open("docs/base_conocimiento.txt", "r", encoding="utf-8") as archivo:
        contenido = archivo.read()

    # Limpieza por si quedó algún <br> accidental
    contenido = contenido.replace("<br>", "\n\n")

    bloques = contenido.split("\n\n")

    for bloque in bloques:
        bloque = bloque.strip()

        if ":" in bloque:
            clave = bloque.split(":")[0].strip().lower()
            BASE_CONOCIMIENTO[clave] = bloque

    print("✅ Base de conocimiento cargada correctamente")

except Exception as e:
    print("❌ Error cargando base de conocimiento:", e)


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


async def validar_acceso(update: Update, mensaje: str):

    user_id = update.effective_user.id

    # Si no existen IDs configurados, igual bloqueamos por seguridad
    if not USUARIOS_AUTORIZADOS:

        await update.message.reply_text(
            "⚠️ Seguridad no configurada.\n\n"
            "No hay IDs autorizados registrados.\n\n"
            "Usa /id para obtener tu ID de Telegram y luego configúralo en Render en:\n"
            "AUTHORIZED_USER_IDS"
        )
        return False

    # Validar ID autorizado
    if user_id not in USUARIOS_AUTORIZADOS:

        await update.message.reply_text(
            "⛔ Usuario no autorizado.\n\n"
            f"Tu ID de Telegram es: {user_id}\n\n"
            "Solicita al administrador que agregue tu ID al SOC Assistant."
        )
        return False

    # Validar contraseña
    if user_id not in usuarios_logueados:

        if mensaje == ACCESS_CODE:

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

    if user_id not in USUARIOS_AUTORIZADOS:

        await update.message.reply_text(
            "🔒 Para usar el bot, primero debes estar autorizado.\n\n"
            f"Tu ID de Telegram es: {user_id}\n\n"
            "Solicita al administrador que agregue tu ID."
        )
        return

    if user_id not in usuarios_logueados:

        await update.message.reply_text(
            "🔐 Ingresa la contraseña de acceso."
        )
        return


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

    saludos = [
        "hola",
        "buenos dias",
        "buen dia",
        "buenas tardes",
        "buenas noches"
    ]

    # Responder saludo primero, como solicitaste
    if mensaje in saludos:

        await update.message.reply_text(
            "👋 Hola.\n\n"
            "Soy el Assistant del SOC."
        )

        acceso_ok = await validar_acceso(update, mensaje_original)

        if not acceso_ok:
            return

        return

    # Validar acceso antes de responder consultas
    acceso_ok = await validar_acceso(update, mensaje_original)

    if not acceso_ok:
        return

    # Buscar coincidencia exacta primero
    if mensaje in BASE_CONOCIMIENTO:

        await update.message.reply_text(
            BASE_CONOCIMIENTO[mensaje]
        )
        return

    # Buscar coincidencia dentro de frase completa
    # Se ordena por longitud para priorizar conceptos largos como "validar fan sharing"
    for clave in sorted(BASE_CONOCIMIENTO.keys(), key=len, reverse=True):

        clave_limpia = limpiar_mensaje(clave)

        if clave_limpia in mensaje:

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
        "NCE TROUBLESHOOTING\n"
        "HELIX CREAR TICKET"
    )


# ========================================
# COMANDOS DIRECTOS
# ========================================

async def helix(update: Update, context: ContextTypes.DEFAULT_TYPE):

    mensaje = "helix"
    acceso_ok = await validar_acceso(update, mensaje)

    if not acceso_ok:
        return

    if "helix" in BASE_CONOCIMIENTO:
        await update.message.reply_text(BASE_CONOCIMIENTO["helix"])
    else:
        await update.message.reply_text("HELIX no encontrado en la base de conocimiento.")


async def nce(update: Update, context: ContextTypes.DEFAULT_TYPE):

    mensaje = "nce"
    acceso_ok = await validar_acceso(update, mensaje)

    if not acceso_ok:
        return

    if "nce" in BASE_CONOCIMIENTO:
        await update.message.reply_text(BASE_CONOCIMIENTO["nce"])
    else:
        await update.message.reply_text("NCE no encontrado en la base de conocimiento.")


async def smartwifi(update: Update, context: ContextTypes.DEFAULT_TYPE):

    mensaje = "smartwifi"
    acceso_ok = await validar_acceso(update, mensaje)

    if not acceso_ok:
        return

    if "smartwifi" in BASE_CONOCIMIENTO:
        await update.message.reply_text(BASE_CONOCIMIENTO["smartwifi"])
    else:
        await update.message.reply_text("SMARTWIFI no encontrado en la base de conocimiento.")


async def masivas(update: Update, context: ContextTypes.DEFAULT_TYPE):

    mensaje = "evento masivo"
    acceso_ok = await validar_acceso(update, mensaje)

    if not acceso_ok:
        return

    if "evento masivo" in BASE_CONOCIMIENTO:
        await update.message.reply_text(BASE_CONOCIMIENTO["evento masivo"])
    else:
        await update.message.reply_text("EVENTO MASIVO no encontrado en la base de conocimiento.")


# ========================================
# APP
# ========================================

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("id", mi_id))
app.add_handler(CommandHandler("logout", logout))

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

print("🚀 Bot iniciado...")

app.run_polling()
