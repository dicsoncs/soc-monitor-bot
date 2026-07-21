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

except Exception as e:
    print("Error cargando base de conocimiento:", e)

# ========================================
# START
# ========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hola.\n\n"
        "Soy el SOC Assistant.\n\n"
        "Puedes consultarme:\n"
        "LOS\n"
        "OLT\n"
        "NAP\n"
        "SOC\n"
        "HELIX\n"
        "POTENCIA"
    )

# ========================================
# RESPUESTAS LIBRES
# ========================================

async def responder(update: Update, context: ContextTypes.DEFAULT_TYPE):

    mensaje = update.message.text.lower()

    if any(palabra in mensaje for palabra in [
        "hola",
        "buenos dias",
        "buen día",
        "buenas tardes",
        "buenas noches"
    ]):
        await update.message.reply_text(
            "👋 Hola.\n\n"
            "Soy el SOC Assistant."
        )
        return

    for clave, respuesta in BASE_CONOCIMIENTO.items():

        if clave in mensaje:
            await update.message.reply_text(respuesta)
            return

    await update.message.reply_text(
        "🤖 No encontré información en la base de conocimiento."
    )

# ========================================
# COMANDOS
# ========================================

async def helix(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Escribe HELIX o pregunta sobre tickets."
    )

async def nce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Escribe POTENCIA o LOS."
    )

async def smartwifi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Consulta SmartWiFi."
    )

async def masivas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Consulta eventos masivos."
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
