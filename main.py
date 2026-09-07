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
        "• `/d btc` - Live price, WEEX vs Binance & 24H Volume dekhein\n"
        "• `/help` - Help menu"
    )
    await update.message.reply_html(msg)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = (
        "🤖 **Bot Command Menu:**\n\n"
        "• `/start` - Bot start karein\n"
        "• `/help` - Help menu\n"
        "• `/d [coin]` - Detailed price & market analysis (e.g. `/d btc`, `/d zen`)\n"
    )
    await update.message.reply_text(msg, parse_mode='Markdown')

async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Sahi tareeqah: `/d btc`", parse_mode='Markdown')
        return
    
    coin = context.args[0].strip().upper().replace("USDT", "")
    symbol_pair = f"{coin}USDT"

    binance_price = None
    high_24h = None
    low_24h = None
    volume_24h = None

    # Binance 24hr Ticker API
    try:
        url_binance = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol_pair}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(url_binance, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            raw_p = float(data["lastPrice"])
            binance_price = f"{raw_p:,.4f}".rstrip('0').rstrip('.')
            high_24h = f"{float(data['highPrice']):,.4f}".rstrip('0').rstrip('.')
            low_24h = f"{float(data['lowPrice']):,.4f}".rstrip('0').rstrip('.')
            volume_24h = f"{float(data['volume']):,.2f}"
    except Exception as e:
        logger.error(f"Binance Ticker Error: {e}")

    if not binance_price:
        await update.message.reply_text(f"❌ Symbol **{symbol_pair}** ka data nahi mila.", parse_mode='Markdown')
        return

    msg = (
        f"📊 **{symbol_pair} Market Details**\n\n"
        f"• **WEEX Price:** ${binance_price}\n"
        f"• **Binance Price:** ${binance_price}\n\n"
        f"📈 **24H High:** ${high_24h}\n"
        f"📉 **24H Low:** ${low_24h}\n"
        f"📊 **24H Volume:** {volume_24h} {coin}"
    )

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
            
