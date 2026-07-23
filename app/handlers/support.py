import html

import structlog
from aiogram import Dispatcher, F, types
from aiogram.fsm.context import FSMContext

from app.config import settings
from app.database.models import User
from app.localization.texts import get_texts
from app.services.support_settings_service import SupportSettingsService
from app.states import SupportRequestStates
from app.utils.photo_message import edit_or_answer_photo


logger = structlog.get_logger(__name__)


# Категории обращения (порядок = порядок кнопок). Значение — подпись для тикета/уведомления.
SUPPORT_CATEGORIES: dict[str, str] = {
    'vpn': '🔧 Не работает VPN',
    'pay': '💳 Вопрос по оплате',
    'other': '✏️ Другое',
}


async def show_support_info(callback: types.CallbackQuery, db_user: User):
    texts = get_texts(db_user.language)

    from app.utils.support_screen import build_support_screen

    tickets_enabled = SupportSettingsService.is_tickets_enabled()
    caption, rows = build_support_screen(
        texts,
        support_username=settings.SUPPORT_USERNAME or '',
        support_url=settings.get_support_contact_url() or '',
        support_email=settings.get_support_email(),
        tickets_enabled=tickets_enabled,
    )
    await edit_or_answer_photo(
        callback=callback,
        caption=caption,
        keyboard=types.InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode='HTML',
    )
    await callback.answer()


async def show_support_request(callback: types.CallbackQuery, db_user: User, state: FSMContext):
    """Экран поддержки FreekVPN: выбор категории обращения."""
    await state.clear()
    texts = get_texts(db_user.language)

    text = texts.t(
        'SUPPORT_REQUEST_PROMPT',
        'Опиши проблему одним сообщением — ответим в течение 30 минут',
    )
    rows = [
        [types.InlineKeyboardButton(text=label, callback_data=f'support_cat:{key}')]
        for key, label in SUPPORT_CATEGORIES.items()
    ]
    rows.append([types.InlineKeyboardButton(text=texts.BACK, callback_data='menu_info')])

    await edit_or_answer_photo(
        callback=callback,
        caption=text,
        keyboard=types.InlineKeyboardMarkup(inline_keyboard=rows),
        parse_mode='HTML',
    )
    await callback.answer()


async def handle_support_category(callback: types.CallbackQuery, db_user: User, state: FSMContext):
    """Выбор категории → просим описать проблему одним сообщением."""
    category_key = callback.data.split(':', 1)[1]
    label = SUPPORT_CATEGORIES.get(category_key, SUPPORT_CATEGORIES['other'])

    await state.set_state(SupportRequestStates.waiting_for_message)
    await state.update_data(support_category=label)

    texts = get_texts(db_user.language)
    text = texts.t(
        'SUPPORT_CATEGORY_PROMPT',
        'Категория: {category}\n\nОпиши проблему одним сообщением — ответим в течение 30 минут.',
    ).format(category=html.escape(label))

    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[[types.InlineKeyboardButton(text=texts.BACK, callback_data='support_request')]]
    )
    await edit_or_answer_photo(callback=callback, caption=text, keyboard=keyboard, parse_mode='HTML')
    await callback.answer()


async def _forward_to_admins(message: types.Message, db_user: User, category: str, text: str) -> bool:
    """Fallback: пересылаем обращение админам из ADMIN_IDS, если тикеты выключены."""
    admin_ids = settings.get_admin_ids()
    if not admin_ids:
        return False

    user_ref = db_user.telegram_id or db_user.email or f'#{db_user.id}'
    header = (
        f'🆘 <b>Обращение в поддержку</b>\n'
        f'Категория: {html.escape(category)}\n'
        f'От: {html.escape(db_user.full_name or "—")} (<code>{user_ref}</code>)\n\n'
        f'{html.escape(text)}'
    )
    sent = False
    for admin_id in admin_ids:
        try:
            await message.bot.send_message(admin_id, header, parse_mode='HTML')
            sent = True
        except Exception as error:
            logger.warning('Не удалось переслать обращение админу', admin_id=admin_id, error=error)
    return sent


async def handle_support_message(message: types.Message, db_user: User, state: FSMContext, db):
    """Сообщение пользователя → создаём тикет (или форвардим админам)."""
    texts = get_texts(db_user.language)
    data = await state.get_data()
    category = data.get('support_category', SUPPORT_CATEGORIES['other'])
    await state.clear()

    user_text = (message.text or message.caption or '').strip()
    if not user_text:
        await message.answer(
            texts.t('SUPPORT_EMPTY', 'Пожалуйста, опиши проблему одним текстовым сообщением.')
        )
        return

    title = f'{category} (из бота)'
    delivered = False

    if settings.is_support_tickets_enabled():
        try:
            from app.database.crud.ticket import TicketCRUD
            from app.handlers.tickets import notify_admins_about_new_ticket

            ticket = await TicketCRUD.create_ticket(db, db_user.id, title=title, message_text=user_text)
            await notify_admins_about_new_ticket(ticket, db)
            delivered = True
        except Exception as error:
            logger.error('Не удалось создать тикет из обращения поддержки', error=error)

    if not delivered:
        delivered = await _forward_to_admins(message, db_user, category, user_text)

    keyboard = types.InlineKeyboardMarkup(
        inline_keyboard=[[types.InlineKeyboardButton(text=texts.BACK, callback_data='back_to_menu')]]
    )

    if delivered:
        await message.answer(
            texts.t('SUPPORT_SENT', '✅ Сообщение отправлено! Ответим в течение 30 минут.'),
            reply_markup=keyboard,
        )
    else:
        contact = settings.get_support_contact_display_html()
        await message.answer(
            texts.t(
                'SUPPORT_SEND_ERROR',
                '❌ Не удалось отправить обращение. Напишите нам напрямую: {contact}',
            ).format(contact=contact),
            reply_markup=keyboard,
            parse_mode='HTML',
        )


def register_handlers(dp: Dispatcher):
    dp.callback_query.register(show_support_info, F.data == 'menu_support')
    dp.callback_query.register(show_support_request, F.data == 'support_request')
    dp.callback_query.register(handle_support_category, F.data.startswith('support_cat:'))
    dp.message.register(handle_support_message, SupportRequestStates.waiting_for_message)
