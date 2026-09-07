import os
import sys
import logging
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

if not TOKEN:
    logger.error("No TELEGRAM_BOT_TOKEN environment variable found!")
    sys.exit("Error: TELEGRAM_BOT_TOKEN missing.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    msg = (
        f"Salam {user.mention_html()}! **WEEX Market Alerts Bot** mein khushandeed.\n\n"
        "Commands:\n"
        "• `/d btc` - Live price dekhein\n"
        "• `/help` - Help menu"
    )
    await update.message.reply_html(msg)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = (
        "🤖 **Bot Command Menu:**\n\n"
        "• `/start` - Bot start karein\n"
        "• `/help` - Help menu\n"
        "• `/d [coin]` - Price dekhein (e.g. `/d btc`, `/d zen`)\n"
    )
    await update.message.reply_text(msg, parse_mode='Markdown')

async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Sahi tareeqah: `/d btc`", parse_mode='Markdown')
        return
    
    coin = context.args[0].strip().upper()
    clean_coin = coin.replace("USDT", "")
    symbol_pair = f"{clean_coin}USDT"

    weex_price = None
    binance_price = None

    # WEEX Official Spot Endpoint
    try:
        url_weex = f"https://api-spot.weex.com/api/v1/market/ticker?symbol={symbol_pair}"
        res_weex = requests.get(url_weex, timeout=5).json()
        if isinstance(res_weex, dict) and "data" in res_weex:
            data = res_weex["data"]
            if isinstance(data, dict):
                weex_price = data.get("last") or data.get("close")
        elif isinstance(res_weex, list) and len(res_weex) > 0:
            weex_price = res_weex[0].get("lastPrice")
    except Exception as e:
        logger.error(f"WEEX Spot API Error: {e}")

    # Binance Public API
    try:
        url_binance = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol_pair}"
        res_binance = requests.get(url_binance, timeout=5).json()
        if "price" in res_binance:
            binance_price = str(round(float(res_binance["price"]), 4))
    except Exception as e:
        logger.error(f"Binance API Error: {e}")

    if not weex_price and not binance_price:
        await update.message.reply_text(f"❌ Symbol **{symbol_pair}** ka data nahi mila.", parse_mode='Markdown')
        return

    msg = f"📊 **{symbol_pair} Market Price**\n\n"
    if weex_price:
        msg += f"• **WEEX:** ${weex_price}\n"
    if binance_price:
        msg += f"• **Binance:** ${binance_price}\n"

    await update.message.reply_text(msg, parse_mode='Markdown')

def main() -> None:
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("d", price_command))

    logger.info("Bot is starting polling...")
    application.run_polling()

if __name__ == '__main__':
    main()
    
