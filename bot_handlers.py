import logging
from telegram import Update
from telegram.ext import ContextTypes
from config import ADMIN_ID, ADMIN_GROUP_ID, PRICES, WAVE_NUMBER, KPAY_NUMBER

logger = logging.getLogger(__name__)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    welcome_message = (
        f"မင်္ဂလာပါ {user.first_name}! 👋\n\n"
        "ကျွန်ုပ်သည် Telegram Bot တစ်ခုဖြစ်ပါသည်။\n"
        "အောက်ပါ commands များကို အသုံးပြုနိုင်ပါသည်:\n\n"
        "/start - Bot ကို စတင်အသုံးပြုရန်\n"
        "/help - အကူအညီ သိရှိရန်\n\n"
        "သင့်စာတိုများကို ပြန်လည်ပေးပို့ပေးပါမည်! 📩"
    )
    
    try:
        await update.message.reply_text(welcome_message)
        logger.info(f"Start command executed for user {user.id}")
    except Exception as e:
        logger.error(f"Error in start command: {e}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    help_message = (
        "🤖 Bot အကူအညီ\n\n"
        "ရရှိနိုင်သော Commands:\n"
        "/start - Bot ကို စတင်အသုံးပြုရန်\n"
        "/help - ဤအကူအညီမက်ဆေ့ကို ပြသရန်\n\n"
        "📝 Bot အသုံးပြုပုံ:\n"
        "• စာတို တစ်ခုခု ပို့ပါ - Bot က ပြန်လည်ပေးပို့ပေးပါမည်\n"
        "• Commands များသည် / နှင့် စတင်ပါသည်\n\n"
        "🆘 အကူအညီလိုအပ်ပါက admin ထံ ဆက်သွယ်ပါ။"
    )
    
    try:
        await update.message.reply_text(help_message)
        logger.info(f"Help command executed for user {update.effective_user.id}")
    except Exception as e:
        logger.error(f"Error in help command: {e}")

async def echo_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echo the user message with some processing."""
    user_message = update.message.text
    user = update.effective_user
    
    # Simple message processing - echo with additional info
    response_message = (
        f"📨 သင့်စာတို: {user_message}\n\n"
        f"👤 ပို့သူ: {user.first_name}\n"
        f"📊 စာလုံးရေ: {len(user_message)}\n"
        f"📱 စာလုံးအရေအတွက်: {len(user_message.split())}\n\n"
        "✅ မက်ဆေ့ရရှိပြီးပြီ!"
    )
    
    try:
        await update.message.reply_text(response_message)
        logger.info(f"Echoed message from user {user.id}: {user_message[:50]}...")
    except Exception as e:
        logger.error(f"Error echoing message: {e}")

async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show current prices for data packages."""
    price_message = (
        "💰 လက်ရှိ ဈေးနှုန်းများ\n\n"
        f"📊 1GB - {PRICES['1gb']} MMK\n"
        f"📊 2GB - {PRICES['2gb']} MMK\n"
        f"📊 5GB - {PRICES['5gb']} MMK\n"
        f"📊 10GB - {PRICES['10gb']} MMK\n"
        f"📊 Unlimited - {PRICES['unlimited']} MMK\n\n"
        "💳 ငွေပေးချေမှု:\n"
        f"📱 Wave: {WAVE_NUMBER}\n"
        f"📱 KPay: {KPAY_NUMBER}\n\n"
        "🛒 Order လုပ်ရန် /order ကို အသုံးပြုပါ"
    )
    
    try:
        await update.message.reply_text(price_message)
        logger.info(f"Price command executed for user {update.effective_user.id}")
    except Exception as e:
        logger.error(f"Error in price command: {e}")

async def order_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle user orders."""
    user = update.effective_user
    chat = update.effective_chat
    
    order_message = (
        f"🛒 Order တင်ရန်:\n\n"
        "ကျေးဇူးပြု၍ အောက်ပါ format အတိုင်း ပို့ပါ:\n"
        "📋 Package: [1GB/2GB/5GB/10GB/Unlimited]\n"
        "💳 Payment: [Wave/KPay]\n"
        "📞 Phone: 09xxxxxxxxx\n\n"
        "ဥပမာ:\n"
        "Package: 5GB\n"
        "Payment: Wave\n"
        "Phone: 09123456789"
    )
    
    try:
        await update.message.reply_text(order_message)
        logger.info(f"Order command executed for user {user.id}")
    except Exception as e:
        logger.error(f"Error in order command: {e}")

# Admin command functions
async def set_wave(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set Wave number (Admin only)."""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ ခွင့်ပြုချက်မရှိပါ")
        return
    
    if not context.args:
        await update.message.reply_text("❌ Wave နံပါတ် လိုအပ်ပါသည်\nFormat: /setwave 09xxxxxxxxx")
        return
    
    new_wave = context.args[0]
    global WAVE_NUMBER
    WAVE_NUMBER = new_wave
    
    await update.message.reply_text(f"✅ Wave နံပါတ် ပြောင်းလဲပြီး: {new_wave}")
    logger.info(f"Wave number updated to {new_wave} by admin {update.effective_user.id}")

async def set_kpay(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set KPay number (Admin only)."""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ ခွင့်ပြုချက်မရှိပါ")
        return
    
    if not context.args:
        await update.message.reply_text("❌ KPay နံပါတ် လိုအပ်ပါသည်\nFormat: /setkpay 09xxxxxxxxx")
        return
    
    new_kpay = context.args[0]
    global KPAY_NUMBER
    KPAY_NUMBER = new_kpay
    
    await update.message.reply_text(f"✅ KPay နံပါတ် ပြောင်းလဲပြီး: {new_kpay}")
    logger.info(f"KPay number updated to {new_kpay} by admin {update.effective_user.id}")

async def set_price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set package prices (Admin only)."""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ ခွင့်ပြုချက်မရှိပါ")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ Format: /setprice [package] [price]\n"
            "ဥပမာ: /setprice 1gb 600"
        )
        return
    
    package = context.args[0].lower()
    try:
        price = int(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ ဈေးနှုန်း သည် နံပါတ်ဖြစ်ရပါမည်")
        return
    
    if package in PRICES:
        PRICES[package] = price
        await update.message.reply_text(f"✅ {package.upper()} ဈေးနှုန်း {price} MMK သို့ ပြောင်းလဲပြီး")
        logger.info(f"Price updated: {package} = {price} MMK by admin {update.effective_user.id}")
    else:
        await update.message.reply_text(f"❌ Package '{package}' မတွေ့ပါ\nရရှိနိုင်သော packages: {', '.join(PRICES.keys())}")

async def process_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process user order and notify admin."""
    user = update.effective_user
    chat = update.effective_chat
    message_text = update.message.text
    
    # Check if message contains order format
    if "Package:" in message_text and "Payment:" in message_text and "Phone:" in message_text:
        order_info = (
            f"🛒 အသစ် Order ရောက်လာပါပြီ!\n\n"
            f"👤 အမည်: {user.first_name} {user.last_name or ''}\n"
            f"📱 Username: @{user.username or 'N/A'}\n"
            f"🆔 User ID: {user.id}\n"
            f"💬 Chat Type: {'Group' if chat.type == 'group' or chat.type == 'supergroup' else 'Private'}\n\n"
            f"📋 Order Details:\n{message_text}\n\n"
            f"⏰ အချိန်: {update.message.date}"
        )
        
        try:
            # Send to admin group
            await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text=order_info)
            
            # Confirm to user
            confirmation = (
                "✅ သင့် Order ကို လက်ခံရရှိပါပြီ!\n\n"
                "🔄 အတည်ပြုချက်အတွက် မကြာမီ ဆက်သွယ်ပေးပါမည်။\n"
                "📞 အရေးကြီးပါက admin ကို တိုက်ရိုက်ဆက်သွယ်နိုင်ပါသည်။"
            )
            await update.message.reply_text(confirmation)
            
            logger.info(f"Order processed from user {user.id}: {message_text[:50]}...")
            
        except Exception as e:
            logger.error(f"Error processing order: {e}")
            await update.message.reply_text(
                "😔 Order ပို့ရာတွင် ပြဿနာ ဖြစ်ပါသည်။\n"
                "ကျေးဇူးပြု၍ နောက်မှ ထပ်စမ်းကြည့်ပါ။"
            )

async def admin_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show admin commands (Admin only)."""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ ခွင့်ပြုချက်မရှိပါ")
        return
    
    admin_commands = (
        "🔧 Admin Commands:\n\n"
        "/setwave [နံပါတ်] - Wave နံပါတ် ပြောင်းရန်\n"
        "/setkpay [နံပါတ်] - KPay နံပါတ် ပြောင်းရန်\n"
        "/setprice [package] [price] - ဈေးနှုန်း ပြောင်းရန်\n"
        "/adminhelp - Admin commands များ ကြည့်ရန်\n\n"
        "📋 Examples:\n"
        "/setwave 09123456789\n"
        "/setkpay 09987654321\n"
        "/setprice 5gb 2500"
    )
    
    try:
        await update.message.reply_text(admin_commands)
        logger.info(f"Admin help shown to user {update.effective_user.id}")
    except Exception as e:
        logger.error(f"Error in admin help: {e}")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the developer."""
    logger.error(f"Exception while handling an update: {context.error}")
    
    # Try to send error message to user if update is available
    if isinstance(update, Update) and update.effective_message:
        error_message = (
            "😔 တစ်ခုခုမှားယွင်းနေပါသည်။\n"
            "ကျေးဇူးပြု၍ နောက်မှ ထပ်စမ်းကြည့်ပါ။\n\n"
            "🔄 /start ကို နှိပ်၍ ပြန်စတင်နိုင်ပါသည်။"
        )
        
        try:
            await update.effective_message.reply_text(error_message)
        except Exception as e:
            logger.error(f"Error sending error message: {e}")
