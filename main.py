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

    binance_price = None
    weex_price = None

    # Binance Public Ticker API
    try:
        url_binance = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol_pair}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url_binance, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if "price" in data:
                raw_p = float(data["price"])
                binance_price = f"{raw_p:,.4f}".rstrip('0').rstrip('.')
    except Exception as e:
        logger.error(f"Binance API Error: {e}")

    # WEEX API Check
    try:
        url_weex = f"https://api.weex.com/api/v1/market/ticker?symbol=cmt_{clean_coin.lower()}usdt"
        res_w = requests.get(url_weex, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5)
        if res_w.status_code == 200 and res_w.headers.get('content-type', '').startswith('application/json'):
            w_data = res_w.json()
            if w_data.get("code") == "00000" and "data" in w_data:
                weex_price = w_data["data"].get("last")
    except Exception as e:
        logger.error(f"WEEX API Error: {e}")

    if not binance_price and not weex_price:
        await update.message.reply_text(f"❌ Symbol **{symbol_pair}** ka data nahi mila.", parse_mode='Markdown')
        return

    msg = f"📊 **{symbol_pair} Market Price**\n\n"
    if binance_price:
        msg += f"• **Binance:** ${binance_price}\n"
    if weex_price:
        msg += f"• **WEEX:** ${weex_price}\n"
    elif binance_price:
        msg += f"• **WEEX:** ${binance_price} *(Estimated)*\n"

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
        
