import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
from PIL import Image, ImageDraw, ImageFont
import io
import datetime as dt
import aiohttp
import json
from dotenv import load_dotenv
import os
import pytz
import random
import string
import pandas as pd
from openpyxl import load_workbook
from io import BytesIO
import sqlite3
from PIL import Image, ImageDraw, ImageFont
import io
import base64
import requests
import sys
from io import StringIO


class WebhookIO(StringIO):
    def __init__(self, original_stream, webhook_url, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_stream = original_stream
        self.webhook_url = webhook_url
        self.buffer = ""
        self.in_code_block = False

    def write(self, s):
        # Перенаправляем в оригинальный поток
        self.original_stream.write(s)

        # Добавляем в буфер
        self.buffer += s

        # Проверяем начало/конец блока кода
        if '```' in s:
            self.in_code_block = not self.in_code_block

        # Если есть перевод строки и не внутри блока кода, отправляем сообщение
        if '\n' in self.buffer and not self.in_code_block:
            self.flush()

    def flush(self):
        if self.buffer.strip():
            # Форматируем сообщение
            message = self.buffer.strip()

            # Если сообщение не начинается с ```, добавляем их
            if not message.startswith('```'):
                message = f"```\n{message}\n```"

            # Разбиваем длинные сообщения на части
            max_length = 1990  # Оставляем место для ```
            if len(message) > max_length:
                parts = []
                current_part = ""
                for line in message.split('\n'):
                    if len(current_part) + len(line) + 1 > max_length:
                        parts.append(current_part)
                        current_part = line
                    else:
                        current_part += '\n' + line if current_part else line
                if current_part:
                    parts.append(current_part)

                # Отправляем части по очереди
                for part in parts:
                    self._send_message(part)
            else:
                self._send_message(message)

        # Очищаем буфер
        self.buffer = ""
        super().flush()

    def _send_message(self, message):
        # Убедимся, что код блоки правильно закрыты
        if message.count('```') % 2 != 0:
            message += '\n```'

        data = {
            'content': message,
            'avatar_url': "#",
            'username': "UWU Manager"
        }
        try:
            response = requests.post(self.webhook_url, json=data)
            if response.status_code != 204:
                self.original_stream.write(f"Webhook error: {response.text}\n")
        except Exception as e:
            self.original_stream.write(f"Webhook send error: {e}\n")


def setup_webhook_logging(webhook_url):
    # Перенаправляем stdout и stderr
    sys.stdout = WebhookIO(sys.stdout, webhook_url)
    sys.stderr = WebhookIO(sys.stderr, webhook_url)


# Пример использования
WEBHOOK_URL = "#"
setup_webhook_logging(WEBHOOK_URL)

# Bot setup
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
REMOTE_DB_URL = "#"


def cmd_logging(cmd, interaction, args):
    url = "#"
    user = interaction.user.mention
    if user == "<@926763178925379604>":
        user = "_deepslate"
    data = {
        "content": f"{user} used `{cmd}` in {interaction.channel.mention}\n{'   '.join(list(map(str, args)))}"
    }
    try:
        response = requests.post(url, json=data)
        if response.status_code != 204:
            print("Error:", response.text)
    except Exception as e:
        print("Error:", e)


# Role checks
def is_founder(interaction: discord.Interaction):
    return "Founders" in [role.name for role in interaction.user.roles]


def is_member(interaction: discord.Interaction):
    return "Member" in [role.name for role in interaction.user.roles]


def generate_booking_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


def norm_flight_number(fn):
    fn = fn.replace(' ', '').replace("-", "").upper()
    return f"{fn[:2]} {fn[2:]}"


def printy(s):
    print(s)


def check_datetime(datetime_str):
    try:
        date, time = datetime_str.split(' ')
        year, month, day = date.split('-')
        hour, minute = time.split(':')
        print(date, time, year, month, day, hour, minute)
        if str(year) >= "2025" and int(month) in range(-1, 13) and int(day) in range(-1, 32) and int(hour) in range(-1, 24) and int(minute) in range(-1, 60):
            return True
        else:
            return False
    except Exception as e:
        print(e)
        return False


async def generate_boarding_pass(flight_number: str, booking_id: str, roblox_nickname: str,
                                 roblox_displayname: str, flight_class: str, seat: str):
    flight_number = norm_flight_number(flight_number)
    try:
        flight = ""
        try:
            reqst = requests.get(REMOTE_DB_URL + f"/sql/boardpass/{flight_number.replace(' ', '')}")
            if reqst.status_code == 200:
                printy(reqst.json())
                flight = reqst.json()
            else:
                printy(reqst.text)
        except Exception as e:
            printy(f"{e}")
        if flight == "None":
            return flight

        departure, arrival, datetime_str = flight
        date_part, time_part = datetime_str.split(' ')
        departure_city, dep_iata = ' '.join(departure.split(' ')[:-1]), departure.split(' ')[-1]
        arrival_city, arr_iata = ' '.join(arrival.split(' ')[:-1]), arrival.split(' ')[-1]

        # Создаем изображение
        try:
            # Основной фон
            input_image_path = "background.png"
            overlay_image_path = f"assets/{flight_number[:2]}_534_300.png"  # Путь к изображению для наложения
            text_color_light = (255, 185, 228)
            text_color = (0, 32, 96)

            # Открываем основное изображение
            image = Image.open(input_image_path).convert("RGBA")

            # Открываем изображение для наложения (если существует)
            try:
                overlay = Image.open(overlay_image_path).convert("RGBA")
                image.paste(overlay, (1300, 45), overlay)
            except FileNotFoundError:
                printy("Оверлейное изображение не найдено, продолжаем без него")

            draw = ImageDraw.Draw(image)

            # Загружаем шрифты
            try:
                font = ImageFont.truetype("RobotoMono-Bold.ttf", 128)
                font_big = ImageFont.truetype("RobotoMono-Bold.ttf", 200)
                font_small = ImageFont.truetype("RobotoMono-Light.ttf", 48)
                font_med = ImageFont.truetype("RobotoMono-Light.ttf", 81)
            except:
                font = ImageFont.load_default(size=128)
                font_big = ImageFont.load_default(size=200)
                font_small = ImageFont.load_default(size=48)
                font_med = ImageFont.load_default(size=81)

            # Добавляем текст на изображение
            draw.text((45, 100), f"{dep_iata} > {arr_iata}", fill=text_color_light, font=font_big)
            draw.text((45, 330), f"{departure_city} > {arrival_city}", fill=text_color_light, font=font_small)
            draw.text((45, 550), roblox_nickname.upper()[:18], fill=text_color, font=font)
            draw.text((1250, 550), booking_id.upper(), fill=text_color, font=font)
            draw.text((45, 878), time_part, fill=text_color, font=font)
            draw.text((830, 878), seat.upper()[:9], fill=text_color, font=font)
            draw.text((1250, 878), flight_class.upper()[:9], fill=text_color, font=font)

            flnum_text = Image.new('RGBA', font_med.getbbox(f"{flight_number} {date_part}")[2:], (255, 255, 255, 0))
            flnum_draw = ImageDraw.Draw(flnum_text)
            flnum_draw.text((0, 0), f"{flight_number} {date_part}", fill=text_color_light, font=font_med)
            rotated_flnum = flnum_text.rotate(-90, expand=True)

            # Накладываем повернутый текст на изображение
            image.paste(rotated_flnum, (2000, 100), rotated_flnum)

            # Сохраняем в буфер
            img_buffer = io.BytesIO()
            image.save(img_buffer, format='PNG')
            img_buffer.seek(0)

            # Конвертируем в base64
            img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
            return img_base64

        except FileNotFoundError:
            printy("Ошибка: файл 'background.png' не найден!")
            return None
        except Exception as e:
            printy(f"Ошибка при генерации посадочного: {e}")
            return None

    except Exception as e:
        printy(f"Ошибка в generate_boarding_pass: {e}")
        return None


# Booking commands
@bot.tree.command(name="book", description="Book a flight")
@app_commands.describe(
    flight_number="Flight number",
    roblox_nickname="Your Roblox nickname",
    roblox_displayname="Your Roblox display name",
    flight_class="Requested class (Economy/Business/First)"
)
async def book(interaction: discord.Interaction,
               flight_number: str,
               roblox_nickname: str,
               roblox_displayname: str,
               flight_class: str):
    try:
        cmd_logging("/book", interaction, [flight_number, roblox_nickname, roblox_displayname, flight_class])
    except Exception as e:
        print(e)
        
    await interaction.response.defer(ephemeral=True)

    flight_number = norm_flight_number(flight_number)
    flight = ""
    try:
        reqst = requests.get(REMOTE_DB_URL + f"/sql/book/s1/{flight_number.replace(' ', '')}")
        if reqst.status_code == 200:
            printy(reqst.json())
            flight = reqst.json()
            if reqst.status_code != 200:
                await interaction.followup.send("Flight not found!", ephemeral=True)
                return
        else:
            printy(reqst.text)
    except Exception as e:
        printy(f"{e}")

    try:
        data = {
            'flight_number': flight_number.replace(' ', ''),
            'roblox_nickname': roblox_nickname,
            'roblox_displayname': roblox_displayname,
            'flight_class': flight_class,
            'discord_user_id': interaction.user.id
        }
        response = requests.post(f"{REMOTE_DB_URL}/sql/book/s2/", json=data)
        if response.status_code == 200:
            booking_id = response.text
        else:
            await interaction.followup.send("Error occured. Please try again.", ephemeral=True)
            return

        await interaction.followup.send(
            f"""Booking created successfully! Your booking ID:
`{booking_id.replace('"', '')}`
Don't forget to save booking ID somewhere to use it in airlines' services""",
            ephemeral=True)

        await interaction.user.send(f"""Booking created - `{booking_id.replace('"', '')}` for {flight_number}""")
    except Exception as e:
        printy(e)
        await interaction.followup.send("Error occured. Please try again.", ephemeral=True)


@bot.tree.command(name="boardpass", description="Generate boarding pass (Member only)")
@app_commands.describe(
    booking_id="Booking ID",
    flight_class="Assigned class",
    seat="Seat number"
)
async def boardpass(interaction: discord.Interaction,
                    booking_id: str,
                    flight_class: str,
                    seat: str):
    try:
        cmd_logging("/boardpass", interaction, [booking_id, flight_class, seat])
    except Exception as e:
        print(e)

    await interaction.response.defer(ephemeral=True)

    if not is_member(interaction):
        await interaction.followup.send("You don't have permission to use this command.", ephemeral=True)
        return

    booking = ""

    await interaction.response.defer(ephemeral=True)

    if not is_member(interaction):
        await interaction.followup.send("You don't have permission to use this command.", ephemeral=True)
        return

    booking = ""
    try:
        reqst = requests.get(REMOTE_DB_URL + f"/sql/boardpass/s1/{booking_id}")
        if reqst.status_code == 200:
            printy(reqst.json())
            booking = reqst.json()
        else:
            printy(reqst.text)
    except Exception as e:
        printy(f"{e}")

    flight_number, roblox_nickname, roblox_displayname, discord_user_id = booking

    data = {
        'flight_class': flight_class,
        'seat': seat,
        'booking_id': booking_id
    }
    response = requests.post(f"{REMOTE_DB_URL}/sql/boardpass/s2/", json=data)
    if response.status_code == 200:
        printy(response.json())
    else:
        await interaction.followup.send("Error occured. Please try again.", ephemeral=True)

    # Получаем посадочный в base64
    img_base64 = await generate_boarding_pass(
        flight_number, booking_id, roblox_nickname,
        roblox_displayname, flight_class, seat
    )

    if not img_base64:
        await interaction.followup.send("Error generating boarding pass.", ephemeral=True)
        return

    # Отправляем посадочный
    try:
        # Декодируем base64 в bytes
        img_data = base64.b64decode(img_base64)
        img_buffer = io.BytesIO(img_data)

        # Создаем файл для Discord
        file = discord.File(img_buffer, filename="boarding_pass.png")

        # Отправляем в канал
        await interaction.followup.send(
            f"Boarding pass generated for booking `{booking_id}`:",
            file=file
        )

        # Отправляем пользователю в ЛС
        try:
            user = await bot.fetch_user(int(discord_user_id))
            img_buffer.seek(0)  # Сбрасываем позицию буфера
            await user.send(
                f"Here's your boarding pass for flight {flight_number}:",
                file=discord.File(img_buffer, filename="boarding_pass.png")
            )
        except Exception as e:
            await interaction.followup.send(f"Could not send boarding pass to user {discord_user_id}: {e}")
            printy(f"Could not send boarding pass to user {discord_user_id}: {e}")

    except Exception as e:
        printy(f"Error processing boarding pass: {e}")
        await interaction.followup.send("Error processing boarding pass image.", ephemeral=True)


@bot.tree.command(name="delbook", description="Delete a booking (Member only)")
@app_commands.describe(
    booking_id="Booking ID to delete"
)
async def delbook(interaction: discord.Interaction, booking_id: str):
    try:
        cmd_logging("/delbook", interaction, [booking_id])
    except Exception as e:
        print(e)

    await interaction.response.defer(ephemeral=True)
    if not is_member(interaction):
        await interaction.followup.send("You don't have permission to use this command.", ephemeral=True)
        return

    try:
        reqst = requests.get(REMOTE_DB_URL + f"/sql/delbook/{booking_id}")
        if reqst.status_code == 200:
            printy(reqst.json())
            await interaction.followup.send(f"`{booking_id}` deleted successfully")
        else:
            printy(reqst.text)
            await interaction.followup.send("Something went wrong :(")
    except Exception as e:
        await interaction.followup.send("Something went wrong :(")
        printy(f"{e}")


@bot.tree.command(name="booklistadmin", description="List all bookings (Founders only)")
async def booklistadmin(interaction: discord.Interaction):
    try:
        cmd_logging("/booklistadmin", interaction, [])
    except Exception as e:
        print(e)

    if not is_founder(interaction):
        await interaction.followup.send("You don't have permission to use this command.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)

    response = ""
    try:
        reqst = requests.get(REMOTE_DB_URL + f"/sql/booklistadmin/")
        if reqst.status_code == 200:
            printy(reqst.json())
            response = reqst.json()
        elif reqst.status_code == 400:
            await interaction.followup.send("No bookings found", ephemeral=True)
            return
        else:
            printy(reqst.text)
    except Exception as e:
        printy(f"{e}")

    if len(response) > 2000:
        parts = [response[i:i + 2000] for i in range(0, len(response), 2000)]
        await interaction.followup.send(parts[0], ephemeral=True)
        for part in parts[1:]:
            await interaction.followup.send(part, ephemeral=True)
    else:
        await interaction.followup.send(response, ephemeral=True)


@bot.tree.command(name="bookings", description="List bookings for a flight (Member only)")
@app_commands.describe(
    flight_number="Flight number"
)
async def bookings(interaction: discord.Interaction, flight_number: str):
    try:
        cmd_logging("/bookings", interaction, [flight_number])
    except Exception as e:
        print(e)

    await interaction.response.defer(ephemeral=True)
    if not is_member(interaction):
        await interaction.followup.send("You don't have permission to use this command.", ephemeral=True)
        return

    flight_number = norm_flight_number(flight_number)

    bookings = ""
    try:
        reqst = requests.get(REMOTE_DB_URL + f"/bookings/{flight_number.replace(' ', '')}")
        if reqst.status_code == 200:
            printy(reqst.json())
            bookings = reqst.json()
        elif reqst.status_code == 400:
            await interaction.followup.send("No bookings found", ephemeral=True)
            return
        else:
            printy(reqst.text)
    except Exception as e:
        printy(f"{e}")

    response = f""
    for booking_id, booking_data in bookings.items():
        response += (
            f"{booking_id}; {booking_data['roblox_displayname']}; "
            f"(@{booking_data['roblox_nickname']}); "
            f"{booking_data['class']}; {booking_data['seat']}\n"
        )

    # Split into multiple messages if too long
    if len(response) > 1900:
        parts = [response[i:i + 1900] for i in range(0, len(response), 2000)]
        await interaction.followup.send(parts[0], ephemeral=True)
        for part in parts[1:]:
            await interaction.followup.send(f"```{part}```", ephemeral=True)
    else:
        await interaction.followup.send(f"```{response}```", ephemeral=True)


async def create_flight_event(guild: discord.Guild, flight_number: str, departure: str, arrival: str, datetime_str: str):
    try:
        date, timey = datetime_str.split(' ')

        year, month, day = map(int, date.split('-'))
        hour, minute = map(int, timey.split(':'))

        # Создаем осведомленный объект datetime с использованием UTC
        start_time = dt.datetime(year, month, day, hour, minute, tzinfo=dt.timezone.utc)
        end_time = start_time + dt.timedelta(hours=1)

        # Создаем событие
        event = await bot.get_guild(1335994271815307325).create_scheduled_event(
            name=f"{flight_number} {departure.split(' ')[-1]} → {arrival.split(' ')[-1]}",
            description=f"{departure} → {arrival}",
            start_time=start_time,
            end_time=end_time,
            entity_type=discord.EntityType.external,
            location=f"Flight {flight_number}",
            privacy_level=discord.PrivacyLevel.guild_only
        )

        return event.id
    except Exception as e:
        printy(f"Error creating event: {e}")
        return None


@bot.tree.command(name="newflight", description="Add a new flight (Member only)")
@app_commands.describe(
    flight_number="Flight number",
    departure="Departure city",
    arrival="Arrival city",
    datentime="Date and Time (YYYY-MM-DD HH:MM)",
    status="Flight status"
)
async def newflight(interaction: discord.Interaction,
                    flight_number: str,
                    departure: str,
                    arrival: str,
                    datentime: str,
                    status: str,
                    silent: bool = False):
    try:
        cmd_logging("/newflight", interaction, [flight_number, departure, arrival, datentime, status])
    except Exception as e:
        print(e)
        
    await interaction.response.defer(ephemeral=True)
    if not is_member(interaction):
        await interaction.followup.send("You don't have permission to use this command.", ephemeral=True)
        return

    try:
        if check_datetime(datentime):
            flight_number = norm_flight_number(flight_number)

            printy(f"datetime_str: {datentime}")
            # Create the event
            event_id = await create_flight_event(interaction.client.get_guild(1335994271815307325), flight_number, departure, arrival, datentime)

            try:
                data = {
                    'flight_number': flight_number,
                    'departure': departure,
                    'arrival': arrival,
                    'datentime': datentime,
                    'status': status,
                    'event_id': event_id,
                }
                headers = {'Content-Type': 'application/json'}
                response = requests.post((REMOTE_DB_URL + '/sql/newflight/'), json=data, headers=headers)

            except Exception as e:
                printy(f"{e}")
                await interaction.followup.send('Something went wrong :(', ephemeral=True)
                return

            NOTIFICATION_CHANNEL_ID = 1368408244501872780

            user_id = interaction.user.id
            current_time = time.time()

            if user_id in user_cooldowns and not silent:
                last_used = user_cooldowns[user_id]
                cooldown_remaining = (last_used + 600) - current_time

                if cooldown_remaining > 0:
                    cooldown_time = str(timedelta(seconds=int(cooldown_remaining)))
                    await interaction.followup.send(
                        f"You can use this command again in {cooldown_time}",
                        ephemeral=True
                    )
                    return

            try:
                # Получаем канал для уведомлений
                channel = bot.get_channel(NOTIFICATION_CHANNEL_ID)
                if not channel:
                    await interaction.followup.send("Channel not found :(", ephemeral=True)
                    return

                embed = discord.Embed(
                    title=f"",
                    description=f"# New flight - {flight_number}",
                    color=discord.Color.pink()
                )

                if not silent:
                    pingg = "<@&1338042789996269570>"
                else:
                    pingg = "."

                await channel.send(pingg, embed=embed)
                user_cooldowns[user_id] = current_time

            except Exception as e:
                await interaction.followup.send(
                    f"Error: {str(e)}",
                    ephemeral=True
                )

        else:
            await interaction.followup.send("Invalid datetime format. Use YYYY-MM-DD HH:MM.", ephemeral=True)
            return

        await interaction.followup.send(f"Flight {flight_number} added successfully with event!", ephemeral=True)
    except ValueError:
        await interaction.followup.send("Invalid datetime format. Use YYYY-MM-DD HH:MM.", ephemeral=True)


@bot.tree.command(name="editflight", description="Edit flight information (Member only)")
@app_commands.describe(
    flight_number="Flight number",
    param="Parameter to edit (departure/arrival/datetime/status)",
    new_info="New value"
)
async def editflight(interaction: discord.Interaction,
                     flight_number: str,
                     param: str,
                     new_info: str):
    try:
        cmd_logging("/editflight", interaction, [flight_number, param, new_info])
    except Exception as e:
        print(e)
    
    await interaction.response.defer(ephemeral=True)
    if not is_member(interaction):
        await interaction.followup.send("You don't have permission to use this command.", ephemeral=True)
        return

    valid_params = ["departure", "arrival", "datetime", "status"]
    if param not in valid_params:
        await interaction.followup.send(f"Invalid parameter. Valid options: {', '.join(valid_params)}", ephemeral=True)
        return

    try:
        flight_number = norm_flight_number(flight_number)

        data = {
            'flight_number': flight_number,
            'param': param,
            'new_info': new_info
        }
        response = requests.post(REMOTE_DB_URL + f'/sql/editflight/', json=data)
        if response.status_code != 200:
            await interaction.followup.send("Something went wrong", ephemeral=True)
            return
        else:
            flight_data = response.json()

        if param == "datetime":
            if check_datetime(new_info):
                try:
                    # Check if we have a valid event_id
                    if flight_data["event_id"] and flight_data["event_id"].lower() != 'none':
                        try:
                            event = await interaction.client.get_guild(1335994271815307325).fetch_scheduled_event(int(flight_data["event_id"]))
                            if event:
                                await event.delete()
                        except discord.NotFound:
                            printy(f"Event {flight_data['event_id']} not found, creating new one")
                        except ValueError:
                            printy(f"Invalid event ID format: {flight_data['event_id']}")

                    # Create new event with updated time
                    event_id = await create_flight_event(
                        interaction.client.get_guild(1335994271815307325),
                        flight_number,
                        new_info if param == "departure" else flight_data["departure"],
                        new_info if param == "arrival" else flight_data["arrival"],
                        new_info
                    )

                    data = {
                        'flight_number': flight_number,
                        'event_id': event_id
                    }
                    response = requests.post(REMOTE_DB_URL + '/sql/editflight/event_upd', json=data)

                    if response.status_code != 200:
                        printy(response.json())
                        await interaction.followup.send(f"Something went wrong", ephemeral=True)
                        return
                except Exception as e:
                    printy(f"Error updating event: {e}")
                    await interaction.followup.send(f"Something went wrong", ephemeral=True)
                    return
            else:
                await interaction.followup.send("Invalid datetime format. Use YYYY-MM-DD HH:MM.", ephemeral=True)
                return

        await interaction.followup.send(f"Flight {flight_number} updated successfully!", ephemeral=True)
        return
    except ValueError:
        await interaction.followup.send("Invalid datetime format. Use YYYY-MM-DD HH:MM.", ephemeral=True)
        return


@bot.tree.command(name="delflight", description="Delete a flight (Member only)")
@app_commands.describe(
    flight_number="Flight number"
)
async def delflight(interaction: discord.Interaction, flight_number: str):
    try:
        cmd_logging("/delflight", interaction, [flight_number])
    except Exception as e:
        print(e)
    
    await interaction.response.defer(ephemeral=True)
    if not is_member(interaction):
        await interaction.followup.send("You don't have permission to use this command.", ephemeral=True)
        return

    try:
        reqst = requests.get(REMOTE_DB_URL + f"/sql/delflight/{flight_number.replace(' ', '')}")
        if reqst.status_code == 200:
            printy(reqst.json())
            event_id = reqst.json()

            if event_id:
                try:
                    tguild = interaction.client.get_guild(1335994271815307325)
                    event = await tguild.fetch_scheduled_event(int(event_id))
                    await event.delete()
                except Exception as e:
                    printy(e)
                    pass
        else:
            printy(reqst.text)
    except Exception as e:
        printy(f"{e}")
    
    await interaction.followup.send("Flight deleted successfully!", ephemeral=True)
    return


@bot.tree.command(name="newmember", description="Add a new member (Founders only)")
@app_commands.describe(
    name="Airline name",
    link="Discord invite link",
    representative="Representative's user ID",
    iata="IATA code",
    icao="ICAO code"
)
async def newmember(interaction: discord.Interaction,
                    name: str,
                    link: str,
                    representative: str,
                    iata: str,
                    icao: str):
    try:
        cmd_logging("/newmember", interaction, [name, link, representative, iata, icao])
    except Exception as e:
        print(e)
    
    await interaction.response.defer(ephemeral=True)

    if not is_founder(interaction):
        await interaction.followup.send("You don't have permission to use this command.", ephemeral=True)
        return

    # Create the embed payload
    embed_data = {
        "content": "",
        "tts": False,
        "embeds": [
            {
                "description": f"## {name}\n{link}\n-# <@{representative}>\n-# {iata} / {icao}",
                "color": 16736750,
                "fields": []
            }
        ],
        "components": [],
        "actions": {}
    }

    # Send via webhook
    webhook_url = "#"  # Replace with your actual webhook URL
    async with aiohttp.ClientSession() as session:
        async with session.post(webhook_url, json=embed_data) as response:
            if response.status == 204:
                await interaction.followup.send("New member announcement sent successfully!", ephemeral=True)
            else:
                await interaction.followup.send("Failed to send announcement.", ephemeral=True)


# Изменённый метод команды "/schedule":
@bot.tree.command(name="schedule", description="Show flight schedule")
async def schedule(interaction: discord.Interaction):
    try:
        cmd_logging("/schedule", interaction, [])
    except Exception as e:
        print(e)
    
    await interaction.response.defer(ephemeral=True)
    flights = ""
    try:
        reqst = requests.get(REMOTE_DB_URL + f"/sql/schedule/")
        if reqst.status_code == 200:
            printy(reqst.json())
            flights = reqst.json()
        else:
            printy(reqst.text)
    except Exception as e:
        printy(f"{e}")

    # Рассчитываем размеры изображения
    rows = len(flights)
    header_height = 120
    row_height = 60
    padding = 40
    col_widths = [100, 200, 200, 100, 100, 150]

    total_width = sum(col_widths) + padding * 2
    total_height = header_height + (rows * row_height) + padding

    # Создаём новое изображение
    bg_color = (5, 15, 45)  # #050F2D
    text_color = (255, 255, 255)  # #FFFFFF
    image = Image.new('RGB', (total_width, total_height), color=bg_color)
    draw = ImageDraw.Draw(image)

    try:
        font_path = "arialbd.ttf"
        title_font = ImageFont.truetype(font_path, 28)
        header_font = ImageFont.truetype(font_path, 18)
        row_font = ImageFont.truetype(font_path, 16)
    except:
        title_font = ImageFont.load_default()
        header_font = ImageFont.load_default()
        row_font = ImageFont.load_default()

    # Отображаем название страницы
    title = "UWU Flights Schedule"
    title_width = draw.textlength(title, font=title_font)
    draw.text(((total_width - title_width) // 2, 30), title, fill=text_color, font=title_font)

    # Заголовки колонок
    headers = ["Flight #", "Departure", "Arrival", "Date", "Time", "Status"]
    y_position = header_height - 30

    draw.line((padding, 80, total_width - padding, 80),
              fill=(100, 100, 150), width=1)
    draw.line((padding, 120, total_width - padding, 120),
              fill=(100, 100, 150), width=1)

    x_position = padding
    for i, (header, width) in enumerate(zip(headers, col_widths)):
        draw.text((x_position + 10, y_position), header, fill=text_color, font=header_font)
        if i < len(headers) - 1:
            draw.line((x_position + width, y_position - 10, x_position + width, y_position + 30),
                      fill=(100, 100, 150), width=1)
        x_position += width

    # Заполняем таблицу рейсами
    y_position = header_height
    for flight in flights:
        # Распаковываем каждый рейс
        flight_number, departure, arrival, datetime_str, status, _ = flight  # Игнорируем последний элемент (event_id)

        # Разделяем дату и время
        date_part, time_part = datetime_str.split(' ')

        # Определяем позицию каждого элемента
        x_position = padding
        values = [
            flight_number,  # Flight #
            departure,  # Departure
            arrival,  # Arrival
            date_part,  # Дата (Date)
            time_part,  # Время (Time)
            status  # Статус (Status)
        ]

        for i, (value, width) in enumerate(zip(values, col_widths)):
            draw.text((x_position + 10, y_position + 15), str(value), fill=text_color, font=row_font)
            x_position += width

        # Линия между строками
        draw.line((padding, y_position + row_height - 10, total_width - padding, y_position + row_height - 10),
                  fill=(100, 100, 150), width=1)
        y_position += row_height

    # Сохраняем изображение и отправляем его в чат
    img_buffer = io.BytesIO()
    image.save(img_buffer, format='PNG')
    img_buffer.seek(0)
    file = discord.File(img_buffer, filename="schedule.png")
    await interaction.followup.send(file=file)


@bot.tree.command(name="archive", description="Archive bookings for a specific flight")
@app_commands.describe(
    flight="Flight number to archive bookings from"
)
async def archive(interaction: discord.Interaction, flight: str):
    try:
        cmd_logging("/archive", interaction, [flight])
    except Exception as e:
        print(e)
        
    await interaction.response.defer(ephemeral=True)
    if not is_member(interaction):
        await interaction.followup.send("You don't have permission to use this command.", ephemeral=True)
        return

    try:
        try:
            flight = norm_flight_number(flight)
            reqst = requests.get(REMOTE_DB_URL + f"/sql/archive/{flight}")
            if reqst.status_code == 200:
                await interaction.followup.send(reqst.json(), ephemeral=True)
            else:
                printy(reqst.text)
        except Exception as e:
            printy(f"{e}")

    except Exception as e:
        await interaction.followup.send(
            f"An error occurred while archiving: {str(e)}",
            ephemeral=True
        )
        printy(f"Archive error: {e}")


@bot.tree.command(name="memory", description="Save your best memories")
@app_commands.describe(
    image="Image URL",
    caption="Caption for the memory",
    date="Date of the memory"
)
async def memory(interaction: discord.Interaction,
                 image: str,
                 caption: str,
                 date: str):
    try:
        cmd_logging("/memory", interaction, [image, caption, date])
    except Exception as e:
        print(e)
        
    await interaction.response.defer(ephemeral=True)
    try:
        user_id = str(interaction.user.id)

        data = {
            "image": image,
            "caption": caption,
            "memdate": date,
            "user_id": user_id,
        }
        response = requests.post(REMOTE_DB_URL + '/sql/memory/', json=data)
        if response.status_code != 200:
            printy(response.json())
            await interaction.followup.send(f"Something went wrong", ephemeral=True)

        await interaction.followup.send(f"Saved!", ephemeral=True)
        return True
    except Exception as e:
        await interaction.followup.send(f"Error: {e}", ephemeral=True)
        return False


@bot.tree.command(name="apply", description="Apply to join UWU Family!")
@app_commands.describe(
    link="Link to your server",
    icao="ICAO code of your airline",
    iata="IATA code of your airline",
    reason="Why should we accept you (DONT PUT YOUR WHOLE AD HERE!)"
)
async def apply(interaction: discord.Interaction,
                link: str,
                icao: str,
                iata: str,
                reason: str):
    try:
        cmd_logging("/apply", interaction, [link, icao, iata, reason])
    except Exception as e:
        print(e)
        
    await interaction.response.defer(ephemeral=True)
    guild = bot.get_guild(1335994271815307325)
    joinchat = guild.get_channel(1335999793935155362)

    msg = await joinchat.send(f"||<@&1336004078999965778>||\n{link} - {iata.upper()}/{icao.upper()}\n{reason}\n-# <@{interaction.user.id}>")
    await msg.add_reaction('✅')
    await msg.add_reaction('❌')

    await interaction.followup.send(f"Done! We'll reach out to you with decision soon", ephemeral=True)
    return True


user_cooldowns = {}
from discord import app_commands
import time
from datetime import datetime, timedelta


@bot.tree.command(name="notify", description="Send flight notification")
@app_commands.describe(
    flight="Flight number",
    link="Link to join"
)
async def notify(interaction: discord.Interaction, flight: str, link: str, silent: bool = False):
    
    try:
        cmd_logging("/notify", interaction, [flight, link, silent])
    except Exception as e:
        print(e)
    
    await interaction.response.defer(ephemeral=True)
    if not is_member(interaction):
        await interaction.followup.send("You don't have permission to use this command.", ephemeral=True)
        return

    NOTIFICATION_CHANNEL_ID = 1368408244501872780

    user_id = interaction.user.id
    current_time = time.time()
    flight = norm_flight_number(flight)
    if user_id in user_cooldowns and not silent:
        last_used = user_cooldowns[user_id]
        cooldown_remaining = (last_used + 600) - current_time

        if cooldown_remaining > 0:
            cooldown_time = str(timedelta(seconds=int(cooldown_remaining)))
            await interaction.followup.send(
                f"You can use this command again in {cooldown_time}",
                ephemeral=True
            )
            return

    try:
        # Получаем канал для уведомлений
        channel = bot.get_channel(NOTIFICATION_CHANNEL_ID)
        if not channel:
            await interaction.followup.send("Channel not found :(", ephemeral=True)
            return

        flight_data = ""
        try:
            reqst = requests.get(REMOTE_DB_URL + f"/sql/notify/s1/{flight}")
            if reqst.status_code == 200:
                printy(reqst.json())
                flight_data = reqst.json()
            else:
                printy(reqst.text)
        except Exception as e:
            printy(f"{e}")

        departure, arrival = flight_data
        embed = discord.Embed(
            title=f"",
            description=f"## {flight}\n## {departure} → {arrival}\n## [Click to join!](<{link}>)",
            color=discord.Color.pink()
        )

        # Отправляем сообщение
        if silent:
            pinng = '.'
        else:
            pinng = '<@&1338042789996269570>'
        await channel.send(str(pinng), embed=embed)

        # Обновляем кулдаун
        user_cooldowns[user_id] = current_time

        users_with_booking = ""
        try:
            reqst = requests.get(REMOTE_DB_URL + f"/sql/notify/s2/{flight}")
            if reqst.status_code == 200:
                printy(reqst.json())
                users_with_booking = reqst.json()
            else:
                printy(reqst.text)
        except Exception as e:
            printy(f"{e}")

        for user_id_tuple in users_with_booking:
            user_id = user_id_tuple[0]
            user = await bot.fetch_user(user_id)
            await user.send(embed=embed)

        # Отправляем подтверждение пользователю
        await interaction.followup.send(
            f"Notification for {flight} sent successfully",
            ephemeral=True
        )

    except Exception as e:
        await interaction.followup.send(
            f"Error: {str(e)}",
            ephemeral=True
        )


@bot.event
async def on_ready():
    printy(f'Bot {bot.user} is ready!')
    try:
        synced = await bot.tree.sync()
        printy(f"Synced {len(synced)} commands")
    except Exception as e:
        printy(f"Error syncing commands: {e}")

    await bot.tree.sync()


load_dotenv()
bot.run("#")
