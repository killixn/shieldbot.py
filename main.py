from bot.client import client
import json

if __name__ == '__main__':
    config = json.load(open('config/config.json'))

    client.run(config['bot_token'])