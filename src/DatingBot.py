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

            self.bot.send_message(message.chat.id, 'Привет! Добро пожаловать в бот для поиска знакомств!',
                                  reply_markup=markup)

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

        self.bot.send_message(message.chat.id, 'Подтвердить создание анкеты?', reply_markup=markup)
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

        elif message.text == 'Просмотреть лайки':
            self.show_likes(message)

        elif message.text == 'Удалить анкету':
            anq_id = self._get_anquette_id(message.from_user.id)
            req2 = self.api.delete_anquette(anq_id)
            print(f'Проверка удаления анкеты, код: {req2.status_code}')
            self.bot.send_message(message.chat.id, "Анкета удалена.")
            self.send_welcome(message)

        elif message.text == 'Просмотреть анкеты':
            self.find_profiles(message)

        # возврат в меню
        elif message.text == 'Назад в меню' or message.text == 'Просмотреть анкеты':
            self.show_menu(message)


    def show_likes(self, message):
        """Загружает лайки и запускает просмотр"""
        my_anq_id = self._get_anquette_id(message.from_user.id)
        if not my_anq_id:
            self.bot.send_message(message.chat.id, "Сначала создайте анкету!")
            return

        try:
            response = self.api.get_likes(my_anq_id)
            response.raise_for_status()
            likes_list = response.json()
        except Exception as e:
            print(f"Ошибка получения лайков: {e}")
            self.bot.send_message(message.chat.id, "Ошибка при загрузке лайков.")
            return

        if not likes_list:
            self.bot.send_message(message.chat.id, "У тебя пока нет новых лайков! Возвращайся позже.")
            self.show_menu(message)
            return

        # Начинаем просмотр с индекса 0
        self._show_next_like_profile(message, likes_list, 0)

    def _show_next_like_profile(self, message, likes_list, index):
        """Рекурсивно показывает анкеты из списка"""
        # Если список закончился
        if index >= len(likes_list):
            self.bot.send_message(message.chat.id, "Это все лайки! Больше анкет пока нет.")
            self.show_menu(message)
            return

        # Получаем ID анкеты того, кто лайкнул
        target_anq_id = likes_list[index].get('anquette_id')

        # Загружаем детали этой анкеты через API
        try:
            req = self.api.get_anquette(target_anq_id)
            if req.status_code != 200:
                # Если анкета удалена или ошибка - пропускаем
                self._show_next_like_profile(message, likes_list, index + 1)
                return
            target_data = req.json()
        except Exception as e:
            print(f"Error fetching profile: {e}")
            self._show_next_like_profile(message, likes_list, index + 1)
            return

        # Формируем текст
        info_text = (f"*{target_data.get('name')}*, {target_data.get('age')} лет\n"
                     f"Город: {target_data.get('city')}\n"
                     f"Пол: {target_data.get('gender')}\n"
                     f"Описание: {target_data.get('description')}")

        # Клавиатура действий
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        markup.add(
            types.KeyboardButton('Лайк'),
            types.KeyboardButton('Дизлайк'),
            types.KeyboardButton('Валентинка'),
            types.KeyboardButton('Жалоба'),
            types.KeyboardButton('Назад в меню')
        )

        self.bot.send_message(message.chat.id, info_text, reply_markup=markup, parse_mode='Markdown')

        # Регистрируем шаг обработки действия
        self.bot.register_next_step_handler(
            message,
            self._handle_like_action,
            likes_list,
            index,
            target_anq_id
        )

    def _handle_like_action(self, message, likes_list, index, target_anq_id):
        """Обрабатывает нажатие кнопки (Лайк/Дизлайк...)"""

        if message.text == 'Назад в меню':
            self.show_menu(message)
            return

        actions_map = {
            'Лайк': ('interactions/like', 'Лайк отправлен!'),
            'Дизлайк': ('interactions/dislike', 'Дизлайк отправлен.'),
            'Валентинка': ('interactions/valentine', 'Валентинка отправлена!'),
            'Жалоба': ('complaints/complaint', 'Жалоба отправлена.')
        }

        if message.text not in actions_map:
            self.bot.send_message(message.chat.id, "Пожалуйста, выберите действие кнопкой.")
            # Повторяем показ ТОЙ ЖЕ анкеты
            self.bot.register_next_step_handler(message, self._handle_like_action,
                                                likes_list, index, target_anq_id)
            return

        # Получаем параметры для запроса
        endpoint, success_msg = actions_map[message.text]
        my_anq_id = self._get_anquette_id(message.from_user.id)

        payload = {
            'from_anquette_id': my_anq_id,
            'to_anquette_id': target_anq_id,
            'action_type': endpoint.split('/')[-1]  # like, dislike...
        }

        # Отправляем в API
        try:
            self.api.perform_interaction(endpoint, payload)
            self.bot.send_message(message.chat.id, success_msg)
        except Exception as e:
            print(f"Ошибка взаимодействия: {e}")
            self.bot.send_message(message.chat.id, "Что-то пошло не так, но мы идем дальше.")

        # Переходим к следующему лайку (index + 1)
        self._show_next_like_profile(message, likes_list, index + 1)


    # --- ЛОГИКА ПОИСКА (ПРОСМОТР АНКЕТ) ---

    def find_profiles(self, message):
        """Загружает список всех анкет и запускает просмотр"""
        my_anq_id = self._get_anquette_id(message.from_user.id)
        if not my_anq_id:
            self.bot.send_message(message.chat.id, "Сначала создайте анкету!")
            return

        try:
            # 1. Получаем список всех анкет
            response = self.api.get_candidates()
            response.raise_for_status()
            candidates = response.json()
        except Exception as e:
            print(f"Ошибка загрузки кандидатов: {e}")
            self.bot.send_message(message.chat.id, "Не удалось загрузить анкеты.")
            self.show_menu(message)
            return

        # 2. Фильтруем список
        candidates = [c for c in candidates if c.get('id') != my_anq_id]

        if not candidates:
            self.bot.send_message(message.chat.id, "Пока нет никого нового. Заходи позже!")
            self.show_menu(message)
            return

        self.bot.send_message(message.chat.id, "Поиск пары... 🔍")
        # 3. Начинаем показ с 0-го индекса
        self._show_next_candidate(message, candidates, 0)

    def _show_next_candidate(self, message, candidates, index):
        """Показывает конкретного кандидата по индексу"""

        # Если дошли до конца списка
        if index >= len(candidates):
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add('В начало списка', 'Назад в меню')
            self.bot.send_message(message.chat.id, "Анкеты закончились! Показать заново?", reply_markup=markup)
            self.bot.register_next_step_handler(message, self._handle_end_of_search, candidates)
            return

        candidate = candidates[index]

        info_text = (f"*{candidate.get('name')}*, {candidate.get('age')} лет\n"
                     f"Город: {candidate.get('city')}\n"
                     f"Пол: {candidate.get('gender')}\n"
                     f"Описание:\n{candidate.get('description')}")

        # Клавиатура действий
        markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
        markup.add(
            types.KeyboardButton('❤️'),
            types.KeyboardButton('👎'),
            types.KeyboardButton('💌'),
            types.KeyboardButton('💤')
        )

        self.bot.send_message(message.chat.id, info_text, reply_markup=markup, parse_mode='Markdown')

        # Ждем реакции
        self.bot.register_next_step_handler(
            message,
            self._handle_candidate_action,
            candidates,
            index,
            candidate.get('id')
        )

    def _handle_candidate_action(self, message, candidates, index, target_anq_id):
        """Обрабатывает Лайк/Дизлайк и листает дальше"""

        my_anq_id = self._get_anquette_id(message.from_user.id)

        # Карта действий (Текст кнопки -> API endpoint)
        actions_map = {
            '❤️': 'interactions/like',
            '👎': 'interactions/dislike',
            '💌': 'interactions/valentine',
        }

        # 1. Если нажали "Сон" - выходим
        if message.text == '💤':
            self.show_menu(message)
            return

        # 2. Если нажали кнопку действия
        if message.text in actions_map:
            endpoint = actions_map[message.text]
            payload = {
                'from_anquette_id': my_anq_id,
                'to_anquette_id': target_anq_id,
                'action_type': endpoint.split('/')[-1]
            }

            try:
                self.api.perform_interaction(endpoint, payload)
                # Можно писать "Лайк отправлен", а можно просто молча листать дальше
            except Exception as e:
                print(f"Ошибка интеракции: {e}")

            # ЛИСТАЕМ ДАЛЬШЕ (index + 1)
            self._show_next_candidate(message, candidates, index + 1)

        else:
            self.bot.send_message(message.chat.id, "Используй кнопки!")
            # Повторяем тот же профиль
            self.bot.register_next_step_handler(message, self._handle_candidate_action, candidates, index,
                                                target_anq_id)

    def _handle_end_of_search(self, message, candidates):
        if message.text == 'В начало списка':
            self._show_next_candidate(message, candidates, 0)
        else:
            self.show_menu(message)