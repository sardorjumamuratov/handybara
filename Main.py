import os
from json import JSONEncoder, JSONDecodeError

from telegram import *
from telegram.constants import ParseMode
from telegram.ext import *
from pathlib import Path
import json
from Item import *
from datetime import datetime as dt

items_list = []
deleted_items_list = []
parse_mode_global = ParseMode.HTML
emojis = {
    "done": '✅',
    "left_arrow": '⬅️',
    "right_arrow": '➡️',
    "x": '❌'
}

users_user_id = {
    "sardor": 648501941,
    "max": 0
}

user_ids = [648501941]

last_items_list_message_id = {user_ids[0]: 0}

last_message_id_bot = {user_ids[0]: 0}

is_item_being_added = {user_ids[0]: False}

path_deleted_items_json_file = Path('util/files/deleted_items.json')
path_items_txt_file = Path('util/files/items.txt')
path_users_info_file = Path('util/files/users_info.txt')

selected_users_filter = filters.User(user_ids)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global last_message_id_bot
    buttons = [[KeyboardButton(text="Items to be purchased")]]
    user_id = update.effective_user.id
    last_message_id_bot[user_id] = update.effective_message.id + 1
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text="Hi. I'll help you sort out "
                                        "your problems with groceries.",
                                   reply_markup=ReplyKeyboardMarkup(buttons,
                                                                    resize_keyboard=True,
                                                                    one_time_keyboard=True))


async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global last_message_id_bot

    user_id = update.effective_user.id
    last_message_id_bot[user_id] = update.effective_message.id + 1
    await context.bot.send_document(chat_id=update.effective_chat.id, document=path_deleted_items_json_file)


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Sorry, I didn't understand that command.")


async def texts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global items_list, last_items_list_message_id, last_message_id_bot, user_ids, selected_users_filter
    user_id = update.effective_user.id
    if update.message.text == "Items to be purchased":
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=message_items_list(),
                                       reply_markup=generate_inline_keyboard_markup(),
                                       parse_mode=parse_mode_global)

        if last_items_list_message_id[user_id]:
            await context.bot.edit_message_text(chat_id=update.effective_chat.id,
                                                text="<i>This items list is expired... You've got the new one "
                                                     "though</i>",
                                                message_id=last_items_list_message_id[user_id],
                                                parse_mode=parse_mode_global)
        last_message_id_bot[user_id] = update.effective_message.id + 1
        last_items_list_message_id[user_id] = update.effective_message.id + 1
        with open(path_users_info_file, 'w+') as users_info_file:
            res = ''
            for cur_user_id, last_items_list_id in last_items_list_message_id.items():
                res = res + f'{cur_user_id}|{last_message_id_bot[cur_user_id]}|{last_items_list_id}|{is_item_being_added[cur_user_id]},\n'
            users_info_file.write(res)
    elif is_item_being_added[user_id]:
        await add_item_and_edit_and_delete_message(update, context)
    elif update.message.text.__contains__("add_user") and update.effective_user.id == user_ids[0]:
        new_user_id = int(update.message.text.split(' ')[1])
        user_ids.append(new_user_id)
        last_items_list_message_id[new_user_id] = 0
        last_message_id_bot[new_user_id] = 0
        is_item_being_added[new_user_id] = False
        selected_users_filter.add_user_ids(new_user_id)
        with open(path_users_info_file, 'a') as users_info_file:
            res = f'{new_user_id}|{last_message_id_bot[new_user_id]}|{last_items_list_message_id[new_user_id]}|{is_item_being_added[new_user_id]},\n'
            users_info_file.write(res)


async def add_item_and_edit_and_delete_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_item_being_added
    eff_message = update.effective_message
    cur_date = update.effective_message.date
    new_item = Item(eff_message.text,
                    dt(
                        int(cur_date.year), int(cur_date.month), int(cur_date.day),
                        int(cur_date.hour), int(cur_date.minute), int(cur_date.second)),
                    eff_message.from_user.username or
                    eff_message.from_user.first_name + ' ' + eff_message.from_user.last_name)

    items_list.append(new_item)
    add_item_to_file(new_item)

    is_item_being_added[update.effective_user.id] = False

    for chat in user_ids:
        if last_message_id_bot[chat] == 0 or not last_message_id_bot[chat]:
            continue
        await context.bot.edit_message_text(chat_id=chat,
                                            message_id=last_message_id_bot[chat],
                                            text=message_items_list(),
                                            reply_markup=generate_inline_keyboard_markup(),
                                            parse_mode=parse_mode_global)
    await context.bot.delete_messages(chat_id=update.effective_chat.id,
                                      message_ids=[update.effective_message.id])


async def callback_query_clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global last_items_list_message_id, last_message_id_bot, is_item_being_added, user_ids

    query = update.callback_query.data
    await update.callback_query.answer()
    cur_user_id = update.effective_user.id
    if query == ":clear:":
        clear_items(update)
        for chat in user_ids:
            if last_message_id_bot[chat] == 0 or not last_message_id_bot[chat]:
                continue
            await context.bot.edit_message_text(chat_id=chat,
                                                text=message_items_list(),
                                                message_id=last_items_list_message_id[chat],
                                                reply_markup=generate_inline_keyboard_markup(),
                                                parse_mode=parse_mode_global)
    elif query == ":new_item:":
        await context.bot.edit_message_text(chat_id=update.effective_chat.id,
                                            message_id=update.effective_message.message_id,
                                            text="What would you like to be purchased?",
                                            parse_mode=parse_mode_global)
        is_item_being_added[cur_user_id] = True
    elif query.isdigit():
        item_id_to_be_changed = int(query)
        items_list[item_id_to_be_changed - 1].name = items_list[item_id_to_be_changed - 1].name + f' {emojis["done"]}'

        for chat in user_ids:
            if last_message_id_bot[chat] == 0 or not last_message_id_bot[chat]:
                continue
            await context.bot.edit_message_text(chat_id=chat,
                                                message_id=last_items_list_message_id[chat],
                                                text=message_items_list(),
                                                reply_markup=generate_inline_keyboard_markup(),
                                                parse_mode=parse_mode_global)


def generate_inline_keyboard_markup():
    inline_buttons = [
        [InlineKeyboardButton(text="Add a new item", callback_data=":new_item:")],
        [InlineKeyboardButton(text=f"{emojis['x']} Clear items {emojis['x']}", callback_data=":clear:")]
    ]

    if items_list:
        for i in range(len(items_list)):
            if (i + 1) % 5 == 1:
                if len(inline_buttons[-1]) != 0:
                    inline_buttons.insert(-1, [])
            inline_buttons[-2].append(InlineKeyboardButton(text=str(i + 1), callback_data=f"{str(i + 1)}"))
        # inline_buttons.insert(-1, [InlineKeyboardButton(text=emojis['left_arrow'], callback_data=":left_arrow:"),
        #                            InlineKeyboardButton(text=emojis['x'], callback_data=":x:"),
        #                            InlineKeyboardButton(text=emojis['right_arrow'], callback_data=":right_arrow:")])
    return InlineKeyboardMarkup(inline_buttons)


def clear_items(update: Update):
    eff_message = update.effective_message
    cur_date = eff_message.date
    for item in items_list:
        date_format = "%Y-%m-%d %H:%M:%S"
        added_at = dt.strptime(str(item.added_at), date_format)
        deleted_item = DeletedItem(
            added_at=dt(
                int(added_at.year), int(added_at.month), int(added_at.day),
                int(added_at.hour), int(added_at.minute), int(added_at.second)),
            added_by=item.added_by,
            deleted_date=dt(
                int(cur_date.year), int(cur_date.month), int(cur_date.day),
                int(cur_date.hour), int(cur_date.minute), int(cur_date.second)),
            deleted_by=update.callback_query.from_user.username or
                       update.callback_query.from_user.first_name + ' ' +
                       update.callback_query.from_user.last_name,
            was_done=str(item.name).__contains__(emojis['done']),
            name=str(item.name)[:-1] if str(item.name).__contains__(
                emojis['done']) else str(item.name)
        )

        deleted_items_list.append(deleted_item)

    key_value_items_list_dict = {"deleted_items": deleted_items_list}

    with open(path_deleted_items_json_file, "r+") as outfile:
        try:
            items_json_file_key_value = json.load(outfile, parse_int=int, object_hook=_dict_to_object)
            print(f'items_json_file_key_value: {items_json_file_key_value}')
            if items_json_file_key_value['deleted_items']:
                key_value_items_list = items_json_file_key_value['deleted_items']
                key_value_items_list.extend(deleted_items_list)
                key_value_items_list_dict = {"deleted_items": key_value_items_list}
            with open(path_deleted_items_json_file, "w") as infile:
                json.dump(key_value_items_list_dict, cls=DeletedItemEncoder, indent=4, default=obj_dict, fp=infile)
        except JSONDecodeError as e:
            with open(path_deleted_items_json_file, "w") as infile:
                json.dump(key_value_items_list_dict, cls=DeletedItemEncoder, indent=4, default=obj_dict, fp=infile)

    items_list.clear()
    refresh_and_upload_items_list_to_items_txt()


def _dict_to_object(d):
    if isinstance(d, dict):
        if 'deleted_items' in d:
            for item in d['deleted_items']:
                item['added_at'] = dt(**item['added_at'])
                item['deleted_date'] = dt(**item['deleted_date'])
        return d


def obj_dict(obj):
    if isinstance(obj, dt):
        return dict(year=obj.year, month=obj.month, day=obj.day,
                    hour=obj.hour, minute=obj.minute, second=obj.second)
    else:
        return obj.__dict__


def message_items_list():
    message_list = message_joined_list() or "You don't have any items to purchase yet. "

    if items_list:
        message_list_more = " more "
    else:
        message_list_more = " "
    return message_list + f'\n\nWould you like to <b>add some{message_list_more}things</b> to the list to be purchased?'


def message_joined_list():
    return '\n'.join(str(i) + '. ' + j for i, j in enumerate(map(item_names, items_list), 1))


def item_names(item):
    return item.name


def load_from_items_file_to_items_list():
    global items_list
    with open(path_items_txt_file, 'r+') as items_file:
        try:
            items_list_lines = items_file.readlines()

            for item_line in items_list_lines:
                item = item_line[:-2].split('|')
                items_list.append(Item(name=item[0], added_by=item[1], added_at=item[2]))
        except IndexError:
            pass


def add_item_to_file(new_item: Item):
    with open(path_items_txt_file, 'a+') as items_txt:
        items_txt.write(f'{new_item.name}|{new_item.added_by}|{new_item.added_at},\n')


def refresh_and_upload_items_list_to_items_txt():
    global items_list
    if not items_list:
        open(path_items_txt_file, 'w').close()

    with open(path_items_txt_file, 'w') as items_file:
        res = ''
        for item in items_list:
            res = res + f'{item.name}|{item.added_by}|{item.added_at},\n'
        items_file.write(res)


def load_users_info_from_file_to_lists():
    global last_items_list_message_id, user_ids, is_item_being_added, last_message_id_bot, selected_users_filter
    if path_users_info_file.stat().st_size == 0:
        return

    user_ids = []

    with open(path_users_info_file, 'r+') as messages_info_file:
        try:
            lines = messages_info_file.readlines()
            for line in lines:
                info = line[:-2].split('|')
                cur_user_id = int(info[0])
                last_message_id = int(info[1])
                last_item_message_id = int(info[2])
                cur_is_item_being_added = info[3] == 'True'
                last_items_list_message_id[cur_user_id] = last_item_message_id
                last_message_id_bot[cur_user_id] = last_message_id
                is_item_being_added[cur_user_id] = cur_is_item_being_added
                user_ids.append(cur_user_id)
                if not user_ids.__contains__(cur_user_id):
                    selected_users_filter.add_user_ids(cur_user_id)
        except IndexError as e:
            print(f'Error: {e}')
            pass


if __name__ == '__main__':
    bot_token = os.environ['token']
    application = ApplicationBuilder().token(bot_token).build()

    load_users_info_from_file_to_lists()
    load_from_items_file_to_items_list()

    application.add_handler(CommandHandler('start', start, selected_users_filter))
    application.add_handler(CommandHandler('history', history, selected_users_filter))
    application.add_handler(
        MessageHandler((filters.TEXT & ~filters.COMMAND) & selected_users_filter, texts))
    application.add_handler(MessageHandler(filters.COMMAND & selected_users_filter, unknown))
    application.add_handler(CallbackQueryHandler(callback_query_clear))
    application.run_polling()
