import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import ContextTypes, Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from sqlalchemy.orm import Session
import asyncio
import re
from datetime import datetime
import sqlite3

# Set logging level to suppress excessive debug logs
logging.basicConfig(level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Use /game to choose an option.")

async def get_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    await update.message.reply_text(f"Your Telegram User ID is: {user_id}")

async def game(update, context):
    keyboard = [
        [InlineKeyboardButton("Register", callback_data='register')],
        [InlineKeyboardButton("Deposit", callback_data='deposit')],
        [InlineKeyboardButton("Demo Play", callback_data='demo_play')],
        [InlineKeyboardButton("Select Game", callback_data='select_game')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Choose an option:", reply_markup=reply_markup)

async def register(update, context):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("You selected: Register")

# Modify the deposit method to include bank type selection
async def deposit(update, context):
    keyboard = [
        [InlineKeyboardButton("Bank of Abyssinia", callback_data='bank_abyssinia')],
        [InlineKeyboardButton("Commercial Bank of Ethiopia", callback_data='bank_cbe')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.edit_message_text(
        "Select the bank you want to deposit to:", reply_markup=reply_markup
    )

# Handle bank selection and proceed to amount selection
async def handle_bank_selection(update, context):
    query = update.callback_query
    bank = query.data.split('_')[1]  # Extract the bank type from callback data

    # Save the selected bank in the context for later use
    context.user_data['selected_bank'] = bank

    keyboard = [
        [InlineKeyboardButton("20 ETB", callback_data='handle_deposit_20')],
        [InlineKeyboardButton("50 ETB", callback_data='handle_deposit_50')],
        [InlineKeyboardButton("100 ETB", callback_data='handle_deposit_100')],
        [InlineKeyboardButton("500 ETB", callback_data='handle_deposit_500')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"You selected {bank}. Now select the amount you want to deposit:", reply_markup=reply_markup
    )

# Create separate handlers for each deposit amount
async def handle_deposit_20(update, context):
    await handle_deposit_amount(update, context, 20)

async def handle_deposit_50(update, context):
    await handle_deposit_amount(update, context, 50)

async def handle_deposit_100(update, context):
    await handle_deposit_amount(update, context, 100)

async def handle_deposit_500(update, context):
    await handle_deposit_amount(update, context, 500)

# Generalized handler for deposit amounts
async def handle_deposit_amount(update, context, amount):
    selected_bank = context.user_data.get('selected_bank', 'Unknown Bank')
    selected_language = context.user_data.get('selected_language', 'english')

    # Language-specific instructions
    instructions = {
        'amharic': (
            f"ባንኩ: {selected_bank}\n"
            "የሂሳብ ቁጥር: 123456789\n"
            "እባኮትን የተመረጠውን መጠን ይላኩ እና የክፍያ ማረጋገጫውን መልእክት እዚህ ያስገቡ።\n"
            "መመሪያዎች:\n"
            "1. የባንክ መተግበሪያዎትን ይክፈቱ ወይም ወደ ባንክ ይሂዱ።\n"
            "2. የተሰጠውን የሂሳብ ቁጥር ወደ ሂሳብዎ ያስተላልፉ።\n"
            "3. የክፍያ ማረጋገጫውን መልእክት እዚህ ያስገቡ።"
        ),
        'afaan_oromoo': (
            f"Magaalaa: {selected_bank}\n"
            "Lakkoofsa Herrega: 123456789\n"
            "Mee maallaqa filatame ergaa fi ergaa ragaa kaffaltii as galchaa.\n"
            "Tartiiba:\n"
            "1. Appii baankii keessanii baniitii ykn gara baankii deemaa.\n"
            "2. Lakkoofsa herregaa kenname gara herrega keessanii ergaa.\n"
            "3. Ergaa ragaa kaffaltii as galchaa."
        ),
        'tigrigna': (
            f"ባንኩ: {selected_bank}\n"
            "ቁጽሪ ሕሳብ: 123456789\n"
            "ብቑልፍ ዝተመረጸ መጠን ኣንብቡና መልእኽቲ ምልክት ክፍሊት ኣብዚ ኣእቱ።\n"
            "መመሪያታት:\n"
            "1. ኣፕሊኬሽን ባንክኩም ክፉቱ ወይ ናብ ባንክ ንኸዱ።\n"
            "2. ቁጽሪ ሕሳብ ዝተሰማማዕ ናብ ሕሳብኩም ኣእቱ።\n"
            "3. መልእኽቲ ምልክት ክፍሊት ኣብዚ ኣእቱ።"
        ),
        'somali': (
            f"Bangiga: {selected_bank}\n"
            "Lambarka Akoonka: 123456789\n"
            "Fadlan lacagta aad dooratay ku shub oo fariinta xaqiijinta lacag bixinta halkan ku dheji.\n"
            "Tallaabooyinka:\n"
            "1. Fur app-ka bangigaaga ama tag bangiga.\n"
            "2. Ku shub lambarka akoonta ee la bixiyay.\n"
            "3. Fariinta xaqiijinta lacag bixinta halkan ku dheji."
        ),
        'english': (
            f"Bank Name: {selected_bank}\n"
            "Account Number: 123456789\n"
            "Please transfer the selected amount and paste the payment confirmation message here.\n"
            "Steps:\n"
            "1. Open your banking app or visit the bank.\n"
            "2. Transfer the selected amount to the account number provided.\n"
            "3. Copy the payment confirmation message and paste it here."
        )
    }

    account_details = instructions.get(selected_language, instructions['english'])

    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        f"You selected {amount} ETB.\n\n{account_details}"
    )

    # Save the selected amount in the context for later use
    context.user_data['deposit_amount'] = amount

async def demo_play(update, context):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("You selected: Demo Play")

async def select_game(update, context):
    keyboard = [
        [InlineKeyboardButton("Keno", callback_data='keno')],
        [InlineKeyboardButton("Bingo", callback_data='bingo')],
        [InlineKeyboardButton("Spin", callback_data='spin')],
        [InlineKeyboardButton("Ludo", callback_data='ludo')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("Select a game:", reply_markup=reply_markup)

def button(update, context):
    query = update.callback_query
    query.answer()
    query.edit_message_text(text=f"Selected option: {query.data}")

def handle_message(update, context):
    update.message.reply_text(f"You said: {update.message.text}")

# Process the payment message
async def process_payment_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message.text

    # Extract details from the message using regex
    sender = re.search(r'Dear\s([A-Za-z]+)', message)
    transaction_number = re.search(r'(?:transaction number is|Receipt: https://\S+/\?trx=)(\S+)', message)
    amount = re.search(r'ETB\s([\d,]+\.\d{2})', message)

    sender = sender.group(1) if sender else "Unknown"
    transaction_number = transaction_number.group(1) if transaction_number else "Unknown"
    amount = float(amount.group(1).replace(",", "")) if amount else 0.0

    # Check if the amount matches the selected deposit amount
    expected_amount = context.user_data.get('deposit_amount', 0)
    if amount != expected_amount:
        await update.message.reply_text(
            f"The amount {amount} ETB does not match the expected deposit amount of {expected_amount} ETB."
        )
        return

    # Save the payment to the database
    with sqlite3.connect("transactions.db") as conn:
        conn.execute(
            """
            INSERT INTO transactions (transaction_code, amount, sender, raw_message, timestamp)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (transaction_number, amount, sender, message)
        )

    # Notify the user of successful deposit
    await update.message.reply_text(
        f"Payment of {amount} ETB has been successfully processed. Thank you!"
    )

# Add a language selection step
async def select_language(update, context):
    keyboard = [
        [InlineKeyboardButton("Amharic", callback_data='lang_amharic')],
        [InlineKeyboardButton("Afaan Oromoo", callback_data='lang_afaan_oromoo')],
        [InlineKeyboardButton("Tigrigna", callback_data='lang_tigrigna')],
        [InlineKeyboardButton("Somali", callback_data='lang_somali')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Please select your preferred language:", reply_markup=reply_markup
    )

# Handle language selection
async def handle_language_selection(update, context):
    query = update.callback_query
    language = query.data.split('_')[1]  # Extract the selected language

    # Save the selected language in the context for later use
    context.user_data['selected_language'] = language

    # Respond with a confirmation message
    language_map = {
        'amharic': "Amharic",
        'afaan_oromoo': "Afaan Oromoo",
        'tigrigna': "Tigrigna",
        'somali': "Somali"
    }
    selected_language = language_map.get(language, "English")
    await query.answer()
    await query.edit_message_text(
        f"You selected {selected_language}. Now you can proceed with the bot's instructions."
    )

telegram_app = Application.builder().token('7637824158:AAFwZzrqiipVkKcl7H4V3_OFv46VCyL79v0').build()

telegram_app.add_handler(CommandHandler("getid", get_user_id))
telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(CommandHandler("game", game))
telegram_app.add_handler(CallbackQueryHandler(register, pattern='register'))
telegram_app.add_handler(CallbackQueryHandler(deposit, pattern='deposit'))
telegram_app.add_handler(CallbackQueryHandler(demo_play, pattern='demo_play'))
telegram_app.add_handler(CallbackQueryHandler(select_game, pattern='select_game'))
telegram_app.add_handler(CallbackQueryHandler(lambda update, context: update.callback_query.edit_message_text(f"You selected: {update.callback_query.data}"), pattern='keno|bingo|spin|ludo'))
telegram_app.add_handler(CallbackQueryHandler(handle_bank_selection, pattern='bank_\w+'))
telegram_app.add_handler(CallbackQueryHandler(handle_deposit_20, pattern='handle_deposit_20'))
telegram_app.add_handler(CallbackQueryHandler(handle_deposit_50, pattern='handle_deposit_50'))
telegram_app.add_handler(CallbackQueryHandler(handle_deposit_100, pattern='handle_deposit_100'))
telegram_app.add_handler(CallbackQueryHandler(handle_deposit_500, pattern='handle_deposit_500'))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_payment_message))
telegram_app.add_handler(CommandHandler("language", select_language))
telegram_app.add_handler(CallbackQueryHandler(handle_language_selection, pattern='lang_\w+'))

# Set bot commands for the menu
async def set_bot_commands(application):
    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("game", "Choose a game option"),
        BotCommand("register", "Register for the game"),
        BotCommand("deposit", "Deposit funds"),
        BotCommand("demo_play", "Play a demo game"),
        BotCommand("select_game", "Select a game to play"),
        BotCommand("getid", "Get your Telegram User ID"),
        BotCommand("language", "Select your preferred language")
    ]
    await application.bot.set_my_commands(commands)

# Update the main function to set commands
async def main():
    await telegram_app.initialize()
    await set_bot_commands(telegram_app)  # Set the bot commands
    await telegram_app.start()
    await telegram_app.updater.start_polling()
    print("Bot is running... Press Ctrl+C to stop.")
    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        await telegram_app.updater.stop()
        await telegram_app.stop()

# if __name__ == "__main__":
#     import asyncio
#     asyncio.run(main())