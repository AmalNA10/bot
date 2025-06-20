import asyncio
import logging
from collections import defaultdict
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config import BOT_TOKEN

# Set up logging
logging.basicConfig(level=logging.INFO)

# State
waiting_users = []
user_pairs = {}           # Maps user_id -> partner_id
user_states = defaultdict(lambda: "idle")  # "idle", "searching", "chatting"

# ==========================
# Command Handlers
# ==========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Welcome new user."""
    user_states[update.effective_user.id] = "idle"
    await update.message.reply_text(
        "Welcome to Anonymous Chat! 👋\n"
        "Send /search to find a chat partner."
    )

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Search for a new partner."""
    user_id = update.effective_user.id
    if user_states[user_id] == "chatting":
        await update.message.reply_text("You're already in a chat. Use /stop to end it first.")
        return
    if user_id in waiting_users:
        await update.message.reply_text("You're already in the queue...")
        return
    if waiting_users:
        partner_id = waiting_users.pop(0)
        user_pairs[user_id] = partner_id
        user_pairs[partner_id] = user_id
        user_states[user_id] = "chatting"
        user_states[partner_id] = "chatting"

        await context.bot.send_message(user_id, "Partner found 😺\n/next — find a new partner\n/stop — stop this chat\nhttps://t.me/chatbot")
        await context.bot.send_message(partner_id, "Partner found 😺\n/next — find a new partner\n/stop — stop this chat\nhttps://t.me/chatbot")
    else:
        user_states[user_id] = "searching"
        waiting_users.append(user_id)
        await update.message.reply_text("Searching for a partner... 🔍\nPlease wait.")

async def next_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Same as stop + search."""
    await stop(update, context)  # Ends current chat
    await search(update, context)  # Starts new search

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Stop the current chat."""
    user_id = update.effective_user.id
    partner_id = user_pairs.pop(user_id, None)

    if partner_id:
        user_pairs.pop(partner_id, None)
        user_states[partner_id] = "idle"

        await context.bot.send_message(partner_id,
            "Your partner has stopped the chat 😞\nType /search to find a new partner\nhttps://t.me/chatbot"
        )
    user_states[user_id] = "idle"
    await update.message.reply_text(
        "You have stopped the chat.\nType /search to find a new partner.\nhttps://t.me/chatbot"
    )
    if user_id in waiting_users:
        waiting_users.remove(user_id)

# ==========================
# Message Relay
# ==========================
async def relay_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Relay messages between chat partners."""
    user_id = update.effective_user.id
    if user_states[user_id] != "chatting":
        await update.message.reply_text("Use /search to find a chat partner.")
        return
    partner_id = user_pairs.get(user_id)
    if partner_id:
        await context.bot.send_message(partner_id, update.message.text)

# ==========================
# Main
# ==========================
def main() -> None:
    """Run the bot."""
    application = Application.builder().token(BOT_TOKEN).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("search", search))
    application.add_handler(CommandHandler("next", next_user))
    application.add_handler(CommandHandler("stop", stop))

    # Message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, relay_message))

    # Run
    application.run_polling()

if __name__ == "__main__":
    main()
