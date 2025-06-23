# main.py
import os
import asyncio
from fastapi import FastAPI, Request
import telegram
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ConversationHandler, filters, ContextTypes
)
from telegram import Update

app = FastAPI()
telegram_app = None

ASK_PAIN, ASK_LEVEL = range(2)

# Dummy test handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello beta! Mom is here! 💖")
    return ASK_PAIN

@app.on_event("startup")
async def init_bot():
    global telegram_app
    telegram_app = ApplicationBuilder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()
    telegram_app.add_handler(CommandHandler("start", start))

    webhook_url = os.getenv("WEBHOOK_URL")
    if webhook_url:
        await telegram_app.bot.set_webhook(webhook_url)

    asyncio.create_task(telegram_app.initialize())

@app.post("/api/webhook")
async def webhook(req: Request):
    update = telegram.Update.de_json(await req.json(), telegram_app.bot)
    await telegram_app.process_update(update)
    return {"ok": True}

@app.get("/")
async def root():
    return {"status": "MomCure is Live"}
