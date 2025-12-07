import telebot
from telebot import types
import requests
from config import API_BASE_URL
from anquette_id_check import id_check

bot = telebot.TeleBot('8509340429:AAH9ML0auG1v24MgMsobUAeh_iI0OBD1UCQ')

@bot.message_handler(commands=['start'] )
def send_welcome(message):
    request = requests.get(f'{API_BASE_URL}/users/{message.from_user.id}')
    print(f'Проверка существования пользователя, код: {request.status_code}')
    if request.status_code == 404:
        markup = types.ReplyKeyboardMarkup()
        btn_create = types.KeyboardButton('Создать анкету')
        markup.add(btn_create)

        query = {
            'tg_id': message.from_user.id,
            'tg_username': message.from_user.username,
            'anquette_id': None
        }
        response = requests.post(f"{API_BASE_URL}/users", json=query)
        print(f'Проверка создания пользователя, код: {response.status_code}')

        bot.send_message(message.chat.id, 'Привет! Добро пожаловать в бот для поиска знакомств!',
                         reply_markup=markup)
        bot.register_next_step_handler(message, create_form)
    else:
        show_menu(message)

def create_form(message):
    if message.text == 'Создать анкету':
        bot.send_message(message.chat.id, 'Введи своё имя:', reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(message, create_form_name)
    else:
        send_welcome(message)

def create_form_name(message):
    userinfo = [message.text]

    bot.send_message(message.chat.id, 'Введи свой возраст:')
    bot.register_next_step_handler(message, create_form_age, userinfo)

def create_form_age(message, userinfo):
    try:
        userinfo.append(int(message.text))
    except ValueError:
        bot.send_message(message.chat.id, 'Возраст должен быть числом! Введи его снова:')
        bot.register_next_step_handler(message, create_form_age, userinfo[:-1])
        return

    markup = types.ReplyKeyboardMarkup()
    btn_male = types.KeyboardButton('Мужской')
    btn_female = types.KeyboardButton('Женский')
    markup.row(btn_male, btn_female)

    bot.send_message(message.chat.id, 'Выбери свой пол:', reply_markup=markup)
    bot.register_next_step_handler(message, create_form_gender_user, userinfo)

def create_form_gender_user(message, userinfo):
    userinfo.append(message.text)

    bot.send_message(message.chat.id, 'Выбери пол, который ты ищешь:')
    bot.register_next_step_handler(message, create_form_gender_search, userinfo)

def create_form_gender_search(message, userinfo):
    userinfo.append(message.text)

    bot.send_message(message.chat.id, 'Напиши город, в котором проживаешь:', reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(message, create_form_city, userinfo)

def create_form_city(message, userinfo):
    userinfo.append(message.text)

    bot.send_message(message.chat.id, 'Добавь описание (не меньше 50 символов):')
    bot.register_next_step_handler(message, create_form_desc, userinfo)

def create_form_desc(message, userinfo):
    userinfo.append(message.text)

    markup = types.ReplyKeyboardMarkup()
    btn_confirm = types.KeyboardButton('Подтвердить')
    btn_no = types.KeyboardButton('Неа')
    markup.add(btn_confirm, btn_no)

    bot.send_message(message.chat.id, 'Подтвердить сооздание анкеты?', reply_markup=markup)
    bot.register_next_step_handler(message, create_final, userinfo)

def create_final(message, userinfo):
    if message.text == 'Подтвердить':
        query = {
            'name': userinfo[0],
            'age': userinfo[1],
            'city': userinfo[4],
            'gender': userinfo[2],
            'preferences': userinfo[3],
            'description': userinfo[5]
        }

        response = requests.get(f"{API_BASE_URL}/users/{message.from_user.id}")  # требует теста
        print(f'Проверка существования анкеты у пользователя, код: {response.status_code}')
        if response.status_code == 404:
            req = requests.post(f"{API_BASE_URL}/anquettes", json=query)
            print(f'Проверка создания новой анкеты, код: {req.status_code}')

            anquette_data = req.json()
            anquette_id = anquette_data.get('id')
            print(f"ID созданной анкеты: {anquette_id}")

            update_data = {
                'tg_id': message.from_user.id,
                'tg_username': message.from_user.username,
                'anquette_id': anquette_id
            }
            update_req = requests.put(f"{API_BASE_URL}/users/{message.from_user.id}", json=update_data)
            print(f'Обновление пользователя: {update_req.status_code}')

            bot.send_message(message.chat.id, 'Анкета создана! Вот так она выглядит:',
                         reply_markup=types.ReplyKeyboardRemove())
            bot.send_message(message.chat.id, f'Имя: {userinfo[0]}\n'
                                            f'Возраст: {userinfo[1]} лет\n'
                                            f'Пол: {userinfo[2].lower()}\n'
                                            f'Город: {userinfo[4]}\n'
                                            f'Описание:\n{userinfo[5]}')
        else:
            req = requests.put(f"{API_BASE_URL}/anquettes/{id_check(message)}", json=query)
            print(f'Проверка обновления анкеты, код: {req.status_code}')

            bot.send_message(message.chat.id, 'Анкета обновлена!')
    else:
        bot.send_message(message.chat.id, 'Создание анкеты остановлено. Напишите /start заного')

@bot.message_handler(commands=['menu'])
def show_menu(message):
    markup = types.ReplyKeyboardMarkup()
    btn_likes = types.KeyboardButton('Просмотреть лайки')
    btn_find = types.KeyboardButton('Просмотреть анкеты')
    btn_change = types.KeyboardButton('Изменить анкету')
    btn_delete = types.KeyboardButton('Удалить анкету')
    markup.row(btn_find, btn_change)
    markup.row(btn_delete, btn_likes)

    req = requests.get(f"{API_BASE_URL}/anquettes/{id_check(message)}")  # требует теста
    print(f'Проверка получения данных анкеты, код: {req.status_code}')
    data = req.json()

    name = data['name']
    age = data['age']
    city = data['city']
    gender = data['gender']
    description = data['description']

    info = ''
    info += ('Твоя анкета:\n'
            f'Имя: {name}\n'
            f'Возраст: {age} лет\n'
            f'Пол: {gender.lower()}\n'
            f'Город: {city}\n'
            f'Описание:\n{description}')

    bot.send_message(message.chat.id, info, reply_markup=markup)
    bot.register_next_step_handler(message, change_form)

def change_form(message):
    if message.text == 'Изменить анкету':
        bot.send_message(message.chat.id, 'Введи своё имя:', reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(message, create_form_name)
    elif message.text == 'Просмотреть анкеты':
        pass  # заглушка для функции поиска анкет
    elif message.text == 'Просмотреть лайки':
        pass  # заглушка для функции показа лайков
    elif message.text == 'Удалить анкету':
        req2 = requests.delete(f"{API_BASE_URL}/anquettes/{id_check(message)}")  # требует теста
        print(f'Проверка удаления анкеты, код: {req2.status_code}')

bot.infinity_polling()