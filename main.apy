"""Standalone WEEX and Binance Telegram price bot."""

from __future__ import annotations

import logging
import os
import re
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from html import escape
from typing import Literal
from zoneinfo import ZoneInfo

import requests
import telebot
from flask import Flask
from telebot.apihelper import ApiTelegramException


WEEX_SPOT_TICKER_URL = "https://api-spot.weex.com/api/v3/market/ticker/24hr"
BINANCE_SPOT_TICKER_URL = "https://api.binance.com/api/v3/ticker/24hr"
WEEX_FUTURES_TICKER_URL = (
    "https://api-contract.weex.com/capi/v3/market/ticker/24hr"
)
BINANCE_FUTURES_TICKER_URL = "https://fapi.binance.com/fapi/v1/ticker/24hr"
REQUEST_TIMEOUT_SECONDS = 10
POLL_RECONNECT_DELAY_SECONDS = 3
POLL_TIMEOUT_SECONDS = 30
LONG_POLLING_TIMEOUT_SECONDS = 30
KEEP_ALIVE_INTERVAL_SECONDS = 4 * 60
WEEX_SIGNUP_URL = "https://weex.com/register?vipCode=2zllj"
SYMBOL_PATTERN = re.compile(r"^[A-Z0-9]{2,20}$")
MarketType = Literal["spot", "futures"]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Ticker:
    """The 24-hour ticker values used in the Telegram response."""

    price: Decimal
    high_price: Decimal
    low_price: Decimal
    quote_volume: Decimal
    volume: Decimal | None = None
    price_change_percent: Decimal = Decimal("0")


class TickerFetchError(Exception):
    """Raised when an exchange cannot return a valid ticker."""


HELP_TEXT = (
    "Usage examples:\n\n"
    "Spot market:\n"
    "• /s sol\n"
    "• /s_sol\n"
    "• /s btc\n\n"
    "Futures / Perpetual market:\n"
    "• /f sol\n"
    "• /d sol\n"
    "• /f btc\n\n"
    "Technical analysis:\n"
    "• /ta btc\n"
    "• /analysis sol\n\n"
    "• /an eth\n\n"
    "Symbols are looked up as USDT markets. Examples include BTC, ETH, SOL, "
    "PEPE, XRP, and NEAR.\n\n"
    "Group admins can moderate by replying to a user's message with "
    "/ban, /unban, /mute, /unmute, /kick, or /del."
)
MODERATION_COMMANDS = ["ban", "unban", "mute", "unmute", "kick", "del", "delete"]
MISSING_ARGUMENT_GUIDANCE = (
    "🔴 Please use this command with appropriate arguments using format below:\n\n"
    "```\n"
    "/s PAIRNAME\n"
    "/d PAIRNAME\n"
    "```\n\n"
    "For example:\n"
    "`/s btcusdt`\n"
    "`/s btc`\n"
    "`/d btcusdt`\n"
    "`/d btc`"
)


def get_bot_token() -> str:
    """Read the Telegram token from Replit Secrets/environment."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is not set. Add it to the project's Secrets."
        )
    return token


def normalize_symbol(raw_symbol: str) -> str:
    """Normalize a user symbol to a USDT market symbol."""
    symbol = raw_symbol.strip().upper()
    if symbol.endswith("USDT"):
        symbol = symbol.removesuffix("USDT")
    if not SYMBOL_PATTERN.fullmatch(symbol):
        raise ValueError(
            "Please use a token symbol such as BTC, ETH, SOL, or PEPE."
        )
    return f"{symbol}USDT"


def parse_decimal(payload: dict[str, object], key: str) -> Decimal:
    """Read a numeric ticker field from an exchange response."""
    try:
        value = payload[key]
        if value is None:
            raise KeyError(key)
        return Decimal(str(value))
    except (KeyError, TypeError, InvalidOperation) as error:
        raise TickerFetchError(f"Ticker field {key} is invalid") from error


def extract_ticker_payload(
    payload: object, market_symbol: str, exchange_name: str
) -> dict[str, object]:
    """Extract a ticker object from either exchange's response shape."""
    if isinstance(payload, dict):
        data = payload.get("data")
        if isinstance(data, dict):
            return data
        return payload

    if isinstance(payload, list):
        matching_tickers = [
            item
            for item in payload
            if isinstance(item, dict)
            and str(item.get("symbol", "")).upper() == market_symbol
        ]
        if len(matching_tickers) == 1:
            return matching_tickers[0]

    raise TickerFetchError(f"{exchange_name} does not list {market_symbol}")


def fetch_ticker(url: str, market_symbol: str, exchange_name: str) -> Ticker:
    """Fetch and validate one exchange's 24-hour ticker."""
    try:
        response = requests.get(
            url,
            params={"symbol": market_symbol},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as error:
        raise TickerFetchError(f"{exchange_name} request failed") from error
    except ValueError as error:
        raise TickerFetchError(f"{exchange_name} returned invalid JSON") from error

    ticker_payload = extract_ticker_payload(
        payload, market_symbol, exchange_name
    )

    try:
        price_value = ticker_payload.get("lastPrice", ticker_payload.get("price"))
        if price_value is None:
            raise KeyError("lastPrice")
        volume_value = next(
            (
                ticker_payload.get(key)
                for key in ("volume", "baseVolume", "baseVol")
                if ticker_payload.get(key) is not None
            ),
            None,
        )
        change_value = next(
            (
                ticker_payload.get(key)
                for key in (
                    "priceChangePercent",
                    "changePercent",
                    "priceChangePercentage",
                )
                if ticker_payload.get(key) is not None
            ),
            0,
        )
        try:
            price_change_percent = Decimal(str(change_value))
        except (InvalidOperation, TypeError):
            price_change_percent = Decimal("0")
        return Ticker(
            price=Decimal(str(price_value)),
            high_price=parse_decimal(ticker_payload, "highPrice"),
            low_price=parse_decimal(ticker_payload, "lowPrice"),
            quote_volume=parse_decimal(ticker_payload, "quoteVolume"),
            volume=(
                Decimal(str(volume_value))
                if volume_value is not None
                else None
            ),
            price_change_percent=price_change_percent,
        )
    except (KeyError, TypeError, InvalidOperation, TickerFetchError) as error:
        raise TickerFetchError(
            f"{exchange_name} does not list {market_symbol}"
        ) from error


def format_number(value: Decimal) -> str:
    """Format numeric values without commas using fixed precision."""
    decimals = 8 if abs(value) < 1 else 4
    return f"{value:.{decimals}f}"


def market_configuration(market_type: MarketType) -> tuple[str, str, str]:
    """Return the label and exchange endpoints for a market type."""
    if market_type == "futures":
        return (
            "Futures / Perpetual",
            WEEX_FUTURES_TICKER_URL,
            BINANCE_FUTURES_TICKER_URL,
        )
    return "Spot", WEEX_SPOT_TICKER_URL, BINANCE_SPOT_TICKER_URL


def fetch_market_tickers(
    raw_symbol: str, market_type: MarketType
) -> tuple[str, str, dict[str, Ticker]]:
    """Fetch all available exchange tickers for a normalized market."""
    market_symbol = normalize_symbol(raw_symbol)
    market_label, weex_url, binance_url = market_configuration(market_type)
    tickers: dict[str, Ticker] = {}

    for exchange_name, url in (("WEEX", weex_url), ("Binance", binance_url)):
        try:
            tickers[exchange_name] = fetch_ticker(
                url, market_symbol, exchange_name
            )
        except TickerFetchError as error:
            logger.info(
                "%s %s unavailable for %s: %s",
                market_label,
                exchange_name,
                market_symbol,
                error,
            )

    return market_symbol, market_label, tickers


def build_market_message(raw_symbol: str, market_type: MarketType) -> str:
    """Build the exact monospace comparison response for one token."""
    try:
        market_symbol = normalize_symbol(raw_symbol)
    except ValueError as error:
        return str(error)

    try:
        market_symbol, market_label, tickers = fetch_market_tickers(
            raw_symbol, market_type
        )
    except ValueError as error:
        return str(error)

    asset_symbol = market_symbol.removesuffix("USDT")

    if not tickers:
        return (
            f"I couldn't find {asset_symbol}/USDT in the {market_label.lower()} "
            "market on WEEX or Binance.\n"
            "Check the token symbol and try again."
        )

    weex_ticker = tickers.get("WEEX")
    binance_ticker = tickers.get("Binance")

    volume_ticker = weex_ticker or binance_ticker

    def price_or_unavailable(ticker: Ticker | None) -> str:
        return format_number(ticker.price) if ticker else "Unavailable"

    high_value = (
        f"${format_number(weex_ticker.high_price)} [WEEX]"
        if weex_ticker
        else "Unavailable"
    )
    low_value = (
        f"${format_number(weex_ticker.low_price)} [WEEX]"
        if weex_ticker
        else "Unavailable"
    )
    volume_value = (
        format_number(volume_ticker.volume or volume_ticker.quote_volume)
        if volume_ticker
        else "Unavailable"
    )

    message_lines = [
        f"Pair:       {market_symbol}",
        f"WEEX:       ${price_or_unavailable(weex_ticker)}",
        f"Binance:    ${price_or_unavailable(binance_ticker)}",
        "",
        f"24H High:   {high_value}",
        f"24H Low:    {low_value}",
        f"24H Volume: {volume_value} {asset_symbol}",
        f"Date: {datetime.now(ZoneInfo('Asia/Karachi')).strftime('%d.%m.%Y')}",
    ]
    return "```\n" + "\n".join(message_lines) + "\n```"


def build_analysis_message(raw_symbol: str) -> str:
    """Build a Futures pivot-point analysis response."""
    try:
        market_symbol, _market_label, tickers = fetch_market_tickers(
            raw_symbol, "futures"
        )
    except ValueError as error:
        return str(error)

    if not tickers:
        asset_symbol = market_symbol.removesuffix("USDT")
        return (
            f"❌ I couldn't find {asset_symbol}/USDT for technical analysis. "
            "Please try another symbol."
        )

    high = max(ticker.high_price for ticker in tickers.values())
    low = min(ticker.low_price for ticker in tickers.values())
    close = (tickers.get("WEEX") or tickers["Binance"]).price
    pivot = (high + low + close) / Decimal("3")
    resistance_1 = (Decimal("2") * pivot) - low
    support_1 = (Decimal("2") * pivot) - high
    resistance_2 = pivot + (high - low)
    support_2 = pivot - (high - low)

    if close > pivot:
        trend = "BULLISH 🟢"
    elif close < pivot:
        trend = "BEARISH 🔴"
    else:
        trend = "NEUTRAL 🟡"

    message_lines = [
        f"Pair:       {market_symbol}",
        f"Trend:      {trend}",
        "",
        f"Resistance 2: ${format_number(resistance_2)}",
        f"Resistance 1: ${format_number(resistance_1)}",
        f"Pivot Point:  ${format_number(pivot)}",
        f"Support 1:    ${format_number(support_1)}",
        f"Support 2:    ${format_number(support_2)}",
        f"Date: {datetime.now(ZoneInfo('Asia/Karachi')).strftime('%d.%m.%Y')}",
    ]
    return "```\n" + "\n".join(message_lines) + "\n```"


def build_detailed_analysis_message(raw_symbol: str) -> str:
    """Build the detailed Futures metrics, technicals, and sentiment response."""
    try:
        market_symbol, _market_label, tickers = fetch_market_tickers(
            raw_symbol, "futures"
        )
    except ValueError as error:
        return str(error)

    if not tickers:
        asset_symbol = market_symbol.removesuffix("USDT")
        return (
            f"❌ I couldn't find {asset_symbol}/USDT for technical analysis. "
            "Please try another symbol."
        )

    high = max(ticker.high_price for ticker in tickers.values())
    low = min(ticker.low_price for ticker in tickers.values())
    close_ticker = tickers.get("WEEX") or tickers["Binance"]
    close = close_ticker.price
    change = close_ticker.price_change_percent
    pivot = (high + low + close) / Decimal("3")
    resistance_1 = (Decimal("2") * pivot) - low
    support_1 = (Decimal("2") * pivot) - high
    resistance_2 = pivot + (high - low)
    support_2 = pivot - (high - low)

    if change > Decimal("3"):
        bias = "STRONG BULLISH 🚀"
    elif change > 0:
        bias = "BULLISH 🟢"
    elif change < Decimal("-3"):
        bias = "STRONG BEARISH 🔻"
    else:
        bias = "BEARISH 🔴"

    if close >= resistance_1:
        status = "NEAR RESISTANCE"
    elif close <= support_1:
        status = "NEAR SUPPORT"
    else:
        status = "NEUTRAL"

    message_lines = [
        f"=== DETAILED ANALYSIS: {market_symbol} ===",
        "",
        "[ METRICS ]",
        f"Price:       ${format_number(close)}",
        f"24H Change:  {change:+.2f}%",
        f"24H High:    ${format_number(high)}",
        f"24H Low:     ${format_number(low)}",
        "",
        "[ TECHNICALS ]",
        f"Resistance 2: ${format_number(resistance_2)}",
        f"Resistance 1: ${format_number(resistance_1)}",
        f"Pivot Point:   ${format_number(pivot)}",
        f"Support 1:     ${format_number(support_1)}",
        f"Support 2:     ${format_number(support_2)}",
        "",
        "[ SENTIMENT ]",
        f"Bias:   {bias}",
        f"Status: {status}",
        f"Date: {datetime.now(ZoneInfo('Asia/Karachi')).strftime('%d.%m.%Y')}",
    ]
    return "```\n" + "\n".join(message_lines) + "\n```"


def market_action_keyboard(
    raw_symbol: str, market_type: MarketType
) -> telebot.types.InlineKeyboardMarkup:
    """Build direct Trade and Sign Up buttons."""
    market_symbol = normalize_symbol(raw_symbol)
    asset_symbol = market_symbol.removesuffix("USDT")
    trade_url = f"https://www.weex.com/futures/{asset_symbol}_USDT"

    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.row(
        telebot.types.InlineKeyboardButton(
            f"💰 Trade {asset_symbol}",
            url=trade_url,
        ),
        telebot.types.InlineKeyboardButton(
            "✍️ Sign Up",
            url=WEEX_SIGNUP_URL,
        ),
    )
    return keyboard


def parse_command_symbol(message: telebot.types.Message) -> str | None:
    """Read the symbol argument from a Telegram command."""
    command_parts = (message.text or "").split(maxsplit=1)
    if len(command_parts) < 2:
        return None
    return command_parts[1].strip()


def reply_with_missing_argument_guidance(
    bot: telebot.TeleBot, message: telebot.types.Message
) -> None:
    """Explain the copyable Spot and Futures command formats."""
    bot.reply_to(message, MISSING_ARGUMENT_GUIDANCE, parse_mode="Markdown")


def safe_error_symbol(raw_symbol: str) -> str:
    """Create a safe symbol for Markdown error messages."""
    symbol = re.sub(r"[^A-Z0-9]", "", raw_symbol.upper())
    return symbol or "UNKNOWN"


def status_failure_message(raw_symbol: str) -> str:
    """Build the consistent failure response for a completed status message."""
    return f"❌ Token `{safe_error_symbol(raw_symbol)}` not found or API error."


def resolve_status_message(
    bot: telebot.TeleBot,
    loading_message: telebot.types.Message,
    raw_symbol: str,
) -> bool:
    """Edit a stuck status message, deleting it only if editing is unavailable."""
    failure_message = status_failure_message(raw_symbol)
    try:
        bot.edit_message_text(
            failure_message,
            chat_id=loading_message.chat.id,
            message_id=loading_message.message_id,
            parse_mode="Markdown",
        )
        return True
    except Exception:
        logger.exception("Could not edit failed status message")

    try:
        bot.delete_message(
            chat_id=loading_message.chat.id,
            message_id=loading_message.message_id,
        )
        return True
    except Exception:
        logger.exception("Could not delete failed status message")
        return False


def send_market_data(
    bot: telebot.TeleBot,
    message: telebot.types.Message,
    market_type: MarketType,
) -> None:
    """Send a loading reply and edit it into the completed market response."""
    raw_symbol = ""
    loading_message = None
    status_resolved = False
    try:
        raw_symbol = parse_command_symbol(message) or ""
        if not raw_symbol:
            reply_with_missing_argument_guidance(bot, message)
            return

        loading_message = bot.reply_to(message, "⏳ Getting price info...")
        final_text = build_market_message(raw_symbol, market_type)
        if not final_text.startswith("```"):
            raise ValueError(final_text)
        reply_markup = market_action_keyboard(raw_symbol, market_type)
        bot.edit_message_text(
            final_text,
            chat_id=loading_message.chat.id,
            message_id=loading_message.message_id,
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )
        status_resolved = True
    except Exception:
        logger.exception("Could not update market response for %s", raw_symbol)
        if loading_message is not None:
            status_resolved = resolve_status_message(
                bot, loading_message, raw_symbol
            )
    finally:
        if loading_message is not None and not status_resolved:
            resolve_status_message(bot, loading_message, raw_symbol)


def send_analysis_data(
    bot: telebot.TeleBot, message: telebot.types.Message
) -> None:
    """Send a calculation status and edit it into technical analysis."""
    raw_symbol = ""
    loading_message = None
    status_resolved = False
    try:
        raw_symbol = parse_command_symbol(message) or ""
        if not raw_symbol:
            reply_with_missing_argument_guidance(bot, message)
            return

        loading_message = bot.reply_to(message, "⏳ Calculating Levels...")
        final_text = build_analysis_message(raw_symbol)
        if not final_text.startswith("```"):
            raise ValueError(final_text)
        bot.edit_message_text(
            final_text,
            chat_id=loading_message.chat.id,
            message_id=loading_message.message_id,
            parse_mode="Markdown",
            reply_markup=market_action_keyboard(raw_symbol, "futures"),
        )
        status_resolved = True
    except Exception:
        logger.exception("Could not update analysis response for %s", raw_symbol)
        if loading_message is not None:
            status_resolved = resolve_status_message(
                bot, loading_message, raw_symbol
            )
    finally:
        if loading_message is not None and not status_resolved:
            resolve_status_message(bot, loading_message, raw_symbol)


def send_detailed_analysis_data(
    bot: telebot.TeleBot, message: telebot.types.Message
) -> None:
    """Send a status and edit it into the detailed analysis response."""
    raw_symbol = ""
    loading_message = None
    status_resolved = False
    try:
        raw_symbol = parse_command_symbol(message) or ""
        if not raw_symbol:
            reply_with_missing_argument_guidance(bot, message)
            return

        loading_message = bot.reply_to(message, "⏳ Generating Analysis...")
        final_text = build_detailed_analysis_message(raw_symbol)
        if not final_text.startswith("```"):
            raise ValueError(final_text)
        bot.edit_message_text(
            final_text,
            chat_id=loading_message.chat.id,
            message_id=loading_message.message_id,
            parse_mode="Markdown",
            reply_markup=market_action_keyboard(raw_symbol, "futures"),
        )
        status_resolved = Tru
