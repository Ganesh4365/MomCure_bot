import logging
import os
import random
import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters,
    ConversationHandler, ContextTypes
)
from telegram.ext._application import Application
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import telegram

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Conversation states
ASK_PAIN, ASK_LEVEL = range(2)

# Pain solutions
PAIN_SOLUTIONS = {
    "headache": {
        "remedy": "Drink water, rest, and massage your temples. Warm compress helps too 💆‍♀️",
        "tablet": "Paracetamol (Crocin) if severe. Don't skip meals, beta!"
    },
    "stomachache": {
        "remedy": "Warm water, ginger tea, and rest. Try a hot water bag. 🍵",
        "tablet": "Drotin or Meftal-Spas after food."
    },
    "cold": {
        "remedy": "Warm soup, steam inhale, and keep cozy. Mom’s hug is magic 🫂",
        "tablet": "Take Cetirizine. Rest is most important."
    },
    "fever": {
        "remedy": "Hydrate, rest, and use a cool cloth. I’m here for you 🤗",
        "tablet": "Paracetamol if high. Tell me if it stays."
    }
}

MOM_ANIMATIONS = {
    "greeting": [
        "https://media.giphy.com/media/26ufdipQqU2lhNA4g/giphy.gif",
        "https://media.giphy.com/media/3o6Zt6ML6BklcajjsA/giphy.gif"
    ],
    "comfort": [
        "https://media.giphy.com/media/3oEjI6SIIHBdRxXI40/giphy.gif",
        "https://media.giphy.com/media/3o6ZtpxSZbQRRnwCKQ/giphy.gif"
    ],
    "encourage": [
        "https://media.giphy.com/media/3o6Zt8zb1PpQn1xQk0/giphy.gif",
        "https://media.giphy.com/media/3oKIPwoeGErMmaI43C/giphy.gif"
    ]
}

MOM_BACKGROUNDS = [
    "\n" + "🌸" * 10 + "\n",
    "\n" + "💖" * 10 + "\n",
    "\n" + "🏡" * 10 + "\n"
]

# Bot handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    gif = random.choice(MOM_ANIMATIONS["greeting"])
    bg = random.choice(MOM_BACKGROUNDS)
    await update.message.reply_animation(
        gif,
        caption=bg + "Welcome home, beta! I'm your MomCure bot. Tell me where it hurts 💖\n\nWhat pain are you feeling today? (headache, stomachache, cold, fever)" + bg
    )
    return ASK_PAIN

async def ask_pain(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pain = update.message.text.lower()
    context.user_data['pain'] = pain
    gif = random.choice(MOM_ANIMATIONS["comfort"])
    bg = random.choice(MOM_BACKGROUNDS)
    lines = [
        f"Ohh my dear, you have {pain}? Let mom help 💕",
        f"Aww beta, I'm here. Tell me more about your {pain}.",
        f"Don't worry sweetie, mom will take care of it."
    ]
    await update.message.reply_animation(
        gif,
        caption=bg + random.choice(lines) + "\nOn a scale of 1 to 10, how much does it hurt?" + bg
    )
    return ASK_LEVEL

async def ask_level(update: Update, context: ContextTypes.DEFAULT_TYPE):
    level = update.message.text
    pain = context.user_data.get('pain', 'pain')
    try:
        level_int = int(level)
    except ValueError:
        await update.message.reply_text("Tell me a number from 1 to 10, beta 😊")
        return ASK_LEVEL

    solution = PAIN_SOLUTIONS.get(pain)
    if solution:
        remedy = solution['remedy']
        tablet = solution['tablet']
    else:
        remedy = (
            f"For '{pain}', try rest, hydration, and gentle massage.\n"
            f"For more help, see: https://symptoms.webmd.com/"
        )
        tablet = "Paracetamol or Ibuprofen may help. Consult a doctor for chronic pains."

    gif = random.choice(MOM_ANIMATIONS["encourage"])
    bg = random.choice(MOM_BACKGROUNDS)
    end_lines = [
        "Mom is always here 💖",
        "Sending warm hug! 🫂",
        "You are never alone, beta."
    ]

    await update.message.reply_animation(
        gif,
        caption=(bg +
            f"Thanks for sharing, sweetie. Pain level: {level_int}/10.\n\n"
            f"🌼 Home Remedy: {remedy}\n💊 Tablet Suggestion: {tablet}\n\n"
            f"{random.choice(end_lines)}\nType /start to ask again." + bg)
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Take care beta, Mom is always here. 💖")
    return ConversationHandler.END

# FastAPI app
app = FastAPI()
telegram_app: Application = None

@app.on_event("startup")
async def on_startup():
    global telegram_app
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("TELEGRAM_BOT_TOKEN not set.")
        return

    telegram_app = ApplicationBuilder().token(token).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            ASK_PAIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_pain)],
            ASK_LEVEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_level)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    telegram_app.add_handler(conv_handler)

    webhook_url = os.getenv("WEBHOOK_URL")
    if webhook_url:
        await telegram_app.bot.set_webhook(webhook_url)
    asyncio.create_task(telegram_app.initialize())

@app.post("/api/webhook")
async def telegram_webhook(request: Request):
    update = telegram.Update.de_json(await request.json(), telegram_app.bot)
    await telegram_app.process_update(update)
    return {"ok": True}

# 🏡 Serve HTML Landing Page on /
@app.get("/", response_class=HTMLResponse)
async def home():
    with open("landing.html", "r", encoding="utf-8") as f:
        return f.read()
