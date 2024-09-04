import logging
from loader import dp, bot, admin_id
from aiogram import types
from myFilters.user import IsCode
from data.db import get_films, get_AllChennel, get_error_link_complaint_unix, update_error_link_complaint_unix, get_text
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from time import time
from keybord_s.ohter import ikb_close, ikb_close_oikb
from keybord_s.user import sub_list, kb_films
from datetime import datetime, timedelta
from aiogram.utils.callback_data import CallbackData

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# CallbackData для обработки подписки
subscribed_callback = CallbackData("subscribed", "channel_id")

# получение фильма по коду с добавлением кнопки "Я подписался"
@dp.message_handler(IsCode())
async def get_FimsWithCode(message: types.Message):
    logging.info(f'Получен запрос на фильм от пользователя {message.from_user.id} с кодом: {message.text}')
    await message.delete()
    
    # Проверка всех каналов
    data_chennel = await get_AllChennel()
    for i in data_chennel:
        try:
            status = await bot.get_chat_member(chat_id=i[0], user_id=message.from_user.id)
            if status.status == 'left':
                # Формирование инлайн-клавиатуры с каналами
                channels_kb = InlineKeyboardMarkup(row_width=1)
                for channel in data_chennel:
                    channels_kb.add(InlineKeyboardButton(text=channel[1], url=channel[2]))

                # Создание обычной кнопки "Я подписался"
                subscribe_button = ReplyKeyboardMarkup(resize_keyboard=True)
                subscribe_button.add(KeyboardButton(text="Я подписался"))

                # Отправка сообщения с инлайн-кнопками каналов и обычной кнопкой "Я подписался"
                logging.info(f'Пользователь {message.from_user.id} не подписан на один или несколько каналов.')
                await message.answer(
                    'Вы не подписаны на канал(ы)❌\nПодпишитесь на следующие каналы, затем нажмите "Я подписался" и повторите попытку👌',
                    reply_markup=channels_kb
                )
                await message.answer(
                    'После подписки нажмите "Я подписался".',
                    reply_markup=subscribe_button
                )
                return
        except Exception as e:
            logging.error(f'Ошибка при проверке подписки пользователя {message.from_user.id} на канал {i[0]}: {str(e)}')
            await bot.send_message(
                chat_id=admin_id,
                text=f'Похоже этот канал удалил нас, запустите "Проверку каналов"\nЧтобы проверить меня на наличие прав\nИдентификатор: {i[0]}\nНазвание: {i[1]}\nСсылка: {i[2]}\nОшибка: {str(e)}',
                reply_markup=ikb_close.row(InlineKeyboardButton(text='Проверить каналы⚛️', callback_data='check_chennel_admin'))
            )

    # Проверка существования фильма по коду
    film_data = await get_films(code=message.text)
    logging.info(f'Полученные данные фильма для кода {message.text}: {film_data}')
    
    if not film_data:
        logging.warning(f'Неправильный код фильма от пользователя {message.from_user.id}: {message.text}')
        await message.answer('Неправильный код фильма❌\nПожалуйста, проверьте код и попробуйте снова.')
        return

    text_film = await get_text(type='text_text', text_type='film')
    text_film = text_film[0][0]
    me = await bot.get_me()
    text_film = str(text_film).replace('{username_bot}', me.mention)
    text_film = str(text_film).replace('{bot_id}', str(me.id))
    text_film = str(text_film).replace('{username}', message.from_user.mention)
    text_film = str(text_film).replace('{full_name}', message.from_user.full_name)
    text_film = str(text_film).replace('{user_id}', str(message.from_user.id)) 
    text_film = str(text_film).replace('{film_name}', film_data[0][1]) 
    text_film = str(text_film).replace('{film_code}', message.text) 
    
    ikb_films = await kb_films(name_films=film_data[0][1])
    logging.info(f'Отправка информации о фильме пользователю {message.from_user.id}')
    await bot.send_photo(chat_id=message.from_user.id, photo=film_data[0][2], caption=text_film, reply_markup=ikb_films.row(ikb_close_oikb), parse_mode=types.ParseMode.HTML)

# Обработчик обычной кнопки "Я подписался"
@dp.message_handler(lambda message: message.text == "Я подписался")
async def check_subscription(message: types.Message):
    logging.info(f'Проверка подписки пользователя {message.from_user.id}')
    data_chennel = await get_AllChennel()

    for i in data_chennel:
        try:
            status = await bot.get_chat_member(chat_id=i[0], user_id=message.from_user.id)
            if status.status == 'left':
                logging.warning(f'Пользователь {message.from_user.id} еще не подписался на все каналы.')
                await message.answer("Вы еще не подписались на все каналы❌")
                return
        except Exception as e:
            logging.error(f'Ошибка при проверке подписки пользователя {message.from_user.id} на канал {i[0]}: {str(e)}')
            await bot.send_message(
                chat_id=admin_id,
                text=f'Ошибка при проверке подписки пользователя {message.from_user.id} на канал {i[0]}: {str(e)}',
                reply_markup=ikb_close
            )

    # Удаление кнопки "Я подписался"
    logging.info(f'Пользователь {message.from_user.id} подтвердил подписку.')
    await message.answer("Спасибо за подписку! Теперь вы можете запросить фильм заново.", reply_markup=types.ReplyKeyboardRemove())

# Обработка кнопки "Одна из ссылок не работает❓"
@dp.callback_query_handler(text='link_no_work')
async def Link_complaint(call: types.CallbackQuery):
    logging.info(f'Пользователь {call.from_user.id} пожаловался на неработающую ссылку.')
    if await get_error_link_complaint_unix(user_id=call.from_user.id) is None or await get_error_link_complaint_unix(user_id=call.from_user.id) <= time():
        await call.message.answer('Мы отправили администратору ошибку☑️', reply_markup=ikb_close)
        await bot.send_message(chat_id=admin_id, text=f'Пользователь [{call.from_user.full_name}](tg://user?id={call.from_user.id}) пожаловался на неработающую ссылку❗️', parse_mode=types.ParseMode.MARKDOWN, reply_markup=ikb_close.row(InlineKeyboardButton(text='Проверить каналы⚛️', callback_data='check_chennel_admin')))
        timeub = datetime.now() + timedelta(hours=3)
        await update_error_link_complaint_unix(user_id=call.from_user.id, time_ub=timeub.timestamp())
    else:
        await call.answer('Вы уже жаловались❌')
