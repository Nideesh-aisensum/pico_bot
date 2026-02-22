import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# ─── Config ───────────────────────────────────────────────
TELEGRAM_TOKEN   = os.environ["TELEGRAM_TOKEN"]
NVIDIA_API_KEY   = os.environ["NVIDIA_API_KEY"]
ALLOWED_USER_ID  = int(os.environ.get("ALLOWED_USER_ID", "0"))  # 0 = allow all

# Choose your model:
# "moonshotai/kimi-k2.5"   ← multimodal, thinking mode
# "zhipuai/glm-5-plus"     ← GLM-5, great for reasoning
MODEL = os.environ.get("MODEL", "moonshotai/kimi-k2.5")

# ─── NVIDIA Client (OpenAI-compatible) ─────────────────────
client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=NVIDIA_API_KEY
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Store conversation history per user
conversations = {}

# ─── Health check server (keeps Render alive) ──────────────
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK - Bot is running!")
    def log_message(self, format, *args):
        pass  # suppress logs

def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    logger.info(f"Health server on port {port}")
    server.serve_forever()

# ─── Bot Handlers ──────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conversations[user_id] = []  # reset history
    await update.message.reply_text(
        f"👋 Hello! I'm powered by **{MODEL}** via NVIDIA NIM.\n\n"
        "Just send me any message to chat!\n"
        "Use /reset to clear conversation history.\n"
        "Use /model to switch between Kimi K2.5 and GLM-5.",
        parse_mode="Markdown"
    )

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conversations[user_id] = []
    await update.message.reply_text("🔄 Conversation reset!")

async def switch_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global MODEL
    if MODEL == "moonshotai/kimi-k2.5":
        MODEL = "zhipuai/glm-5-plus"
        name = "GLM-5"
    else:
        MODEL = "moonshotai/kimi-k2.5"
        name = "Kimi K2.5"
    await update.message.reply_text(f"✅ Switched to **{name}**!", parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Optional: restrict to only your user ID
    if ALLOWED_USER_ID != 0 and user_id != ALLOWED_USER_ID:
        await update.message.reply_text("⛔ Unauthorized.")
        return

    user_text = update.message.text
    
    # Initialize history for new user
    if user_id not in conversations:
        conversations[user_id] = []

    # Add user message to history
    conversations[user_id].append({"role": "user", "content": user_text})

    # Show typing indicator
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        # Build request params
        params = {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": "You are a helpful AI assistant."},
                *conversations[user_id][-10:]  # keep last 10 messages for context
            ],
            "max_tokens": 1024,
            "temperature": 1.0 if "kimi" in MODEL else 0.7,
        }

        # Enable thinking mode for Kimi K2.5
        if "kimi" in MODEL:
            params["extra_body"] = {"chat_template_kwargs": {"thinking": True}}

        response = client.chat.completions.create(**params)
        reply = response.choices[0].message.content

        # Save assistant reply to history
        conversations[user_id].append({"role": "assistant", "content": reply})

        # Split long messages (Telegram limit is 4096 chars)
        if len(reply) > 4096:
            for i in range(0, len(reply), 4096):
                await update.message.reply_text(reply[i:i+4096])
        else:
            await update.message.reply_text(reply)

    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

# ─── Main ──────────────────────────────────────────────────
if __name__ == "__main__":
    # Start health server in background thread
    health_thread = threading.Thread(target=run_health_server, daemon=True)
    health_thread.start()

    # Start Telegram bot
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("model", switch_model))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info(f"Bot started with model: {MODEL}")
    app.run_polling()
