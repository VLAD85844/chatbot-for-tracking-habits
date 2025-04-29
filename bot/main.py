import os
import httpx
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ContextTypes, Application, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackQueryHandler
from handlers.habits import start_add_habit, save_habit_name, save_habit_time, list_habits, mark_habit_done_command, \
    handle_done_callback, execute_delete, confirm_delete, start_delete_habit, save_changes, enter_new_value, select_field_to_edit, start_edit_habit
from telegram.error import TelegramError
from services.api import login_user, BASE_URL, create_user
import logging

logger = logging.getLogger(__name__)

AUTH, MAIN = range(2)
(ADD_HABIT_NAME, ADD_HABIT_TIME, SELECT_FIELD,
 ENTER_NEW_VALUE, SAVE_CHANGES, CONFIRM_DELETE) = range(6)

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔐 Для работы с ботом необходимо:\n"
        "1. Зарегистрироваться: /register\n"
        "2. Войти: /login\n\n"
        "После этого вы сможете использовать команды: /add, /list, /done, /edit, /delete."
    )

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите имя пользователя и пароль через пробел:")
    return AUTH

async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите имя пользователя и пароль через пробел:")
    return AUTH

async def authenticate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        username, password = update.message.text.split(maxsplit=1)

        if len(password) < 6:
            await update.message.reply_text("❌ Пароль должен быть не короче 6 символов!")
            return ConversationHandler.END

        auth_data = {"username": username, "password": password}
        token = await login_user(auth_data)

        if not token.get("access_token"):
            user_data = {"username": username, "password": password}
            creation_result = await create_user(user_data)

            if creation_result.get("status") == "error":
                await update.message.reply_text(f"❌ Ошибка регистрации: {creation_result.get('message')}")
                return ConversationHandler.END

            token = await login_user(auth_data)
            if not token.get("access_token"):
                await update.message.reply_text("❌ Ошибка входа после регистрации")
                return ConversationHandler.END

        context.user_data.update({
            "token": token["access_token"],
            "username": username,
            "telegram_id": update.message.from_user.id
        })

        async with httpx.AsyncClient(base_url=BASE_URL) as client:
            response = await client.put(
                f"/users/{username}/link_telegram",
                json={"telegram_id": update.message.from_user.id},
                headers={"Authorization": f"Bearer {token['access_token']}"}
            )
            response.raise_for_status()

        await update.message.reply_text("✅ Регистрация и вход выполнены! Telegram привязан.")
        return MAIN

    except Exception as e:
        logger.error(f"Error in authenticate: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")
        return ConversationHandler.END

async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("✅ Вы успешно вышли из системы.")
    return ConversationHandler.END

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    try:
        logger.error(f"Error: {context.error}", exc_info=True)
        if update and hasattr(update, 'message'):
            await update.message.reply_text("⚠️ Произошла ошибка. Попробуйте позже.")
        elif update and hasattr(update, 'callback_query'):
            await update.callback_query.answer("❌ Ошибка обработки запроса")
    except Exception as e:
        logger.error(f"Error in error handler: {e}")

async def cancel_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
    context.user_data.clear()
    await update.message.reply_text("Действие отменено")
    return ConversationHandler.END


def protected(handler):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if "token" not in context.user_data:
            await update.message.reply_text("⚠️ Сначала выполните /login!")
            return ConversationHandler.END
        return await handler(update, context)
    return wrapper

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_error_handler(error_handler)

    auth_conv = ConversationHandler(
        entry_points=[CommandHandler("register", register),
                      CommandHandler("login", login)],
        states={
            AUTH: [MessageHandler(filters.TEXT & ~filters.COMMAND, authenticate)],
            MAIN: []
        },
        fallbacks=[CommandHandler("cancel", cancel_edit)]
    )

    add_habit_conv = ConversationHandler(
        entry_points=[CommandHandler('add', protected(start_add_habit))],
        states={
            ADD_HABIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, protected(save_habit_name))],
            ADD_HABIT_TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, protected(save_habit_time))],
        },
        fallbacks=[CommandHandler('cancel', cancel_edit)],
        allow_reentry=True
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
    app.add_handler(CommandHandler("logout", logout))
    app.add_handler(auth_conv)
    app.add_handler(add_habit_conv)
    app.add_handler(CommandHandler("list", protected(list_habits)))
    app.add_handler(CommandHandler("done", protected(mark_habit_done_command)))
    app.add_handler(edit_conv_handler)
    app.add_handler(delete_conv_handler)
    app.add_handler(CallbackQueryHandler(protected(handle_done_callback), pattern='^done_'))

    app.run_polling()

if __name__ == "__main__":
    main()
