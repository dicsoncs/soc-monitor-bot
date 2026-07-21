from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters
)

import os

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# ========================================
# CARGAR BASE DE CONOCIMIENTO
# ========================================

BASE_CONOCIMIENTO = {}

try:
    with open("docs/base_conocimiento.txt", "r", encoding="utf-8") as archivo:
        contenido = archivo.read()

    bloques = contenido.split("\n\n")

    for bloque in bloques:
        if ":" in bloque:
            clave = bloque.split(":")[0].strip().lower()
            BASE_CONOCIMIENTO[clave] = bloque

    print("Base de conocimiento cargada correctamente")

except Exception as e:
    print("Error cargando base de conocimiento:", e)

# ========================================
# START
# ========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "👋 Hola.\n\n"
        "Soy el SOC Assistant.\n\n"
        "Consultas disponibles:\n"
        "SOC\n"
        "TAC\n"
        "NOC\n"
        "OLT\n"
        "NAP\n"
        "ONU\n"
        "GPON\n"
        "HELIX\n"
        "NCE\n"
        "SMARTWIFI\n"
        "LOS\n"
        "TCM"
    )

# ========================================
# RESPUESTAS LIBRES
# ========================================

async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):

    mensaje = update.message.text.lower().strip()

    # Saludos
    if mensaje in [
        "hola",
        "buenos dias",
        "buen día",
        "buenas tardes",
        "buenas noches"
    ]:

        await update.message.reply_text(
            "👋 Hola.\n\n"
            "Soy el SOC Assistant."
        )
        return

    # Buscar coincidencia EXACTA
    if mensaje in BASE_CONOCIMIENTO:

        await update.message.reply_text(
            BASE_CONOCIMIENTO[mensaje]
        )
        return

    await update.message.reply_text(
        "🤖 No encontré información en la base de conocimiento.\n\n"
        "Intenta con:\n"
        "SOC\n"
        "TAC\n"
        "NOC\n"
        "GPON\n"
        "ONU\n"
        "OLT\n"
        "HELIX"
    )

# ========================================
# COMANDOS
# ========================================

async def helix(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "Escribe HELIX para ver la definición."
    )

async def nce(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "Escribe NCE para consultar la plataforma."
    )

async def smartwifi(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "Escribe SMARTWIFI para consultar información."
    )

async def masivas(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "Escribe EVENTO MASIVO para consultar el procedimiento."
    )

# ========================================
# APP
# ========================================

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
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

print("Bot iniciado...")

app.run_polling()
