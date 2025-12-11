import telebot
from telebot import types
import requests

# логика бота
class DatingBot:
    def __init__(self, token, api_client):
        self.bot = telebot.TeleBot(token)
        self.api = api_client
        self.user_state = {}  # Для хранения временных данных (userinfo)
        self.register_handlers()


    def _get_anquette_id(self, tg_id):
        """Получает anquette_id пользователя из API. Возвращает 0, если анкеты нет."""
        try:
            req = self.api.get_user(tg_id)
            if req.status_code == 200:
                response_json = req.json()

                # 1. Получаем словарь 'data'
                data = response_json.get('data')

                if data:
                    # 2. Получаем 'anquette_id' из словаря 'data'
                    # Проверяем на None, поскольку None в Go-ответе может быть 0
                    anq_id = data.get('anquette_id')
                    return anq_id if anq_id is not None else 0

        except Exception as e:
            print(f"Ошибка при получении anquette_id: {e}")

        return 0

    def _get_tg_username(self, tg_id):
        """Получает tg_username пользователя из API."""
        try:
            req = self.api.get_user(tg_id)
            if req.status_code == 200:
                return req.json().get('tg_username', f'user_{tg_id}')
        except Exception as e:
            print(f"Ошибка при получении tg_username: {e}")
        return f'user_{tg_id}'  # Дефолтное значение

    # --- Регистрация обработчиков ---

    def register_handlers(self):
        self.bot.register_message_handler(self.send_welcome, commands=['start'])
        self.bot.register_message_handler(self.show_menu, commands=['menu'])

    # --- Запуск ---

    def run(self):
        print("DatingBot запущен и ждет команд.")
        self.bot.infinity_polling()

    # --- Основные команды ---

    def send_welcome(self, message):
        """Обрабатывает команду /start."""

        # 1. Проверяем, существует ли пользователь в БД
        request = self.api.get_user(message.from_user.id)
        print(f'Проверка существования пользователя, код: {request.status_code}')

        if request.status_code == 404:
            # Пользователя нет, создаем его
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            btn_create = types.KeyboardButton('Создать анкету')
            markup.add(btn_create)

            # anquette_id для нового пользователя должен быть 0
            query = {
                'tg_id': message.from_user.id,
                'tg_username': message.from_user.username if message.from_user.username else '',
                'anquette_id': 0
            }
            response = self.api.create_user(query)
            print(f'Проверка создания пользователя, код: {response.status_code}')

            if response.status_code == 201:
                self.bot.send_message(message.chat.id,
                                      'Добро пожаловать! Я вижу, что вы здесь впервые. Начнем с создания анкеты.',
                                      reply_markup=markup)
                self.bot.register_next_step_handler(message, self.create_form)
            else:
                self.bot.send_message(message.chat.id, 'Ошибка при регистрации. Попробуйте позже.')
        else:
            # Пользователь есть, показываем меню
            self.show_menu(message)

    def show_menu(self, message):
        """Обрабатывает команду /menu и показывает анкету."""

        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        btn_find = types.KeyboardButton('Просмотреть анкеты')
        btn_likes = types.KeyboardButton('Просмотреть лайки')
        btn_change = types.KeyboardButton('Изменить анкету')
        btn_delete = types.KeyboardButton('Удалить анкету')
        markup.row(btn_find, btn_change)
        markup.row(btn_delete, btn_likes)

        anq_id = self._get_anquette_id(message.from_user.id)

        if not anq_id or anq_id == 0:
            self.bot.send_message(
                message.chat.id,
                "У вас еще нет анкеты. Сначала создайте её.",
                reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add('Создать анкету')
            )
            self.bot.register_next_step_handler(message, self.create_form)
            return

        # Если ID валидный, пытаемся получить анкету
        try:
            req = self.api.get_anquette(anq_id)
            print(f'Проверка получения данных анкеты ID={anq_id}, код: {req.status_code}')

            if req.status_code != 200:
                self.bot.send_message(message.chat.id, "Ошибка при загрузке вашей анкеты. Возможно, она была удалена.")
                return

            response_json = req.json()

            data = response_json.get('data', response_json)

            # если че то не подгрузится
            name = data.get('name', 'Не указано')
            age = data.get('age', 'Unknown')
            city = data.get('city', 'Не указан')
            gender = data.get('gender', '-')
            description = data.get('description', '')

            info = (f'Твоя анкета:\n'
                    f'Имя: {name}\n'
                    f'Возраст: {age} лет\n'
                    f'Пол: {gender.lower()}\n'
                    f'Город: {city}\n'
                    f'Описание:\n{description}')

            self.bot.send_message(message.chat.id, info, reply_markup=markup)
            self.bot.register_next_step_handler(message, self.change_form)

        except requests.exceptions.RequestException as e:
            self.bot.send_message(message.chat.id, f"Произошла ошибка при запросе к API: {e}")
        except Exception as e:
            self.bot.send_message(message.chat.id, f"Произошла непредвиденная ошибка: {e}")

    # --- Логика создания/изменения анкеты ---

    def create_form(self, message):
        """Начало процесса создания/изменения анкеты."""
        if message.text == 'Создать анкету' or message.text == 'Изменить анкету':
            self.bot.send_message(message.chat.id, 'Введи своё имя:', reply_markup=types.ReplyKeyboardRemove())
            # Инициализируем user_state для текущего пользователя
            self.user_state[message.from_user.id] = []
            self.bot.register_next_step_handler(message, self.create_form_name)
        else:
            self.bot.send_message(message.chat.id, 'Пожалуйста, выберите "Создать анкету" или "Назад в меню".')
            self.bot.register_next_step_handler(message, self.create_form)

    def create_form_name(self, message):
        if message.text == '/menu': return self.show_menu(message)
        self.user_state[message.from_user.id].append(message.text)
        self.bot.send_message(message.chat.id, 'Введи свой возраст (только число):')
        self.bot.register_next_step_handler(message, self.create_form_age)

    def create_form_age(self, message):
        if message.text == '/menu': return self.show_menu(message)

        # --- ВАЛИДАЦИЯ: Возраст должен быть числом ---
        try:
            age = int(message.text)
            if not (18 <= age <= 100):
                self.bot.send_message(message.chat.id, 'Возраст должен быть от 18 до 100. Введи возраст снова:')
                self.bot.register_next_step_handler(message, self.create_form_age)
                return
            self.user_state[message.from_user.id].append(
                str(age))  # Сохраняем как строку, преобразуем в int перед API-запросом
        except ValueError:
            self.bot.send_message(message.chat.id, 'Неверный формат. Введи возраст ТОЛЬКО числом:')
            self.bot.register_next_step_handler(message, self.create_form_age)
            return

        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        markup.add('Мужской', 'Женский')
        self.bot.send_message(message.chat.id, 'Укажи свой пол:', reply_markup=markup)
        self.bot.register_next_step_handler(message, self.create_form_gender)

    def create_form_gender(self, message):
        if message.text == '/menu': return self.show_menu(message)
        if message.text not in ['Мужской', 'Женский']:
            markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
            markup.add('Мужской', 'Женский')
            self.bot.send_message(message.chat.id, 'Пожалуйста, выбери пол кнопкой:', reply_markup=markup)
            self.bot.register_next_step_handler(message, self.create_form_gender)
            return

        self.user_state[message.from_user.id].append(message.text)

        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        markup.add('Мужской', 'Женский', 'Все равно')
        self.bot.send_message(message.chat.id, 'Укажи предпочтения по полу:', reply_markup=markup)
        self.bot.register_next_step_handler(message, self.create_form_preferences)

    def create_form_preferences(self, message):
        if message.text == '/menu': return self.show_menu(message)
        if message.text not in ['Мужской', 'Женский', 'Все равно']:
            markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
            markup.add('Мужской', 'Женский', 'Все равно')
            self.bot.send_message(message.chat.id, 'Пожалуйста, выбери предпочтения кнопкой:', reply_markup=markup)
            self.bot.register_next_step_handler(message, self.create_form_preferences)
            return

        self.user_state[message.from_user.id].append(message.text)
        self.bot.send_message(message.chat.id, 'Укажи свой город (одной строкой):',
                              reply_markup=types.ReplyKeyboardRemove())
        self.bot.register_next_step_handler(message, self.create_form_city)

    def create_form_city(self, message):
        if message.text == '/menu': return self.show_menu(message)
        self.user_state[message.from_user.id].append(message.text)
        self.bot.send_message(message.chat.id,
                              'Опиши себя (не менее 50 символов - это важно!):')  # Указываем требование Go-бэкенда
        self.bot.register_next_step_handler(message, self.create_form_description)

    def create_form_description(self, message):
        if message.text == '/menu': return self.show_menu(message)
        userinfo = self.user_state.get(message.from_user.id, [])

        if len(message.text) < 50:
            self.bot.send_message(message.chat.id,
                                  f'Описание слишком короткое ({len(message.text)}). Введи не менее 50 символов:')
            self.bot.register_next_step_handler(message, self.create_form_description)
            return

        userinfo.append(message.text)

        # Предварительный показ анкеты
        info = (f'Проверьте данные:\n'
                f'Имя: {userinfo[0]}\n'
                f'Возраст: {userinfo[1]} лет\n'
                f'Пол: {userinfo[2]}\n'
                f'Предпочтения: {userinfo[3]}\n'
                f'Город: {userinfo[4]}\n'
                f'Описание:\n{userinfo[5]}')

        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        markup.add('Подтвердить', 'Отмена')

        self.bot.send_message(message.chat.id, info, reply_markup=markup)
        self.bot.register_next_step_handler(message, self.create_final, userinfo)

    def create_final(self, message, userinfo):
        """Финальный этап создания/обновления анкеты и отправка в API."""
        if message.text == 'Отмена' or message.text == '/menu':
            self.user_state.pop(message.from_user.id, None)
            self.bot.send_message(message.chat.id, 'Создание/изменение анкеты отменено.',
                                  reply_markup=types.ReplyKeyboardRemove())
            return self.show_menu(message)

        if message.text != 'Подтвердить':
            self.bot.send_message(message.chat.id, 'Пожалуйста, нажмите "Подтвердить" или "Отмена".')
            self.bot.register_next_step_handler(message, self.create_final, userinfo)
            return

        # --- ФОРМИРОВАНИЕ И ВАЛИДАЦИЯ ДАННЫХ ДЛЯ API ---
        try:
            # преобразуем возраст из строки в int
            age_int = int(userinfo[1])
        except ValueError:
            self.bot.send_message(message.chat.id, 'Критическая ошибка: Возраст не является числом.',
                                  reply_markup=types.ReplyKeyboardRemove())
            return

        query = {
            'name': userinfo[0],
            'age': age_int,
            'city': userinfo[4],
            'gender': userinfo[2],
            'preferences': userinfo[3],
            'description': userinfo[5]
        }

        anq_id = self._get_anquette_id(message.from_user.id)

        if not anq_id or anq_id == 0:
            # --- СЦЕНАРИЙ: СОЗДАНИЕ НОВОЙ АНКЕТЫ (POST) ---

            print(f'Данные для создания анкеты (POST /anquettes): {query}')
            req = self.api.create_anquette(query)
            print(f'Создание анкеты, код: {req.status_code}')

            if req.status_code not in [200, 201]:
                error_response = req.json().get('Error', 'Неизвестная ошибка') if req.text else 'Нет ответа'
                self.bot.send_message(message.chat.id,
                                      f'Не удалось создать анкету. Код ошибки: {req.status_code}. Ответ сервера: {error_response}')
                return

            # Анкета создана. Получаем ID анкеты из ответа
            try:
                response_json = req.json()
                new_anq_id = response_json.get('id')

                if not new_anq_id:
                    # Дополнительная проверка на случай, если Go-сервер вернул статус, но не ID
                    print(f"Тело ответа сервера: {response_json}")
                    raise ValueError("ID анкеты не найден в ответе API.")
            except Exception as e:
                self.bot.send_message(message.chat.id,
                                      f'Анкета создана, но не удалось получить её ID для привязки. Ошибка: {e}.')
                return

            # Привязываем ID анкеты к пользователю (UPDATE)
            user_data = {
                'tg_id': message.from_user.id,
                'tg_username': self._get_tg_username(message.from_user.id),
                'anquette_id': new_anq_id
            }
            update_req = self.api.update_user(message.from_user.id, user_data)
            print(f'Привязка анкеты к пользователю, код: {update_req.status_code}')

            if update_req.status_code == 200:
                self.bot.send_message(message.chat.id, '🎉 Анкета успешно создана и привязана к вашему профилю!',
                                      reply_markup=types.ReplyKeyboardRemove())
            else:
                self.bot.send_message(message.chat.id,
                                      f'Анкета создана, но не привязана к профилю. Код ошибки: {update_req.status_code}')

        else:
            # --- СЦЕНАРИЙ: ОБНОВЛЕНИЕ СУЩЕСТВУЮЩЕЙ (PUT) ---

            print(f'Обновление анкеты ID: {anq_id}')
            print(f'Данные, отправляемые на PUT: {query}')

            req = self.api.update_anquette(anq_id, query)
            print(f'Обновление анкеты, код: {req.status_code}')

            if req.status_code != 200:
                error_response = req.json().get('Error', 'Неизвестная ошибка') if req.text else 'Нет ответа'
                self.bot.send_message(message.chat.id,
                                      f'Не удалось обновить анкету. Код ошибки: {req.status_code}. Ответ сервера: {error_response}')
                return

            self.bot.send_message(message.chat.id, '✅ Анкета обновлена!', reply_markup=types.ReplyKeyboardRemove())

        # Очищаем временные данные и переходим в меню
        self.user_state.pop(message.from_user.id, None)
        self.show_menu(message)

    def change_form(self, message):
        """Обрабатывает выбор в основном меню."""
        if message.text == 'Изменить анкету':
            self.bot.send_message(message.chat.id, 'Начинаем изменение. Введи своё имя:',
                                  reply_markup=types.ReplyKeyboardRemove())
            self.user_state[message.from_user.id] = []  # Начинаем сбор данных с нуля
            self.bot.register_next_step_handler(message, self.create_form_name)

        elif message.text == 'Удалить анкету':
            anq_id = self._get_anquette_id(message.from_user.id)
            if anq_id and anq_id != 0:
                # 1. Удаляем анкету
                req2 = self.api.delete_anquette(anq_id)
                print(f'Удаление анкеты, код: {req2.status_code}')

                # 2. Обнуляем anquette_id у пользователя
                user_data = {
                    'tg_id': message.from_user.id,
                    'tg_username': self._get_tg_username(message.from_user.id),
                    'anquette_id': 0
                }
                self.api.update_user(message.from_user.id, user_data)

                self.bot.send_message(message.chat.id, '❌ Ваша анкета удалена.')
                self.show_menu(message)
            else:
                self.bot.send_message(message.chat.id, 'У вас нет активной анкеты для удаления.')

        elif message.text == 'Просмотреть анкеты':
            # Здесь будет вызов логики показа анкет
            self.bot.send_message(message.chat.id, 'Функция просмотра анкет пока не реализована.')

        elif message.text == 'Просмотреть лайки':
            # Здесь будет вызов логики просмотра лайков
            self.bot.send_message(message.chat.id, 'Функция просмотра лайков пока не реализована.')

        else:
            self.show_menu(message)