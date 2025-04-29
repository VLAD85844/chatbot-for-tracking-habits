from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from services.api import create_habit, get_habits, mark_habit_done, create_user, update_habit, delete_habit
from telegram.error import BadRequest
import re
import logging


logger = logging.getLogger(__name__)
ADD_HABIT_NAME, ADD_HABIT_TIME = range(2)
TIME_REGEX = re.compile(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$')


async def start_add_habit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "token" not in context.user_data:
        await update.message.reply_text("⚠️ Сначала выполните /login!")
        return ConversationHandler.END
    await update.message.reply_text("Введите название привычки:")
    return ADD_HABIT_NAME


async def save_habit_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "token" not in context.user_data:
        await update.message.reply_text("⚠️ Сначала выполните /login!")
        return ConversationHandler.END

    habit_name = update.message.text
    context.user_data["habit_name"] = habit_name
    await update.message.reply_text("Введите время напоминания (HH:MM):")
    return ADD_HABIT_TIME


async def save_habit_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    habit_name = context.user_data["habit_name"]
    reminder_time = update.message.text

    if not TIME_REGEX.match(reminder_time):
        await update.message.reply_text("❌ Некорректный формат времени! Используйте HH:MM")
        return ConversationHandler.END

    try:
        result = await create_habit(
            {
                "telegram_id": user_id,
                "name": habit_name,
                "reminder_time": reminder_time
            },
            context.user_data["token"]
        )

        if result.get("status") == "error":
            await update.message.reply_text(f"❌ Ошибка: {result.get('message')}")
        else:
            await update.message.reply_text(f"✅ Привычка '{habit_name}' создана!")
            del context.user_data["habit_name"]

    except Exception as e:
        logger.error(f"Ошибка: {e}", exc_info=True)
        await update.message.reply_text("⚠️ Ошибка при создании привычки")

    return ConversationHandler.END


async def list_habits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вывод списка привычек пользователя"""
    telegram_id = update.message.from_user.id
    habits = await get_habits(telegram_id)

    if not habits or isinstance(habits, dict) and habits.get("status") == "error":
        await update.message.reply_text("У вас пока нет привычек!")
        return

    text = "📋 Ваши привычки:\n" + "\n".join(
        f"{i + 1}. {h['name']}"
        for i, h in enumerate(habits)
    )
    await update.message.reply_text(text)


async def mark_habit_done_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /done с клавиатурой"""
    user_id = update.message.from_user.id
    habits = await get_habits(user_id)

    if not habits:
        await update.message.reply_text("У вас нет привычек для отметки!")
        return

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(h["name"], callback_data=f"done_{h['id']}")]
        for h in habits
    ])
    await update.message.reply_text("Выберите привычку:", reply_markup=keyboard)


async def handle_done_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    habit_id = int(query.data.split("_")[1])
    telegram_id = query.from_user.id

    result = await mark_habit_done(habit_id, telegram_id)

    if result.get("status") == "error":
        await query.edit_message_text(f"❌ {result.get('message')}")
        return

    habits = await get_habits(telegram_id)
    text = "✅ Привычка отмечена!\n\n" + "\n".join(
        f"{i + 1}. {h['name']}"
        for i, h in enumerate(habits)
    )

    await query.edit_message_text(text=text)


async def start_edit_habit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало диалога редактирования привычки"""
    try:
        telegram_id = update.message.from_user.id
        habits = await get_habits(telegram_id, context.user_data.get("token"))

        if not habits or isinstance(habits, dict) and habits.get("status") == "error":
            await update.message.reply_text("У вас нет привычек для редактирования!")
            return ConversationHandler.END

        keyboard = [
            [InlineKeyboardButton(h["name"], callback_data=f"edit_{h['id']}")]
            for h in habits if isinstance(h, dict)
        ]

        await update.message.reply_text(
            "Выберите привычку для редактирования:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return "SELECT_FIELD"
    except Exception as e:
        logger.error(f"Error in start_edit_habit: {e}", exc_info=True)
        await update.message.reply_text("⚠️ Произошла ошибка")
        return ConversationHandler.END


async def select_field_to_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    habit_id = int(query.data.split("_")[1])
    context.user_data["edit_habit_id"] = habit_id

    keyboard = [
        [InlineKeyboardButton("Название", callback_data="field_name")],
        [InlineKeyboardButton("Время напоминания", callback_data="field_time")],
        [InlineKeyboardButton("Активность", callback_data="field_active")],
    ]

    await query.edit_message_text(
        text="Что вы хотите изменить?",
        reply_markup=InlineKeyboardMarkup(keyboard))

    return "ENTER_NEW_VALUE"


async def enter_new_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора поля для изменения"""
    query = update.callback_query
    await query.answer()

    field = query.data.split("_")[1]
    context.user_data["edit_field"] = field

    if field == "active":
        keyboard = [
            [InlineKeyboardButton("✅ Активна", callback_data="set_active_true")],
            [InlineKeyboardButton("❌ Неактивна", callback_data="set_active_false")],
        ]
        await query.edit_message_text(
            text="Выберите новый статус:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        field_name = "название" if field == "name" else "время напоминания"
        await query.edit_message_text(f"Введите новое {field_name}:")

    return "SAVE_CHANGES"


async def save_changes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохранение изменений привычки"""
    try:
        if update.callback_query:
            query = update.callback_query
            await query.answer()
            new_value = query.data == "set_active_true"
            message = query.message
        else:
            new_value = update.message.text
            message = update.message
            if context.user_data["edit_field"] == "time" and not TIME_REGEX.match(new_value):
                await message.reply_text("❌ Неверный формат времени. Используйте HH:MM")
                return "ENTER_NEW_VALUE"

        update_data = {
            context.user_data["edit_field"]: new_value
        }

        result = await update_habit(
            context.user_data["edit_habit_id"],
            context.user_data["token"],
            **update_data
        )

        if result.get("status") == "error":
            raise Exception(result.get("message"))

        if update.callback_query:
            await query.edit_message_text("✅ Привычка обновлена!")
        else:
            await message.reply_text("✅ Привычка обновлена!")

    except Exception as e:
        error_msg = f"❌ Ошибка: {str(e)}"
        if update.callback_query:
            await query.edit_message_text(error_msg)
        else:
            await update.message.reply_text(error_msg)

    context.user_data.pop("edit_habit_id", None)
    context.user_data.pop("edit_field", None)
    return ConversationHandler.END


async def start_delete_habit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало диалога удаления привычки"""
    try:
        telegram_id = update.message.from_user.id
        habits = await get_habits(telegram_id, context.user_data.get("token"))

        if not habits or isinstance(habits, dict) and habits.get("status") == "error":
            await update.message.reply_text("У вас нет привычек для удаления!")
            return ConversationHandler.END

        keyboard = [
            [InlineKeyboardButton(h["name"], callback_data=f"delete_{h['id']}")]
            for h in habits if isinstance(h, dict)
        ]

        await update.message.reply_text(
            "Выберите привычку для удаления:",
            reply_markup=InlineKeyboardMarkup(keyboard))
        return "CONFIRM_DELETE"
    except Exception as e:
        logger.error(f"Error in start_delete_habit: {e}", exc_info=True)
        await update.message.reply_text("⚠️ Произошла ошибка")
        return ConversationHandler.END


async def confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение удаления привычки"""
    query = update.callback_query
    await query.answer()

    habit_id = int(query.data.split("_")[1])
    context.user_data["delete_habit_id"] = habit_id

    keyboard = [
        [InlineKeyboardButton("✅ Да, удалить", callback_data="confirm_yes")],
        [InlineKeyboardButton("❌ Нет, отменить", callback_data="confirm_no")],
    ]

    await query.edit_message_text(
        text="Вы уверены, что хотите удалить эту привычку?",
        reply_markup=InlineKeyboardMarkup(keyboard))
    return "CONFIRM_DELETE"


async def execute_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выполнение удаления привычки"""
    query = update.callback_query
    await query.answer()

    if query.data == "confirm_no":
        await query.edit_message_text("❌ Удаление отменено")
        return ConversationHandler.END

    try:
        habit_id = context.user_data["delete_habit_id"]
        result = await delete_habit(
            habit_id,
            update.callback_query.from_user.id,
            context.user_data["token"]
        )

        if result.get("status") == "error":
            raise Exception(result.get("message"))

        await query.edit_message_text("✅ Привычка успешно удалена!")
    except Exception as e:
        await query.edit_message_text(f"❌ Ошибка при удалении: {str(e)}")

    context.user_data.pop("delete_habit_id", None)
    return ConversationHandler.END