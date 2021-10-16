import html
import logging

import requests
from telegram import InlineQueryResultMpeg4Gif, InlineKeyboardButton, InlineKeyboardMarkup, \
    InputMediaAnimation
from telegram.ext import Updater, CommandHandler, InlineQueryHandler, ChosenInlineResultHandler

import settings
PREFERRED_QUALITY="mp4"
LOGGER = logging.getLogger("Tenor")
HELLO_TEXT = """
Hi, %(name)s!
I am %(me_username)s, a bot designed to search GIFs using Google's service called Tenor.
To use me, type in any chat: <code>%(me_username)s YOUR_QUERY_HERE</code>.
For example:
<code>%(me_username)s cat</code>
"""
PLEASE_WAIT = InlineKeyboardMarkup(
    [[InlineKeyboardButton(text="HQ loading...", url="https://www.youtube.com/watch?v=yLnd3AYEd2k")]])


# TENOR_KEY = requests.get("https://api.tenor.com/v1/anonid",
#                          params={"key": settings.TENOR_KEY}).json()["anon_id"]


def create_generic_response(text):
    def reply(update, context):
        userdata = {"name": html.escape(
            update.message.from_user.first_name), "username": update.message.from_user.username,
            "me_username": "@" + updater.bot.getMe().username}
        update.message.reply_text(text % userdata, parse_mode="HTML")

    return reply


def search(update, context):
    query = update.inline_query
    if query.query != "":
        req_args = {"q": query.query, "key": settings.TENOR_KEY, "limit": 50}
        if query.offset != "":
            req_args["pos"] = query.offset
        r = requests.get("https://api.tenor.com/v1/search", params=req_args)
    else:
        LOGGER.info("showing trending to %s", update.effective_user)
        req_args = {"key": settings.TENOR_KEY, "limit": 50}
        if query.offset != "":
            req_args["pos"] = query.offset
        r = requests.get("https://api.tenor.com/v1/trending", params=req_args)
    LOGGER.info(r.url)
    r = r.json()
    resp = []
    for gif in r["results"]:
        for mp4type in [PREFERRED_QUALITY, "mp4", "tinymp4", "nanomp4"]:
            media = gif["media"][0][mp4type]
            # LOGGER.debug("%s | %s", mp4type, media)
            if mp4type != PREFERRED_QUALITY:
                buttons = InlineKeyboardMarkup([[InlineKeyboardButton(url="https://www.youtube.com/watch?v=dQw4w9WgXcQ", text="Loading Hi-Res")]])
            else:
                buttons = None
            if "size" in media:
                if media["size"] < 1000000:
                    resp.append(InlineQueryResultMpeg4Gif(id=f'{mp4type}-{gif["id"]}',
                                                          mpeg4_url=media["url"],
                                                          thumb_url=media["preview"],
                                                          mpeg4_width=int(media["dims"][0]),
                                                          mpeg4_height=int(media["dims"][1]),
                                                          mpeg4_duration=int(media["duration"]),
                                                          reply_markup=buttons
                                                          ))
                    break
    LOGGER.info("Results length: %s, next_offset: %s", len(resp), r["next"])
    query.answer(results=resp, next_offset=r["next"], switch_pm_text=settings.PM_TEXT,
                 switch_pm_parameter=settings.PM_KEY, cache_time=0)


def update_gif(update, context):
    gif_info = update.chosen_inline_result.result_id.split("-")
    if not gif_info[0] == PREFERRED_QUALITY:
        LOGGER.debug("%s not %s - fixing that!", gif_info, PREFERRED_QUALITY)
        req_args = {"ids": gif_info[1], "key": settings.TENOR_KEY}
        r = requests.get("https://api.tenor.com/v1/gifs", params=req_args)
        buttons = None
        media = r.json()["results"][0]["media"][0][PREFERRED_QUALITY]
        context.bot.editMessageMedia(inline_message_id=update.chosen_inline_result.inline_message_id,
                             media=InputMediaAnimation(media=media["url"],
                                                       width=int(media["dims"][0]),
                                                       height=int(media["dims"][1]),
                                                       duration=int(media["duration"])),
                             reply_markup=buttons
                             )
    else:
        LOGGER.debug("%s is %s already", gif_info, PREFERRED_QUALITY)


def start(update, context):
    if settings.PM_KEY is not None:
        update.message.reply_text("Warning: this bot is moved to @tenorbot and @thetenorbot will be shut down soon!")
    if settings.PM_KEY is None or (settings.PM_KEY is not None and not update.message.text.endswith(settings.PM_KEY)):
        userdata = {"name": html.escape(
            update.message.from_user.first_name), "username": update.message.from_user.username,
            "me_username": "@" + updater.bot.getMe().username}
        update.message.reply_text(HELLO_TEXT % userdata, parse_mode="HTML")


updater = Updater(settings.TOKEN, **settings.UPDATER_KWARGS)

updater.dispatcher.add_handler(CommandHandler(
    'start', start))
updater.dispatcher.add_handler(InlineQueryHandler(search))
updater.dispatcher.add_handler(ChosenInlineResultHandler(update_gif))
if __name__ == '__main__':
    updater.start_polling(clean=True)
    LOGGER.info("Started polling - idling")
    updater.idle()
