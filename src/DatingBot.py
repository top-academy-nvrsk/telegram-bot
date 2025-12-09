import telebot
from telebot import types

# логика бота
class DatingBot:
    def __init__(self, token, api_client):
        self.bot = telebot.TeleBot(token)
        self.api = api_client
        self.register_handlers() # запуск регистрации команд

    # связь команды /start и /menu с методами класса
    def register_handlers(self):
        self.bot.register_message_handler(self.send_welcome, commands=['start'])
        self.bot.register_message_handler(self.show_menu, commands=['menu'])

    # метод для запуска бота
    def run(self):
        self.bot.infinity_polling()

    # /start
    def send_welcome(self, message):
        request = self.api.get_user(message.from_user.id)

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
            response = self.api.create_user(query)
            print(f'Проверка создания пользователя, код: {response.status_code}')

            self.bot.send_message(message.chat.id, 'Привет! Добро пожаловать...', reply_markup=markup)

            self.bot.register_next_step_handler(message, self.create_form)
        else:
            self.show_menu(message)

    def create_form(self, message):
        if message.text == 'Создать анкету':
            self.bot.send_message(message.chat.id, 'Введи своё имя:', reply_markup=types.ReplyKeyboardRemove())
            self.bot.register_next_step_handler(message, self.create_form_name)
        else:
            self.send_welcome(message)

    def create_form_name(self, message):
        userinfo = [message.text]

        self.bot.send_message(message.chat.id, 'Введи свой возраст:')
        self.bot.register_next_step_handler(message, self.create_form_age, userinfo)

    def create_form_age(self, message, userinfo):
        try:
            userinfo.append(int(message.text))
        except ValueError:
            self.bot.send_message(message.chat.id, 'Возраст должен быть числом! Введи его снова:')
            self.bot.register_next_step_handler(message, self.create_form_age, userinfo[:-1])
            return

        markup = types.ReplyKeyboardMarkup()
        btn_male = types.KeyboardButton('Мужской')
        btn_female = types.KeyboardButton('Женский')
        markup.row(btn_male, btn_female)

        self.bot.send_message(message.chat.id, 'Выбери свой пол:', reply_markup=markup)
        self.bot.register_next_step_handler(message, self.create_form_gender_user, userinfo)

    def create_form_gender_user(self, message, userinfo):
        userinfo.append(message.text)

        self.bot.send_message(message.chat.id, 'Выбери пол, который ты ищешь:')
        self.bot.register_next_step_handler(message, self.create_form_gender_search, userinfo)

    def create_form_gender_search(self, message, userinfo):
        userinfo.append(message.text)

        self.bot.send_message(message.chat.id, 'Напиши город, в котором проживаешь:',
                         reply_markup=types.ReplyKeyboardRemove())
        self.bot.register_next_step_handler(message, self.create_form_city, userinfo)

    def create_form_city(self, message, userinfo):
        userinfo.append(message.text)

        self.bot.send_message(message.chat.id, 'Добавь описание (не меньше 50 символов):')
        self.bot.register_next_step_handler(message, self.create_form_desc, userinfo)

    def create_form_desc(self, message, userinfo):
        userinfo.append(message.text)

        markup = types.ReplyKeyboardMarkup()
        btn_confirm = types.KeyboardButton('Подтвердить')
        btn_no = types.KeyboardButton('Неа')
        markup.add(btn_confirm, btn_no)

        self.bot.send_message(message.chat.id, 'Подтвердить сооздание анкеты?', reply_markup=markup)
        self.bot.register_next_step_handler(message, self.create_final, userinfo)

    def create_final(self, message, userinfo):
        # проверка отмены действия
        if message.text != 'Подтвердить':
            self.bot.send_message(message.chat.id, 'Создание анкеты остановлено. Напишите /start заново')
            return

        # формируем данные
        query = {
            'name': userinfo[0],
            'age': userinfo[1],
            'city': userinfo[4],
            'gender': userinfo[2],
            'preferences': userinfo[3],
            'description': userinfo[5]
        }

        response = self.api.get_user(message.from_user.id)

        print(f'Проверка существования анкеты, код: {response.status_code}')

        if response.status_code == 404:

            req = self.api.create_anquette(query)
            print(f'Создание анкеты, код: {req.status_code}')

            anquette_data = req.json()
            anquette_id = anquette_data.get('id')

            # данные для обновления пользователя
            update_data = {
                'tg_id': message.from_user.id,
                'tg_username': message.from_user.username,
                'anquette_id': anquette_id
            }

            # привязываем анкету к пользователю через метод API
            update_req = self.api.update_user(message.from_user.id, update_data)
            print(f'Обновление пользователя: {update_req.status_code}')

            self.bot.send_message(message.chat.id, 'Анкета создана! Вот так она выглядит:',
                                  reply_markup=types.ReplyKeyboardRemove())

            info_text = (f'Имя: {userinfo[0]}\n'
                         f'Возраст: {userinfo[1]} лет\n'
                         f'Пол: {userinfo[2].lower()}\n'
                         f'Город: {userinfo[4]}\n'
                         f'Описание:\n{userinfo[5]}')
            self.bot.send_message(message.chat.id, info_text)
        else:
            anq_id = self._get_anquette_id(message.from_user.id)

            req = self.api.update_anquette(anq_id, query)
            print(f'Обновление анкеты, код: {req.status_code}')

            self.bot.send_message(message.chat.id, 'Анкета обновлена!')

    # бывшая anquette_id_check.py, берёт анкету юзера по тг айди юзера
    def _get_anquette_id(self, user_id):
        req = self.api.get_user(user_id)
        data = req.json()
        return data.get('anquette_id')

    # /menu
    def show_menu(self, message):
        markup = types.ReplyKeyboardMarkup()
        btn_likes = types.KeyboardButton('Просмотреть лайки')
        btn_find = types.KeyboardButton('Просмотреть анкеты')
        btn_change = types.KeyboardButton('Изменить анкету')
        btn_delete = types.KeyboardButton('Удалить анкету')
        markup.row(btn_find, btn_change)
        markup.row(btn_delete, btn_likes)

        anq_id = self._get_anquette_id(message.from_user.id)
        req = self.api.get_anquette(anq_id)  # требует теста

        print(f'Проверка получения данных анкеты, код: {req.status_code}')
        data = req.json()

        name = data['name']
        age = data['age']
        city = data['city']
        gender = data['gender']
        description = data['description']

        info = ('Твоя анкета:\n'
                f'Имя: {name}\n'
                f'Возраст: {age} лет\n'
                f'Пол: {gender.lower()}\n'
                f'Город: {city}\n'
                f'Описание:\n{description}')

        self.bot.send_message(message.chat.id, info, reply_markup=markup)
        self.bot.register_next_step_handler(message, self.change_form)

    def change_form(self, message):
        if message.text == 'Изменить анкету':
            self.bot.send_message(message.chat.id, 'Введи своё имя:', reply_markup=types.ReplyKeyboardRemove())
            self.bot.register_next_step_handler(message, self.create_form_name)

        elif message.text == 'Удалить анкету':
            anq_id = self._get_anquette_id(message.from_user.id)
            req2 = self.api.delete_anquette(anq_id)
            print(f'Проверка удаления анкеты, код: {req2.status_code}')
            self.bot.send_message(message.chat.id, "Анкета удалена.")
            self.send_welcome(message)  # возвращаем на старт