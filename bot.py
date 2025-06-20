import logging
import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)
from telegram.helpers import escape_markdown
from telegram.error import TelegramError
from urllib.parse import quote

# --- Configuration & Logger Setup ---
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Environment Variables ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")

if not TELEGRAM_BOT_TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN environment variable is not set.")
    raise ValueError("TELEGRAM_BOT_TOKEN is required")

# --- Course Data ---
COURSE_DATA = {
    "course_a": {
        "name": "Ordinary Group",
        "price": 30.00,
        "description": "Get Leaked content, daily updates ✅",
        "features": ["Basic content access", "Daily updates"]
    },
    "course_b": {
        "name": "Standard Group",
        "price": 50.00,
        "description": "Get premium content, daily updates ✅",
        "features": ["Premium content access", "Daily updates", "Priority support"]
    },
    "course_c": {
        "name": "Premium Group 👑",
        "price": 100.00,
        "description": "Get unlimited premium content, daily updates ✅",
        "features": ["Unlimited content access", "Daily updates", "24/7 support", "Exclusive materials"]
    }
}

# --- Utility Functions ---
def create_course_keyboard():
    """Create the main Group selection keyboard."""
    keyboard = [
        [InlineKeyboardButton(
            f"{course['name']} (₹{int(course['price'])}.{int(round((course['price'] - int(course['price'])) * 100)):02d})",
            callback_data=f"select_course_{course_id}"
        )]
        for course_id, course in COURSE_DATA.items()
    ]
    # Add demo button at the bottom
    keyboard.append([InlineKeyboardButton("📸 Show Demo", url="https://t.me/+ukJYiqlkRLYzOTFl")])
    return InlineKeyboardMarkup(keyboard)

def create_course_detail_keyboard(course_id):
    """Create the keyboard for course details view with auto-filled admin contact."""
    course = COURSE_DATA.get(course_id)
    if not course:
        return None

    # URL encode the course details for the deep link
    course_name = quote(course['name'])
    price = course['price']
    features = "|".join([quote(f) for f in course['features']])

    # Create a deep link with pre-filled message
    deep_link = f"https://t.me/{ADMIN_USERNAME}?text="
    message_text = (
        f"Hello Admin,%0A%0A"
        f"I'm interested in the following Group:%0A"
        f"📘 Group: {course_name}%0A"
        f"💰 Price: ₹{price}%0A"
        f"📋 Features: {features}%0A%0A"
        f"Please provide payment details."
    )
    deep_link += message_text

    keyboard = [
        [InlineKeyboardButton("Contact Admin", url=deep_link)],
        [InlineKeyboardButton("⬅️ Back to Groups", callback_data="back_to_groups")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def send_safe_message(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, reply_markup=None, parse_mode=None):
    """
    Safely send a message with proper escaping of special characters.
    Automatically falls back to plain text if formatting fails.
    """
    try:
        if parse_mode == "MarkdownV2":
            escaped_text = escape_markdown(text, version=2)
        elif parse_mode == "HTML":
            escaped_text = text  # HTML escaping is handled by the library
        else:
            escaped_text = text

        if update.callback_query:
            if parse_mode:
                await update.callback_query.edit_message_text(
                    escaped_text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
            else:
                await update.callback_query.edit_message_text(
                    escaped_text,
                    reply_markup=reply_markup
                )
        else:
            if parse_mode:
                await update.message.reply_text(
                    escaped_text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
            else:
                await update.message.reply_text(
                    escaped_text,
                    reply_markup=reply_markup
                )
    except TelegramError as e:
        logger.error(f"Error sending message: {e}")
        # Fallback to plain text if formatting fails
        try:
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    text,
                    reply_markup=reply_markup
                )
            else:
                await update.message.reply_text(
                    text,
                    reply_markup=reply_markup
                )
        except TelegramError as e:
            logger.error(f"Fallback message failed: {e}")
            if update.callback_query:
                await update.callback_query.answer("Sorry, an error occurred. Please try again.")

# --- Handler Functions ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command."""
    welcome_text = "🌟 Welcome to our Premium Bot 📚\n\nSelect a Group below to see its details:"
    await send_safe_message(update, context, welcome_text, reply_markup=create_course_keyboard())

async def show_courses_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the main courses menu."""
    menu_text = "🌟 Welcome to our Premium Bot 📚\n\nSelect a Group below to see its details:"
    await send_safe_message(update, context, menu_text, reply_markup=create_course_keyboard())

async def select_course(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle course selection and show Group details."""
    try:
        query = update.callback_query
        await query.answer()

        course_id = query.data.replace("select_course_", "")
        course = COURSE_DATA.get(course_id)

        if not course:
            await send_safe_message(update, context, "Error: Group information not found.")
            return

        # Store the selected course details in user_data
        context.user_data['selected_course'] = {
            'id': course_id,
            'name': course['name'],
            'price': course['price'],
            'features': course['features']
        }

        # Build the course details message
        features = "\n• ".join(course['features'])
        description = course['description']

        price_text = f"₹{int(course['price'])}.{int(round((course['price'] - int(course['price'])) * 100)):02d}"

        description_text = (
            f"📘 {course['name']} 👑\n\n"
            f"💰 Price: {price_text}\n\n"
            f"📋 Features:\n• {features}\n\n"
            f"📝 Description:\n{description}"
        )

        await send_safe_message(
            update,
            context,
            description_text,
            reply_markup=create_course_detail_keyboard(course_id)
        )
    except Exception as e:
        logger.error(f"Error selecting Group: {e}")
        await send_safe_message(update, context, "Sorry, an error occurred while processing your request.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors Group by updates."""
    logger.error(f"Update {update} caused error {context.error}")
    if update.effective_message:
        await send_safe_message(update, context, "An error occurred. Please try again later.")


async def contact_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the contact admin request."""
    try:
        query = update.callback_query
        await query.answer()

        course_id = query.data.replace("contact_admin_", "")
        course = COURSE_DATA.get(course_id)

        if not course:
            await send_safe_message(update, context, "Error: Group information not found.")
            return

        user = update.effective_user
        user_info = f"User: {user.first_name} {user.last_name or ''} (@{user.username})"

        message_text = (
            f"New course inquiry from {user_info}:\n\n"
            f"📘 Group: {course['name']}\n"
            f"💰 Price: ₹{course['price']}\n"
            f"📋 Features: {', '.join(course['features'])}"
        )

        # Send message to admin
        await context.bot.send_message(
            chat_id=f"@{ADMIN_USERNAME}",
            text=message_text
        )

        # Notify user
        await send_safe_message(
            update,
            context,
            "Your request has been sent to the admin. They will contact you shortly with payment details."
        )

    except Exception as e:
        logger.error(f"Error contacting admin: {e}")
        await send_safe_message(update, context, "Sorry, an error occurred while contacting the admin.")

# --- Main Function ---
def main():
    """Start the bot."""
    try:
        # Create the Application
        application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

        # Add handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CallbackQueryHandler(show_courses_menu, pattern="^back_to_groups$"))
        application.add_handler(CallbackQueryHandler(select_course, pattern=r"^select_course_"))
        application.add_handler(CallbackQueryHandler(contact_admin, pattern=r"^contact_admin_"))

        # Add error handler
        application.add_error_handler(error_handler)

        # Start the Bot
        logger.info("Starting bot...")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception as e:
        logger.critical(f"Fatal error starting bot: {e}")
        raise
if __name__ == "__main__":
    main()
