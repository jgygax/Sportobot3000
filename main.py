#!/usr/bin/python3

import utils
import logging
from datetime import datetime
from dateutil.relativedelta import relativedelta
from fuzzywuzzy import process, fuzz

import telegram
from telegram import Update, ForceReply, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler

import pandas as pd
import os


def help_command(update: Update, context: CallbackContext):
    """Send a message when the command /help is issued."""
    update.message.reply_text("These are the commands I know:\n" + instructions(),
                              parse_mode=telegram.ParseMode.HTML)


def command(update, context):
    if update.effective_user.id not in utils.users:
        print("Sorry, you have to sign up first")
        update.message.reply_markdown_v2(
            fr'Hi {user.mention_markdown_v2()}\!',
            reply_markup=ForceReply(False, selective=False),
        )
        update.message.reply_markdown_v2(
            fr'To use the Sportomat 3000, you have to sign up first\.\.\.',
            reply_markup=ForceReply(False, selective=False),
        )
    else:
        raw_text = update.message.text.strip()
        command = raw_text.split(" ")[0]

        result = process.extractOne(command, list(
            available_commands.keys()), scorer=fuzz.ratio)
        print(result, ".....")
        if result[1] < 50:
            out = "Oops, I'm not sure which command you mean. Possible options are:\n" + instructions()
            update.message.reply_text(
                text=out,
                parse_mode=telegram.ParseMode.HTML)
        else:
            available_commands[result[0]][0](update, context)


def instructions():
    out = ""
    for command_name, (function, command_description) in available_commands.items():
        out += "/{} - <i>{}</i>\n".format(command_name, command_description)
    return out


def training(update, context):
    raw_text = update.message.text.strip()
    command = raw_text.split(" ")[0]
    text = raw_text.replace(command, "").strip()
    choices = [["schwimme"], ["jogge"], ["superkondi"], ["öppis anders"]]
    show_keyboard(update, context, choices, "training", "Was hesch gmacht?")


def delete(bot, update):
    command = "SELECT ts,amount,drinks.name FROM consumptions JOIN drinks ON consumptions.drink_id = drinks.id WHERE consumptions.user_id = {} and consumptions.deleted = 0 ORDER BY consumptions.ts DESC LIMIT 5;".format(
        update.message.from_user.id)
    drinks = list(execute_command(db_file, command))

    if len(drinks) > 0:
        choices = []
        for timestamp, amount, drink in drinks:
            dt_object = datetime.fromtimestamp(timestamp)
            text = "{:%d.%m %H:%M:%S} {}l {}".format(dt_object, amount, drink)
            choices.append([text])
        choices.reverse()
        show_keyboard(bot, update, choices, "delete",
                      "Was hesch ned gmacht gha?")
    else:
        bot.send_message(update.message.from_user.id,
                         text="Du hesch jo no gar kä Sport gmacht!?",
                         parse_mode=telegram.ParseMode.HTML)


def undelete(bot, update):
    command = "SELECT ts,amount,drinks.name FROM consumptions JOIN drinks ON consumptions.drink_id = drinks.id WHERE consumptions.user_id = {} and consumptions.deleted = 1 ORDER BY consumptions.ts DESC LIMIT 5;".format(
        update.message.from_user.id)
    drinks = list(execute_command(db_file, command))

    if len(drinks) > 0:
        choices = []
        for timestamp, amount, drink in drinks:
            dt_object = datetime.fromtimestamp(timestamp)
            text = "{:%d.%m %H:%M:%S} {}l {}".format(dt_object, amount, drink)
            choices.append([text])
        choices.reverse()
        show_keyboard(bot, update, choices, "undelete",
                      "Hesch doch Sport gmacht gha?")
    else:
        bot.send_message(update.message.from_user.id,
                         text="Du hesch no gar nüüt glöscht!",
                         parse_mode=telegram.ParseMode.HTML)


def get_weight(update, context):
    print("-- get weight --")
    global df
    raw_text = update.message.text.strip()
    command = raw_text.split(" ")[0]
    try:
        weight = raw_text.split(" ")[1]
        if "kg" in weight:
            weight = weight.replace("kg", "")
            weight = float(weight)
        elif "g" in weight:
            weight = weight.replace("g", "")
            weight = float(weight) * 1000
        else:
            weight = float(weight)
    except Exception as e:
        print(e)
        update.message.reply_text(
            text="Das hani ned verstande. Korrekts biispel: <code>/weight 75kg</code>",
            parse_mode=telegram.ParseMode.HTML)
        return

    row = {
        'date': datetime.now().timestamp(),
        'user_id': update.effective_user.id,
        'user_name': update.effective_user.first_name,
        'training_type': None,
        'training_duration': None,
        'weight': weight,
        'training_distance': None
    }

    df = df.append(row, ignore_index=True)
    df.to_csv(table_name)
    print(df)

    update.message.reply_text(
        text="Du besch jetzt {:.0f}kg schwär!".format(weight),
        parse_mode=telegram.ParseMode.HTML)


def add_training(update, context, sport, duration):
    print("-- add training --")
    global df

    row = {
        'date': datetime.now().timestamp(),
        'user_id': update.effective_user.id,
        'user_name': update.effective_user.first_name,
        'training_type': sport,
        'training_duration': duration,
        'weight': None,
        'training_distance': None
    }

    df = df.append(row, ignore_index=True)
    df.to_csv(table_name)
    print(df)

    if sport == "superkondi":
        sport = "Superkondi mache"
    elif sport == "öppis anders":
        sport = "Sport mache"

    if duration == "länger":
        context.bot.send_message(update.effective_user.id,
                                 text="Du besch jetzt go " + sport + " för meh als en Stond! Nice :)",
                                 parse_mode=telegram.ParseMode.HTML)

    else:
        context.bot.send_message(update.effective_user.id,
                                 text="Du besch jetzt go " + sport + " för " + duration + "! Nice :)",
                                 parse_mode=telegram.ParseMode.HTML)


def show_keyboard(update, context, choices, action, message, command=None, user_id=None):
    keyboard = []
    if user_id is None:
        user_id = update.message.from_user.id
    if command is None:
        command = update.message.text.strip().split(" ")[0]
    for row in choices:
        keyboard.append([])
        for column in row:
            callback_data = "{} {} {} {}".format(
                action, user_id, command, column)
            keyboard[-1].append(
                InlineKeyboardButton(column, callback_data=callback_data))
    context.bot.send_message(user_id, message,
                             reply_markup=InlineKeyboardMarkup(keyboard))


def keyboard_response(update, context):
    query = update.callback_query
    data = query.data.split(" ")
    if data[0] == "öppis":
        action = "öppis anders"
        user_id = data[2]
        command = data[3]
        value = " ".join(data[4:])
    else:
        action = data[0]
        user_id = data[1]
        command = data[2]
        value = " ".join(data[3:])

    # bot.deleteMessage(chat_id=query.message.chat_id,
    #                   message_id=query.message.message_id)

    print(action, "**")
    if action == "training":
        print("-- add training --")
        # context.bot.send_message(user_id, "Wie lang besch go schwimme?",
        #                          parse_mode=telegram.ParseMode.HTML)
        choices = [["20min", "30min", "40min"], ["50min", "60min", "länger"]]
        show_keyboard(update, context, choices, value,
                      "Wie lang besch go Sport mache?", command=command, user_id=user_id)

    elif action == "list_training":
        training_list(update, context, user_id, value)
    elif action == "list_all":
        training_list_all(update, context, user_id, value)
    elif action == "highscore":
        get_highscore(update, context, user_id, value)

    else:
        add_training(update, context, action, value)


def highscore(update, context):
    choices = [["1 Woche", "1 Monet"], ["De Monet", "∞"]]
    show_keyboard(update, context, choices, "highscore", "Set wenn?")


def list_training(update, context):
    choices = [["1 Woche", "1 Monet"], ["De Monet", "∞"]]
    show_keyboard(update, context, choices, "list_training", "Set wenn?")


def list_all(update, context):
    choices = [["1 Woche", "1 Monet"], ["De Monet", "∞"]]
    show_keyboard(update, context, choices, "list_all", "Set wenn?")


def training_list(update, context, user_id, value):

    if value == "1 Woche":
        start_date = datetime.now() + relativedelta(weeks=-1)
        start_date = start_date.timestamp()
    elif value == "1 Monet":
        start_date = datetime.now() + relativedelta(months=-1)
        start_date = start_date.timestamp()
    elif value == "De Monet":
        start_date = datetime.today().replace(day=1)
        start_date = start_date.timestamp()
    else:
        start_date = 0

    print_user(update, context, user_id, start_date,
               update.effective_user.first_name)


def training_list_all(update, context, user_id, value):
    global df

    if value == "1 Woche":
        start_date = datetime.now() + relativedelta(weeks=-1)
        start_date = start_date.timestamp()
    elif value == "1 Monet":
        start_date = datetime.now() + relativedelta(months=-1)
        start_date = start_date.timestamp()
    elif value == "De Monet":
        start_date = datetime.today().replace(day=1)
        start_date = start_date.timestamp()
    else:
        start_date = 0

    users = list(set(df.user_name))
    user_ids = []
    for n in users:
        user_ids.append(list(set(df.loc[df['user_name'] == n].user_id))[0])

    for name, uid in zip(users, user_ids):
        print_user(update, context, uid, start_date, name)


def get_highscore(update, context, user_id, value):
    global df

    if value == "1 Woche":
        start_date = datetime.now() + relativedelta(weeks=-1)
        start_date = start_date.timestamp()
    elif value == "1 Monet":
        start_date = datetime.now() + relativedelta(months=-1)
        start_date = start_date.timestamp()
    elif value == "De Monet":
        start_date = datetime.today().replace(day=1)
        start_date = start_date.timestamp()
    else:
        start_date = 0

    users = list(set(df.user_name))
    user_ids = []
    for n in users:
        user_ids.append(list(set(df.loc[df['user_name'] == n].user_id))[0])

    highscores = {
        "time_all": {
            "name": [],
            "value": -1
        },
        "count": {
            "name": [],
            "value": -1
        },
        "time_run": {
            "name": [],
            "value": -1
        },
        "time_swim": {
            "name": [],
            "value": -1
        },
    }
    for name, uid in zip(users, user_ids):
        h = get_user_highscores(update, context, uid, start_date, name)
        for key, value in highscores.items():
            if value["value"] < h[key]:
                value["name"] = [h["name"]]
                value["value"] = h[key]
            elif value["value"] == h[key]:
                value["name"].append(h["name"])
        print(h)
    print("________________ ")
    print(highscores)

    names = ["Number of training", "Total Training Time",
             "Total Jogging Time", "Total Swimming Time"]
    keys = ["count", "time_all", "time_run", "time_swim"]

    message = "HIGHSCORES: \n"

    for n, k in zip(names, keys):
        message += "\n" + n + ":\n\t\t\t"
        for i, name in enumerate(highscores[k]["name"]):
            message += name
            if i != len(highscores[k]["name"])-1:
                message += " und "
        message += ": " + str(int(highscores[k]["value"]))
        if k != "count":
            message += " min"
        message += "\n"

    context.bot.send_message(update.effective_user.id, message)


def get_user_highscores(update, context, user_id, start_date, name=""):
    global df

    highscores = {
        "userid": user_id,
        "name": name,
        "time_all": 0,
        "count": 0,
        "time_run": 0,
        "time_swim": 0,
    }

    cnt = 1
    for idx, row in df.iterrows():
        if row.user_id == int(user_id):
            if not row.training_type == "nan":
                timestamp = row.date

                if timestamp >= start_date:
                    try:
                        time = float(row.training_duration.split("min")[0])
                    except:
                        time = float(row.training_duration.split("h")[0])
                    highscores["time_all"] += time
                    highscores["count"] += 1

                    if row.training_type == "jogge":
                        highscores["time_run"] += time
                    elif row.training_type == "schwimme":
                        highscores["time_swim"] += time
    return highscores


def print_user(update, context, user_id, start_date, name=""):
    global df
    message = name + ":\n"

    cnt = 1
    for idx, row in df.iterrows():
        if row.user_id == int(user_id):
            if not row.training_type == "nan":
                timestamp = row.date

                if timestamp >= start_date:
                    str_date_time = datetime.fromtimestamp(
                        timestamp).strftime("%d-%m-%Y")

                    message += str(cnt) + ": " + str_date_time + " - " + \
                        row.training_type + " - " + row.training_duration + "\n"
                    cnt += 1

    context.bot.send_message(update.effective_user.id, message)


def get_best(min_timestamp):
    command = "SELECT SUM(consumptions.amount*drinks.vol),users.name,users.id FROM consumptions JOIN users ON consumptions.user_id = users.id JOIN drinks on consumptions.drink_id = drinks.id WHERE consumptions.ts > {} and deleted = 0 GROUP BY consumptions.user_id ORDER BY SUM(consumptions.amount*drinks.vol) DESC;".format(min_timestamp)
    return list(execute_command(db_file, command))


def start(update: Update, context: CallbackContext):
    """Send a message when the command /start is issued."""
    print("-- start --")
    user = update.effective_user
    # user_id = update.message.from_user.id
    # user_name = update.message.from_user.first_name
    print("user id", user.id, user.first_name)

    if user.id not in utils.users:
        print("Sorry, you have to sign up first")
        update.message.reply_markdown_v2(
            fr'Hi {user.mention_markdown_v2()}\!',
            reply_markup=ForceReply(False, selective=False),
        )
        update.message.reply_markdown_v2(
            fr'To use the Sportomat 3000, you have to sign up first\.\.\.',
            reply_markup=ForceReply(False, selective=False),
        )
    else:
        update.message.reply_markdown_v2(
            fr"Hi {user.mention_markdown_v2()}\!",
            reply_markup=ForceReply(False, selective=False),
        )
        update.message.reply_markdown_v2(
            fr"Let's do some training :\)",
            reply_markup=ForceReply(False, selective=False),
        )
        update.message.reply_text("Welcome to Sportomat 3000. These are the commands I know:\n" + instructions(),
                                  parse_mode=telegram.ParseMode.HTML)


def create_table():
    global df
    if os.path.exists(table_name):
        df = pd.read_csv(table_name, index_col=0)
        df = df.astype({'training_type': str,
                        'training_duration': str})
    else:
        df = pd.DataFrame(
            columns=cols)
        df.to_csv(table_name)
    print(df)


cols = ['date', 'user_id', 'user_name', 'training_type',
        'training_duration', 'weight', 'training_distance']
table_name = "sport.csv"
available_commands = {"training": (training, "Zeig was trainiert hesch!"),
                      "highscore": (highscore, "Wer esch am sportlichste?"),
                      "list_training": (list_training, "Was hesch so gmacht?"),
                      "list_all": (list_all, "Was hend di andere so gmacht?"),
                      "delete": (delete, "Falls zvell ageh hesch."),
                      "undelete": (undelete, "Falls es doch gmacht gha hesch."),
                      "weight": (get_weight, "En Gwichtstracker."),
                      "help": (help_command, "En Liste vo allne commands.")
                      }


if __name__ == '__main__':
    """Start the bot."""

    create_table()

    # Create the Updater and pass it your bot's token.
    updater = Updater(utils.apikey)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Enable logging
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
    )

    logger = logging.getLogger(__name__)

    # on different commands - answer in Telegram
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))

    dispatcher.add_handler(MessageHandler(Filters.all, command))
    updater.dispatcher.add_handler(CallbackQueryHandler(keyboard_response))

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()
