import os

# ===== توکن بات (از محیط) =====
TOKEN = os.environ.get("TOKEN")

# ===== دیتابیس (از محیط) =====
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql:///postgres")

# ===== ادمین (از محیط) =====
ADMIN_ID = int(os.environ.get("ADMIN_ID", 5596656149))

# ===== تنظیمات اسم =====
MIN_NAME_LENGTH = 2
MAX_NAME_LENGTH = 20

# ===== نسبت فروش =====
SELL_PRICE_RATIO = 0.5

# ===== کلاس‌ها =====
CLASSES = {
    "warrior": {
        "name": "شوالیه",
        "emoji": "🗡️",
        "hp": 1000,
        "atk": 18,
        "def": 12,
        "spd": 12,
        "lck": 10,
        "color": "danger",
        "desc": "قدرتمند در نبرد نزدیک، همه‌کاره"
    },
    "samurai": {
        "name": "سامورایی",
        "emoji": "⚔️",
        "hp": 1000,
        "atk": 15,
        "def": 10,
        "spd": 22,
        "lck": 12,
        "color": "primary",
        "desc": "سریع و ماهر با کاتانا، ضربات مرگبار",
        "start_level": 3,
        "start_exp": 200
    },
    "assassin": {
        "name": "اساسین",
        "emoji": "🗡️",
        "hp": 800,
        "atk": 10,
        "def": 8,
        "spd": 18,
        "lck": 20,
        "color": "success",
        "desc": "مرگبار در سایه‌ها، شانس بالا برای آیتم"
    },
    "paladin": {
        "name": "پالادین",
        "emoji": "🛡️",
        "hp": 1500,
        "atk": 14,
        "def": 18,
        "spd": 10,
        "lck": 14,
        "color": "primary",
        "desc": "دفاعی و مقدس، زره‌پوش مقاوم"
    }
}

# ===== آیتم‌های اولیه =====
INITIAL_ITEMS = {
    "warrior": {
        "weapons": [("شمشیر آهنی", 1)],
        "armors": [("زره مسی", 1)],
        "consumables": [("پوشن جون لول ۱", 2)]
    },
    "samurai": {
        "weapons": [("کاتانای آهنی", 1)],
        "armors": [("زره چوبی", 1)],
        "consumables": []
    },
    "assassin": {
        "weapons": [("خنجر آهنی", 1)],
        "armors": [("زره پارچه‌ای", 1)],
        "consumables": []
    },
    "paladin": {
        "weapons": [("شمشیر مسی", 1)],
        "armors": [("زره آهنی", 1)],
        "consumables": [("پوشن جون لول ۲", 3)]
    }
}

# ===== اطلاعات آماری آیتم‌ها (×۱۰) =====
ITEM_STATS = {
    "weapon": {
        "شمشیر چوبی": {"atk_bonus": 30, "value": 100},
        "شمشیر برنزی": {"atk_bonus": 60, "value": 200},
        "شمشیر آهنی": {"atk_bonus": 100, "value": 350},
        "شمشیر فولادی": {"atk_bonus": 150, "value": 500},
        "شمشیر مسی": {"atk_bonus": 50, "value": 250},
        "شمشیر الماسی": {"atk_bonus": 200, "value": 800},
        "شمشیر افسانه‌ای": {"atk_bonus": 300, "value": 1500},
        "کاتانای چوبی": {"atk_bonus": 40, "value": 120},
        "کاتانای برنزی": {"atk_bonus": 80, "value": 220},
        "کاتانای آهنی": {"atk_bonus": 120, "value": 380},
        "کاتانای فولادی": {"atk_bonus": 180, "value": 550},
        "کاتانای ماسامونه": {"atk_bonus": 250, "value": 900},
        "کاتانای روح": {"atk_bonus": 350, "value": 1600},
        "خنجر چوبی": {"atk_bonus": 20, "value": 80},
        "خنجر برنزی": {"atk_bonus": 40, "value": 150},
        "خنجر آهنی": {"atk_bonus": 60, "value": 250},
        "خنجر فولادی": {"atk_bonus": 100, "value": 400},
        "خنجر زهرآلود": {"atk_bonus": 150, "value": 700},
        "خنجر خونین": {"atk_bonus": 220, "value": 1400},
        "تبر چوبی": {"atk_bonus": 50, "value": 150},
        "تبر برنزی": {"atk_bonus": 90, "value": 250},
        "تبر آهنی": {"atk_bonus": 140, "value": 400},
        "تبر جنگی": {"atk_bonus": 200, "value": 600},
        "تبر دو لبه": {"atk_bonus": 280, "value": 900},
        "تبر غول‌کش": {"atk_bonus": 400, "value": 1500},
    },
    "armor": {
        "زره پارچه‌ای": {"def_bonus": 0, "value": 150},
        "زره چرمی": {"def_bonus": 30, "value": 200},
        "زره چوبی": {"def_bonus": 20, "value": 250},
        "زره مسی": {"def_bonus": 50, "value": 350},
        "زره برنزی": {"def_bonus": 80, "value": 400},
        "زره آهنی": {"def_bonus": 120, "value": 500},
        "زره فولادی": {"def_bonus": 160, "value": 650},
        "زره نقره‌ای": {"def_bonus": 200, "value": 800},
        "زره طلایی": {"def_bonus": 250, "value": 1000},
        "زره الماسی": {"def_bonus": 300, "value": 1300},
        "زره میتریل": {"def_bonus": 360, "value": 1600},
        "زره آدامانتین": {"def_bonus": 420, "value": 2000},
        "زره اژدها": {"def_bonus": 500, "value": 2500},
        "زره تایتان": {"def_bonus": 600, "value": 3000},
        "زره الهی": {"def_bonus": 750, "value": 4000},
    },
    "consumable": {
        "پوشن جون لول ۱": {"heal_percent": 0.33, "value": 150},
        "پوشن جون لول ۲": {"heal_percent": 0.50, "value": 300},
        "پوشن جون لول ۳": {"heal_percent": 1.00, "value": 450},
    }
}

# ===== آیتم‌های شاپ =====
SHOP_ITEMS = {
    "sword": [
        {"name": "شمشیر چوبی", "price": 1000, "atk_bonus": 30, "req_atk": 5, "desc": "شمشیر ابتدایی برای تمرین"},
        {"name": "شمشیر برنزی", "price": 2000, "atk_bonus": 60, "req_atk": 8, "desc": "شمشیر برنزی با کیفیت متوسط"},
        {"name": "شمشیر آهنی", "price": 3500, "atk_bonus": 100, "req_atk": 10, "desc": "شمشیر آهنی استاندارد", "is_default": True},
        {"name": "شمشیر فولادی", "price": 5000, "atk_bonus": 150, "req_atk": 15, "desc": "شمشیر فولادی محکم و برنده"},
        {"name": "شمشیر الماسی", "price": 8000, "atk_bonus": 200, "req_atk": 20, "desc": "شمشیر الماسی کمیاب و قدرتمند"},
        {"name": "شمشیر افسانه‌ای", "price": 15000, "atk_bonus": 300, "req_atk": 30, "desc": "شمشیر افسانه‌ای با قدرت بی‌نظیر"},
    ],
    "katana": [
        {"name": "کاتانای چوبی", "price": 1200, "atk_bonus": 40, "req_atk": 5, "req_spd": 5, "desc": "کاتانای چوبی برای تمرین"},
        {"name": "کاتانای برنزی", "price": 2200, "atk_bonus": 80, "req_atk": 8, "req_spd": 8, "desc": "کاتانای برنزی با تعادل خوب"},
        {"name": "کاتانای آهنی", "price": 3800, "atk_bonus": 120, "req_atk": 10, "req_spd": 10, "desc": "کاتانای آهنی استاندارد", "is_default": True},
        {"name": "کاتانای فولادی", "price": 5500, "atk_bonus": 180, "req_atk": 15, "req_spd": 15, "desc": "کاتانای فولادی تیز و سریع"},
        {"name": "کاتانای ماسامونه", "price": 9000, "atk_bonus": 250, "req_atk": 22, "req_spd": 18, "desc": "کاتانای افسانه‌ای ماسامونه"},
        {"name": "کاتانای روح", "price": 16000, "atk_bonus": 350, "req_atk": 30, "req_spd": 25, "desc": "کاتانای روحی با قدرت اسرارآمیز"},
    ],
    "dagger": [
        {"name": "خنجر چوبی", "price": 800, "atk_bonus": 20, "req_atk": 3, "req_spd": 5, "desc": "خنجر چوبی سبک"},
        {"name": "خنجر برنزی", "price": 1500, "atk_bonus": 40, "req_atk": 5, "req_spd": 8, "desc": "خنجر برنزی تیز"},
        {"name": "خنجر آهنی", "price": 2500, "atk_bonus": 60, "req_atk": 5, "req_spd": 12, "desc": "خنجر آهنی استاندارد", "is_default": True},
        {"name": "خنجر فولادی", "price": 4000, "atk_bonus": 100, "req_atk": 10, "req_spd": 15, "desc": "خنجر فولادی مقاوم"},
        {"name": "خنجر زهرآلود", "price": 7000, "atk_bonus": 150, "req_atk": 15, "req_spd": 20, "req_lck": 10, "desc": "خنجر آغشته به زهر مرگبار"},
        {"name": "خنجر خونین", "price": 14000, "atk_bonus": 220, "req_atk": 20, "req_spd": 25, "req_lck": 15, "desc": "خنجر خونین با قدرت ویرانگر"},
    ],
    "axe": [
        {"name": "تبر چوبی", "price": 1500, "atk_bonus": 50, "req_atk": 8, "req_spd": 3, "desc": "تبر چوبی سنگین"},
        {"name": "تبر برنزی", "price": 2500, "atk_bonus": 90, "req_atk": 12, "req_spd": 5, "desc": "تبر برنزی محکم"},
        {"name": "تبر آهنی", "price": 4000, "atk_bonus": 140, "req_atk": 15, "req_spd": 5, "desc": "تبر آهنی استاندارد"},
        {"name": "تبر جنگی", "price": 6000, "atk_bonus": 200, "req_atk": 20, "req_spd": 8, "desc": "تبر جنگی سنگین و قدرتمند"},
        {"name": "تبر دو لبه", "price": 9000, "atk_bonus": 280, "req_atk": 25, "req_spd": 10, "desc": "تبر دو لبه با قدرت تخریب بالا"},
        {"name": "تبر غول‌کش", "price": 15000, "atk_bonus": 400, "req_atk": 35, "req_spd": 12, "desc": "تبر افسانه‌ای غول‌کش"},
    ],
    "armors": [
        {"name": "زره پارچه‌ای", "price": 1500, "def_bonus": 0, "req_def": 0, "desc": "زره پارچه‌ای سبک", "is_default": True},
        {"name": "زره چرمی", "price": 2000, "def_bonus": 30, "req_def": 2, "desc": "زره چرمی با دوام"},
        {"name": "زره چوبی", "price": 2500, "def_bonus": 20, "req_def": 3, "desc": "زره چوبی محکم", "is_default": True},
        {"name": "زره مسی", "price": 3500, "def_bonus": 50, "req_def": 5, "desc": "زره مسی استاندارد", "is_default": True},
        {"name": "زره برنزی", "price": 4000, "def_bonus": 80, "req_def": 8, "desc": "زره برنزی مقاوم"},
        {"name": "زره آهنی", "price": 5000, "def_bonus": 120, "req_def": 10, "desc": "زره آهنی سنگین", "is_default": True},
        {"name": "زره فولادی", "price": 6500, "def_bonus": 160, "req_def": 15, "desc": "زره فولادی محکم"},
        {"name": "زره نقره‌ای", "price": 8000, "def_bonus": 200, "req_def": 20, "desc": "زره نقره‌ای کمیاب"},
        {"name": "زره طلایی", "price": 10000, "def_bonus": 250, "req_def": 25, "desc": "زره طلایی مجلل"},
        {"name": "زره الماسی", "price": 13000, "def_bonus": 300, "req_def": 30, "desc": "زره الماسی با ارزش"},
        {"name": "زره میتریل", "price": 16000, "def_bonus": 360, "req_def": 35, "desc": "زره میتریل سبک و محکم"},
        {"name": "زره آدامانتین", "price": 20000, "def_bonus": 420, "req_def": 40, "desc": "زره آدامانتین شکست‌ناپذیر"},
        {"name": "زره اژدها", "price": 25000, "def_bonus": 500, "req_def": 45, "desc": "زره اژدها با قدرت اساطیری"},
        {"name": "زره تایتان", "price": 30000, "def_bonus": 600, "req_def": 50, "desc": "زره تایتان غول‌پیکر"},
        {"name": "زره الهی", "price": 40000, "def_bonus": 750, "req_def": 60, "desc": "زره الهی با قدرت بی‌نهایت"},
    ],
    "consumables": [
        {"name": "پوشن جون لول ۱", "price": 150, "heal_percent": 0.33, "desc": "یک سوم جون رو پر میکنه"},
        {"name": "پوشن جون لول ۲", "price": 300, "heal_percent": 0.50, "desc": "نصف جون رو پر میکنه"},
        {"name": "پوشن جون لول ۳", "price": 450, "heal_percent": 1.00, "desc": "همه جون رو پر میکنه"},
    ]
}

# ===== دسته‌بندی‌ها =====
CATEGORIES = {
    "sword": {"emoji": "⚔️", "name": "شمشیرها", "desc": "تعادل بین قدرت و سرعت، همه‌کاره"},
    "katana": {"emoji": "🗡️", "name": "کاتاناها", "desc": "سریع و مرگبار، نیاز به چابکی دارن"},
    "dagger": {"emoji": "🔪", "name": "خنجرها", "desc": "ضعیف‌ترین اما سریع‌ترین، برای ضربات پنهانی"},
    "axe": {"emoji": "🪓", "name": "تبرها", "desc": "سنگین و قدرتمند، کند اما کشنده"},
    "armor": {"emoji": "🛡️", "name": "زره‌ها", "desc": "محافظت از جان در برابر حملات"},
    "consumable": {"emoji": "🧪", "name": "آیتم‌ها", "desc": "موارد مصرفی برای کمک در ماجراجویی"},
}

# ===== بونوس‌های سلاح‌ها =====
WEAPON_BONUSES = {
    "sword": {
        "name": "زخم عمیق",
        "emoji": "⚔️",
        "type": "deep_wound",
        "chances": {
            "شمشیر چوبی": 0.00,
            "شمشیر برنزی": 0.20,
            "شمشیر آهنی": 0.30,
            "شمشیر فولادی": 0.40,
            "شمشیر الماسی": 0.48,
            "شمشیر افسانه‌ای": 0.60,
        }
    },
    "katana": {
        "name": "ضربه مرگبار",
        "emoji": "🗡️",
        "type": "execute",
        "chances": {
            "کاتانای چوبی": 0.00,
            "کاتانای برنزی": 0.10,
            "کاتانای آهنی": 0.20,
            "کاتانای فولادی": 0.30,
            "کاتانای ماسامونه": 0.40,
            "کاتانای روح": 0.50,
        }
    },
    "dagger": {
        "name": "کریتیکال",
        "emoji": "🔪",
        "type": "critical",
        "chances": {
            "خنجر چوبی": 0.20,
            "خنجر برنزی": 0.30,
            "خنجر آهنی": 0.40,
            "خنجر فولادی": 0.45,
            "خنجر زهرآلود": 0.50,
            "خنجر خونین": 0.55,
        },
        "lifesteal": {
            "خنجر خونین": 0.30
        }
    },
    "axe": {
        "name": "نادیده گرفتن دفاع",
        "emoji": "🪓",
        "type": "armor_pierce",
        "chance": 0.80,
    }
}

# ===== تنظیمات دانجن =====
DUNGEONS = {
    "goblin": {
        "name": "دانجن گابلین‌ها",
        "emoji": "🗡️",
        "description": "گله‌ای از گابلین‌ها به روستاهای اطراف حمله کردن. شوالیه‌ها باید جلوی اونها رو بگیرن!",
        "level_required": 0,
        "stages": 3,
        "enemy_hp": 500,
        "enemy_atk": 250,
        "enemy_def": 10,
        "base_cooldown": 640,
        "base_reward_gold": 1000,
        "base_reward_upgrade": 3,
        "base_reward_exp": 250,
        "drop_items": [
            {"name": "شمشیر مسی", "chance": 0.30, "type": "weapon"},
            {"name": "پوشن جون لول ۱", "chance": 0.20, "type": "consumable"},
            {"name": "زره پارچه‌ای", "chance": 0.15, "type": "armor"}
        ]
    },
    "troll": {
        "name": "دانجن ترول‌ها",
        "emoji": "🪓",
        "description": "ترول‌های غول‌پیکر به کوهستان‌ها حمله کردن. شوالیه‌های شجاع باید جلوی اونها رو بگیرن!",
        "level_required": 8,
        "stages": 4,
        "enemy_hp": 700,
        "enemy_atk": 480,
        "enemy_def": 25,
        "base_cooldown": 940,
        "base_reward_gold": 2000,
        "base_reward_upgrade": 6,
        "base_reward_exp": 500,
        "drop_items": [
            {"name": "شمشیر آهنی", "chance": 0.25, "type": "weapon"},
            {"name": "زره الماسی", "chance": 0.01, "type": "armor"},
            {"name": "پوشن جون لول ۲", "chance": 0.15, "type": "consumable"}
        ]
    }
}
