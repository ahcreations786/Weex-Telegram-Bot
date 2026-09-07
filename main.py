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

# Coin Mapping for Public API
COIN_MAP = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "BNB": "binancecoin",
    "XRP": "ripple",
    "ADA": "cardano",
    "DOGE": "dogecoin",
    "DOT": "polkadot",
    "MATIC": "matic-network",
    "LTC": "litecoin",
    "ZEN": "horizen"
}

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
        "• `/d [coin]` - Price dekhein (e.g. `/d btc`, `/d zen`, `/d eth`)\n"
    )
    await update.message.reply_text(msg, parse_mode='Markdown')

async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text("Sahi tareeqah: `/d btc`", parse_mode='Markdown')
        return
    
    coin = context.args[0].strip().upper().replace("USDT", "")
    coin_id = COIN_MAP.get(coin, coin.lower())
    
    price_usd = None

    # Primary: CoinGecko API (No IP restrictions on GitHub Actions)
    try:
        url_cg = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
        res_cg = requests.get(url_cg, headers={'User-Agent': 'Mozilla/5.0'}, timeout=5).json()
        if coin_id in res_cg and "usd" in res_cg[coin_id]:
            raw_val = res_cg[coin_id]["usd"]
            price_usd = f"{raw_val:,.4f}".rstrip('0').rstrip('.')
    except Exception as e:
        logger.error(f"CoinGecko Error: {e}")

    # Backup: CryptoCompare API
    if not price_usd:
        try:
            url_cc = f"https://min-api.cryptocompare.com/data/price?fsym={coin}&tsyms=USD"
            res_cc = requests.get(url_cc, timeout=5).json()
            if "USD" in res_cc:
                raw_val = res_cc["USD"]
                price_usd = f"{raw_val:,.4f}".rstrip('0').rstrip('.')
        except Exception as e:
            logger.error(f"CryptoCompare Error: {e}")

    if not price_usd:
        await update.message.reply_text(f"❌ Symbol **{coin}USDT** ka data nahi mila.", parse_mode='Markdown')
        return

    msg = (
        f"📊 **{coin}/USDT Market Price**\n\n"
        f"• **Live Price:** ${price_usd}\n"
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
        
