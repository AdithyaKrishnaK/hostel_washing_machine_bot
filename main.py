import os
from telebot import TeleBot, types
import json
import datetime
from functools import partial
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('API_KEY')

bot = TeleBot(API_KEY)


def load_data(func):
    def decorated(*args, **kwargs):
        with open("data.json", "r") as f:
            data = json.load(f)
        if data['time'] != "":
            free_time = datetime.datetime.strptime(
                data['time'], '%m/%d/%y %H:%M')
            if datetime.datetime.now() > free_time:
                data['free'] = True
                
                with open("data.json", "w") as f:
                        f.write(json.dumps(data))

        kwargs['data'] = data
        return func(*args, **kwargs)

    return decorated


@bot.message_handler(commands=['Hi'])
def greet(message):
    bot.reply_to(message, "Hi")
@bot.message_handler(commands=['start'])
def start(message):
    msg = "/free to check if the washing machine is free \n/currentUser to see who is using it now \n/previousUser to see who used it before \nuse time(in minutes) to start using the the machine"
    bot.send_message(message.chat.id, msg)

@bot.message_handler(commands=['free'])
@load_data
def is_machine_free(message, data):
    if data['free']:
        bot.send_message(message.chat.id, "Machine is free")
    else:
        bot.send_message(
            message.chat.id, f"Machine will be free at {data['time']}. It is currently used by {data['user']}.")


def change_request(message):
    request = message.text.split()
    if len(request) < 2 or request[0].lower() != "use" or not request[1].isnumeric():
        return False
    else:
        return True


@bot.message_handler(func=change_request)
@load_data
def use_machine(message, data):
    minutes = int(message.text.split()[1])
    if message.from_user.first_name is not None:
        user_name = message.from_user.first_name + " " 
        if message.from_user.last_name is not None:
            user_name += message.from_user.last_name
    elif message.from_user.username is not None:
        user_name = message.from_user.username
    else:
        user_name = "John Doe"

    user = {
        'id': message.from_user.id,
        'user': user_name,
        'contact': message.contact,
        'time':datetime.datetime.now()+datetime.timedelta(minutes=minutes)
    }
    if data['free'] or user['id']==data['user_id']:
        change_user(user, data)
        bot.send_message(message.chat.id, f"Acknowledged. Washing ends at {user['time']}")
    else:
        markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
        markup.add('yes', 'no')
        bot.send_message(
            message.chat.id, f"This machine is currently being used by {data['user']}. Do you wish to continue?", reply_markup=markup)
        override_user_partial = partial(override_user, user)
        bot.register_next_step_handler(message, override_user_partial)


@load_data
def override_user(user, message, data):
    bot.send_message(message.chat.id, f"Copy that. Washing ends at {user['time']}")
    bot.send_message(
        data['user_id'], f"Washing machine is now being used by {message.from_user.first_name}")
    change_user(user, data)


def change_user(user, data):
    data['free'] = False
    data['prev_user_id'] = data['user_id']
    data['prev_user'] = data['user']
    data['prev_user_contact'] = data['contact']

    data['time'] = user['time'].strftime('%m/%d/%y %H:%M')
    data['user_id'] = user['id']
    data['user'] = user['user']
    data['contact'] = user['contact']
    with open('data.json', 'w') as f:
        f.write(json.dumps(data))


@bot.message_handler(commands=['currentUser'])
@load_data
def current_user(message, data):
    if data['free']:
        bot.send_message(message.chat.id, "Machine is free")
    elif data['user'] != "":
        bot.send_message(
            message.chat.id, f"Machine is being used by {data['user']}, contact: {data['contact']}")
    else:
        bot.send_message(message.chat.id, "Idk")


@bot.message_handler(commands=['previousUser'])
@load_data
def prev_user(message, data):
    if data['prev_user'] != "":
        bot.send_message(
            message.chat.id, f"Machine was last used by {data['prev_user']}, contact: {data['prev_user_contact']}")
    else:
        bot.send_message(message.chat.id, "Idk")


bot.polling()
