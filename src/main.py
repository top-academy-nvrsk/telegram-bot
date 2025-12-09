from DatingBot import DatingBot
from config import API_BASE_URL, BOT_TOKEN
from DatingAPI import DatingAPI

if __name__ == '__main__':
    my_api = DatingAPI(API_BASE_URL)

    my_bot = DatingBot(BOT_TOKEN, my_api)

    print("Бот запускается...")
    my_bot.run()