from dataclasses import dataclass
from config import CLASSES, ITEM_STATS

@dataclass
class PlayerStats:
    hp: int
    max_hp: int
    atk: int
    defense: int
    spd: int
    lck: int
    gold: int = 0
    level: int = 1
    exp: int = 0
    max_exp: int = 100
    upgrade_points: int = 0

@dataclass
class Player:
    user_id: int
    username: str
    character_name: str
    class_key: str
    stats: PlayerStats
    is_registered: bool

    @classmethod
    def from_db_row(cls, row):
        if not row:
            return None
        stats = PlayerStats(
            hp=row['hp'],
            max_hp=row['max_hp'],
            atk=row['atk'],
            defense=row['def'],
            spd=row['spd'],
            lck=row['lck'],
            gold=row['gold'],
            level=row['level'],
            exp=row['exp'],
            max_exp=row.get('max_exp', 100),
            upgrade_points=row.get('upgrade_points', 0)
        )
        return cls(
            user_id=row['user_id'],
            username=row['username'],
            character_name=row['character_name'] or '',
            class_key=row['class'] or '',
            stats=stats,
            is_registered=row['is_registered'] or False
        )

    def get_class_info(self):
        return CLASSES.get(self.class_key, {})

    def get_hp_bar(self, length: int = 15) -> str:
        if self.stats.max_hp <= 0:
            return "░" * length
        filled = int((self.stats.hp / self.stats.max_hp) * length)
        if filled > length:
            filled = length
        empty = length - filled
        return "█" * filled + "░" * empty

    def get_exp_bar(self, length: int = None) -> str:
        """نوار اکس‌پی با تعداد خونه‌های پویا (بر اساس max_exp)"""
        
        # محاسبه تعداد خونه‌ها بر اساس max_exp
        if self.stats.max_exp <= 100:
            length = 10
        elif self.stats.max_exp <= 200:
            length = 12
        elif self.stats.max_exp <= 500:
            length = 15
        elif self.stats.max_exp <= 1000:
            length = 18
        else:
            length = 20
        
        if self.stats.max_exp <= 0:
            return "░" * length
        
        filled = int((self.stats.exp / self.stats.max_exp) * length)
        if filled > length:
            filled = length
        empty = length - filled
        
        return "▓" * filled + "░" * empty

    def get_status_display(self) -> str:
        return (
            f"📜 **وضعیت {self.character_name}**\n\n"
            f"📖 کلاس: {self.get_class_info().get('emoji', '')} {self.get_class_info().get('name', '')}\n\n"
            f"❤️ **جون**: {self.stats.hp} / {self.stats.max_hp}\n"
            f"`{self.get_hp_bar()}`\n\n"
            f"📈 **اکس‌پی**: {self.stats.exp} / {self.stats.max_exp}\n"
            f"`{self.get_exp_bar()}`\n\n"
            f"⭐ **سطح**: {self.stats.level}\n"
            f"💰 **طلا**: {self.stats.gold}\n"
            f"⭐ **آپگرید پوینت**: {self.stats.upgrade_points}\n\n"
            f"⚔️ **قدرت اتک**: {self.stats.atk}\n"
            f"🛡️ **قدرت دفاع**: {self.stats.defense}\n"
            f"💨 **سرعت**: {self.stats.spd}\n"
            f"🍀 **شانس**: {self.stats.lck}\n"
        )


@dataclass
class Item:
    """مدل آیتم - با متد factory برای ساخت از دیتابیس"""
    id: int = None
    user_id: int = None
    item_type: str = ""
    item_name: str = ""
    quantity: int = 0
    level: int = 1
    equipped: bool = False

    @classmethod
    def from_db_row(cls, row) -> 'Item':
        """ساخت آیتم از ردیف دیتابیس"""
        return cls(
            id=row.get('id'),
            user_id=row.get('user_id'),
            item_type=row.get('item_type', ''),
            item_name=row.get('item_name', ''),
            quantity=row.get('quantity', 0),
            level=row.get('level', 1),
            equipped=row.get('equipped', False)
        )

    @classmethod
    def from_db_list(cls, rows: list) -> list:
        """ساخت لیست آیتم‌ها از ردیف‌های دیتابیس"""
        return [cls.from_db_row(dict(row)) for row in rows]

    def get_stats(self):
        return ITEM_STATS.get(self.item_type, {}).get(self.item_name, {})

    def get_display_name(self) -> str:
        if self.item_type == "consumable":
            return f"{self.item_name} (لول {self.level})"
        return self.item_name

    def get_effect_description(self) -> str:
        stats = self.get_stats()
        if self.item_type == "weapon":
            return f"⚔️ +{stats.get('atk_bonus', 0)} اتک"
        elif self.item_type == "armor":
            return f"🛡️ +{stats.get('def_bonus', 0)} دفاع"
        elif self.item_type == "consumable":
            percent = stats.get('heal_percent', 0) * 100
            return f"❤️ {int(percent)}% جون"
        return ""

    def to_dict(self) -> dict:
        """تبدیل به دیکشنری برای ذخیره در دیتابیس"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'item_type': self.item_type,
            'item_name': self.item_name,
            'quantity': self.quantity,
            'level': self.level,
            'equipped': self.equipped
        }

