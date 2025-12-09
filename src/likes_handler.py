import telebot
from telebot import types
import requests
from config import API_BASE_URL
from anquette_id_check import id_check

def _poluchit_id_ankety_polzovatelya(message):
    """функция для получения id анкеты текущего пользователя"""
    return id_check(message)

def _otpravit_soobshenie_i_zaregistrirovat_sleduyushiy_shag(bot, message, tekst, razmetka_otveta, funktsiya_sleduyushego_shaga, *args):
    """отправляет сообщение и рег следующий шаг"""
    bot.send_message(message.chat.id, tekst, reply_markup=razmetka_otveta)
    bot.register_next_step_handler(message, funktsiya_sleduyushego_shaga, bot, *args)

def _poluchit_detali_ankety(id_ankety):
    """получает детали анкеты по ее id"""
    try:
        otvet = requests.get(f'{API_BASE_URL}/anquettes/{id_ankety}')
        print(f'получение данных анкеты {id_ankety}, код: {otvet.status_code}')
        otvet.raise_for_status() # Вызовет исключение для ошибок HTTP (4xx или 5xx)
        return otvet.json()
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при получении данных анкеты {id_ankety}: {e}")
        return None

def _uvedomit_ob_otsutstvii_laikov(bot, message, tekst_soobsheniya):
    """Уведомляет пользователя об отсутствии лайков и предлагает вернуться в меню"""
    razmetka = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True)
    knopka_menu = types.KeyboardButton('Назад в меню')
    razmetka.add(knopka_menu)
    _otpravit_soobshenie_i_zaregistrirovat_sleduyushiy_shag(bot, message, tekst_soobsheniya, razmetka, _obrabotat_vozvrat_v_menu)

def show_likes(bot, message):
    """основная функция для отображения анкет, которые лайкнули пользователя"""
    id_tekushego_polzovatelya = _poluchit_id_ankety_polzovatelya(message)
    if not id_tekushego_polzovatelya:
        bot.send_message(message.chat.id, "Не удалось получить ID вашей анкеты. Пожалуйста, попробуйте снова")
        return

    try:
        otvet = requests.get(f'{API_BASE_URL}/likes/{id_tekushego_polzovatelya}')
        print(f'получение лайков для анкеты {id_tekushego_polzovatelya}, код: {otvet.status_code}')
        otvet.raise_for_status() # Вызовет исключение для ошибок HTTP (4xx или 5xx)
        spisok_laikov = otvet.json()
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при получении лайков: {e}")
        _uvedomit_ob_otsutstvii_laikov(bot, message, 'Произошла ошибка при загрузке лайков. Пожалуйста, попробуйте позже.')
        return

    if not spisok_laikov:
        _uvedomit_ob_otsutstvii_laikov(bot, message, 'У тебя пока нет новых лайков! Возвращайся позже.')
        return

    _pokazat_anketu_iz_laikov(bot, message, spisok_laikov, 0)

def _pokazat_anketu_iz_laikov(bot, message, spisok_laikov, tekushiy_index):
    """отображает конкретную анкету из списка лайков."""
    if tekushiy_index >= len(spisok_laikov):
        # если анкеты закончились
        _uvedomit_ob_otsutstvii_laikov(bot, message, 'Это все лайки! Больше анкет пока нет.')
        return

    id_ankety_dlya_pokaza = spisok_laikov[tekushiy_index].get('anquette_id')
    if not id_ankety_dlya_pokaza:
        print(f"Не найден 'anquette_id' для элемента {tekushiy_index} в списке лайков.")
        _pokazat_anketu_iz_laikov(bot, message, spisok_laikov, tekushiy_index + 1)
        return

    dannye_ankety = _poluchit_detali_ankety(id_ankety_dlya_pokaza)

    if not dannye_ankety:
        # если анкета недоступна, переходим к следующей
        bot.send_message(message.chat.id, f"Не удалось загрузить анкету ID: {id_ankety_dlya_pokaza}. Переходим к следующей.")
        _pokazat_anketu_iz_laikov(bot, message, spisok_laikov, tekushiy_index + 1)
        return

    # парсим данные анкеты
    name = dannye_ankety.get('name', 'Неизвестно')
    age = dannye_ankety.get('age', 'Неизвестно')
    city = dannye_ankety.get('city', 'Неизвестно')
    gender = dannye_ankety.get('gender', 'Неизвестно')
    description = dannye_ankety.get('description', 'Без описания')

    # формируем текст анкеты
    tekst_ankety = (f"*{name}*, {age} лет\n"
                   f"Город: {city}\n"
                   f"Пол: {gender}\n"
                   f"Описание: {description}")

    # создаем клавиатуру с действиями
    razmetka = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    razmetka.add(types.KeyboardButton('Лайк'),
               types.KeyboardButton('Дизлайк'),
               types.KeyboardButton('Валентинка'),
               types.KeyboardButton('Жалоба'),
               types.KeyboardButton('Назад в меню'))

    bot.send_message(message.chat.id, tekst_ankety, reply_markup=razmetka, parse_mode='Markdown')

    # регистрируем обработчик действий
    bot.register_next_step_handler(message, _obrabotat_deystvie, bot, spisok_laikov,
                                 tekushiy_index, id_ankety_dlya_pokaza)

def _obrabotat_vzaimodeystvie(id_otpravitelya, id_poluchatelya, tip_deystviya, endpoint):
    """отправляет запрос на сервер для выполнения действия."""
    dannye_dlya_otpravki = {
        'from_anquette_id': id_otpravitelya,
        'to_anquette_id': id_poluchatelya,
        'action_type': tip_deystviya
    }
    try:
        otvet = requests.post(f'{API_BASE_URL}/{endpoint}', json=dannye_dlya_otpravki)
        print(f'отправка {tip_deystviya} на {endpoint}, код: {otvet.status_code}, ответ: {otvet.text}')
        otvet.raise_for_status()
        return otvet
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при отправке действия '{tip_deystviya}': {e}")
        return None

def _obrabotat_deystvie(message, bot, spisok_laikov, tekushiy_index, id_ankety_dlya_pokaza):
    """обрабатывает действия пользователя с анкетой."""
    id_tekushego_polzovatelya = _poluchit_id_ankety_polzovatelya(message)
    if not id_tekushego_polzovatelya:
        bot.send_message(message.chat.id, "Не удалось получить ID вашей анкеты для совершения действия. Попробуйте снова.")
        _pokazat_anketu_iz_laikov(bot, message, spisok_laikov, tekushiy_index)
        return

    soobsheniya_deystviy = {
        'Лайк': 'Лайк отправлен!',
        'Дизлайк': 'Дизлайк отправлен.',
        'Валентинка': 'Валентинка отправлена!',
        'Жалоба': 'Жалоба отправлена.'
    }
    endpointy_deystviy = {
        'Лайк': ('interactions', 'like'),
        'Дизлайк': ('interactions', 'dislike'),
        'Валентинка': ('interactions', 'valentine'),
        'Жалоба': ('complaints', 'complaint')
    }

    if message.text in soobsheniya_deystviy:
        endpoint, tip_deystviya_val = endpointy_deystviy[message.text]
        result = _obrabotat_vzaimodeystvie(id_tekushego_polzovatelya, id_ankety_dlya_pokaza, tip_deystviya_val, endpoint)

        if result:
            bot.send_message(message.chat.id, soobsheniya_deystviy[message.text])
        else:
            bot.send_message(message.chat.id, f"Не удалось выполнить действие '{message.text}'. Попробуйте еще раз.")

        _pokazat_anketu_iz_laikov(bot, message, spisok_laikov, tekushiy_index + 1)
    elif message.text == 'Назад в меню':
        _obrabotat_vozvrat_v_menu(message, bot)
    else:
        bot.send_message(message.chat.id, 'Пожалуйста, выберите действие из предложенных кнопок!')
        _pokazat_anketu_iz_laikov(bot, message, spisok_laikov, tekushiy_index)

def _obrabotat_vozvrat_v_menu(message, bot):
    """возврат в главное меню."""
    try:
        from main import show_menu
        show_menu(message)
    except ImportError:
        bot.send_message(message.chat.id, "Произошла ошибка при возврате в меню. Пожалуйста, перезапустите бота.")