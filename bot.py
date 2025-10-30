import os
import tempfile
import requests
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from terabox_downloader import TeraboxDownloader

# --- CONFIG ---
API_ID = int(os.environ.get("API_ID", "123456"))
API_HASH = os.environ.get("API_HASH", "your_api_hash")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "1234:ABCD")

# 👇 Your channel username (for public) or ID (for private)
TARGET_CHANNEL = os.environ.get("TARGET_CHANNEL", "@myteraboxvideos")
# ----------------

app = Client("terabox_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)


def looks_like_terabox_link(text: str) -> bool:
    return "terabox" in text.lower()


@app.on_message(filters.private & filters.text & ~filters.command(["start", "help"]))
async def handle_link(client, message):
    link = message.text.strip()
    if not looks_like_terabox_link(link):
        await message.reply_text("Please send a valid TeraBox link.")
        return

    info_msg = await message.reply_text("🔍 Fetching file info...")

    try:
        tb = TeraboxDownloader()
        file_info = tb.get_file_info(link)

        name = file_info.get("name", "video.mp4")
        url = file_info.get("download_url")

        if not url:
            await info_msg.edit("❌ Couldn't resolve download link.")
            return

        await info_msg.edit(f"⬇️ Downloading **{name}**...")

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, name)
            with requests.get(url, stream=True, timeout=60) as r:
                r.raise_for_status()
                with open(path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            f.write(chunk)

            await info_msg.edit("📤 Uploading to channel...")

            # --- Upload video to your channel ---
            sent = await client.send_video(
                chat_id=TARGET_CHANNEL,
                video=path,
                caption=f"🎬 **{name}**\nUploaded via TeraBox Downloader Bot",
            )

            # --- Build the Telegram post link ---
            # For public channels (e.g. @mychannel)
            if isinstance(TARGET_CHANNEL, str) and TARGET_CHANNEL.startswith("@"):
                channel_username = TARGET_CHANNEL.lstrip("@")
                post_link = f"https://t.me/{channel_username}/{sent.id}"
            else:
                # Private channels use numeric IDs
                # You can get channel_id like -100xxxxxxxxxx
                channel_id = str(sent.chat.id).replace("-100", "")
                post_link = f"https://t.me/c/{channel_id}/{sent.id}"

            # --- Send button to user with post link ---
            button = InlineKeyboardMarkup(
                [[InlineKeyboardButton("📺 Watch in Channel", url=post_link)]]
            )

            await info_msg.edit("✅ Uploaded successfully!")
            await message.reply_text(
                f"✅ Your video has been uploaded to the channel!\n\n🎞️ {name}",
                reply_markup=button,
            )

    except Exception as e:
        await info_msg.edit(f"⚠️ Error: {e}")


@app.on_message(filters.command("start"))
async def start(_, message):
    await message.reply_text(
        "👋 Send me a TeraBox link and I’ll upload the video to the channel.\n"
        "After upload, you’ll get a button to open the post directly."
    )


app.run()

