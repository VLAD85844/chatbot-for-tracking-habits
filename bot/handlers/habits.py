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
    """Начало диалога добавления привычки"""
    await update.message.reply_text("Введите название привычки:")
    return ADD_HABIT_NAME


async def save_habit_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохранение названия привычки"""
    context.user_data['habit_name'] = update.message.text
    await update.message.reply_text("Введите время напоминания в формате HH:MM (например, 09:00):")
    return ADD_HABIT_TIME


async def save_habit_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохранение времени напоминания и создание привычки"""
    user_id = update.message.from_user.id
    habit_name = context.user_data['habit_name']
    reminder_time = update.message.text.strip()

    if not TIME_REGEX.match(reminder_time):
        await update.message.reply_text("❌ Неверный формат времени. Используйте HH:MM (например, 09:00)")
        return ConversationHandler.END

    user_result = await create_user({
        "telegram_id": user_id,
        "username": update.message.from_user.username
    })

    if user_result.get("status") == "error":
        await update.message.reply_text(f"❌ Ошибка создания пользователя: {user_result.get('message')}")
        return ConversationHandler.END

    result = await create_habit({
        "user_id": user_id,
        "name": habit_name,
        "reminder_time": reminder_time
    })

    if result.get("status") == "error":
        await update.message.reply_text(f"❌ Ошибка: {result.get('message')}")
    else:
        await update.message.reply_text(
            f"✅ Привычка '{habit_name}' добавлена с напоминанием в {reminder_time}!"
        )

    return ConversationHandler.END


async def list_habits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вывод списка привычек пользователя"""
    telegram_id = update.message.from_user.id
    habits = await get_habits(telegram_id)

    if not habits or isinstance(habits, dict) and habits.get("status") == "error":
        await update.message.reply_text("У вас пока нет привычек!")
        return

    text = "📋 Ваши привычки:\n" + "\n".join(
        f"{i + 1}. {h['name']} ({h['reminder_time']})"
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
        f"{i + 1}. {h['name']} ({h['reminder_time']})"
        for i, h in enumerate(habits)
    )

    await query.edit_message_text(text=text)


async def start_edit_habit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало диалога редактирования привычки"""
    telegram_id = update.message.from_user.id
    habits = await get_habits(telegram_id)

    if not habits:
        await update.message.reply_text("У вас нет привычек для редактирования!")
        return ConversationHandler.END

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(h["name"], callback_data=f"edit_{h['id']}")]
        for h in habits
    ])
    await update.message.reply_text("Выберите привычку для редактирования:", reply_markup=keyboard)
    return "SELECT_FIELD"


async def select_field_to_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбор поля для редактирования"""
    query = update.callback_query
    await query.answer()

    habit_id = int(query.data.split("_")[1])
    context.user_data["edit_habit_id"] = habit_id

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Название", callback_data="field_name")],
        [InlineKeyboardButton("Время напоминания", callback_data="field_time")],
        [InlineKeyboardButton("Активность", callback_data="field_active")],
    ])
    await query.edit_message_text("Что вы хотите изменить?", reply_markup=keyboard)
    return "ENTER_NEW_VALUE"


async def enter_new_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ввод нового значения"""
    query = update.callback_query
    await query.answer()

    field = query.data.split('_')[1]
    context.user_data["edit_field"] = f"field_{field}"

    if field == "active":
        keyboard = [
            [InlineKeyboardButton("✅ Активна", callback_data="active_true")],
            [InlineKeyboardButton("❌ Неактивна", callback_data="active_false")],
        ]
        await query.edit_message_text(
            text="Выберите новый статус привычки:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        field_name = "название" if field == "name" else "время напоминания"
        await query.edit_message_text(f"Введите новое {field_name}:")

    return "SAVE_CHANGES"


async def save_changes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сохранение изменений"""
    try:
        query = update.callback_query
        is_callback = query is not None

        if is_callback:
            await query.answer()
            if query.data.startswith("active_"):
                new_value = query.data == "active_true"
                update_data = {"is_active": new_value}
                message = query.message
            else:
                await query.edit_message_text("⚠️ Неизвестная команда")
                return ConversationHandler.END
        else:
            new_value = update.message.text
            message = update.message
            field = context.user_data.get("edit_field")

            if not field:
                await message.reply_text("⚠️ Не удалось определить поле")
                return ConversationHandler.END

            field_map = {
                "field_name": "name",
                "field_time": "reminder_time",
                "field_active": "is_active"
            }
            api_field = field_map.get(field)
            if not api_field:
                await message.reply_text("⚠️ Неизвестное поле")
                return ConversationHandler.END

            if field == "field_time" and not TIME_REGEX.match(new_value):
                await message.reply_text("❌ Неверный формат времени. Используйте HH:MM")
                return "ENTER_NEW_VALUE"

            update_data = {api_field: new_value}

        habit_id = context.user_data["edit_habit_id"]
        result = await update_habit(habit_id, **update_data)

        response_text = ("✅ Привычка обновлена!"
                         if result.get("status") != "error"
                         else f"❌ Ошибка: {result.get('message')}")

        if is_callback:
            await message.edit_text(response_text)
        else:
            await message.reply_text(response_text)

        context.user_data.clear()
        return ConversationHandler.END

    except Exception as e:
        logger.error(f"Error in save_changes: {e}", exc_info=True)
        error_text = "⚠️ Произошла ошибка при обновлении"

        if is_callback:
            await query.edit_message_text(error_text)
        else:
            await update.message.reply_text(error_text)

        context.user_data.clear()
        return ConversationHandler.END


async def start_delete_habit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало диалога удаления привычки"""
    telegram_id = update.message.from_user.id
    habits = await get_habits(telegram_id)

    if not habits:
        await update.message.reply_text("У вас нет привычек для удаления!")
        return ConversationHandler.END

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(h["name"], callback_data=f"delete_{h['id']}")]
        for h in habits
    ])
    await update.message.reply_text("Выберите привычку для удаления:", reply_markup=keyboard)
    return "CONFIRM_DELETE"


async def confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение удаления"""
    query = update.callback_query
    await query.answer()

    habit_id = int(query.data.split('_')[1])
    context.user_data["delete_habit_id"] = habit_id

    keyboard = [
        [InlineKeyboardButton("✅ Да, удалить", callback_data="confirm_yes")],
        [InlineKeyboardButton("❌ Нет, отменить", callback_data="confirm_no")],
    ]
    await query.edit_message_text(
        text="Вы уверены, что хотите удалить эту привычку?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return "CONFIRM_DELETE"


async def execute_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выполнение удаления"""
    query = update.callback_query
    await query.answer()

    if query.data == "confirm_no":
        await query.edit_message_text("Удаление отменено")
        return ConversationHandler.END

    try:
        habit_id = context.user_data.get("delete_habit_id")
        if not habit_id:
            habit_id = int(query.data.split("_")[1]) if "_" in query.data else None

        if not habit_id:
            await query.edit_message_text("❌ Не удалось определить привычку для удаления")
            return ConversationHandler.END

        telegram_id = query.from_user.id
        result = await delete_habit(habit_id, telegram_id)

        if result.get("status") == "error":
            await query.edit_message_text(f"❌ {result.get('message')}")
        else:
            await query.edit_message_text("✅ Привычка успешно удалена!")

    except Exception as e:
        logger.error(f"Error in execute_delete: {e}", exc_info=True)
        await query.edit_message_text("⚠️ Произошла ошибка при удалении")

    context.user_data.clear()
    return ConversationHandler.END