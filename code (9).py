
import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler, # Добавляем для обработки inline-кнопок
)

# --- КОНФИГУРАЦИЯ БОТА ---
TOKEN = "8288215811:AAEWWB3v8_qyHnBp0XMAZUKBhPSTVO5n2t4" # Замените на токен
ADMIN_CHAT_ID = 5948811101  # Замените на ваш ID чата

# --- НАСТРОЙКА ЛОГИРОВАНИЯ ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# --- СОСТОЯНИЯ ДЛЯ СБОРА КОНТАКТОВ ---
# Эти состояния используются ConversationHandler для отслеживания этапов диалога
ASK_CONTACT_NAME, ASK_CONTACT_DATA = range(2)

# --- КЛАВИАТУРЫ ---
# Главная клавиатура бота (ReplyKeyboardMarkup)
main_keyboard_buttons = [
    ["Написать письмо ✍️"],
    ["О боте ℹ️"],
]
MAIN_KEYBOARD = ReplyKeyboardMarkup(main_keyboard_buttons, resize_keyboard=True, one_time_keyboard=False)

# Клавиатура для отмены действия во время сбора контактов (ReplyKeyboardMarkup)
cancel_keyboard_buttons = [["Отмена ❌"]]
CANCEL_KEYBOARD = ReplyKeyboardMarkup(cancel_keyboard_buttons, resize_keyboard=True, one_time_keyboard=True)

# Inline-клавиатура для предложения оставить контакты после письма
PROMPT_CONTACT_INLINE_KEYBOARD = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("Да, хочу оставить контакты 📞", callback_data="start_contact_conv"),
        InlineKeyboardButton("Нет, спасибо", callback_data="decline_contact_conv")
    ]
])


# --- ОБРАБОТЧИКИ КОМАНД И СООБЩЕНИЙ ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет приветственное сообщение и главное меню."""
    user = update.effective_user
    welcome_message = (
        f"Привет, {user.first_name}! Я бот «Письмо Деду Морозу»! 🎅\n\n"
        "Выбери, что хочешь сделать:"
    )
    await update.message.reply_html(welcome_message, reply_markup=MAIN_KEYBOARD)

async def about_bot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет информацию о боте."""
    about_message = (
        "Я бот «Письмо Деду Морозу»! 🎅\n\n"
        "Моя задача — принимать ваши письма и пожелания, а затем передавать их "
        "Деду Морозу. Если Деду Морозу или его помощникам понадобится "
        "связаться с вами, вы можете оставить свои контакты.\n\n"
        "Счастливых праздников!"
    )
    await update.message.reply_text(about_message, reply_markup=MAIN_KEYBOARD)

async def prompt_for_letter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Запрашивает у пользователя написать письмо."""
    await update.message.reply_text(
        "Отлично! Напишите свое письмо Деду Морозу прямо сейчас. Я передам каждое слово! ✨",
        reply_markup=MAIN_KEYBOARD # Клавиатура остаётся
    )

async def handle_letter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Принимает письмо от пользователя, пересылает его админу и предлагает оставить контакты."""
    user = update.effective_user
    letter_text = update.message.text

    # Формируем сообщение для админа
    admin_message = (
        f"📩 *Новое письмо от Деду Морозу!* 📩\n\n"
        f"👤 От: {user.full_name} (ID: `{user.id}`"
    )
    if user.username:
        admin_message += f", @{user.username}"
    admin_message += f")\n\n"
    admin_message += f"*Письмо:*\n`{letter_text}`"

    try:
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID, text=admin_message, parse_mode="Markdown"
        )
        # Отправляем подтверждение и предложение оставить контакты
        await update.message.reply_text(
            "Спасибо! Твое письмо Деду Морозу получено и скоро будет доставлено! ✨\n\n"
            "Хочешь оставить свои данные для обратной связи? Дед Мороз или его помощники смогут связаться с тобой.",
            reply_markup=PROMPT_CONTACT_INLINE_KEYBOARD # Добавляем inline-кнопки
        )
        logger.info(f"Письмо от {user.id} переслано админу и предложены контакты.")
    except Exception as e:
        logger.error(f"Ошибка при пересылке письма от {user.id} админу: {e}")
        await update.message.reply_text(
            "Извини, произошла ошибка при отправке письма. Попробуй еще раз позже.",
            reply_markup=MAIN_KEYBOARD
        )

# --- ФУНКЦИИ ДЛЯ СБОРА КОНТАКТОВ (ConversationHandler) ---

# Это функция запускает диалог сбора контактов, будь то через кнопку "Оставить контакты"
# или через inline-кнопку после отправки письма.
async def start_contact_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начинает процесс сбора контактных данных."""
    # Удаляем inline-клавиатуру, если разговор начат через нее
    if update.callback_query:
        await update.callback_query.answer() # Обязательно для inline-кнопок, чтобы убрать "часики"
        await update.callback_query.edit_message_text(
            text="Отлично! Начинаем собирать контакты. Как тебя зовут? (Имя или никнейм)"
        )
    else: # Если разговор начат через Reply-кнопку
        await update.message.reply_text(
            "Отлично! Как тебя зовут? (Имя или никнейм)"
        )

    await context.bot.send_message( # Отдельно отправляем сообщение с клавиатурой, чтобы она заменила старую
        chat_id=update.effective_chat.id,
        text="Введи свое имя:",
        reply_markup=CANCEL_KEYBOARD # Показываем клавиатуру с кнопкой "Отмена"
    )
    return ASK_CONTACT_NAME

async def decline_contact_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Пользователь отказался оставлять контакты."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        text="Хорошо, Дед Мороз понял. Ты всегда можешь оставить контакты позже, выбрав 'Оставить контакты' в меню.",
        reply_markup=MAIN_KEYBOARD # Если хотим вернуть основную клавиатуру в Reply-зону
    )
    # Если нужно убрать основную клавиатуру, но она уже есть, то ничего не делаем.
    # ReplyKeyboardMarkup управляет Reply-зоной, InlineKeyboardMarkup - в сообщении.
    # Так как мы тут редактируем сообщение с Inline-клавиатурой, Reply-клавиатура не меняется.

async def ask_contact_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получает имя пользователя и запрашивает контактные данные."""
    user_name = update.message.text
    context.user_data["contact_name"] = user_name
    await update.message.reply_text(
        f"Принято, {user_name}! Теперь, пожалуйста, укажи свои контактные данные "
        "(например, email, номер телефона или твой Telegram username), "
        "чтобы Дед Мороз или его помощники могли связаться с тобой.",
        reply_markup=CANCEL_KEYBOARD
    )
    return ASK_CONTACT_DATA

async def ask_contact_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получает контактные данные, отправляет их админу и завершает разговор."""
    contact_data = update.message.text
    user_name = context.user_data.get("contact_name", "Не указано")
    user_telegram = update.effective_user

    admin_message = (
        f"📝 *Новые контактные данные для обратной связи!* 📝\n\n"
        f"👤 Имя (указано пользователем): *{user_name}*\n"
        f"💬 Контактные данные: `{contact_data}`\n"
        f"🆔 Telegram-пользователь: {user_telegram.full_name} (ID: `{user_telegram.id}`"
    )
    if user_telegram.username:
        admin_message += f", @{user_telegram.username}"
    admin_message += ")"

    try:
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID, text=admin_message, parse_mode="Markdown"
        )
        await update.message.reply_text(
            "Спасибо! Твои контактные данные получены. "
            "Дед Мороз передает, что, возможно, скоро свяжется! 🎁",
            reply_markup=MAIN_KEYBOARD
        )
        logger.info(f"Контактные данные от {user_telegram.id} пересланы админу.")
    except Exception as e:
        logger.error(f"Ошибка при пересылке контактов от {user_telegram.id} админу: {e}")
        await update.message.reply_text(
            "Извини, произошла ошибка при сохранении твоих контактов. Попробуй еще раз позже.",
            reply_markup=MAIN_KEYBOARD
        )

    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отменяет процесс сбора контактных данных."""
    await update.message.reply_text(
        "Сбор контактных данных отменен. Ты всегда можешь начать его снова, выбрав 'Оставить контакты'.",
        reply_markup=MAIN_KEYBOARD
    )
    context.user_data.clear()
    return ConversationHandler.END

# --- ОСНОВНАЯ ФУНКЦИЯ ЗАПУСКА БОТА ---
def main() -> None:
    """Запускает бота."""
    application = Application.builder().token(TOKEN).build()

    # Обработчик команды /start
    application.add_handler(CommandHandler("start", start))

    # Обработчик кнопки "О боте"
    application.add_handler(MessageHandler(filters.Regex("^О боте ℹ️$"), about_bot))

    # Обработчик кнопки "Написать письмо" (только для вызова подсказки)
    application.add_handler(MessageHandler(filters.Regex("^Написать письмо ✍️$"), prompt_for_letter))

    # Обработчик для inline-кнопки "Нет, спасибо" (отказ от контактов)
    application.add_handler(CallbackQueryHandler(decline_contact_conversation, pattern="^decline_contact_conv$"))

    # Обработчик для сбора контактов (ConversationHandler)
    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^Оставить контакты 📞$"), start_contact_conversation), # Через Reply-кнопку
            CallbackQueryHandler(start_contact_conversation, pattern="^start_contact_conv$") # Через Inline-кнопку
        ],
        states={
            ASK_CONTACT_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex("^Отмена ❌$"), ask_contact_name)
            ],
            ASK_CONTACT_DATA: [
                MessageHandler(filters.TEXT & ~filters.COMMAND & ~filters.Regex("^Отмена ❌$"), ask_contact_data)
            ],
        },
        fallbacks=[MessageHandler(filters.Regex("^Отмена ❌$"), cancel)],
    )
    application.add_handler(conv_handler)

    # ОБРАТИТЕ ВНИМАНИЕ: Этот обработчик должен идти ПОСЛЕ ConversationHandler,
    # чтобы сообщения в ходе диалога не перехватывались им.
    # Он будет ловить ЛЮБОЙ текстовый ввод, который не является командой или кнопкой
    # и не относится к активному ConversationHandler.
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_letter))

    logger.info("Бот запущен. Ожидание обновлений...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
