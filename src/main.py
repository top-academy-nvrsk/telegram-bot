import telebot
from telebot import types
import sqlite3  # временная бд
import requests  # будущая связь с апи, наверное??

bot = telebot.TeleBot('8509340429:AAH9ML0auG1v24MgMsobUAeh_iI0OBD1UCQ')

@bot.message_handler(commands=['start'] )
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup()
    btn_create = types.KeyboardButton('Создать анкету')
    markup.add(btn_create)

    conn = sqlite3.connect('test.db')  # тестовая бд
    cursor = conn.cursor()

    cursor.execute('CREATE TABLE IF NOT EXISTS users ('
                   'form_id INTEGER PRIMARY KEY AUTOINCREMENT, '
                   'name varchar(50) NOT NULL,'
                   'age varchar(50) NOT NULL,'
                   'gender_user varchar(50) NOT NULL, '
                   'gender_search varchar(50) NOT NULL,'
                   'city varchar(50) NOT NULL, '
                   'desc varchar(255) NOT NULL)')
    conn.commit()
    cursor.close()
    conn.close()

    bot.send_message(message.chat.id, 'Привет! Добро пожаловать в бот для поиска знакомств!', reply_markup=markup)
    bot.register_next_step_handler(message, create_form)

def create_form(message):
    if message.text == 'Создать анкету':
        bot.send_message(message.chat.id, 'Введи своё имя:', reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(message, create_form_name)
    else:
        send_welcome(message)

def create_form_name(message):
    name = message.text
    bot.send_message(message.chat.id, 'Введи свой возраст:')
    bot.register_next_step_handler(message, create_form_age, name)

def create_form_age(message, name):
    age = message.text

    markup = types.ReplyKeyboardMarkup()
    btn_male = types.KeyboardButton('Мужской')
    btn_female = types.KeyboardButton('Женский')
    markup.row(btn_male, btn_female )

    bot.send_message(message.chat.id, 'Выбери свой пол:', reply_markup=markup)
    bot.register_next_step_handler(message, create_form_gender_user, name, age)

def create_form_gender_user(message, name, age):
    gender_user = message.text

    bot.send_message(message.chat.id, 'Выбери пол, который ты ищешь:')
    bot.register_next_step_handler(message, create_form_gender_search, name, age, gender_user)

def create_form_gender_search(message, name, age, gender_user):
    gender_search = message.text
    bot.send_message(message.chat.id, 'Напиши город, в котором проживаешь:',
                     reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(message, create_form_city, name, age,
                                   gender_user, gender_search)

def create_form_city(message, name, age, gender_user, gender_search):
    city = message.text
    bot.send_message(message.chat.id, 'Добавь описание (не меньше 50 символов):')
    bot.register_next_step_handler(message, create_form_desc, name, age,
                                   gender_user, gender_search, city)

def create_form_desc(message, name, age, gender_user, gender_search, city):
    desc = message.text
    user_id = message.from_user.id

    # временная бд
    conn = sqlite3.connect('test.db')
    cursor = conn.cursor()
    cursor.execute(f'INSERT INTO users (name, age, gender_user, gender_search, city, desc) '
                   f'VALUES ("{name}", "{age}", "{gender_user}", "{gender_search}", "{city}", "{desc}")')
    conn.commit()
    cursor.close()
    conn.close()

    bot.send_message(message.chat.id, 'Анкета успешно создана! Вот так она выглядит:')
    bot.send_message(message.chat.id, f'Имя: {name}\n'
                                      f'Возраст: {age} лет\n'
                                      f'Пол: {gender_user.lower()}\n'
                                      f'Город: {city}\n'
                                      f'Описание:\n{desc}')

bot.infinity_polling()