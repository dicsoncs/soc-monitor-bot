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
# START
# ========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hola.\n\n"
        "Soy el SOC Assistant.\n"
        "Bot SOC funcionando correctamente.\n\n"
        "Comandos disponibles:\n"
        "/helix\n"
        "/nce\n"
        "/smartwifi\n"
        "/masivas"
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
            "Soy el SOC Assistant.\n\n"
            "Puedo ayudarte con:\n"
            "✅ HELIX\n"
            "✅ NCE GPON\n"
            "✅ SmartWiFi\n"
            "✅ Eventos Masivos\n\n"
            "Ejemplos:\n"
            "/nce potencia\n"
            "/helix ticket"
        )

    elif "los" in mensaje:

        await update.message.reply_text(
            "📘 LOS = Loss Of Signal.\n\n"
            "Corresponde a una pérdida de señal óptica."
        )

    elif "potencia" in mensaje:

        await update.message.reply_text(
            "📘 Potencia Óptica\n\n"
            "1. Ingresar al servicio.\n"
            "2. ONU Optical Module Info.\n"
            "3. Revisar Rx Optical Power.\n"
            "4. Valor recomendado hasta -23 dBm."
        )

    elif "ticket" in mensaje:

        await update.message.reply_text(
            "📘 HELIX - Creación de Ticket\n\n"
            "1. Ingresar a Aplicaciones.\n"
            "2. Crear incidencia.\n"
            "3. Asociar OLT.\n"
            "4. Seleccionar Torre de Control.\n"
            "5. Asignar a TCM.\n"
            "6. Adjuntar evidencia."
        )

    elif "olt" in mensaje:

        await update.message.reply_text(
            "📘 Caída de OLT\n\n"
            "1. Validar alarmas.\n"
            "2. Revisar energía.\n"
            "3. Verificar uplinks.\n"
            "4. Escalar al equipo correspondiente."
        )

    elif "nap" in mensaje:

        await update.message.reply_text(
            "📘 Caída de NAP\n\n"
            "1. Validar clientes afectados.\n"
            "2. Identificar OLT.\n"
            "3. Registrar incidente.\n"
            "4. Escalar a TCM.\n"
            "5. Notificar involucrados."
        )

    else:

        await update.message.reply_text(
            "🤖 Consulta recibida.\n\n"
            "Aún estoy aprendiendo.\n"
            "Próximamente responderé más consultas del SOC."
        )


# ========================================
# HELIX
# ========================================

async def helix(update: Update, context: ContextTypes.DEFAULT_TYPE):

    consulta = " ".join(context.args).lower()

    if not consulta:

        await update.message.reply_text(
            "✅ Consulta HELIX recibida\n\n"
            "Ejemplos:\n"
            "/helix ticket\n"
            "/helix tcm"
        )
        return

    if "ticket" in consulta:

        await update.message.reply_text(
            "📘 MANUAL HELIX\n\n"
            "Creación de Ticket:\n"
            "1. Ingresar a Aplicaciones.\n"
            "2. Crear nueva incidencia.\n"
            "3. Asociar OLT afectada.\n"
            "4. Seleccionar Torre de Control.\n"
            "5. Asignar a TCM.\n"
            "6. Adjuntar evidencias."
        )

    elif "tcm" in consulta:

        await update.message.reply_text(
            "📘 MANUAL HELIX\n\n"
            "La notificación a TCM se realiza mediante ticket HELIX y evidencia adjunta."
        )

    else:

        await update.message.reply_text(
            f"🔍 No encontré una regla para: {consulta}"
        )


# ========================================
# NCE
# ========================================

async def nce(update: Update, context: ContextTypes.DEFAULT_TYPE):

    consulta = " ".join(context.args).lower()

    if not consulta:

        await update.message.reply_text(
            "✅ Consulta NCE GPON recibida\n\n"
            "Ejemplos:\n"
            "/nce potencia\n"
            "/nce los"
        )
        return

    if "potencia" in consulta:

        await update.message.reply_text(
            "📘 MANUAL NCE GPON\n\n"
            "Verificación de Potencia Óptica:\n"
            "1. Ingresar al servicio.\n"
            "2. ONU Optical Module Info.\n"
            "3. Revisar Rx Optical Power.\n"
            "4. Valor recomendado hasta -23 dBm."
        )

    elif "los" in consulta:

        await update.message.reply_text(
            "📘 MANUAL NCE GPON\n\n"
            "LOS = Loss Of Signal.\n"
            "Corresponde a una pérdida de señal óptica."
        )

    else:

        await update.message.reply_text(
            f"🔍 No encontré una regla para: {consulta}"
        )


# ========================================
# SMARTWIFI
# ========================================

async def smartwifi(update: Update, context: ContextTypes.DEFAULT_TYPE):

    consulta = " ".join(context.args).lower()

    if not consulta:

        await update.message.reply_text(
            "✅ Consulta SmartWiFi recibida\n\n"
            "Ejemplos:\n"
            "/smartwifi fibra\n"
            "/smartwifi energia"
        )
        return

    if "fibra" in consulta:

        await update.message.reply_text(
            "📘 SMARTWIFI\n\n"
            "Alarma de Fibra:\n"
            "1. Revisar Event List.\n"
            "2. Validar ONT.\n"
            "3. Confirmar última conexión."
        )

    elif "energia" in consulta:

        await update.message.reply_text(
            "📘 SMARTWIFI\n\n"
            "Verificar reinicios ocasionados por pérdida de energía."
        )

    else:

        await update.message.reply_text(
            f"🔍 No encontré una regla para: {consulta}"
        )


# ========================================
# MASIVAS
# ========================================

async def masivas(update: Update, context: ContextTypes.DEFAULT_TYPE):

    consulta = " ".join(context.args).lower()

    if not consulta:

        await update.message.reply_text(
            "✅ Consulta Eventos Masivos\n\n"
            "Ejemplos:\n"
            "/masivas nap\n"
            "/masivas olt"
        )
        return

    if "nap" in consulta:

        await update.message.reply_text(
            "📘 EVENTO MASIVO GPON\n\n"
            "1. Validar impacto.\n"
            "2. Identificar OLT.\n"
            "3. Registrar incidente.\n"
            "4. Escalar a TCM."
        )

    elif "olt" in consulta:

        await update.message.reply_text(
            "📘 EVENTO MASIVO GPON\n\n"
            "1. Validar alarmas.\n"
            "2. Revisar energía.\n"
            "3. Verificar uplinks.\n"
            "4. Escalar al equipo correspondiente."
        )

    else:

        await update.message.reply_text(
            f"🔍 No encontré una regla para: {consulta}"
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
