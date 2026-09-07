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
        "Kuch zaroori commands:\n"
        "• `/d btc` - Live price dekhein\n"
        "• `/help` - Tamam commands ki list"
    )
    await update.message.reply_html(msg)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = (
        "🤖 **Bot Command Menu:**\n\n"
        "• `/start` - Bot start karein\n"
        "• `/help` - Help menu dekhein\n"
        "• `/d [coin]` - Market price dekhein (e.g. `/d btc`)\n"
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

    # Try WEEX
    try:
        url_weex = f"https://api.weex.com/api/v1/market/ticker?symbol=cmt_{clean_coin.lower()}usdt"
        res_weex = requests.get(url_weex, timeout=5).json()
        if res_weex.get("code") == "00000" and "data" in res_weex:
            weex_price = res_weex["data"].get("last")
    except Exception as e:
        logger.error(f"WEEX API error: {e}")

    # Fallback/Alternative WEEX format
    if not weex_price:
        try:
            url_weex2 = f"https://api.weex.com/api/v1/market/ticker?symbol={clean_coin.lower()}_usdt"
            res_weex2 = requests.get(url_weex2, timeout=5).json()
            if res_weex2.get("code") == "00000" and "data" in res_weex2:
                weex_price = res_weex2["data"].get("last")
        except Exception as e:
            logger.error(f"WEEX API alt error: {e}")

    # Binance Price Fetch
    try:
        url_binance = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol_pair}"
        res_binance = requests.get(url_binance, timeout=5).json()
        if "price" in res_binance:
            binance_price = str(round(float(res_binance["price"]), 4))
    except Exception as e:
        logger.error(f"Binance API error: {e}")

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
        
