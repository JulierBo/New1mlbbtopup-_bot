import json, os, asyncio
from datetime import datetime
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ChatMember


# Load environment variables from .env file
try:
    with open('.env', 'r') as f:
        for line in f:
            if '=' in line:
                key, value = line.strip().split('=', 1)
                os.environ[key] = value
except FileNotFoundError:
    pass

BOT_TOKEN = os.getenv("BOT_TOKEN")
# Hard-coded admin IDs (override environment variables)
ADMIN_ID = 6437656033
ADMIN_GROUP_ID = -1002747496932
DATA_FILE = "data.json"

# Authorized users - only these users can use the bot
AUTHORIZED_USERS = set()

# User states for restricting actions after screenshot
user_states = {}

# Bot maintenance mode
bot_maintenance = {
    "orders": True,    # True = enabled, False = disabled
    "topups": True,    # True = enabled, False = disabled
    "general": True    # True = enabled, False = disabled
}

# Payment information
payment_info = {
    "kpay_number": "09678786528",
    "kpay_name": "Ma May Phoo Wai",
    "kpay_image": None,  # Store file_id of KPay QR code image
    "wave_number": "09673585480",
    "wave_name": "Nine Nine",
    "wave_image": None   # Store file_id of Wave QR code image
}

def is_user_authorized(user_id):
    """Check if user is authorized to use the bot"""
    return str(user_id) in AUTHORIZED_USERS or int(user_id) == ADMIN_ID

async def is_bot_admin_in_group(bot, chat_id):
    """Check if bot is admin in the group"""
    try:
        bot_member = await bot.get_chat_member(chat_id, bot.id)
        return bot_member.status in [ChatMember.ADMINISTRATOR, ChatMember.OWNER]
    except Exception:
        return False



def simple_reply(message_text):
    """
    Simple auto-replies for common queries
    """
    message_lower = message_text.lower()

    # Greetings
    if any(word in message_lower for word in ["hello", "hi", "မင်္ဂလာပါ", "ဟယ်လို", "ဟိုင်း", "ကောင်းလား"]):
        return ("👋 မင်္ဂလာပါ! MLBB Diamond Top-up Bot မှ ကြိုဆိုပါတယ်!\n\n"
                "📱 Bot commands များ သုံးရန် `/start` နှိပ်ပါ\n"
                "💡 အကူအညီလိုရင် `/help` နှိပ်ပါ")

    # Help requests
    elif any(word in message_lower for word in ["help", "ကူညီ", "အကူအညီ", "မသိ", "လမ်းညွှန်"]):
        return ("📱 **အသုံးပြုနိုင်တဲ့ commands:**\n"
                "• `/start` - Bot စတင်အသုံးပြုရန်\n"
                "• `/mmb gameid serverid amount` - Diamond ဝယ်ယူရန်\n"
                "• `/balance` - လက်ကျန်ငွေ စစ်ရန်\n"
                "• `/topup amount` - ငွေဖြည့်ရန်\n"
                "• `/price` - ဈေးနှုန်းများ ကြည့်ရန်\n"
                "• `/history` - မှတ်တမ်းများ ကြည့်ရန်\n\n"
                "💡 အသေးစိတ် လိုအပ်ရင် admin ကို ဆက်သွယ်ပါ!")

    # Default response
    else:
        return ("📱 **MLBB Diamond Top-up Bot**\n\n"
                "💎 Diamond ဝယ်ယူရန် `/mmb` command သုံးပါ\n"
                "💰 ဈေးနှုန်းများ သိရှိရန် `/price` နှိပ်ပါ\n"
                "🆘 အကူအညီ လိုရင် `/start` နှိပ်ပါ")

def load_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w") as f:
            json.dump({"users": {}, "prices": {}}, f)
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def load_authorized_users():
    """Load authorized users from data file"""
    global AUTHORIZED_USERS
    data = load_data()
    AUTHORIZED_USERS = set(data.get("authorized_users", []))

def save_authorized_users():
    """Save authorized users to data file"""
    data = load_data()
    data["authorized_users"] = list(AUTHORIZED_USERS)
    save_data(data)

def load_prices():
    """Load custom prices from data file"""
    data = load_data()
    return data.get("prices", {})

def save_prices(prices):
    """Save prices to data file"""
    data = load_data()
    data["prices"] = prices
    save_data(data)

def validate_game_id(game_id):
    """Validate MLBB Game ID (6-10 digits)"""
    if not game_id.isdigit():
        return False
    if len(game_id) < 6 or len(game_id) > 10:
        return False
    return True

def validate_server_id(server_id):
    """Validate MLBB Server ID (3-5 digits)"""
    if not server_id.isdigit():
        return False
    if len(server_id) < 3 or len(server_id) > 5:
        return False
    return True

def is_banned_account(game_id):
    """
    Check if MLBB account is banned
    This is a simple example - in reality you'd need to integrate with MLBB API
    For now, we'll use some common patterns of banned accounts
    """
    # Add known banned account IDs here
    banned_ids = [
        "123456789",  # Example banned ID
        "000000000",  # Invalid pattern
        "111111111",  # Invalid pattern
    ]

    # Check if game_id matches banned patterns
    if game_id in banned_ids:
        return True

    # Check for suspicious patterns (all same digits, too simple patterns)
    if len(set(game_id)) == 1:  # All same digits like 111111111
        return True

    if game_id.startswith("000") or game_id.endswith("000"):
        return True

    return False

def get_price(diamonds):
    # Load custom prices first - these override defaults
    custom_prices = load_prices()
    if diamonds in custom_prices:
        return custom_prices[diamonds]

    # Default prices
    if diamonds.startswith("wp") and diamonds[2:].isdigit():
        n = int(diamonds[2:])
        if 1 <= n <= 10:
            return n * 6000
    table = {
        "11": 950, "22": 1900, "33": 2850, "56": 4200, "112": 8200,
        "86": 5100, "172": 10200, "257": 15300, "343": 20400,
        "429": 25500, "514": 30600, "600": 35700, "706": 40800,
        "878": 51000, "963": 56100, "1049": 61200, "1135": 66300,
        "1412": 81600, "2195": 122400, "3688": 204000,
        "5532": 306000, "9288": 510000, "12976": 714000,
        "55": 3500, "165": 10000, "275": 16000, "565": 33000
    }
    return table.get(diamonds)

def is_payment_screenshot(update):
    """
    Check if the image is likely a payment screenshot
    This is a basic validation - you can enhance it with image analysis
    """
    # For now, we'll accept all photos as payment screenshots
    # You can add image analysis here to check for payment app UI elements
    if update.message.photo:
        # Check if photo has caption containing payment keywords
        caption = update.message.caption or ""
        payment_keywords = ["kpay", "wave", "payment", "pay", "transfer", "လွှဲ", "ငွေ"]

        # Accept all photos for now, but you can add more validation here
        return True
    return False

pending_topups = {}

async def check_pending_topup(user_id):
    """Check if user has pending topups"""
    data = load_data()
    user_data = data["users"].get(user_id, {})

    for topup in user_data.get("topups", []):
        if topup.get("status") == "pending":
            return True
    return False

async def send_pending_topup_warning(update: Update):
    """Send pending topup warning message"""
    await update.message.reply_text(
        "⏳ **Pending Topup ရှိနေပါတယ်!**\n\n"
        "❌ သင့်မှာ admin က approve မလုပ်သေးတဲ့ topup ရှိနေပါတယ်။\n\n"
        "**လုပ်ရမည့်အရာများ**:\n"
        "• Admin က topup ကို approve လုပ်ပေးတဲ့အထိ စောင့်ပါ\n"
        "• Approve ရပြီးမှ command တွေကို ပြန်အသုံးပြုနိုင်ပါမယ်\n\n"
        "📞 အရေးပေါ်ဆိုရင် admin ကို ဆက်သွယ်ပါ။\n"
        "💡 `/balance` နဲ့ status စစ်ကြည့်နိုင်ပါတယ်။",
        parse_mode="Markdown"
    )

async def check_maintenance_mode(command_type):
    """Check if specific command type is in maintenance mode"""
    return bot_maintenance.get(command_type, True)

async def send_maintenance_message(update: Update, command_type):
    """Send maintenance mode message with beautiful UI"""
    user_name = update.effective_user.first_name or "User"
    
    if command_type == "orders":
        msg = (
            f"မင်္ဂလာပါ {user_name}! 👋\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "⏸️ **Bot အော်ဒါတင်ခြင်းအား ခေတ္တ ယာယီပိတ်ထားပါသည်** ⏸️\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🔄 Admin မှ ပြန်လည်ဖွင့်ပေးမှ အသုံးပြုနိုင်ပါမည်။\n\n"
            "📞 အရေးပေါ်ဆိုရင် Admin ကို ဆက်သွယ်ပါ။"
        )
    elif command_type == "topups":
        msg = (
            f"မင်္ဂလာပါ {user_name}! 👋\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "⏸️ **Bot ငွေဖြည့်ခြင်းအား ခေတ္တ ယာယီပိတ်ထားပါသည်** ⏸️\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🔄 Admin မှ ပြန်လည်ဖွင့်ပေးမှ အသုံးပြုနိုင်ပါမည်။\n\n"
            "📞 အရေးပေါ်ဆိုရင် Admin ကို ဆက်သွယ်ပါ။"
        )
    else:
        msg = (
            f"မင်္ဂလာပါ {user_name}! 👋\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "⏸️ **Bot အား ခေတ္တ ယာယီပိတ်ထားပါသည်** ⏸️\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🔄 Admin မှ ပြန်လည်ဖွင့်ပေးမှ အသုံးပြုနိုင်ပါမည်။\n\n"
            "📞 အရေးပေါ်ဆိုရင် Admin ကို ဆက်သွယ်ပါ။"
        )

    await update.message.reply_text(msg, parse_mode="Markdown")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)
    username = user.username or "-"
    name = f"{user.first_name} {user.last_name or ''}".strip()

    # Load authorized users
    load_authorized_users()

    # Check if user is authorized
    if not is_user_authorized(user_id):
        # Create keyboard with Owner contact button
        keyboard = [[InlineKeyboardButton("👑 Contact Owner", url=f"tg://user?id={ADMIN_ID}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"🚫 **Bot အသုံးပြုခွင့် မရှိပါ!**\n\n"
            f"👋 မင်္ဂလာပါ `{name}`!\n"
            f"🆔 Your ID: `{user_id}`\n\n"
            "❌ သင်သည် ဤ bot ကို အသုံးပြုခွင့် မရှိသေးပါ။\n\n"
            "**လုပ်ရမည့်အရာများ**:\n"
            "• အောက်က 'Contact Owner' button ကို နှိပ်ပါ\n"
            "• Owner ထံ bot အသုံးပြုခွင့် တောင်းဆိုပါ\n"
            "• သင့် User ID ကို ပေးပို့ပါ\n\n"
            "✅ Owner က approve လုပ်ပြီးမှ bot ကို အသုံးပြုနိုင်ပါမယ်။",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        return

    data = load_data()

    # Check for pending topups first
    if await check_pending_topup(user_id):
        await send_pending_topup_warning(update)
        return

    if user_id not in data["users"]:
        data["users"][user_id] = {
            "name": name,
            "username": username,
            "balance": 0,
            "orders": [],
            "topups": []
        }
        save_data(data)

    # Clear any restricted state when starting
    if user_id in user_states:
        del user_states[user_id]

    # Create keyboard with Owner contact button
    keyboard = [[InlineKeyboardButton("👑 Contact Owner", url=f"tg://user?id={ADMIN_ID}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    msg = (
        f"👋 မင်္ဂလာပါ `{name}`!\n"
        f"🆔 Telegram User ID: `{user_id}`\n\n"
        "📱 MLBB Diamond Top-up Bot မှ ကြိုဆိုပါတယ်။\n\n"
        "**အသုံးပြုနိုင်တဲ့ command များ**:\n"
        "➤ `/mmb gameid serverid amount`\n"
        "➤ `/balance` - ဘယ်လောက်လက်ကျန်ရှိလဲ စစ်မယ်\n"
        "➤ `/topup amount` - ငွေဖြည့်မယ် (screenshot တင်ပါ)\n"
        "➤ `/price` - Diamond များရဲ့ ဈေးနှုန်းများ\n"
        "➤ `/history` - အော်ဒါမှတ်တမ်းကြည့်မယ်\n\n"
        "**📌 ဥပမာ**:\n"
        "`/mmb 123456789 12345 wp1`\n"
        "`/mmb 123456789 12345 86`\n\n"
        "လိုအပ်တာရှိရင် Owner ကို ဆက်သွယ်နိုင်ပါတယ်။ "
    )
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=reply_markup)

async def mmb_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    # Check authorization
    load_authorized_users()
    if not is_user_authorized(user_id):
        keyboard = [[InlineKeyboardButton("👑 Contact Owner", url=f"tg://user?id={ADMIN_ID}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🚫 **အသုံးပြုခွင့် မရှိပါ!**\n\n"
            "Owner ထံ bot အသုံးပြုခွင့် တောင်းဆိုပါ။",
            reply_markup=reply_markup
        )
        return

    # Check maintenance mode
    if not await check_maintenance_mode("orders"):
        await send_maintenance_message(update, "orders")
        return

    # Check if user is restricted after screenshot
    if user_id in user_states and user_states[user_id] == "waiting_approval":
        await update.message.reply_text(
            "⏳ **Screenshot ပို့ပြီးပါပြီ!**\n\n"
            "❌ Admin က လက်ခံပြီးကြောင်း အတည်ပြုတဲ့အထိ commands တွေ အသုံးပြုလို့ မရပါ။\n\n"
            "⏰ Admin က approve လုပ်ပြီးမှ ပြန်လည် အသုံးပြုနိုင်ပါမယ်။\n"
            "📞 အရေးပေါ်ဆိုရင် admin ကို ဆက်သွယ်ပါ။",
            parse_mode="Markdown"
        )
        return

    # Check for pending topups first
    if await check_pending_topup(user_id):
        await send_pending_topup_warning(update)
        return

    args = context.args

    if len(args) != 3:
        await update.message.reply_text(
            "❌ အမှားရှိပါတယ်!\n\n"
            "**မှန်ကန်တဲ့ format**:\n"
            "`/mmb gameid serverid amount`\n\n"
            "**ဥပမာ**:\n"
            "`/mmb 123456789 12345 wp1`\n"
            "`/mmb 123456789 12345 86`",
            parse_mode="Markdown"
        )
        return

    game_id, server_id, amount = args

    # Validate Game ID
    if not validate_game_id(game_id):
        await update.message.reply_text(
            "❌ Game ID မှားနေပါတယ်!\n\n"
            "**Game ID requirements**:\n"
            "• ကိန်းဂဏန်းများသာ ပါရမည်\n"
            "• 6-10 digits ရှိရမည်\n\n"
            "**ဥပမာ**: `123456789`",
            parse_mode="Markdown"
        )
        return

    # Validate Server ID
    if not validate_server_id(server_id):
        await update.message.reply_text(
            "❌ Server ID မှားနေပါတယ်!\n\n"
            "**Server ID requirements**:\n"
            "• ကိန်းဂဏန်းများသာ ပါရမည်\n"
            "• 3-5 digits ရှိရမည်\n\n"
            "**ဥပမာ**: `8662`, `12345`",
            parse_mode="Markdown"
        )
        return

    # Check if account is banned
    if is_banned_account(game_id):
        await update.message.reply_text(
            "🚫 **Account Ban ဖြစ်နေပါတယ်!**\n\n"
            f"🎮 Game ID: `{game_id}`\n"
            f"🌐 Server ID: `{server_id}`\n\n"
            "❌ ဒီ account မှာ diamond topup လုပ်လို့ မရပါ။\n\n"
            "**အကြောင်းရင်းများ**:\n"
            "• Account suspended/banned ဖြစ်နေခြင်း\n"
            "• Invalid account pattern\n"
            "• MLBB မှ ပိတ်ပင်ထားခြင်း\n\n"
            "🔄 အခြား account သုံးပြီး ထပ်ကြိုးစားကြည့်ပါ။\n"
            "📞 ပြဿနာရှိရင် admin ကို ဆက်သွယ်ပါ။",
            parse_mode="Markdown"
        )

        # Notify admin about banned account attempt
        admin_msg = (
            f"🚫 **Banned Account Topup ကြိုးစားမှု**\n\n"
            f"👤 User: [{update.effective_user.first_name}](tg://user?id={user_id})\n\n"
            f"🆔 User ID: `{user_id}`\n"
            f"🎮 Game ID: `{game_id}`\n"
            f"🌐 Server ID: `{server_id}`\n"
            f"💎 Amount: {amount}\n"
            f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            "⚠️ ဒီ account မှာ topup လုပ်လို့ မရပါ။"
        )

        try:
            await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, parse_mode="Markdown")
        except:
            pass

        return

    price = get_price(amount)

    if not price:
        await update.message.reply_text(
            "❌ Diamond amount မှားနေပါတယ်!\n\n"
            "**ရရှိနိုင်တဲ့ amounts**:\n"
            "• Weekly Pass: wp1-wp10\n"
            "• Diamonds: 11, 22, 33, 56, 86, 112, 172, 257, 343, 429, 514, 600, 706, 878, 963, 1049, 1135, 1412, 2195, 3688, 5532, 9288, 12976",
            parse_mode="Markdown"
        )
        return

    data = load_data()
    user_balance = data["users"].get(user_id, {}).get("balance", 0)

    if user_balance < price:
        await update.message.reply_text(
            f"❌ လက်ကျန်ငွေ မလုံလောက်ပါ!\n\n"
            f"💰 လိုအပ်တဲ့ငွေ: {price:,} MMK\n"
            f"💳 သင့်လက်ကျန်: {user_balance:,} MMK\n"
            f"❗ လိုအပ်သေးတာ: {price - user_balance:,} MMK\n\n"
            "ငွေဖြည့်ရန် `/topup amount` သုံးပါ။",
            parse_mode="Markdown"
        )
        return

    # Process order
    order_id = f"ORD{datetime.now().strftime('%Y%m%d%H%M%S')}"
    order = {
        "order_id": order_id,
        "game_id": game_id,
        "server_id": server_id,
        "amount": amount,
        "price": price,
        "status": "pending",
        "timestamp": datetime.now().isoformat(),
        "user_id": user_id,
        "chat_id": update.effective_chat.id  # Store chat ID where order was placed
    }

    # Deduct balance
    data["users"][user_id]["balance"] -= price
    data["users"][user_id]["orders"].append(order)
    save_data(data)

    # Create confirm/cancel buttons for admin
    keyboard = [
        [
            InlineKeyboardButton("✅ Confirm", callback_data=f"order_confirm_{order_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"order_cancel_{order_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Notify admin
    admin_msg = (
        f"🔔 **အော်ဒါအသစ်ရောက်ပါပြီ!**\n\n"
        f"📝 Order ID: `{order_id}`\n"
        f"👤 User: [{update.effective_user.first_name}](tg://user?id={user_id})\n\n"
        f"🆔 User ID: `{user_id}`\n"
        f"🎮 Game ID: `{game_id}`\n"
        f"🌐 Server ID: `{server_id}`\n"
        f"💎 Amount: {amount}\n"
        f"💰 Price: {price:,} MMK\n"
        f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"📊 Status: ⏳ စောင့်ဆိုင်းနေသည်"
    )

    # Send to all admins (with buttons for everyone)
    data = load_data()
    admin_list = data.get("admin_ids", [ADMIN_ID])
    for admin_id in admin_list:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=admin_msg,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
        except:
            pass

    # Notify admin group
    await notify_group_order(order, update.effective_user.first_name or "Unknown", user_id)

    await update.message.reply_text(
        f"✅ **အော်ဒါ အောင်မြင်ပါပြီ!**\n\n"
        f"📝 Order ID: `{order_id}`\n"
        f"🎮 Game ID: `{game_id}`\n"
        f"🌐 Server ID: `{server_id}`\n"
        f"💎 Diamond: {amount}\n"
        f"💰 ကုန်ကျစရိတ်: {price:,} MMK\n"
        f"💳 လက်ကျန်ငွေ: {data['users'][user_id]['balance']:,} MMK\n"
        f"📊 Status: ⏳ စောင့်ဆိုင်းနေသည်\n\n"
        "⚠️ Admin က confirm လုပ်ပြီးမှ diamonds များ ရရှိပါမယ်။\n"
        "📞 ပြဿနာရှိရင် admin ကို ဆက်သွယ်ပါ။",
        parse_mode="Markdown"
    )

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    # Check authorization
    load_authorized_users()
    if not is_user_authorized(user_id):
        keyboard = [[InlineKeyboardButton("👑 Contact Owner", url=f"tg://user?id={ADMIN_ID}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🚫 **အသုံးပြုခွင့် မရှိပါ!**\n\n"
            "Owner ထံ bot အသုံးပြုခွင့် တောင်းဆိုပါ။",
            reply_markup=reply_markup
        )
        return

    # Check if user is restricted after screenshot
    if user_id in user_states and user_states[user_id] == "waiting_approval":
        await update.message.reply_text(
            "⏳ **Screenshot ပို့ပြီးပါပြီ!**\n\n"
            "❌ Admin က လက်ခံပြီးကြောင်း အတည်ပြုတဲ့အထိ commands တွေ အသုံးပြုလို့ မရပါ။\n\n"
            "⏰ Admin က approve လုပ်ပြီးမှ ပြန်လည် အသုံးပြုနိုင်ပါမယ်။\n"
            "📞 အရေးပေါ်ဆိုရင် admin ကို ဆက်သွယ်ပါ။",
            parse_mode="Markdown"
        )
        return

    # Check for pending topups first
    if await check_pending_topup(user_id):
        await send_pending_topup_warning(update)
        return

    data = load_data()
    user_data = data["users"].get(user_id)

    if not user_data:
        await update.message.reply_text("❌ အရင်ဆုံး /start နှိပ်ပါ။")
        return

    balance = user_data.get("balance", 0)
    total_orders = len(user_data.get("orders", []))
    total_topups = len(user_data.get("topups", []))

    # Check for pending topups
    pending_topups_count = 0
    pending_amount = 0

    for topup in user_data.get("topups", []):
        if topup.get("status") == "pending":
            pending_topups_count += 1
            pending_amount += topup.get("amount", 0)

    # Escape special characters in name and username
    name = user_data.get('name', 'Unknown')
    username = user_data.get('username', 'None')

    # Remove or escape problematic characters for Markdown
    name = name.replace('*', '').replace('_', '').replace('`', '').replace('[', '').replace(']', '')
    username = username.replace('*', '').replace('_', '').replace('`', '').replace('[', '').replace(']', '')

    status_msg = ""
    if pending_topups_count > 0:
        status_msg = f"\n⏳ **Pending Topups**: {pending_topups_count} ခု ({pending_amount:,} MMK)\n❗ Diamond order ထားလို့မရပါ။ Admin approve စောင့်ပါ။"

    # Create inline keyboard with topup button
    keyboard = [[InlineKeyboardButton("💳 ငွေဖြည့်မယ်", callback_data="topup_button")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    balance_text = (
        f"💳 **သင့်ရဲ့ Account အချက်အလက်များ**\n\n"
        f"💰 လက်ကျန်ငွေ: `{balance:,} MMK`\n"
        f"📦 စုစုပေါင်း အော်ဒါများ: {total_orders}\n"
        f"💳 စုစုပေါင်း ငွေဖြည့်မှုများ: {total_topups}{status_msg}\n\n"
        f"👤 နာမည်: {name}\n"
        f"🆔 Username: @{username}"
    )

    # Try to get user's profile photo
    try:
        user_photos = await context.bot.get_user_profile_photos(user_id=int(user_id), limit=1)
        if user_photos.total_count > 0:
            # Send photo with balance info as caption
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=user_photos.photos[0][0].file_id,
                caption=balance_text,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
        else:
            # No profile photo, send text only
            await update.message.reply_text(
                balance_text,
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
    except:
        # If error getting photo, send text only
        await update.message.reply_text(
            balance_text,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )

async def topup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    # Check authorization
    load_authorized_users()
    if not is_user_authorized(user_id):
        keyboard = [[InlineKeyboardButton("👑 Contact Owner", url=f"tg://user?id={ADMIN_ID}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🚫 **အသုံးပြုခွင့် မရှိပါ!**\n\n"
            "Owner ထံ bot အသုံးပြုခွင့် တောင်းဆိုပါ။",
            reply_markup=reply_markup
        )
        return

    # Check maintenance mode
    if not await check_maintenance_mode("topups"):
        await send_maintenance_message(update, "topups")
        return

    # Check if user is restricted after screenshot
    if user_id in user_states and user_states[user_id] == "waiting_approval":
        await update.message.reply_text(
            "⏳ **Screenshot ပို့ပြီးပါပြီ!**\n\n"
            "❌ Admin က လက်ခံပြီးကြောင်း အတည်ပြုတဲ့အထိ commands တွေ အသုံးပြုလို့ မရပါ။\n\n"
            "⏰ Admin က approve လုပ်ပြီးမှ ပြန်လည် အသုံးပြုနိုင်ပါမယ်။\n"
            "📞 အရေးပေါ်ဆိုရင် admin ကို ဆက်သွယ်ပါ။",
            parse_mode="Markdown"
        )
        return

    # Check for pending topups first
    if await check_pending_topup(user_id):
        await send_pending_topup_warning(update)
        return

    args = context.args

    if not args:
        # Create payment buttons
        keyboard = [
            [InlineKeyboardButton("📱 Copy KPay Number", callback_data="copy_kpay")],
            [InlineKeyboardButton("📱 Copy Wave Number", callback_data="copy_wave")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "❌ ငွေပမာဏ ထည့်ပါ!\n\n"
            "**ဥပမာ**: `/topup 50000`\n\n"
            "💳 ငွေလွှဲရန် အောက်က buttons များကို သုံးပါ။",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        return

    try:
        amount = int(args[0])
        if amount < 1000:
            await update.message.reply_text("❌ အနည်းဆုံး 1,000 MMK ဖြည့်ပါ။")
            return
    except ValueError:
        await update.message.reply_text("❌ ကိန်းဂဏန်းသာ ထည့်ပါ။")
        return

    # Store pending topup
    pending_topups[user_id] = {
        "amount": amount,
        "timestamp": datetime.now().isoformat()
    }

    # Create payment buttons
    keyboard = [
        [InlineKeyboardButton("📱 Copy KPay Number", callback_data="copy_kpay")],
        [InlineKeyboardButton("📱 Copy Wave Number", callback_data="copy_wave")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    topup_msg = (
        "💳 **ငွေဖြည့်လုပ်ငန်းစဉ်**\n\n"
        f"💰 ပမာဏ: `{amount:,} MMK`\n\n"
        "**အဆင့် 1**: ငွေပမာဏ ရေးပါ\n"
        "`/topup amount` ဥပမာ: `/topup 50000`\n\n"
        "**အဆင့် 2**: ငွေလွှဲပါ\n"
        f"🔵 KBZ Pay: `{payment_info['kpay_number']}` ({payment_info['kpay_name']})\n"
        f"📱 Wave Money: `{payment_info['wave_number']}` ({payment_info['wave_name']})\n\n"
        "**အဆင့် 3**: Screenshot တင်ပါ\n"
        "ငွေလွှဲပြီးရင် screenshot ကို ဒီမှာ တင်ပေးပါ။\n\n"
        "⏰ 24 နာရီအတွင်း confine လုပ်ပါမယ်။"
    )

    # Send KPay QR if available
    if payment_info.get("kpay_image"):
        try:
            await update.message.reply_photo(
                photo=payment_info["kpay_image"],
                caption=f"📱 **KBZ Pay QR Code**\n\n"
                        f"📞 နံပါတ်: `{payment_info['kpay_number']}`\n"
                        f"👤 နာမည်: {payment_info['kpay_name']}",
                parse_mode="Markdown"
            )
        except:
            pass

    # Send Wave QR if available
    if payment_info.get("wave_image"):
        try:
            await update.message.reply_photo(
                photo=payment_info["wave_image"],
                caption=f"📱 **Wave Money QR Code**\n\n"
                        f"📞 နံပါတ်: `{payment_info['wave_number']}`\n"
                        f"👤 နာမည်: {payment_info['wave_name']}",
                parse_mode="Markdown"
            )
        except:
            pass

    await update.message.reply_text(
        topup_msg,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    # Check authorization
    load_authorized_users()
    if not is_user_authorized(user_id):
        keyboard = [[InlineKeyboardButton("👑 Contact Owner", url=f"tg://user?id={ADMIN_ID}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🚫 **အသုံးပြုခွင့် မရှိပါ!**\n\n"
            "Owner ထံ bot အသုံးပြုခွင့် တောင်းဆိုပါ။",
            reply_markup=reply_markup
        )
        return

    # Check if user is restricted after screenshot
    if user_id in user_states and user_states[user_id] == "waiting_approval":
        await update.message.reply_text(
            "⏳ **Screenshot ပို့ပြီးပါပြီ!**\n\n"
            "❌ Admin က လက်ခံပြီးကြောင်း အတည်ပြုတဲ့အထိ commands တွေ အသုံးပြုလို့ မရပါ။\n\n"
            "⏰ Admin က approve လုပ်ပြီးမှ ပြန်လည် အသုံးပြုနိုင်ပါမယ်။\n"
            "📞 အရေးပေါ်ဆိုရင် admin ကို ဆက်သွယ်ပါ။",
            parse_mode="Markdown"
        )
        return

    # Get custom prices
    custom_prices = load_prices()

    # Default prices
    default_prices = {
        # Weekly Pass
        "wp1": 6000, "wp2": 12000, "wp3": 18000, "wp4": 24000, "wp5": 30000,
        "wp6": 36000, "wp7": 42000, "wp8": 48000, "wp9": 54000, "wp10": 60000,
        # Regular Diamonds
        "11": 950, "22": 1900, "33": 2850, "56": 4200, "86": 5100, "112": 8200,
        "172": 10200, "257": 15300, "343": 20400, "429": 25500, "514": 30600,
        "600": 35700, "706": 40800, "878": 51000, "963": 56100, "1049": 61200,
        "1135": 66300, "1412": 81600, "2195": 122400, "3688": 204000,
        "5532": 306000, "9288": 510000, "12976": 714000,
        # 2X Diamond Pass
        "55": 3500, "165": 10000, "275": 16000, "565": 33000
    }

    # Merge custom prices with defaults (custom overrides default)
    current_prices = {**default_prices, **custom_prices}

    price_msg = "💎 **MLBB Diamond ဈေးနှုန်းများ**\n\n"

    # Weekly Pass section
    price_msg += "🎟️ **Weekly Pass**:\n"
    for i in range(1, 11):
        wp_key = f"wp{i}"
        if wp_key in current_prices:
            price_msg += f"• {wp_key} = {current_prices[wp_key]:,} MMK\n"
    price_msg += "\n"

    # Regular Diamonds section
    price_msg += "💎 **Regular Diamonds**:\n"
    regular_diamonds = ["11", "22", "33", "56", "86", "112", "172", "257", "343", 
                       "429", "514", "600", "706", "878", "963", "1049", "1135", 
                       "1412", "2195", "3688", "5532", "9288", "12976"]

    for diamond in regular_diamonds:
        if diamond in current_prices:
            price_msg += f"• {diamond} = {current_prices[diamond]:,} MMK\n"
    price_msg += "\n"

    # 2X Diamond Pass section
    price_msg += "💎 **2X Diamond Pass**:\n"
    double_pass = ["55", "165", "275", "565"]
    for dp in double_pass:
        if dp in current_prices:
            price_msg += f"• {dp} = {current_prices[dp]:,} MMK\n"
    price_msg += "\n"

    # Show any other custom items not in default categories
    other_customs = {k: v for k, v in custom_prices.items() 
                    if k not in default_prices}
    if other_customs:
        price_msg += "🔥 **Special Items**:\n"
        for item, price in other_customs.items():
            price_msg += f"• {item} = {price:,} MMK\n"
        price_msg += "\n"

    price_msg += (
        "**📝 အသုံးပြုနည်း**:\n"
        "`/mmb gameid serverid amount`\n\n"
        "**ဥပမာ**:\n"
        "`/mmb 123456789 12345 wp1`\n"
        "`/mmb 123456789 12345 86`"
    )

    await update.message.reply_text(price_msg, parse_mode="Markdown")

async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    # Check authorization
    load_authorized_users()
    if not is_user_authorized(user_id):
        keyboard = [[InlineKeyboardButton("👑 Contact Owner", url=f"tg://user?id={ADMIN_ID}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "🚫 **အသုံးပြုခွင့် မရှိပါ!**\n\n"
            "Owner ထံ bot အသုံးပြုခွင့် တောင်းဆိုပါ။",
            reply_markup=reply_markup
        )
        return

    # Check if user is restricted after screenshot
    if user_id in user_states and user_states[user_id] == "waiting_approval":
        await update.message.reply_text(
            "⏳ **Screenshot ပို့ပြီးပါပြီ!**\n\n"
            "❌ Admin က လက်ခံပြီးကြောင်း အတည်ပြုတဲ့အထိ commands တွေ အသုံးပြုလို့ မရပါ။\n\n"
            "⏰ Admin က approve လုပ်ပြီးမှ ပြန်လည် အသုံးပြုနိုင်ပါမယ်။\n"
            "📞 အရေးပေါ်ဆိုရင် admin ကို ဆက်သွယ်ပါ။",
            parse_mode="Markdown"
        )
        return

    # Check for pending topups first
    if await check_pending_topup(user_id):
        await send_pending_topup_warning(update)
        return

    data = load_data()
    user_data = data["users"].get(user_id)

    if not user_data:
        await update.message.reply_text("❌ အရင်ဆုံး /start နှိပ်ပါ။")
        return

    orders = user_data.get("orders", [])
    topups = user_data.get("topups", [])

    if not orders and not topups:
        await update.message.reply_text("📋 သင့်မှာ မည်သည့် မှတ်တမ်းမှ မရှိသေးပါ။")
        return

    msg = "📋 **သင့်ရဲ့ မှတ်တမ်းများ**\n\n"

    if orders:
        msg += "🛒 **အော်ဒါများ** (နောက်ဆုံး 5 ခု):\n"
        for order in orders[-5:]:
            status_emoji = "✅" if order.get("status") == "completed" else "⏳"
            msg += f"{status_emoji} {order['order_id']} - {order['amount']} ({order['price']:,} MMK)\n"
        msg += "\n"

    if topups:
        msg += "💳 **ငွေဖြည့်များ** (နောက်ဆုံး 5 ခု):\n"
        for topup in topups[-5:]:
            status_emoji = "✅" if topup.get("status") == "approved" else "⏳"
            msg += f"{status_emoji} {topup['amount']:,} MMK - {topup.get('timestamp', 'Unknown')[:10]}\n"

    await update.message.reply_text(msg, parse_mode="Markdown")



async def approve_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    # Check if user is any admin
    if not is_admin(user_id):
        await update.message.reply_text("❌ သင်သည် admin မဟုတ်ပါ!")
        return

    args = context.args
    if len(args) != 2:
        await update.message.reply_text(
            "❌ အမှားရှိပါတယ်!\n\n"
            "**မှန်ကန်တဲ့ format**: `/approve user_id amount`\n"
            "**ဥပမာ**: `/approve 123456789 50000`"
        )
        return

    try:
        target_user_id = args[0]
        amount = int(args[1])
    except ValueError:
        await update.message.reply_text("❌ ငွေပမာဏမှားနေပါတယ်!")
        return

    data = load_data()

    if target_user_id not in data["users"]:
        await update.message.reply_text("❌ User မတွေ့ရှိပါ!")
        return

    # Add balance to user
    data["users"][target_user_id]["balance"] += amount

    # Update topup status
    topups = data["users"][target_user_id]["topups"]
    for topup in reversed(topups):
        if topup["status"] == "pending" and topup["amount"] == amount:
            topup["status"] = "approved"
            topup["approved_at"] = datetime.now().isoformat()
            break

    save_data(data)

    # Clear user restriction state after approval
    if target_user_id in user_states:
        del user_states[target_user_id]

    # Notify user
    try:
        user_msg = (
            f"✅ **ငွေဖြည့်မှု အတည်ပြုပါပြီ!** 🎉\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💰 **ပမာဏ:** `{amount:,} MMK`\n"
            f"💳 **လက်ကျန်ငွေ:** `{data['users'][target_user_id]['balance']:,} MMK`\n"
            f"⏰ **အချိန်:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🎉 **ယခုအခါ diamonds များ ဝယ်ယူနိုင်ပါပြီ!** 💎\n\n"
            "⚡ အမြန်ဆုံး diamonds များကို `/mmb` command နဲ့ မှာယူပါ ⚡\n\n"
            "🔓 **Bot လုပ်ဆောင်ချက်များ ပြန်လည် အသုံးပြုနိုင်ပါပြီ!**"
        )
        await context.bot.send_message(chat_id=int(target_user_id), text=user_msg, parse_mode="Markdown")
    except:
        pass

    # Confirm to admin
    await update.message.reply_text(
        f"✅ **Approve အောင်မြင်ပါပြီ!**\n\n"
        f"👤 User ID: `{target_user_id}`\n"
        f"💰 Amount: `{amount:,} MMK`\n"
        f"💳 User's new balance: `{data['users'][target_user_id]['balance']:,} MMK`\n"
        f"🔓 User restrictions cleared!",
        parse_mode="Markdown"
    )

async def deduct_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    # Check if user is any admin
    if not is_admin(user_id):
        await update.message.reply_text("❌ သင်သည် admin မဟုတ်ပါ!")
        return

    args = context.args
    if len(args) != 2:
        await update.message.reply_text(
            "❌ အမှားရှိပါတယ်!\n\n"
            "**မှန်ကန်တဲ့ format**: `/deduct user_id amount`\n"
            "**ဥပမာ**: `/deduct 123456789 10000`"
        )
        return

    try:
        target_user_id = args[0]
        amount = int(args[1])
        if amount <= 0:
            await update.message.reply_text("❌ ငွေပမာဏသည် သုညထက် ကြီးရမည်!")
            return
    except ValueError:
        await update.message.reply_text("❌ ငွေပမာဏမှားနေပါတယ်!")
        return

    data = load_data()

    if target_user_id not in data["users"]:
        await update.message.reply_text("❌ User မတွေ့ရှိပါ!")
        return

    current_balance = data["users"][target_user_id]["balance"]

    if current_balance < amount:
        await update.message.reply_text(
            f"❌ **နှုတ်လို့မရပါ!**\n\n"
            f"👤 User ID: `{target_user_id}`\n"
            f"💰 နှုတ်ချင်တဲ့ပမာဏ: `{amount:,} MMK`\n"
            f"💳 User လက်ကျန်ငွေ: `{current_balance:,} MMK`\n"
            f"❗ လိုအပ်သေးတာ: `{amount - current_balance:,} MMK`",
            parse_mode="Markdown"
        )
        return

    # Deduct balance from user
    data["users"][target_user_id]["balance"] -= amount
    save_data(data)

    # Notify user
    try:
        user_msg = (
            f"⚠️ **လက်ကျန်ငွေ နှုတ်ခံရမှု**\n\n"
            f"💰 နှုတ်ခံရတဲ့ပမာဏ: `{amount:,} MMK`\n"
            f"💳 လက်ကျန်ငွေ: `{data['users'][target_user_id]['balance']:,} MMK`\n"
            f"⏰ အချိန်: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            "📞 မေးခွန်းရှိရင် admin ကို ဆက်သွယ်ပါ။"
        )
        await context.bot.send_message(chat_id=int(target_user_id), text=user_msg, parse_mode="Markdown")
    except:
        pass

    # Confirm to admin
    await update.message.reply_text(
        f"✅ **Balance နှုတ်ခြင်း အောင်မြင်ပါပြီ!**\n\n"
        f"👤 User ID: `{target_user_id}`\n"
        f"💰 နှုတ်ခဲ့တဲ့ပမာဏ: `{amount:,} MMK`\n"
        f"💳 User လက်ကျန်ငွေ: `{data['users'][target_user_id]['balance']:,} MMK`",
        parse_mode="Markdown"
    )

async def done_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    # Check if user is any admin
    if not is_admin(user_id):
        await update.message.reply_text("❌ သင်သည် admin မဟုတ်ပါ!")
        return

    args = context.args
    if len(args) != 1 or not args[0].isdigit():
        await update.message.reply_text("❌ မှန်ကန်တဲ့အတိုင်း: /done <user_id>")
        return

    target_user_id = int(args[0])
    try:
        await context.bot.send_message(
            chat_id=target_user_id,
            text="🙏 ဝယ်ယူအားပေးမှုအတွက် ကျေးဇူးအများကြီးတင်ပါတယ်။\n\n✅ Order Done! 🎉"
        )
        await update.message.reply_text("✅ User ထံ message ပေးပြီးပါပြီ။")
    except:
        await update.message.reply_text("❌ User ID မှားနေပါတယ်။ Message မပို့နိုင်ပါ။")

async def reply_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    # Check if user is any admin
    if not is_admin(user_id):
        await update.message.reply_text("❌ သင်သည် admin မဟုတ်ပါ!")
        return

    args = context.args
    if len(args) < 2 or not args[0].isdigit():
        await update.message.reply_text("❌ မှန်ကန်တဲ့အတိုင်း: /reply <user_id> <message>")
        return

    target_user_id = int(args[0])
    message = " ".join(args[1:])
    try:
        await context.bot.send_message(
            chat_id=target_user_id,
            text=message
        )
        await update.message.reply_text("✅ Message ပေးပြီးပါပြီ။")
    except:
        await update.message.reply_text("❌ Message မပို့နိုင်ပါ။")

async def authorize_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    # Check if user is any admin
    if not is_admin(user_id):
        await update.message.reply_text("❌ သင်သည် admin မဟုတ်ပါ!")
        return

    args = context.args
    if len(args) != 1 or not args[0].isdigit():
        await update.message.reply_text("❌ မှန်ကန်တဲ့အတိုင်း: /authorize <user_id>")
        return

    target_user_id = args[0]
    load_authorized_users()

    if target_user_id in AUTHORIZED_USERS:
        await update.message.reply_text("ℹ️ User ကို အရင်က authorize လုပ်ထားပြီးပါပြီ။")
        return

    AUTHORIZED_USERS.add(target_user_id)
    save_authorized_users()

    # Clear any restrictions when authorizing
    if target_user_id in user_states:
        del user_states[target_user_id]

    # Notify user
    try:
        await context.bot.send_message(
            chat_id=int(target_user_id),
            text="🎉 **Bot အသုံးပြုခွင့် ရရှိပါပြီ!**\n\n"
                 "✅ Owner က သင့်ကို bot အသုံးပြုခွင့် ပေးပါပြီ။\n\n"
                 "🚀 ယခုအခါ `/start` နှိပ်ပြီး bot ကို အသုံးပြုနိုင်ပါပြီ!"
        )
    except:
        pass

    await update.message.reply_text(
        f"✅ **User Authorize အောင်မြင်ပါပြီ!**\n\n"
        f"👤 User ID: `{target_user_id}`\n"
        f"🎯 Status: Authorized\n"
        f"📝 Total authorized users: {len(AUTHORIZED_USERS)}",
        parse_mode="Markdown"
    )

async def unauthorize_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    # Check if user is any admin
    if not is_admin(user_id):
        await update.message.reply_text("❌ သင်သည် admin မဟုတ်ပါ!")
        return

    args = context.args
    if len(args) != 1 or not args[0].isdigit():
        await update.message.reply_text("❌ မှန်ကန်တဲ့အတိုင်း: /unauthorize <user_id>")
        return

    target_user_id = args[0]
    load_authorized_users()

    if target_user_id not in AUTHORIZED_USERS:
        await update.message.reply_text("ℹ️ User သည် authorize မလုပ်ထားပါ။")
        return

    AUTHORIZED_USERS.remove(target_user_id)
    save_authorized_users()

    # Notify user
    try:
        await context.bot.send_message(
            chat_id=int(target_user_id),
            text="⚠️ **Bot အသုံးပြုခွင့် ရုပ်သိမ်းခံရမှု**\n\n"
                 "❌ Owner က သင့်ရဲ့ bot အသုံးပြုခွင့်ကို ရုပ်သိမ်းလိုက်ပါပြီ။\n\n"
                 "📞 ပြန်လည် အသုံးပြုရန် Owner ကို ဆက်သွယ်ပါ။"
        )
    except:
        pass

    await update.message.reply_text(
        f"✅ **User Unauthorize အောင်မြင်ပါပြီ!**\n\n"
        f"👤 User ID: `{target_user_id}`\n"
        f"🎯 Status: Unauthorized\n"
        f"📝 Total authorized users: {len(AUTHORIZED_USERS)}",
        parse_mode="Markdown"
    )

async def maintenance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    # Check if user is any admin
    if not is_admin(user_id):
        await update.message.reply_text("❌ သင်သည် admin မဟုတ်ပါ!")
        return

    args = context.args
    if len(args) != 2:
        await update.message.reply_text(
            "❌ မှန်ကန်တဲ့အတိုင်း: `/maintenance <feature> <on/off>`\n\n"
            "**Features:**\n"
            "• `orders` - အော်ဒါလုပ်ဆောင်ချက်\n"
            "• `topups` - ငွေဖြည့်လုပ်ဆောင်ချက်\n"
            "• `general` - ယေဘူယျ လုပ်ဆောင်ချက်\n\n"
            "**ဥပမာ:**\n"
            "• `/maintenance orders off`\n"
            "• `/maintenance topups on`"
        )
        return

    feature = args[0].lower()
    status = args[1].lower()

    if feature not in ["orders", "topups", "general"]:
        await update.message.reply_text("❌ Feature မှားနေပါတယ်! orders, topups, general ထဲမှ ရွေးပါ")
        return

    if status not in ["on", "off"]:
        await update.message.reply_text("❌ Status မှားနေပါတယ်! on သို့မဟုတ် off ရွေးပါ")
        return

    bot_maintenance[feature] = (status == "on")

    status_text = "🟢 ဖွင့်ထား" if status == "on" else "🔴 ပိတ်ထား"
    feature_text = {
        "orders": "အော်ဒါလုပ်ဆောင်ချက်",
        "topups": "ငွေဖြည့်လုပ်ဆောင်ချက်", 
        "general": "ယေဘူယျလုပ်ဆောင်ချက်"
    }

    await update.message.reply_text(
        f"✅ **Maintenance Mode ပြောင်းလဲပါပြီ!**\n\n"
        f"🔧 Feature: {feature_text[feature]}\n"
        f"📊 Status: {status_text}\n\n"
        f"**လက်ရှိ Maintenance Status:**\n"
        f"• အော်ဒါများ: {'🟢 ဖွင့်ထား' if bot_maintenance['orders'] else '🔴 ပိတ်ထား'}\n"
        f"• ငွေဖြည့်များ: {'🟢 ဖွင့်ထား' if bot_maintenance['topups'] else '🔴 ပိတ်ထား'}\n"
        f"• ယေဘူယျ: {'🟢 ဖွင့်ထား' if bot_maintenance['general'] else '🔴 ပိတ်ထား'}",
        parse_mode="Markdown"
    )

async def setprice_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    # Check if user is any admin
    if not is_admin(user_id):
        await update.message.reply_text("❌ သင်သည် admin မဟုတ်ပါ!")
        return

    args = context.args
    if len(args) != 2:
        await update.message.reply_text(
            "❌ မှန်ကန်တဲ့အတိုင်း: `/setprice <item> <price>`\n\n"
            "**ဥပမာ:**\n"
            "• `/setprice wp1 7000`\n"
            "• `/setprice 86 5500`\n"
            "• `/setprice 12976 750000`"
        )
        return

    item = args[0]
    try:
        price = int(args[1])
        if price < 0:
            await update.message.reply_text("❌ ဈေးနှုန်း သုညထက် ကြီးရမည်!")
            return
    except ValueError:
        await update.message.reply_text("❌ ဈေးနှုန်း ကိန်းဂဏန်းဖြင့် ထည့်ပါ!")
        return

    custom_prices = load_prices()
    custom_prices[item] = price
    save_prices(custom_prices)

    await update.message.reply_text(
        f"✅ **ဈေးနှုန်း ပြောင်းလဲပါပြီ!**\n\n"
        f"💎 Item: `{item}`\n"
        f"💰 New Price: `{price:,} MMK`\n\n"
        f"📝 Users တွေ `/price` နဲ့ အသစ်တွေ့မယ်။",
        parse_mode="Markdown"
    )

async def removeprice_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    # Check if user is any admin
    if not is_admin(user_id):
        await update.message.reply_text("❌ သင်သည် admin မဟုတ်ပါ!")
        return

    args = context.args
    if len(args) != 1:
        await update.message.reply_text(
            "❌ မှန်ကန်တဲ့အတိုင်း: `/removeprice <item>`\n\n"
            "**ဥပမာ:** `/removeprice wp1`"
        )
        return

    item = args[0]             
    custom_prices = load_prices()
    
    if item not in custom_prices:                
        await update.message.reply_text(f"❌ `{item}` မှာ custom price မရှိပါ!")
        return

    del custom_prices[item]
    save_prices(custom_prices)

    await update.message.reply_text(
        f"✅ **Custom Price ဖျက်ပါပြီ!**\n\n"
        f"💎 Item: `{item}`\n"
        f"🔄 Default price ကို ပြန်သုံးပါမယ်။",
        parse_mode="Markdown"
    )

async def setwavenum_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    # Check if user is any admin
    if not is_admin(user_id):
        await update.message.reply_text("❌ သင်သည် admin မဟုတ်ပါ!")
        return

    args = context.args
    if len(args) != 1:
        await update.message.reply_text(
            "❌ မှန်ကန်တဲ့ format: `/setwavenum <phone_number>`\n\n"
            "**ဥပမာ**: `/setwavenum 09123456789`"
        )
        return

    new_number = args[0]
    payment_info["wave_number"] = new_number

    await update.message.reply_text(
        f"✅ **Wave နံပါတ် ပြောင်းလဲပါပြီ!**\n\n"
        f"📱 အသစ်: `{new_number}`\n\n"
        f"💳 လက်ရှိ Wave ငွေလွှဲ အချက်အလက်:\n"
        f"📱 နံပါတ်: `{payment_info['wave_number']}`\n"
        f"👤 နာမည်: {payment_info['wave_name']}",
        parse_mode="Markdown"
    )

async def setkpaynum_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    # Check if user is any admin
    if not is_admin(user_id):
        await update.message.reply_text("❌ သင်သည် admin မဟုတ်ပါ!")
        return

    args = context.args
    if len(args) != 1:
        await update.message.reply_text(
            "❌ မှန်ကန်တဲ့ format: `/setkpaynum <phone_number>`\n\n"
            "**ဥပမာ**: `/setkpaynum 09123456789`"
        )
        return

    new_number = args[0]
    payment_info["kpay_number"] = new_number

    await update.message.reply_text(
        f"✅ **KPay နံပါတ် ပြောင်းလဲပါပြီ!**\n\n"
        f"📱 အသစ်: `{new_number}`\n\n"
        f"💳 လက်ရှိ KPay ငွေလွှဲ အချက်အလက်:\n"
        f"📱 နံပါတ်: `{payment_info['kpay_number']}`\n"
        f"👤 နာမည်: {payment_info['kpay_name']}",
        parse_mode="Markdown"
    )

async def setwavename_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    # Check if user is any admin
    if not is_admin(user_id):
        await update.message.reply_text("❌ သင်သည် admin မဟုတ်ပါ!")
        return

    args = context.args
    if len(args) < 1:
        await update.message.reply_text(
            "❌ မှန်ကန်တဲ့ format: `/setwavename <name>`\n\n"
            "**ဥပမာ**: `/setwavename Ma Thidar Win`"
        )
        return

    new_name = " ".join(args)
    payment_info["wave_name"] = new_name

    await update.message.reply_text(
        f"✅ **Wave နာမည် ပြောင်းလဲပါပြီ!**\n\n"
        f"👤 အသစ်: {new_name}\n\n"
        f"💳 လက်ရှိ Wave ငွေလွှဲ အချက်အလက်:\n"
        f"📱 နံပါတ်: `{payment_info['wave_number']}`\n"
        f"👤 နာမည်: {payment_info['wave_name']}",
        parse_mode="Markdown"
    )

async def setkpayname_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    # Check if user is any admin
    if not is_admin(user_id):
        await update.message.reply_text("❌ သင်သည် admin မဟုတ်ပါ!")
        return

    args = context.args
    if len(args) < 1:
        await update.message.reply_text(
            "❌ မှန်ကန်တဲ့ format: `/setkpayname <name>`\n\n"
            "**ဥပမာ**: `/setkpayname Ma Thidar Win`"
        )
        return

    new_name = " ".join(args)
    payment_info["kpay_name"] = new_name

    await update.message.reply_text(
        f"✅ **KPay နာမည် ပြောင်းလဲပါပြီ!**\n\n"
        f"👤 အသစ်: {new_name}\n\n"
        f"💳 လက်ရှိ KPay ငွေလွှဲ အချက်အလက်:\n"
        f"📱 နံပါတ်: `{payment_info['kpay_number']}`\n"
        f"👤 နာမည်: {payment_info['kpay_name']}",
        parse_mode="Markdown"
    )

async def setkpayqr_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    # Only owner can set payment QR
    if not is_owner(user_id):
        await update.message.reply_text("❌ Owner သာ payment QR ထည့်နိုင်ပါတယ်!")
        return

    # Check if message is a reply to a photo
    if not update.message.reply_to_message or not update.message.reply_to_message.photo:
        await update.message.reply_text(
            "❌ ပုံကို reply လုပ်ပြီး `/setkpayqr` command သုံးပါ\n\n"
            "**အဆင့်များ**:\n"
            "1. KPay QR code ပုံကို ပို့ပါ\n"
            "2. ပုံကို reply လုပ်ပါ\n"
            "3. `/setkpayqr` ရိုက်ပါ"
        )
        return

    photo = update.message.reply_to_message.photo[-1].file_id
    payment_info["kpay_image"] = photo

    await update.message.reply_text(
        "✅ **KPay QR Code ထည့်သွင်းပြီးပါပြီ!**\n\n"
        "📱 Users တွေ topup လုပ်တဲ့အခါ ဒီ QR code ကို မြင်ရပါမယ်။\n\n"
        "🗑️ ဖျက်ရန်: `/removekpayqr`",
        parse_mode="Markdown"
    )

async def removekpayqr_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    # Only owner can remove payment QR
    if not is_owner(user_id):
        await update.message.reply_text("❌ Owner သာ payment QR ဖျက်နိုင်ပါတယ်!")
        return

    if not payment_info.get("kpay_image"):
        await update.message.reply_text("ℹ️ KPay QR code မရှိသေးပါ။")
        return

    payment_info["kpay_image"] = None

    await update.message.reply_text(
        "✅ **KPay QR Code ဖျက်ပြီးပါပြီ!**\n\n"
        "📝 Users တွေ number သာ မြင်ရပါမယ်။",
        parse_mode="Markdown"
    )

async def setwaveqr_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    # Only owner can set payment QR
    if not is_owner(user_id):
        await update.message.reply_text("❌ Owner သာ payment QR ထည့်နိုင်ပါတယ်!")
        return

    # Check if message is a reply to a photo
    if not update.message.reply_to_message or not update.message.reply_to_message.photo:
        await update.message.reply_text(
            "❌ ပုံကို reply လုပ်ပြီး `/setwaveqr` command သုံးပါ\n\n"
            "**အဆင့်များ**:\n"
            "1. Wave QR code ပုံကို ပို့ပါ\n"
            "2. ပုံကို reply လုပ်ပါ\n"
            "3. `/setwaveqr` ရိုက်ပါ"
        )
        return

    photo = update.message.reply_to_message.photo[-1].file_id
    payment_info["wave_image"] = photo

    await update.message.reply_text(
        "✅ **Wave QR Code ထည့်သွင်းပြီးပါပြီ!**\n\n"
        "📱 Users တွေ topup လုပ်တဲ့အခါ ဒီ QR code ကို မြင်ရပါမယ်။\n\n"
        "🗑️ ဖျက်ရန်: `/removewaveqr`",
        parse_mode="Markdown"
    )

async def removewaveqr_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    # Only owner can remove payment QR
    if not is_owner(user_id):
        await update.message.reply_text("❌ Owner သာ payment QR ဖျက်နိုင်ပါတယ်!")
        return

    if not payment_info.get("wave_image"):
        await update.message.reply_text("ℹ️ Wave QR code မရှိသေးပါ။")
        return

    payment_info["wave_image"] = None

    await update.message.reply_text(
        "✅ **Wave QR Code ဖျက်ပြီးပါပြီ!**\n\n"
        "📝 Users တွေ number သာ မြင်ရပါမယ်။",
        parse_mode="Markdown"
    )


def is_owner(user_id):
    """Check if user is the owner"""
    return int(user_id) == ADMIN_ID

def is_admin(user_id):
    """Check if user is any admin (owner or appointed admin)"""
    data = load_data()
    admin_list = data.get("admin_ids", [ADMIN_ID])
    return int(user_id) in admin_list

async def addadm_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    # Only owner can add admins
    if not is_owner(user_id):
        await update.message.reply_text("❌ Owner သာ admin ခန့်အပ်နိုင်ပါတယ်!")
        return

    args = context.args
    if len(args) != 1 or not args[0].isdigit():
        await update.message.reply_text(
            "❌ မှန်ကန်တဲ့ format: `/addadm <user_id>`\n\n"
            "**ဥပမာ**: `/addadm 123456789`"
        )
        return

    new_admin_id = int(args[0])
    
    # Load data
    data = load_data()
    admin_list = data.get("admin_ids", [ADMIN_ID])
    
    if new_admin_id in admin_list:
        await update.message.reply_text("ℹ️ User သည် admin ဖြစ်နေပြီးပါပြီ။")
        return

    admin_list.append(new_admin_id)
    data["admin_ids"] = admin_list
    save_data(data)

    # Notify new admin
    try:
        await context.bot.send_message(
            chat_id=new_admin_id,
            text="🎉 **Admin ရာထူးရရှိမှု**\n\n"
                 "✅ Owner က သင့်ကို Admin အဖြစ် ခန့်အပ်ပါပြီ။\n\n"
                 "🔧 Admin commands များကို `/adminhelp` နှိပ်၍ ကြည့်နိုင်ပါတယ်။\n\n"
                 "⚠️ သတိပြုရန်:\n"
                 "• Admin အသစ် ခန့်အပ်လို့ မရပါ\n"
                 "• Admin များကို ဖြုတ်လို့ မရပါ\n"
                 "• ကျန်တဲ့ commands တွေ အသုံးပြုလို့ ရပါတယ်"
        )
    except:
        pass

    await update.message.reply_text(
        f"✅ **Admin ထပ်မံထည့်သွင်းပါပြီ!**\n\n"
        f"👤 User ID: `{new_admin_id}`\n"
        f"🎯 Status: Admin\n"
        f"📝 Total admins: {len(admin_list)}",
        parse_mode="Markdown"
    )

async def unadm_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    # Only owner can remove admins
    if not is_owner(user_id):
        await update.message.reply_text("❌ Owner သာ admin ဖြုတ်နိုင်ပါတယ်!")
        return

    args = context.args
    if len(args) != 1 or not args[0].isdigit():
        await update.message.reply_text(
            "❌ မှန်ကန်တဲ့ format: `/unadm <user_id>`\n\n"
            "**ဥပမာ**: `/unadm 123456789`"
        )
        return

    target_admin_id = int(args[0])
    
    # Cannot remove owner
    if target_admin_id == ADMIN_ID:
        await update.message.reply_text("❌ Owner ကို ဖြုတ်လို့ မရပါ!")
        return
    
    # Load data
    data = load_data()
    admin_list = data.get("admin_ids", [ADMIN_ID])
    
    if target_admin_id not in admin_list:
        await update.message.reply_text("ℹ️ User သည် admin မဟုတ်ပါ။")
        return

    admin_list.remove(target_admin_id)
    data["admin_ids"] = admin_list
    save_data(data)

    # Notify removed admin
    try:
        await context.bot.send_message(
            chat_id=target_admin_id,
            text="⚠️ **Admin ရာထူး ရုပ်သိမ်းခံရမှု**\n\n"
                 "❌ Owner က သင့်ရဲ့ admin ရာထူးကို ရုပ်သိမ်းလိုက်ပါပြီ။\n\n"
                 "📞 အကြောင်းရင်း သိရှိရန် Owner ကို ဆက်သွယ်ပါ။"
        )
    except:
        pass

    await update.message.reply_text(
        f"✅ **Admin ဖြုတ်ခြင်း အောင်မြင်ပါပြီ!**\n\n"
        f"👤 User ID: `{target_admin_id}`\n"
        f"🎯 Status: Removed from Admin\n"
        f"📝 Total admins: {len(admin_list)}",
        parse_mode="Markdown"
    )

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    # Check if user is any admin
    if not is_admin(user_id):
        await update.message.reply_text("❌ သင်သည် admin မဟုတ်ပါ!")
        return

    # Check if message has a photo (reply to photo message)
    if update.message.reply_to_message and update.message.reply_to_message.photo:
        # Get the photo and caption
        photo = update.message.reply_to_message.photo[-1].file_id
        args = context.args
        caption = " ".join(args) if args else update.message.reply_to_message.caption or ""
        
        data = load_data()
        
        # Count successful sends
        user_success = 0
        user_fail = 0
        group_success = 0
        group_fail = 0
        
        broadcast_caption = caption if caption else ""
        
        # Send photo to all authorized users
        for uid in AUTHORIZED_USERS:
            try:
                await context.bot.send_photo(
                    chat_id=int(uid),
                    photo=photo,
                    caption=broadcast_caption,
                    parse_mode="Markdown"
                )
                user_success += 1
            except:
                user_fail += 1
        
        # Get all groups where bot is member (from order history)
        group_chats = set()
        for uid, user_data in data["users"].items():
            for order in user_data.get("orders", []):
                chat_id = order.get("chat_id")
                if chat_id and chat_id < 0:  # Negative IDs are groups
                    group_chats.add(chat_id)
        
        # Send photo to all groups
        for chat_id in group_chats:
            try:
                # Check if bot is still admin in the group
                if await is_bot_admin_in_group(context.bot, chat_id):
                    await context.bot.send_photo(
                        chat_id=chat_id,
                        photo=photo,
                        caption=broadcast_caption,
                        parse_mode="Markdown"
                    )
                    group_success += 1
                else:
                    group_fail += 1
            except:
                group_fail += 1
        
        # Report results
        await update.message.reply_text(
            f"✅ **Broadcast (with image) အောင်မြင်ပါပြီ!**\n\n"
            f"👥 Users: {user_success} အောင်မြင်, {user_fail} မအောင်မြင်\n"
            f"👥 Groups: {group_success} အောင်မြင်, {group_fail} မအောင်မြင်\n\n"
            f"📊 စုစုပေါင်း: {user_success + group_success} ပို့ပြီး",
            parse_mode="Markdown"
        )
        return
    
    # Text-only broadcast
    args = context.args
    if len(args) < 1:
        await update.message.reply_text(
            "❌ မှန်ကန်တဲ့ format:\n\n"
            "**Text only**: `/broadcast <message>`\n"
            "**With image**: ပုံကို reply လုပ်ပြီး `/broadcast <caption>` ရေးပါ\n\n"
            "**ဥပမာ**:\n"
            "• `/broadcast Bot maintenance လုပ်နေပါတယ်`\n"
            "• ပုံကို reply လုပ်ပြီး `/broadcast အသစ်တွေ ရောက်ပါပြီ!`"
        )
        return

    message = " ".join(args)
    data = load_data()
    
    # Count successful sends
    user_success = 0
    user_fail = 0
    group_success = 0
    group_fail = 0
    
    # Send to all authorized users
    for uid in AUTHORIZED_USERS:
        try:
            await context.bot.send_message(
                chat_id=int(uid),
                text=message,
                parse_mode="Markdown"
            )
            user_success += 1
        except:
            user_fail += 1
    
    # Get all groups where bot is member (from order history)
    group_chats = set()
    for uid, user_data in data["users"].items():
        for order in user_data.get("orders", []):
            chat_id = order.get("chat_id")
            if chat_id and chat_id < 0:  # Negative IDs are groups
                group_chats.add(chat_id)
    
    # Send to all groups
    for chat_id in group_chats:
        try:
            # Check if bot is still admin in the group
            if await is_bot_admin_in_group(context.bot, chat_id):
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode="Markdown"
                )
                group_success += 1
            else:
                group_fail += 1
        except:
            group_fail += 1
    
    # Report results
    await update.message.reply_text(
        f"✅ **Broadcast အောင်မြင်ပါပြီ!**\n\n"
        f"👥 Users: {user_success} အောင်မြင်, {user_fail} မအောင်မြင်\n"
        f"👥 Groups: {group_success} အောင်မြင်, {group_fail} မအောင်မြင်\n\n"
        f"📊 စုစုပေါင်း: {user_success + group_success} ပို့ပြီး",
        parse_mode="Markdown"
    )

async def adminhelp_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    # Check if user is any admin
    if not is_admin(user_id):
        await update.message.reply_text("❌ သင်သည် admin မဟုတ်ပါ!")
        return

    # Check if user is owner
    is_user_owner = is_owner(user_id)
    
    help_msg = "🔧 **Admin Commands List** 🔧\n\n"
    
    if is_user_owner:
        help_msg += (
            "👑 **Owner Commands:**\n"
            "• `/addadm <user_id>` - Admin ထပ်မံထည့်သွင်း\n"
            "• `/unadm <user_id>` - Admin ဖြုတ်ခြင်း\n\n"
        )
    
    help_msg += (
        "👥 **User Management:**\n"
        "• `/authorize <user_id>` - User အသုံးပြုခွင့်ပေး\n"
        "• `/unauthorize <user_id>` - User အသုံးပြုခွင့်ရုပ်သိမ်း\n\n"
        "💰 **Balance Management:**\n"
        "• `/approve <user_id> <amount>` - Topup approve လုပ်\n"
        "• `/deduct <user_id> <amount>` - Balance နှုတ်ခြင်း\n\n"
        "💬 **Communication:**\n"
        "• `/reply <user_id> <message>` - User ကို message ပို့\n"
        "• `/done <user_id>` - Order complete message ပို့\n"
        "• `/sendgroup <message>` - Admin group ကို message ပို့\n"
        "• `/broadcast <message>` - User အားလုံးနဲ့ Group အားလုံးကို message ပို့\n"
        "• ပုံကို reply လုပ်ပြီး `/broadcast <caption>` - ပုံနဲ့တွဲပို့\n"
        "\n"
        "🔧 **Bot Maintenance:**\n"
        "• `/maintenance <orders/topups/general> <on/off>` - Features ဖွင့်ပိတ်\n\n"
        "💎 **Price Management:**\n"
        "• `/setprice <item> <price>` - Custom price ထည့်\n"
        "• `/removeprice <item>` - Custom price ဖျက်\n\n"
        "💳 **Payment Management:**\n"
        "• `/setwavenum <number>` - Wave နံပါတ် ပြောင်း\n"
        "• `/setkpaynum <number>` - KPay နံပါတ် ပြောင်း\n"
        "• `/setwavename <name>` - Wave နာမည် ပြောင်း\n"
        "• `/setkpayname <name>` - KPay နာမည် ပြောင်း\n\n"
    )
    
    if is_user_owner:
        help_msg += (
            "📱 **Payment QR Management (Owner Only):**\n"
            "• ပုံကို reply လုပ်ပြီး `/setkpayqr` - KPay QR ထည့်\n"
            "• `/removekpayqr` - KPay QR ဖျက်\n"
            "• ပုံကို reply လုပ်ပြီး `/setwaveqr` - Wave QR ထည့်\n"
            "• `/removewaveqr` - Wave QR ဖျက်\n\n"
        )
    
    help_msg += (
        "📊 **Current Status:**\n"
        f"• Orders: {'🟢 Enabled' if bot_maintenance['orders'] else '🔴 Disabled'}\n"
        f"• Topups: {'🟢 Enabled' if bot_maintenance['topups'] else '🔴 Disabled'}\n"
        f"• General: {'🟢 Enabled' if bot_maintenance['general'] else '🔴 Disabled'}\n"
        f"• Authorized Users: {len(AUTHORIZED_USERS)}\n\n"
        f"💳 **Current Payment Info:**\n"
        f"• Wave: {payment_info['wave_number']} ({payment_info['wave_name']})\n"
        f"• KPay: {payment_info['kpay_number']} ({payment_info['kpay_name']})"
    )

    await update.message.reply_text(help_msg, parse_mode="Markdown")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    # Check if user is authorized
    load_authorized_users()
    if not is_user_authorized(user_id):
        return

    # Validate if it's a payment screenshot
    if not is_payment_screenshot(update):
        await update.message.reply_text(
            "❌ **သင့်ပုံ လက်မခံပါ!**\n\n"
            "🔍 Payment screenshot သာ လက်ခံပါတယ်။\n"
            "💳 KPay, Wave လွှဲမှု screenshot များသာ တင်ပေးပါ။\n\n"
            "📷 Payment app ရဲ့ transfer confirmation screenshot ကို တင်ပေးပါ။",
            parse_mode="Markdown"
        )
        return

    if user_id not in pending_topups:
        await update.message.reply_text(
            "❌ **Topup process မရှိပါ!**\n\n"
            "🔄 အရင်ဆုံး `/topup amount` command ကို သုံးပါ။\n"
            "💡 ဥပမာ: `/topup 50000`",
            parse_mode="Markdown"
        )
        return

    pending = pending_topups[user_id]
    amount = pending["amount"]

    # Set user state to restricted
    user_states[user_id] = "waiting_approval"

    # Notify admin about topup request with user profile photo
    admin_msg = (
        f"💳 **ငွေဖြည့်တောင်းဆိုမှု**\n\n"
        f"👤 User: [{update.effective_user.first_name}](tg://user?id={user_id})\n"
        f"🆔 User ID: `{user_id}`\n"
        f"💰 Amount: `{amount:,} MMK`\n"
        f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"Screenshot ပါ ပါပါတယ်။ Approve လုပ်ရန်:\n"
        f"`/approve {user_id} {amount}`"
    )

    try:
        # Try to send user's profile photo first
        try:
            user_photos = await context.bot.get_user_profile_photos(user_id=int(user_id), limit=1)
            if user_photos.total_count > 0:
                await context.bot.send_photo(
                    chat_id=ADMIN_ID,
                    photo=user_photos.photos[0][0].file_id,
                    caption=admin_msg,
                    parse_mode="Markdown"
                )
            else:
                await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, parse_mode="Markdown")
        except:
            await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, parse_mode="Markdown")
        
        # Forward payment screenshot
        await context.bot.forward_message(
            chat_id=ADMIN_ID,
            from_chat_id=update.effective_chat.id,
            message_id=update.message.message_id
        )
    except:
        pass

    # Save topup request first
    data = load_data()
    if user_id not in data["users"]:
        data["users"][user_id] = {"name": "", "username": "", "balance": 0, "orders": [], "topups": []}

    topup_request = {
        "amount": amount,
        "status": "pending",
        "timestamp": datetime.now().isoformat()
    }
    data["users"][user_id]["topups"].append(topup_request)
    save_data(data)

    # Notify admin group
    await notify_group_topup(topup_request, update.effective_user.first_name or "Unknown", user_id)

    del pending_topups[user_id]

    await update.message.reply_text(
        f"✅ **Screenshot လက်ခံပါပြီ!**\n\n"
        f"💰 ပမာဏ: `{amount:,} MMK`\n"
        f"⏰ အချိန်: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        "🔒 **အသုံးပြုမှု ယာယီ ကန့်သတ်ပါ**\n"
        "❌ Screenshot ပို့ပြီးပါပြီ။ Admin က လက်ခံပြီးကြောင်း အတည်ပြုတဲ့အထိ:\n\n"
        "❌ Commands အသုံးပြုလို့ မရပါ\n"
        "❌ စာသား ပို့လို့ မရပါ\n"
        "❌ Voice, Sticker, GIF, Video ပို့လို့ မရပါ\n"
        "❌ Emoji ပို့လို့ မရပါ\n\n"
        "⏰ Admin က approve လုပ်ပြီးမှ ပြန်လည် အသုံးပြုနိုင်ပါမယ်။\n"
        "📞 ပြဿနာရှိရင် admin ကို ဆက်သွယ်ပါ။",
        parse_mode="Markdown"
    )

async def send_to_group_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    # Check if user is any admin
    if not is_admin(user_id):
        await update.message.reply_text("❌ သင်သည် admin မဟုတ်ပါ!")
        return

    args = context.args
    if len(args) < 1:
        await update.message.reply_text(
            "❌ မှန်ကန်တဲ့အတိုင်း: /sendgroup <message>\n"
            "**ဥပမာ**: `/sendgroup Bot test လုပ်နေပါတယ်`"
        )
        return

    message = " ".join(args)

    try:
        await context.bot.send_message(
            chat_id=ADMIN_GROUP_ID,
            text=f"📢 **Admin Message**\n\n{message}",
            parse_mode="Markdown"
        )
        await update.message.reply_text("✅ Group ထဲကို message ပေးပြီးပါပြီ။")
    except Exception as e:
        await update.message.reply_text(f"❌ Group ထဲကို message မပို့နိုင်ပါ။\nError: {str(e)}")

async def notify_group_order(order_data, user_name, user_id):
    """Notify admin group about new order"""
    try:
        bot = Bot(token=BOT_TOKEN)
        message = (
            f"🛒 **အော်ဒါအသစ် ရောက်ပါပြီ!**\n\n"
            f"📝 Order ID: `{order_data['order_id']}`\n"
            f"👤 User: [{user_name}](tg://user?id={user_id})\n"
            f"🎮 Game ID: `{order_data['game_id']}`\n"
            f"🌐 Server ID: `{order_data['server_id']}`\n"
            f"💎 Amount: {order_data['amount']}\n"
            f"💰 Price: {order_data['price']:,} MMK\n"
            f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"#NewOrder #MLBB"
        )
        await bot.send_message(chat_id=ADMIN_GROUP_ID, text=message, parse_mode="Markdown")
    except Exception as e:
        print(f"Group notification error: {e}")

async def notify_group_topup(topup_data, user_name, user_id):
    """Notify admin group about new topup request"""
    try:
        bot = Bot(token=BOT_TOKEN)
        message = (
            f"💳 **ငွေဖြည့်တောင်းဆိုမှု**\n\n"
            f"👤 User: [{user_name}](tg://user?id={user_id})\n"
            f"🆔 User ID: `{user_id}`\n"
            f"💰 Amount: `{topup_data['amount']:,} MMK`\n"
            f"⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"Approve လုပ်ရန်: `/approve {user_id} {topup_data['amount']}`\n\n"
            f"#TopupRequest #Payment"
        )
        await bot.send_message(chat_id=ADMIN_GROUP_ID, text=message, parse_mode="Markdown")
    except Exception as e:
        print(f"Group topup notification error: {e}")

async def handle_restricted_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all non-command messages for restricted users"""
    user_id = str(update.effective_user.id)

    # Check if user is authorized first
    load_authorized_users()
    if not is_user_authorized(user_id):
        # For unauthorized users, give AI reply
        if update.message.text:
            reply = simple_reply(update.message.text)
            await update.message.reply_text(reply, parse_mode="Markdown")
        return

    # Check if user is restricted after sending screenshot
    if user_id in user_states and user_states[user_id] == "waiting_approval":
        # Block everything except photos for restricted users
        if update.message.photo:
            await handle_photo(update, context)
            return

        # Block all other content types
        await update.message.reply_text(
            "❌ **အသုံးပြုမှု ကန့်သတ်ထားပါ!**\n\n"
            "🔒 Screenshot ပို့ပြီးပါပြီ။ Admin က လက်ခံပြီးကြောင်း အတည်ပြုတဲ့အထိ:\n\n"
            "❌ Commands အသုံးပြုလို့ မရပါ\n"
            "❌ စာသား ပို့လို့ မရပါ\n"
            "❌ Voice, Sticker, GIF, Video ပို့လို့ မရပါ\n"
            "❌ Emoji ပို့လို့ မရပါ\n\n"
            "⏰ Admin က approve လုပ်ပြီးမှ ပြန်လည် အသုံးပြုနိုင်ပါမယ်။\n"
            "📞 အရေးပေါ်ဆိုရင် admin ကို ဆက်သွယ်ပါ။",
            parse_mode="Markdown"
        )
        return

    # For authorized users, provide simple auto-reply
    if update.message.text:
        reply = simple_reply(update.message.text)
        await update.message.reply_text(reply, parse_mode="Markdown")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = str(query.from_user.id)
    admin_name = query.from_user.first_name or "Admin"

    # Handle order confirm/cancel
    if query.data.startswith("order_confirm_"):
        order_id = query.data.replace("order_confirm_", "")
        data = load_data()
        
        # Check if order already processed
        order_found = False
        target_user_id = None
        order_details = None
        
        for uid, user_data in data["users"].items():
            for order in user_data.get("orders", []):
                if order["order_id"] == order_id:
                    # Check if already processed
                    if order.get("status") in ["confirmed", "cancelled"]:
                        await query.answer("⚠️ Order ကို လုပ်ဆောင်ပြီးပါပြီ!", show_alert=True)
                        # Remove buttons from current message
                        try:
                            await query.edit_message_reply_markup(reply_markup=None)
                        except:
                            pass
                        return
                    
                    order["status"] = "confirmed"
                    order["confirmed_by"] = admin_name
                    order["confirmed_at"] = datetime.now().isoformat()
                    order_found = True
                    target_user_id = uid
                    order_details = order
                    break
            if order_found:
                break
        
        if order_found:
            save_data(data)
            
            # Remove buttons from current admin's message
            try:
                await query.edit_message_text(
                    text=query.message.text.replace("⏳ စောင့်ဆိုင်းနေသည်", "✅ လက်ခံပြီး"),
                    parse_mode="Markdown",
                    reply_markup=None
                )
            except:
                pass
            
            # Notify all other admins and remove their buttons
            admin_list = data.get("admin_ids", [ADMIN_ID])
            for admin_id in admin_list:
                if admin_id != int(user_id):
                    try:
                        if admin_id == ADMIN_ID:
                            notification_msg = (
                                f"✅ **Order Confirmed!**\n\n"
                                f"📝 Order ID: `{order_id}`\n"
                                f"👤 Confirmed by: {admin_name}\n"
                                f"🎮 Game ID: `{order_details['game_id']}`\n"
                                f"🌐 Server ID: `{order_details['server_id']}`\n"
                                f"💎 Amount: {order_details['amount']}\n"
                                f"💰 Price: {order_details['price']:,} MMK\n"
                                f"📊 Status: ✅ လက်ခံပြီး"
                            )
                        else:
                            notification_msg = (
                                f"✅ **Order Confirmed!**\n\n"
                                f"📝 Order ID: `{order_id}`\n"
                                f"🎮 Game ID: `{order_details['game_id']}`\n"
                                f"🌐 Server ID: `{order_details['server_id']}`\n"
                                f"💎 Amount: {order_details['amount']}\n"
                                f"💰 Price: {order_details['price']:,} MMK\n"
                                f"📊 Status: ✅ လက်ခံပြီး"
                            )
                        await context.bot.send_message(
                            chat_id=admin_id,
                            text=notification_msg,
                            parse_mode="Markdown"
                        )
                    except:
                        pass
            
            # Update status in the chat where order was placed
            try:
                chat_id = order_details.get("chat_id", int(target_user_id))
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"✅ **Order လက်ခံပြီးပါပြီ!**\n\n"
                         f"📝 Order ID: `{order_id}`\n"
                         f"👤 User: {data['users'][target_user_id].get('name', 'Unknown')}\n"
                         f"🎮 Game ID: `{order_details['game_id']}`\n"
                         f"🌐 Server ID: `{order_details['server_id']}`\n"
                         f"💎 Amount: {order_details['amount']}\n"
                         f"📊 Status: ✅ လက်ခံပြီး\n\n"
                         "💎 Diamonds များကို 5-30 မိနစ်အတွင်း ရရှိပါမယ်။",
                    parse_mode="Markdown"
                )
            except:
                pass
            
            await query.answer("✅ Order လက်ခံပါပြီ!", show_alert=True)
        else:
            await query.answer("❌ Order မတွေ့ရှိပါ!", show_alert=True)
        return
    
    elif query.data.startswith("order_cancel_"):
        order_id = query.data.replace("order_cancel_", "")
        data = load_data()
        
        # Check if order already processed
        order_found = False
        target_user_id = None
        refund_amount = 0
        order_details = None
        
        for uid, user_data in data["users"].items():
            for order in user_data.get("orders", []):
                if order["order_id"] == order_id:
                    # Check if already processed
                    if order.get("status") in ["confirmed", "cancelled"]:
                        await query.answer("⚠️ Order ကို လုပ်ဆောင်ပြီးပါပြီ!", show_alert=True)
                        # Remove buttons from current message
                        try:
                            await query.edit_message_reply_markup(reply_markup=None)
                        except:
                            pass
                        return
                    
                    order["status"] = "cancelled"
                    order["cancelled_by"] = admin_name
                    order["cancelled_at"] = datetime.now().isoformat()
                    refund_amount = order["price"]
                    order_found = True
                    target_user_id = uid
                    order_details = order
                    # Refund balance
                    data["users"][uid]["balance"] += refund_amount
                    break
            if order_found:
                break
        
        if order_found:
            save_data(data)
            
            # Remove buttons from current admin's message
            try:
                await query.edit_message_text(
                    text=query.message.text.replace("⏳ စောင့်ဆိုင်းနေသည်", "❌ ငြင်းပယ်ပြီး"),
                    parse_mode="Markdown",
                    reply_markup=None
                )
            except:
                pass
            
            # Notify all other admins and remove their buttons
            admin_list = data.get("admin_ids", [ADMIN_ID])
            for admin_id in admin_list:
                if admin_id != int(user_id):
                    try:
                        if admin_id == ADMIN_ID:
                            notification_msg = (
                                f"❌ **Order Cancelled!**\n\n"
                                f"📝 Order ID: `{order_id}`\n"
                                f"👤 Cancelled by: {admin_name}\n"
                                f"🎮 Game ID: `{order_details['game_id']}`\n"
                                f"🌐 Server ID: `{order_details['server_id']}`\n"
                                f"💎 Amount: {order_details['amount']}\n"
                                f"💰 Refunded: {refund_amount:,} MMK\n"
                                f"📊 Status: ❌ ငြင်းပယ်ပြီး"
                            )
                        else:
                            notification_msg = (
                                f"❌ **Order Cancelled!**\n\n"
                                f"📝 Order ID: `{order_id}`\n"
                                f"🎮 Game ID: `{order_details['game_id']}`\n"
                                f"🌐 Server ID: `{order_details['server_id']}`\n"
                                f"💎 Amount: {order_details['amount']}\n"
                                f"💰 Refunded: {refund_amount:,} MMK\n"
                                f"📊 Status: ❌ ငြင်းပယ်ပြီး"
                            )
                        await context.bot.send_message(
                            chat_id=admin_id,
                            text=notification_msg,
                            parse_mode="Markdown"
                        )
                    except:
                        pass
            
            # Update status in the chat where order was placed
            try:
                chat_id = order_details.get("chat_id", int(target_user_id))
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"❌ **Order ငြင်းပယ်ခံရပါပြီ!**\n\n"
                         f"📝 Order ID: `{order_id}`\n"
                         f"👤 User: {data['users'][target_user_id].get('name', 'Unknown')}\n"
                         f"🎮 Game ID: `{order_details['game_id']}`\n"
                         f"🌐 Server ID: `{order_details['server_id']}`\n"
                         f"💎 Amount: {order_details['amount']}\n"
                         f"📊 Status: ❌ ငြင်းပယ်ပြီး\n"
                         f"💰 ငွေပြန်အမ်း: {refund_amount:,} MMK\n\n"
                         "📞 အကြောင်းရင်း သိရှိရန် admin ကို ဆက်သွယ်ပါ။",
                    parse_mode="Markdown"
                )
            except:
                pass
            
            await query.answer("❌ Order ငြင်းပယ်ပြီး ငွေပြန်အမ်းပါပြီ!", show_alert=True)
        else:
            await query.answer("❌ Order မတွေ့ရှိပါ!", show_alert=True)
        return

    # Check if user is restricted
    if user_id in user_states and user_states[user_id] == "waiting_approval":
        await query.answer("❌ Screenshot ပို့ပြီးပါပြီ! Admin approve စောင့်ပါ။", show_alert=True)
        return

    if query.data == "copy_kpay":
        await query.answer(f"📱 KPay Number copied! {payment_info['kpay_number']}", show_alert=True)
        await query.message.reply_text(
            "📱 **KBZ Pay Number**\n\n"
            f"`{payment_info['kpay_number']}`\n\n"
            f"👤 Name: **{payment_info['kpay_name']}**\n"
            "📋 Number ကို အပေါ်မှ copy လုပ်ပါ",
            parse_mode="Markdown"
        )

    elif query.data == "copy_wave":
        await query.answer(f"📱 Wave Number copied! {payment_info['wave_number']}", show_alert=True)
        await query.message.reply_text(
            "📱 **Wave Money Number**\n\n"
            f"`{payment_info['wave_number']}`\n\n"
            f"👤 Name: **{payment_info['wave_name']}**\n"
            "📋 Number ကို အပေါ်မှ copy လုပ်ပါ",
            parse_mode="Markdown"
        )

    elif query.data == "topup_button":
        try:
            keyboard = [
                [InlineKeyboardButton("📱 Copy KPay Number", callback_data="copy_kpay")],
                [InlineKeyboardButton("📱 Copy Wave Number", callback_data="copy_wave")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                text="💳 **ငွေဖြည့်လုပ်ငန်းစဉ်**\n\n"
                     "**အဆင့် 1**: ငွေပမာဏ ရေးပါ\n"
                     "`/topup amount` ဥပမာ: `/topup 50000`\n\n"
                     "**အဆင့် 2**: ငွေလွှဲပါ\n"
                     f"📱 KBZ Pay: `{payment_info['kpay_number']}` ({payment_info['kpay_name']})\n"
                     f"📱 Wave Money: `{payment_info['wave_number']}` ({payment_info['wave_name']})\n\n"
                     "**အဆင့် 3**: Screenshot တင်ပါ\n"
                     "ငွေလွှဲပြီးရင် screenshot ကို ဒီမှာ တင်ပေးပါ။\n\n"
                     "⏰ 24 နာရီအတွင်း confirm လုပ်ပါမယ်။",
                parse_mode="Markdown",
                reply_markup=reply_markup
            )
        except Exception as e:
            # If edit fails, send new message
            keyboard = [
                [InlineKeyboardButton("📱 Copy KPay Number", callback_data="copy_kpay")],
                [InlineKeyboardButton("📱 Copy Wave Number", callback_data="copy_wave")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.message.reply_text(
                text="💳 **ငွေဖြည့်လုပ်ငန်းစဉ်**\n\n"
                     "**အဆင့် 1**: ငွေပမာဏ ရေးပါ\n"
                     "`/topup amount` ဥပမာ: `/topup 50000`\n\n"
                     "**အဆင့် 2**: ငွေလွှဲပါ\n"
                     f"📱 KBZ Pay: `{payment_info['kpay_number']}` ({payment_info['kpay_name']})\n"
                     f"📱 Wave Money: `{payment_info['wave_number']}` ({payment_info['wave_name']})\n\n"
                     "**အဆင့် 3**: Screenshot တင်ပါ\n"
                     "ငွေလွှဲပြီးရင် screenshot ကို ဒီမှာ တင်ပေးပါ။\n\n"
                     "⏰ 24 နာရီအတွင်း confirm လုပ်ပါမယ်။",
                parse_mode="Markdown",
                reply_markup=reply_markup
            )

def main():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN environment variable မရှိပါ!")
        return

    application = Application.builder().token(BOT_TOKEN).build()

    # Load authorized users on startup
    load_authorized_users()

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("mmb", mmb_command))
    application.add_handler(CommandHandler("balance", balance_command))
    application.add_handler(CommandHandler("topup", topup_command))
    application.add_handler(CommandHandler("price", price_command))
    application.add_handler(CommandHandler("history", history_command))


    # Admin commands
    application.add_handler(CommandHandler("approve", approve_command))
    application.add_handler(CommandHandler("deduct", deduct_command))
    application.add_handler(CommandHandler("done", done_command))
    application.add_handler(CommandHandler("reply", reply_command))
    application.add_handler(CommandHandler("authorize", authorize_command))
    application.add_handler(CommandHandler("unauthorize", unauthorize_command))
    application.add_handler(CommandHandler("addadm", addadm_command))
    application.add_handler(CommandHandler("unadm", unadm_command))
    application.add_handler(CommandHandler("sendgroup", send_to_group_command))
    application.add_handler(CommandHandler("maintenance", maintenance_command))
    application.add_handler(CommandHandler("setprice", setprice_command))
    application.add_handler(CommandHandler("removeprice", removeprice_command))
    application.add_handler(CommandHandler("setwavenum", setwavenum_command))
    application.add_handler(CommandHandler("setkpaynum", setkpaynum_command))
    application.add_handler(CommandHandler("setwavename", setwavename_command))
    application.add_handler(CommandHandler("setkpayname", setkpayname_command))
    application.add_handler(CommandHandler("setkpayqr", setkpayqr_command))
    application.add_handler(CommandHandler("removekpayqr", removekpayqr_command))
    application.add_handler(CommandHandler("setwaveqr", setwaveqr_command))
    application.add_handler(CommandHandler("removewaveqr", removewaveqr_command))
    application.add_handler(CommandHandler("adminhelp", adminhelp_command))
    application.add_handler(CommandHandler("broadcast", broadcast_command))

    # Callback query handler
    application.add_handler(CallbackQueryHandler(button_callback))

    # Photo handler (for payment screenshots)
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # Handle all other message types (text, voice, sticker, video, etc.)
    application.add_handler(MessageHandler(
        (filters.TEXT | filters.VOICE | filters.Sticker.ALL | filters.VIDEO | 
         filters.ANIMATION | filters.AUDIO | filters.Document.ALL) & ~filters.COMMAND, 
        handle_restricted_content
    ))

    print("🤖 Bot စတင်နေပါသည် - 24/7 Running Mode")
    print("✅ Orders, Topups နဲ့ AI စလုံးအဆင်သင့်ပါ")
    print("🔧 Admin commands များ အသုံးပြုနိုင်ပါပြီ")
    application.run_polling()

if __name__ == "__main__":
    main()