import os
import requests
import logging
import threading
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, CallbackContext

# Load environment variables
BOT_TOKEN = os.environ.get("BOT_TOKEN")
TERABOX_API_KEY = os.environ.get("TERABOX_API_KEY")

# Configure logging
logging.basicConfig(
    filename="bot.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    encoding="utf-8"
)

# Initialize Telegram Bot
bot = Bot(token=BOT_TOKEN)

# Function to get Direct Download Link (DDL)
def get_ddl(terabox_url):
    response = requests.get(f"https://terabox-api.example.com/get_link?url={terabox_url}&api_key={TERABOX_API_KEY}")
    data = response.json()
    if "download_link" in data:
        return data["download_link"], data["estimated_size"]
    return None, None

# Function to download video
def download_video(video_url, save_path, chat_id):
    response = requests.get(video_url, stream=True)
    total_size = int(response.headers.get("content-length", 0))
    downloaded_size = 0
    file_path = os.path.join(save_path, "video.mp4")

    with open(file_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=1024 * 1024):
            if chunk:
                f.write(chunk)
                downloaded_size += len(chunk)
                percent_complete = (downloaded_size / total_size) * 100
                bot.send_message(chat_id, f"Download Progress: {percent_complete:.2f}%")
    
    return file_path, total_size / (1024 * 1024)  # Return file size in MB

# Function to handle video processing
async def process_video(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    video_url = update.message.text.split(" ")[1]  # Extract URL from command
    await update.message.reply_text("Fetching Direct Download Link...")

    ddl, estimated_size = get_ddl(video_url)
    if not ddl:
        await update.message.reply_text("Failed to fetch DDL.")
        return
    
    await update.message.reply_text(f"Download Link: {ddl}\nEstimated Size: {estimated_size} MB")
    
    save_path = "downloads"
    os.makedirs(save_path, exist_ok=True)
    
    await update.message.reply_text("Starting video download...")
    file_path, file_size_mb = download_video(ddl, save_path, chat_id)
    
    if file_size_mb > 98:
        await update.message.reply_text(f"Video size exceeds limit ({file_size_mb:.2f} MB). Please download manually from the DDL above.")
        return
    
    if 50 <= file_size_mb <= 98:
        await update.message.reply_text("Splitting the video into two parts...")
        os.system(f"ffmpeg -i {file_path} -fs 48M part1.mp4 -fs 48M part2.mp4")
        await update.message.reply_video(video=open("part1.mp4", "rb"), caption="Part 1")
        await update.message.reply_video(video=open("part2.mp4", "rb"), caption="Part 2")
    else:
        await update.message.reply_video(video=open(file_path, "rb"), caption="Here is your video!")

# Main function to start the bot
def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("getvideo", process_video))
    application.run_polling()

if __name__ == "__main__":
    main()
