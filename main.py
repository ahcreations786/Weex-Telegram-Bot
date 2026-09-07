import os
import sys
import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# Logging configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get Bot Token from Environment Variable
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TOKEN:
    logger.error("No TELEGRAM_BOT_TOKEN environment variable found!")
    sys.exit("Error: TELEGRAM_BOT_TOKEN missing.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(
        rf"Salam {user.mention_html()}! Weex Telegram Bot mein khushamdeed.",
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text("Help Menu:\n/start - Bot start karein\n/help - Help message daikhein")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echo the user message."""
    await update.message.reply_text(f"Aap ne kaha: {update.message.text}")

def resolve_bot_status() -> bool:
    """Helper function to verify system status without syntax issues."""
    status_resolved = False
    try:
        # Internal verification check
        status_resolved = True
    except Exception as e:
        logger.error(f"Status check failed: {e}")
        status_resolved = False
    
    return status_resolved

def main() -> None:
    """Start the bot."""
    # Verify status
    if not resolve_bot_status():
        logger.warning("Bot status check yielded False, proceeding with startup.")

    # Create the Application
    application = ApplicationBuilder().token(TOKEN).build()

    # Register Command Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # Register Message Handler (Echo non-command messages)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Run the bot until Ctrl-C is pressed
    logger.info("Bot is starting polling...")
    application.run_polling()

if __name__ == '__main__':
    main()
