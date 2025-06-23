import logging
import os
import random
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes
)
from telegram.ext._application import Application
from fastapi import FastAPI, Request
import telegram
import asyncio
from fastapi.responses import HTMLResponse

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

ASK_PAIN, ASK_LEVEL = range(2)

PAIN_SOLUTIONS = {
    "headache": {
        "remedy": "Drink a glass of water and rest. A warm compress helps too.",
        "tablet": "Take Paracetamol if needed."
    },
    "stomachache": {
        "remedy": "Warm water and ginger tea help.",
        "tablet": "Try Meftal-Spas after food."
    },
    "cold": {
        "remedy": "Inhale steam and rest warm.",
        "tablet": "Cetirizine works well."
    },
    "fever": {
        "remedy": "Cool cloth and hydration.",
        "tablet": "Paracetamol is okay."
    }
}

MOM_ANIMATIONS = {
    "greeting": ["https://media.giphy.com/media/26ufdipQqU2lhNA4g/giphy.gif"],
    "comfort": ["https://media.giphy.com/media/3o6ZtpxSZbQRRnwCKQ/giphy.gif"],
    "encourage": ["https://media.giphy.com/media/3oKIPwoeGErMmaI43C/giphy.gif"]
}

MOM_BACKGROUNDS = ["\n" + "🌸" * 10 + "\n"]

# ---------------- Telegram Handlers -------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gif = random.choice(MOM_ANIMATIONS["greeting"])
    bg = random.choice(MOM_BACKGROUNDS)
    await update.message.reply_animation(
        gif,
        caption=bg + "Welcome beta! Tell me your pain. (e.g., headache, fever)" + bg
    )
    return ASK_PAIN

async def ask_pain(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pain = update.message.text.lower()
    context.user_data['pain'] = pain
    gif = random.choice(MOM_ANIMATIONS["comfort"])
    bg = random.choice(MOM_BACKGROUNDS)
    await update.message.reply_animation(
        gif,
        caption=bg + f"Oh no! {pain}? Tell me how much it hurts (1-10)." + bg
    )
    return ASK_LEVEL

async def ask_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        level = int(update.message.text)
    except:
        await update.message.reply_text("Beta, give me a number from 1 to 10.")
        return ASK_LEVEL
    pain = context.user_data.get('pain', 'pain')
    solution = PAIN_SOLUTIONS.get(pain, {
        "remedy": "Rest and drink warm water.",
        "tablet": "Paracetamol is generally safe."
    })
    gif = random.choice(MOM_ANIMATIONS["encourage"])
    bg = random.choice(MOM_BACKGROUNDS)
    await update.message.reply_animation(
        gif,
        caption=bg + f"Pain level: {level}/10\n🌼 Home Remedy: {solution['remedy']}\n💊 Tablet: {solution['tablet']}" + bg
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Take care, beta!")
    return ConversationHandler.END

# ------------------- FastAPI -------------------------

app = FastAPI()
telegram_app: Application = None

@app.on_event("startup")
async def startup():
    global telegram_app
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    webhook_url = os.getenv("WEBHOOK_URL")
    if not token or not webhook_url:
        print("❌ TELEGRAM_BOT_TOKEN or WEBHOOK_URL not set.")
        return
    telegram_app = ApplicationBuilder().token(token).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_PAIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_pain)],
            ASK_LEVEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_level)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    telegram_app.add_handler(conv)

    await telegram_app.bot.set_webhook(webhook_url)
    asyncio.create_task(telegram_app.initialize())
    print(f"✅ Webhook set to {webhook_url}")

@app.post("/api/webhook")
async def receive_webhook(request: Request):
    data = await request.json()
    update = telegram.Update.de_json(data, telegram_app.bot)
    await telegram_app.process_update(update)
    return {"ok": True}

@app.get("/", response_class=HTMLResponse)
async def root():
    return "<h2>🤖 MomCure Telegram Bot is Running on Vercel!</h2>"

