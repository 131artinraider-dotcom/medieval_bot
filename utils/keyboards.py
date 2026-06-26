from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import CLASSES

def class_selection_keyboard():
    """دکمه‌های انتخاب کلاس با رنگ‌های مختلف"""
    keyboard = []
    
    for key, cls in CLASSES.items():
        btn_text = (
            f"{cls['emoji']} {cls['name']}\n"
            f"❤️{cls['hp']} ⚔️{cls['atk']} 🛡️{cls['def']} "
            f"💨{cls['spd']} 🍀{cls['lck']}"
        )
        keyboard.append([
            InlineKeyboardButton(
                btn_text,
                callback_data=f"class_{key}",
                style=cls.get('color', 'primary')
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton("❌ انصراف", callback_data="cancel_registration", style="danger")
    ])
    
    return InlineKeyboardMarkup(keyboard)

