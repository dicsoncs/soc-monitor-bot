from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes
)

TOKEN = "8576334407:AAGheqz_tQ8UzoCrMc5R2ELotcxGb-_7E-g"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hola 👋\nBot SOC funcionando correctamente."
    )

async def helix(update: Update, context: ContextTypes.DEFAULT_TYPE):

    consulta = " ".join(context.args).lower()

    if not consulta:
        await update.message.reply_text(
            "✅ Consulta HELIX recibida\n\n"
            "Ejemplos:\n"
            "/helix crear ticket\n"
            "/helix derivacion tcm"
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

async def nce(update: Update, context: ContextTypes.DEFAULT_TYPE):

    consulta = " ".join(context.args).lower()

    if not consulta:
        await update.message.reply_text(
            "✅ Consulta NCE GPON recibida\n\n"
            "Ejemplos:\n"
            "/nce potencia optica\n"
            "/nce alarma los"
        )
        return

    if "potencia" in consulta:

        await update.message.reply_text(
            "📘 MANUAL NCE GPON\n\n"
            "Verificación de Potencia Óptica:\n"
            "1. Ingresar al servicio.\n"
            "2. Seleccionar ONU Optical Module Info.\n"
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
        return

    if "potencia" in consulta:

        await update.message.reply_text(
            "📘 MANUAL NCE GPON\n\n"
            "Verificación de Potencia Óptica:\n"
            "1. Ingresar al servicio.\n"
            "2. Seleccionar ONU Optical Module Info.\n"
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

async def smartwifi(update: Update, context: ContextTypes.DEFAULT_TYPE):

    consulta = " ".join(context.args).lower()

    if not consulta:
        await update.message.reply_text(
            "✅ Consulta SmartWiFi recibida\n\n"
            "Ejemplos:\n"
            "/smartwifi alarma fibra\n"
            "/smartwifi alarma energia"
        )
        return

    if "fibra" in consulta:

        await update.message.reply_text(
            "📘 MANUAL SMARTWIFI\n\n"
            "Alarma de Fibra:\n"
            "1. Ingresar a Event List.\n"
            "2. Revisar eventos de fibra.\n"
            "3. Validar estado ONT.\n"
            "4. Confirmar última conexión del servicio."
        )

    elif "energia" in consulta:

        await update.message.reply_text(
            "📘 MANUAL SMARTWIFI\n\n"
            "Alarma de Energía:\n"
            "Verificar reinicios ocasionados por pérdida de energía o apagado de ONT."
        )

    else:

        await update.message.reply_text(
            f"🔍 No encontré una regla para: {consulta}"
        )

async def masivas(update: Update, context: ContextTypes.DEFAULT_TYPE):

    consulta = " ".join(context.args).lower()

    if not consulta:
        await update.message.reply_text(
            "✅ Consulta Eventos Masivos recibida\n\n"
            "Ejemplos:\n"
            "/masivas caida nap\n"
            "/masivas caida olt"
        )
        return

    if "nap" in consulta:

        await update.message.reply_text(
            "📘 EVENTO MASIVO GPON\n\n"
            "Caída de NAP:\n"
            "1. Validar impacto de clientes.\n"
            "2. Identificar OLT asociada.\n"
            "3. Registrar incidente.\n"
            "4. Escalar a TCM.\n"
            "5. Notificar a las áreas involucradas."
        )

    elif "olt" in consulta:

        await update.message.reply_text(
            "📘 EVENTO MASIVO GPON\n\n"
            "Caída de OLT:\n"
            "1. Validar alarmas.\n"
            "2. Revisar energía.\n"
            "3. Verificar uplinks.\n"
            "4. Escalar al equipo correspondiente."
        )

    else:

        await update.message.reply_text(
            f"🔍 No encontré una regla para: {consulta}"
        )
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("helix", helix))
app.add_handler(CommandHandler("nce", nce))
app.add_handler(CommandHandler("smartwifi", smartwifi))
app.add_handler(CommandHandler("masivas", masivas))

print("Bot iniciado...")

app.run_polling()