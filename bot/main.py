import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ContextTypes, Application, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackQueryHandler
from handlers.habits import start_add_habit, save_habit_name, save_habit_time, list_habits, mark_habit_done_command, \
    handle_done_callback , execute_delete , confirm_delete, start_delete_habit, save_changes, enter_new_value, select_field_to_edit, start_edit_habit, handle_done_callback
from telegram.error import TelegramError

import logging
logger = logging.getLogger(__name__)

ADD_HABIT_NAME, ADD_HABIT_TIME = range(2)
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


async def error_handler(update: object, context):
    print(f"Ошибка: {context.error}")
    if update:
        await update.message.reply_text("⚠️ Произошла ошибка. Попробуйте позже.")


async def start(update, context):
    await update.message.reply_text("Привет! Я помогу тебе отслеживать привычки. Используй /add, /list, /done, /edit, /delete.")


async def cancel_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
    context.user_data.clear()
    await update.message.reply_text("Действие отменено")
    return ConversationHandler.END


def main():
    app = Application.builder().token(TOKEN).build()
    app.add_error_handler(error_handler)
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('add', start_add_habit)],
        states={
            ADD_HABIT_NAME: [MessageHandler(filters.TEXT, save_habit_name)],
            ADD_HABIT_TIME: [MessageHandler(filters.TEXT, save_habit_time)],
        },
        fallbacks=[]
    )
    edit_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('edit', start_edit_habit)],
        states={
            "SELECT_FIELD": [CallbackQueryHandler(select_field_to_edit, pattern=r'^edit_\d+$')],
            "ENTER_NEW_VALUE": [CallbackQueryHandler(enter_new_value, pattern=r'^field_(name|time|active)$')],
            "SAVE_CHANGES": [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_changes),
                CallbackQueryHandler(save_changes, pattern=r'^active_(true|false)$')
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel_edit)],
        allow_reentry=True
    )

    delete_conv_handler = ConversationHandler(
        entry_points=[CommandHandler('delete', start_delete_habit)],
        states={
            "CONFIRM_DELETE": [
                CallbackQueryHandler(execute_delete, pattern=r'^confirm_(yes|no)$'),
                CallbackQueryHandler(confirm_delete, pattern=r'^delete_\d+$')
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel_edit)],
        allow_reentry=True
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("list", list_habits))
    app.add_handler(edit_conv_handler)
    app.add_handler(delete_conv_handler)
    app.add_handler(CommandHandler("done", mark_habit_done_command))
    app.add_handler(CallbackQueryHandler(handle_done_callback, pattern="^done_"))

    app.run_polling()


if __name__ == "__main__":
    main()