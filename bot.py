from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from pymongo import MongoClient
import os

# MongoDB and Bot Token Setup (from environment variables)
MONGO_URI = os.getenv("MONGO_URI")
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Initialize MongoDB Client
client = MongoClient(MONGO_URI)
db = client["Telegram_bot"]

# Start Handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔍 Search PDF", callback_data='search_pdf')],
        [InlineKeyboardButton("📚 PDF SubjectWise", callback_data='subject_wise')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('🤖 Welcome! Choose an option:', reply_markup=reply_markup)

# Search PDF Command
async def search_pdf_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Enter the PDF name to search:')
    context.user_data['state'] = 'search'

# PDF SubjectWise Command
async def subject_wise_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    collections = db.list_collection_names()
    keyboard = [[InlineKeyboardButton(f"📁 {coll}", callback_data=f"subject_{coll}")]
                for coll in collections]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Select a subject:', reply_markup=reply_markup)

# Menu Callback Handler
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'search_pdf':
        await search_pdf_command(query.message, context)
    elif query.data == 'subject_wise':
        await subject_wise_command(query.message, context)

# Handle Text Input (for search functionality)
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    if context.user_data.get('state') == 'search':
        files = db['Telegram_bot'].find({"File Name": {"$regex": user_input, "$options": "i"}})
        results = list(files)
        if results:
            keyboard = [[InlineKeyboardButton(f"📄 {f['File Name']}", callback_data=f'file_{f["_id"]}')]
                        for f in results]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text('Select a file:', reply_markup=reply_markup)
        else:
            await update.message.reply_text('❌ No files found.')
        context.user_data['state'] = None  # Reset state

# Handle Subject Selection and List PDFs
async def subject_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    subject = query.data.split('_')[1]

    files = db[subject].find()
    results = list(files)

    if results:
        keyboard = [[InlineKeyboardButton(f"📄 {f['File Name']}", callback_data=f'file_{f["_id"]}')]
                    for f in results]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text('Select a file:', reply_markup=reply_markup)
    else:
        await query.message.reply_text('❌ No files found.')

# Handle File Selection and Send the PDF to User
async def file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    file_id = query.data.split('_')[1]

    file = db['Telegram_bot'].find_one({"_id": {"$oid": file_id}})
    if file:
        await context.bot.send_document(chat_id=query.message.chat_id, document=file["File ID"])

# Main Function to Set Up the Bot
def main():
    application = Application.builder().token(BOT_TOKEN).build()

    # Register Bot Commands
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('search_pdf', search_pdf_command))
    application.add_handler(CommandHandler('pdf_subjectwise', subject_wise_command))

    # Register Callback Query Handlers
    application.add_handler(CallbackQueryHandler(menu_handler, pattern='^search_pdf$|^subject_wise$'))
    application.add_handler(CallbackQueryHandler(subject_handler, pattern='^subject_'))
    application.add_handler(CallbackQueryHandler(file_handler, pattern='^file_'))

    # Register Text Handler for PDF Search
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    # Start the Bot with Webhook
    application.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        url_path=BOT_TOKEN,
        webhook_url=f"https://currentadda-materials-bot.onrender.com/{BOT_TOKEN}"
    )

if __name__ == '__main__':
    main()
