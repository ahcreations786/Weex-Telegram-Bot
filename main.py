import os
import sys
import logging
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Logging setup
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
        "Kuch zaroori commands:\n"
        "• `/d btc` - Live price aur 24H volume dekhein\n"
        "• `/help` - Tamam commands ki list"
    )
    await update.message.reply_html(msg)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = (
        "🤖 **Bot Command Menu:**\n\n"
        "• `/start` - Bot ko restart/start karein\n"
        "• `/help` - Help menu dekhein\n"
        "• `/d [coin]` - Market price fetch karein (e.g. `/d btc`, `/d zen`, `/d eth`)\n"
    )
    await update.message.reply_text(msg, parse_mode='Markdown')

async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Sahi tareeqah: `/d btc` ya `/d zen`", parse_mode='Markdown')
        return
    
    coin = context.args[0].strip().upper()
    symbol_pair = coin if coin.endswith("USDT") else f"{coin}USDT"
    base_coin = symbol_pair.replace("USDT", "")

    weex_price = "N/A"
    high_24h = "N/A"
    low_24h = "N/A"
    vol_24h = "N/A"
    binance_price = "N/A"

    # Fetch WEEX Price
    try:
        url_weex = f"https://api.weex.com/api/v1/market/ticker?symbol={symbol_pair.lower()}"
        res_weex = requests.get(url_weex, timeout=5).json()
        if res_weex.get("code") == "00000" and "data" in res_weex:
            data = res_weex["data"]
            weex_price = data.get("last", "N/A")
            high_24h = data.get("high_24h", "N/A")
            low_24h = data.get("low_24h", "N/A")
            vol_24h = data.get("vol_24h", "N/A")
    except Exception as e:
        logger.error(f"WEEX API error: {e}")

    # Fetch Binance Price (Backup & Comparison)
    try:
        url_binance = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol_pair}"
        res_binance = requests.get(url_binance, timeout=5).json()
        if "price" in res_binance:
            binance_price = str(float(res_binance["price"]))
    except Exception as e:
        logger.error(f"Binance API error: {e}")

    # If both APIs failed
    if weex_price == "N/A" and binance_price == "N/A":
        await update.message.reply_text(f"❌ Symbol **{symbol_pair}** ka data nahi mila.", parse_mode='Markdown')
        return

    # Response formatting
    msg = (
        f"Pair: {symbol_pair}\n"
        f"WEEX: ${weex_price}\n"
        f"Binance: ${binance_price}\n\n"
        f"24H High: ${high_24h} [WEEX]\n"
        f"24H Low: ${low_24h} [WEEX]\n"
        f"24H Volume: {vol_24h} {base_coin}\n"
        f"Date: 07.09.2026"
    )
    
    await update.message.reply_text(msg)

def main() -> None:
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("d", price_command))

    logger.info("Bot is starting polling...")
    application.run_polling()

if __name__ == '__main__':
    main()
    
