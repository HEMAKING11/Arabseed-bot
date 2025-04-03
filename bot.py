import logging
import requests
import re
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from bs4 import BeautifulSoup
from urllib.parse import urlparse, unquote

# إعدادات البوت
API_TOKEN = "6936061100:AAG0TCEQ8vEw_D9-fuEjCP0pO-9-Rp1V8Z0"
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

logging.basicConfig(level=logging.INFO)

def extract_title_from_url(url):
    parsed_url = urlparse(url)
    path = unquote(parsed_url.path)
    path_parts = path.strip('/').split('-')
    title = ' '.join(path_parts).replace('.html', '').title()
    return title

def get_download_info(download_url, referer):
    try:
        session = requests.Session()
        session.headers.update({'Referer': referer})
        response = session.get(download_url)
        
        short_link_match = re.search(r'link\.href\s*=\s*["\'](.*?)["\']', response.text)
        if not short_link_match:
            return None
        
        short_link = short_link_match.group(1)
        response = session.get(short_link)
        final_link_match = re.search(r'<a\s+id="btn".*?href="(https?://[^"]+)"', response.text, re.DOTALL)
        if not final_link_match:
            return None
            
        final_link = final_link_match.group(1)
        response = session.get(final_link)
        soup = BeautifulSoup(response.text, 'html.parser')

        file_name = soup.select_one('.TitleCenteral h3 span').text.strip()
        file_size = soup.select_one('.TitleCenteral h3:nth-of-type(2) span').text.strip()
        file_link = soup.select_one('.downloadbtn')['href']
        
        return {'direct_link': file_link, 'file_name': file_name, 'file_size': file_size}
    except Exception:
        return None

@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    await message.reply("أرسل لي رابط التحميل من عرب سيد وسأوفر لك الروابط المباشرة! 🗂")

@dp.message_handler()
async def process_link(message: types.Message):
    arabseed_url = message.text.strip()
    if not arabseed_url.startswith('http'):
        await message.reply("❌ الرجاء إرسال رابط صحيح.")
        return

    media_title = extract_title_from_url(arabseed_url)
    session = requests.Session()

    # إرسال رسالة مبدئية
    status_msg = await message.reply("🔍 جاري البحث عن رابط التحميل...")

    try:
        response = session.get(arabseed_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        download_buttons = soup.find_all('a', class_='downloadBTn')
        
        if not download_buttons:
            await status_msg.edit_text("❌ لم يتم العثور على روابط تحميل!")
            return
        
        await status_msg.edit_text("⏳ جاري تحليل جودة الفيديوهات...")
        await asyncio.sleep(1.5)  

        quality_page_url = download_buttons[0]['href']
        response = session.get(quality_page_url, headers={'Referer': arabseed_url})
        soup = BeautifulSoup(response.text, 'html.parser')
        servers = soup.find_all('a', class_='downloadsLink HoverBefore ArabSeedServer')

        arabseed_servers = [s for s in servers if "عرب سيد مباشر" in s.text]
        if not arabseed_servers:
            await status_msg.edit_text("❌ لم يتم العثور على سيرفرات عرب سيد المباشرة!")
            return
        
        await status_msg.edit_text("✅ تم العثور على السيرفرات. جاري استخراج الروابط...")
        await asyncio.sleep(1.5)
        await bot.delete_message(message.chat.id, status_msg.message_id)

        # بدء متابعة استخراج الروابط
        status_text = "📁 جاري استخراج روابط التحميل...⏳\nـ━━━━━━━━━━━━━━━━━━━━━━"
        status_msg = await message.reply(status_text)

        keyboard = InlineKeyboardMarkup()
        referer = arabseed_url

        qualities_status = {}
        for server in arabseed_servers:
            quality = server.find('p').get_text().strip() if server.find('p') else "غير معروف"
            qualities_status[quality] = "🔎"

        for server in arabseed_servers:
            quality = server.find('p').get_text().strip() if server.find('p') else "غير معروف"

            # تحديث الحالة أثناء المعالجة
            qualities_status[quality] = "⏳"
            current_status = status_text + '\n' + '\n'.join([f"{v} الجودة {k}" for k, v in qualities_status.items()])
            await status_msg.edit_text(current_status)

            info = get_download_info(server['href'], referer)
            if info:
                button_text = f"{quality} - {info['file_size']}"
                keyboard.add(InlineKeyboardButton(text=button_text, url=info['direct_link']))
                qualities_status[quality] = "✅"
            else:
                qualities_status[quality] = "❌"

            # تحديث الحالة بعد المحاولة
            current_status = status_text + '\n' + '\n'.join([f"{v} الجودة {k}" for k, v in qualities_status.items()])
            await status_msg.edit_text(current_status)

        await asyncio.sleep(1.5)
        await bot.delete_message(message.chat.id, status_msg.message_id)

        if keyboard.inline_keyboard:
            await message.reply(f"⭕ تــحـــمــيـــل عـــــــرب ســـيـــــد مـبــــاشـــــر 🗂\nـ━━━━━━━━━━━━━━━━━━━━━━\n⌯ {media_title}\n\n🎬 اختر جودة التحميل:", reply_markup=keyboard)
        else:
            await message.reply("❌ لم يتم العثور على روابط تحميل مباشرة.")
    except Exception as e:
        await bot.delete_message(message.chat.id, status_msg.message_id)
        await message.reply(f"❌ حدث خطأ أثناء معالجة الرابط. حاول مرة أخرى لاحقًا.\n🛑 تفاصيل الخطأ: {str(e)}")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)