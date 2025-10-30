import os
import tempfile
import requests
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from terabox_downloader import TeraboxDownloader   # ensure this package is installed and import path is correct

# --- CONFIG ---
API_ID = int(os.environ.get("API_ID", "123456"))
API_HASH = os.environ.get("API_HASH", "your_api_hash")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "1234:ABCD")
TARGET_CHANNEL = os.environ.get("TARGET_CHANNEL", "@yourchannelusername")
# ----------------

app = Client("terabox_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def looks_like_supported_link(text: str) -> bool:
    text = text.lower().strip()
    return ("terabox" in text) or ("terafileshare.com" in text)

def resolve_fileshare_link(link: str) -> dict:
    """
    Resolve a TeraFileShare link and return a dict with:
       { "name": ..., "size": ..., "download_url": ... }
    Note: This is a generic example — you may need to update it if the site structure changes.
    """
    # Send request
    r = requests.get(link, allow_redirects=True, timeout=30)
    r.raise_for_status()
    html = r.text

    # Example parsing logic (update as needed):
    # -- extract a direct download URL somewhere in html
    # Here: look for a link like: <a href="https://downloads.terafileshare.com/…">Download</a>
    import re
    m = re.search(r'href="(https://downloads\.terafileshare\.com/[^"]+)"', html)
    if not m:
        raise Exception("Could not locate download URL for TeraFileShare link.")
    download_url = m.group(1)

    # Extract filename
    m2 = re.search(r'File Name:\s*<b>([^<]+)</b>', html)
    if m2:
        name = m2.group(1).strip()
    else:
        name = os.path.basename(download_url.split("?")[0])

    # Extract size
    m3 = re.search(r'File Size:\s*<b>([^<]+)</b>', html)
    size = m3.group(1).strip() if m3 else None

    return {
        "name": name,
        "size": size,
        "download_url": download_url
    }

@app.on_message(filters.private & filters.text & ~filters.command(["start", "help"]))
async def handle_link(client, message):
    link = message.text.strip()
    if not looks_like_supported_link(link):
        await message.reply_text("❌ Please send a valid TeraBox or TeraFileShare link.")
        return

    info_msg = await message.reply_text("🔍 Resolving link...")

    try:
        if "terabox" in link.lower():
            tb = TeraboxDownloader()
            file_info = tb.get_file_info(link)
        else:
            file_info = resolve_fileshare_link(link)

        name = file_info.get("name", "file.mp4")
        url = file_info.get("download_url")
        if not url:
            await info_msg.edit("❌ Couldn't resolve download URL.")
            return

        await info_msg.edit(f"⬇️ Downloading **{name}**…", parse_mode="markdown")

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, name)
            with requests.get(url, stream=True, timeout=60) as r2:
                r2.raise_for_status()
                with open(path, "wb") as f:
                    for chunk in r2.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            f.write(chunk)

            await info_msg.edit("📤 Uploading to channel…")

            sent = await client.send_video(
                chat_id=TARGET_CHANNEL,
                video=path,
                caption=f"🎬 **{name}**\nUploaded via TeraBox/TeraFileShare Bot",
                # You can add a reply_markup here if you want a button on the channel post itself
            )

            # build post link
            if isinstance(TARGET_CHANNEL, str) and TARGET_CHANNEL.startswith("@"):
                channel_username = TARGET_CHANNEL.lstrip("@")
                post_link = f"https://t.me/{channel_username}/{sent.id}"
            else:
                channel_id_str = str(sent.chat.id).replace("-100", "")
                post_link = f"https://t.me/c/{channel_id_str}/{sent.id}"

            # send to user with button
            button = InlineKeyboardMarkup(
                [[InlineKeyboardButton("📺 View in Channel", url=post_link)]]
            )
            await info_msg.edit("✅ Uploaded successfully!")
            await message.reply_text(
                f"✅ Your video **{name}** has been uploaded to the channel.",
                reply_markup=button,
                parse_mode="markdown"
            )

    except Exception as e:
        await info_msg.edit(f"⚠️ Error: {e}")

@app.on_message(filters.command("start"))
async def start(_, message):
    await message.reply_text(
        "👋 Hello! Send me a TeraBox or TeraFileShare link and I’ll upload the video to the channel and give you a link."
    )

if __name__ == "__main__":
    app.run()


app.run()

