import html
import logging

import aiohttp
from telegram import (
    InlineQueryResultMpeg4Gif,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaAnimation,
    Update,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    InlineQueryHandler,
    ChosenInlineResultHandler,
    ContextTypes,
)

import settings

PREFERRED_QUALITY = "mp4"
LOGGER = logging.getLogger("Tenor")
HELLO_TEXT = """
Hi, %(name)s!
I am %(me_username)s, a bot designed to search GIFs using Google's service called Tenor.
To use me, type in any chat: <code>%(me_username)s YOUR_QUERY_HERE</code>.
For example:
<code>%(me_username)s cat</code>
"""
PLEASE_WAIT = InlineKeyboardMarkup(
    [
        [
            InlineKeyboardButton(
                text="HQ loading...", url="https://www.youtube.com/watch?v=yLnd3AYEd2k"
            )
        ]
    ]
)


def create_generic_response(text):
    async def reply(update, context: ContextTypes.DEFAULT_TYPE):
        userdata = {
            "name": html.escape(update.message.from_user.first_name),
            "username": update.message.from_user.username,
            "me_username": "@" + (await context.bot.getMe()).username,
        }
        await update.message.reply_text(text % userdata, parse_mode="HTML")

    return reply


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query
    async with aiohttp.ClientSession() as session:
        req_args = {"key": settings.TENOR_KEY, "limit": 50}
        if query.query != "":
            if query.offset != "":
                req_args["pos"] = query.offset
            req_args["q"] = query.query
            r = await session.get(
                "https://tenor.googleapis.com/v2/search", params=req_args
            )
        else:
            LOGGER.info("showing trending to %s", update.effective_user)
            if query.offset != "":
                req_args["pos"] = query.offset
            r = await session.get(
                "https://tenor.googleapis.com/v2/featured", params=req_args
            )
        r = await r.json()
    resp = []
    for gif in r["results"]:
        for mp4type in [PREFERRED_QUALITY, "mp4", "tinymp4", "nanomp4"]:
            media = gif["media_formats"][mp4type]
            if mp4type != PREFERRED_QUALITY:
                buttons = InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                                text="Loading Hi-Res",
                            )
                        ]
                    ]
                )
            else:
                buttons = None
            if "size" in media:
                if media["size"] < 1000000:
                    resp.append(
                        InlineQueryResultMpeg4Gif(
                            id=f'{mp4type}-{gif["id"]}',
                            mpeg4_url=media["url"],
                            thumbnail_url=gif["media_formats"]["nanogifpreview"]["url"],
                            mpeg4_width=int(media["dims"][0]),
                            mpeg4_height=int(media["dims"][1]),
                            mpeg4_duration=int(media["duration"]),
                            reply_markup=buttons,
                        )
                    )
                    break
    LOGGER.info("Results length: %s, next_offset: %s", len(resp), r["next"])
    await query.answer(results=resp, next_offset=r["next"], cache_time=0)


async def update_gif(update, context):
    gif_info = update.chosen_inline_result.result_id.split("-")
    if not gif_info[0] == PREFERRED_QUALITY:
        LOGGER.debug("%s not %s - fixing that!", gif_info, PREFERRED_QUALITY)
        async with aiohttp.ClientSession() as session:
            req_args = {"ids": gif_info[1], "key": settings.TENOR_KEY}
            r = await session.get(
                "https://tenor.googleapis.com/v2/posts", params=req_args
            )
            media = (await r.json())["results"][0]["media_formats"][PREFERRED_QUALITY]
        buttons = None
        await context.bot.editMessageMedia(
            inline_message_id=update.chosen_inline_result.inline_message_id,
            media=InputMediaAnimation(
                media=media["url"],
                width=int(media["dims"][0]),
                height=int(media["dims"][1]),
                duration=int(media["duration"]),
            ),
            reply_markup=buttons,
        )
    else:
        LOGGER.debug("%s is %s already", gif_info, PREFERRED_QUALITY)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    userdata = {
        "name": html.escape(update.message.from_user.first_name),
        "username": update.message.from_user.username,
        "me_username": "@" + (await context.bot.getMe()).username,
    }
    await update.message.reply_text(HELLO_TEXT % userdata, parse_mode="HTML")


app = ApplicationBuilder().token(settings.TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(InlineQueryHandler(search))
app.add_handler(ChosenInlineResultHandler(update_gif))
if __name__ == "__main__":
    app.run_polling(drop_pending_updates=True)
