import asyncpg
from datetime import datetime, timedelta
from config import DATABASE_URL, SHOP_ITEMS, DUNGEONS
from models import Item
import random

# ========================================
# 1. CONNECTION
# ========================================
async def get_db():
    return await asyncpg.connect(DATABASE_URL)

async def init_db():
    conn = await get_db()
    
    # ===== جدول users =====
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            username VARCHAR(100),
            character_name VARCHAR(50),
            class VARCHAR(30),
            hp INTEGER DEFAULT 100,
            max_hp INTEGER DEFAULT 100,
            atk INTEGER DEFAULT 10,
            def INTEGER DEFAULT 5,
            spd INTEGER DEFAULT 10,
            lck INTEGER DEFAULT 5,
            gold INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            exp INTEGER DEFAULT 0,
            max_exp INTEGER DEFAULT 100,
            upgrade_points INTEGER DEFAULT 0,
            hp_level INTEGER DEFAULT 1,
            atk_level INTEGER DEFAULT 1,
            def_level INTEGER DEFAULT 1,
            spd_level INTEGER DEFAULT 1,
            lck_level INTEGER DEFAULT 1,
            total_upgrades INTEGER DEFAULT 0,
            is_registered BOOLEAN DEFAULT FALSE,
            respawn_until TIMESTAMP DEFAULT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    
    # ===== جدول inventory =====
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id SERIAL PRIMARY KEY,
            user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
            item_type VARCHAR(20) NOT NULL,
            item_name VARCHAR(50) NOT NULL,
            quantity INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            equipped BOOLEAN DEFAULT FALSE
        )
    """)
    
    # ===== جدول shop_items =====
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS shop_items (
            id SERIAL PRIMARY KEY,
            item_type VARCHAR(20) NOT NULL,
            category VARCHAR(30),
            item_name VARCHAR(50) NOT NULL UNIQUE,
            price INTEGER NOT NULL,
            level_required_atk INTEGER DEFAULT 0,
            level_required_def INTEGER DEFAULT 0,
            level_required_spd INTEGER DEFAULT 0,
            level_required_lck INTEGER DEFAULT 0,
            atk_bonus INTEGER DEFAULT 0,
            def_bonus INTEGER DEFAULT 0,
            spd_bonus INTEGER DEFAULT 0,
            lck_bonus INTEGER DEFAULT 0,
            heal_percent FLOAT DEFAULT 0,
            description TEXT,
            is_default BOOLEAN DEFAULT FALSE
        )
    """)
    
    # ===== جدول dungeons =====
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS dungeons (
            id SERIAL PRIMARY KEY,
            user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
            dungeon_type VARCHAR(30) NOT NULL,
            stage INTEGER DEFAULT 0,
            current_hp INTEGER DEFAULT 0,
            enemy_hp INTEGER DEFAULT 0,
            is_active BOOLEAN DEFAULT FALSE,
            panel_open BOOLEAN DEFAULT FALSE,
            bleed INTEGER DEFAULT 0,
            cooldown_until TIMESTAMP DEFAULT NOW(),
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    
    # ===== جدول group_members =====
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS group_members (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            chat_id BIGINT NOT NULL,
            joined_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(user_id, chat_id)
        )
    """)
    
    # ===== جدول daily_quests =====
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS daily_quests (
            id SERIAL PRIMARY KEY,
            user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
            quest_date TIMESTAMP DEFAULT NOW(),
            quest_type VARCHAR(30) NOT NULL,
            quest_target INTEGER NOT NULL,
            quest_progress INTEGER DEFAULT 0,
            quest_completed BOOLEAN DEFAULT FALSE,
            quest_reward_gold INTEGER NOT NULL,
            quest_reward_upgrade INTEGER NOT NULL,
            quest_difficulty VARCHAR(20) DEFAULT 'normal',
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    
    # ===== جدول keyword_rewards =====
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS keyword_rewards (
            id SERIAL PRIMARY KEY,
            user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
            last_claim TIMESTAMP DEFAULT NOW(),
            created_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(user_id)
        )
    """)
    
    # ===== جدول duel_requests =====
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS duel_requests (
            id SERIAL PRIMARY KEY,
            chat_id BIGINT NOT NULL,
            creator_id BIGINT NOT NULL,
            creator_name VARCHAR(50),
            amount INTEGER NOT NULL,
            accepted BOOLEAN DEFAULT FALSE,
            winner_id BIGINT DEFAULT NULL,
            message_id INTEGER DEFAULT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    
    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_duel_requests_chat_id ON duel_requests(chat_id)
    """)
    
    # ===== جدول panels (برای قفل پنل) =====
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS panels (
            id SERIAL PRIMARY KEY,
            panel_id VARCHAR(20) UNIQUE NOT NULL,
            user_id BIGINT NOT NULL,
            chat_id BIGINT NOT NULL,
            panel_type VARCHAR(30) NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    
    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_panels_panel_id ON panels(panel_id)
    """)
    
    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_panels_user_id ON panels(user_id, chat_id)
    """)
    
    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_panels_created_at ON panels(created_at)
    """)
    
    # ===== پر کردن shop_items =====
    await init_shop_items(conn)
    
    await conn.close()
    print("✅ جدول‌ها بررسی/ساخته شدند")

async def init_shop_items(conn):
    count = await conn.fetchval("SELECT COUNT(*) FROM shop_items")
    if count > 0:
        return
    
    for category, items in SHOP_ITEMS.items():
        if category == "armors":
            item_type = "armor"
            cat = None
        elif category == "consumables":
            item_type = "consumable"
            cat = None
        else:
            item_type = "weapon"
            cat = category
        
        for item in items:
            await conn.execute("""
                INSERT INTO shop_items (
                    item_type, category, item_name, price,
                    level_required_atk, level_required_def, 
                    level_required_spd, level_required_lck,
                    atk_bonus, def_bonus, spd_bonus, lck_bonus,
                    heal_percent, description, is_default
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
            """,
                item_type,
                cat,
                item.get("name"),
                item.get("price", 0),
                item.get("req_atk", 0),
                item.get("req_def", 0),
                item.get("req_spd", 0),
                item.get("req_lck", 0),
                item.get("atk_bonus", 0),
                item.get("def_bonus", 0),
                item.get("spd_bonus", 0),
                item.get("lck_bonus", 0),
                item.get("heal_percent", 0),
                item.get("desc", ""),
                item.get("is_default", False)
            )
    
    print("✅ آیتم‌های شاپ به دیتابیس اضافه شدند")

# ========================================
# 2. USER FUNCTIONS
# ========================================
async def get_user(user_id: int):
    conn = await get_db()
    user = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
    await conn.close()
    return user

async def create_user(user_id: int, username: str):
    conn = await get_db()
    await conn.execute(
        "INSERT INTO users (user_id, username) VALUES ($1, $2) ON CONFLICT (user_id) DO NOTHING",
        user_id, username
    )
    await conn.close()

async def is_user_registered(user_id: int) -> bool:
    conn = await get_db()
    registered = await conn.fetchval(
        "SELECT is_registered FROM users WHERE user_id = $1",
        user_id
    )
    await conn.close()
    return registered or False

async def register_character(user_id: int, name: str, class_key: str, stats: dict, start_exp: int = 0):
    conn = await get_db()
    await conn.execute("""
        UPDATE users SET
            character_name = $1,
            class = $2,
            hp = $3,
            max_hp = $3,
            atk = $4,
            def = $5,
            spd = $6,
            lck = $7,
            exp = $8,
            is_registered = TRUE
        WHERE user_id = $9
    """, name, class_key, stats['hp'], stats['atk'], 
        stats['def'], stats['spd'], stats['lck'], start_exp, user_id)
    await conn.close()

async def update_user_stats(user_id: int, **kwargs):
    conn = await get_db()
    set_clause = ", ".join([f"{key} = ${i+1}" for i, key in enumerate(kwargs.keys())])
    values = list(kwargs.values()) + [user_id]
    query = f"UPDATE users SET {set_clause} WHERE user_id = ${len(values)}"
    await conn.execute(query, *values)
    await conn.close()

async def update_user_hp(user_id: int, new_hp: int):
    conn = await get_db()
    await conn.execute(
        "UPDATE users SET hp = $1 WHERE user_id = $2",
        new_hp, user_id
    )
    await conn.close()

# ========================================
# 3. INVENTORY FUNCTIONS
# ========================================
async def add_item(user_id: int, item_type: str, item_name: str, quantity: int = 1, level: int = 1):
    conn = await get_db()
    
    existing = await conn.fetchrow(
        "SELECT id, quantity FROM inventory WHERE user_id = $1 AND item_type = $2 AND item_name = $3 AND level = $4",
        user_id, item_type, item_name, level
    )
    
    if existing:
        await conn.execute(
            "UPDATE inventory SET quantity = quantity + $1 WHERE id = $2",
            quantity, existing['id']
        )
    else:
        await conn.execute(
            "INSERT INTO inventory (user_id, item_type, item_name, quantity, level) VALUES ($1, $2, $3, $4, $5)",
            user_id, item_type, item_name, quantity, level
        )
    
    await conn.close()

async def remove_item(user_id: int, item_type: str, item_name: str, quantity: int = 1, level: int = 1):
    conn = await get_db()
    
    existing = await conn.fetchrow(
        "SELECT id, quantity FROM inventory WHERE user_id = $1 AND item_type = $2 AND item_name = $3 AND level = $4",
        user_id, item_type, item_name, level
    )
    
    if existing:
        new_qty = existing['quantity'] - quantity
        if new_qty <= 0:
            await conn.execute("DELETE FROM inventory WHERE id = $1", existing['id'])
        else:
            await conn.execute(
                "UPDATE inventory SET quantity = $1 WHERE id = $2",
                new_qty, existing['id']
            )
    
    await conn.close()

async def get_inventory(user_id: int):
    conn = await get_db()
    items = await conn.fetch(
        "SELECT * FROM inventory WHERE user_id = $1 ORDER BY item_type, item_name",
        user_id
    )
    await conn.close()
    return items

async def get_equipped(user_id: int):
    conn = await get_db()
    equipped = await conn.fetch(
        "SELECT * FROM inventory WHERE user_id = $1 AND equipped = TRUE",
        user_id
    )
    await conn.close()
    return equipped

async def get_item_quantity(user_id: int, item_type: str, item_name: str, level: int = 1) -> int:
    conn = await get_db()
    qty = await conn.fetchval(
        "SELECT quantity FROM inventory WHERE user_id = $1 AND item_type = $2 AND item_name = $3 AND level = $4",
        user_id, item_type, item_name, level
    )
    await conn.close()
    return qty or 0

async def equip_item(user_id: int, item_type: str, item_name: str, level: int = 1):
    conn = await get_db()
    
    can_equip_result = await can_equip_item(user_id, item_name)
    if not can_equip_result["can"]:
        await conn.close()
        return can_equip_result
    
    old_equipped = await conn.fetchrow(
        "SELECT * FROM inventory WHERE user_id = $1 AND item_type = $2 AND equipped = TRUE",
        user_id, item_type
    )
    
    if old_equipped:
        await conn.execute(
            "UPDATE inventory SET equipped = FALSE, quantity = quantity + 1 WHERE id = $1",
            old_equipped['id']
        )
    
    new_item = await conn.fetchrow(
        "SELECT * FROM inventory WHERE user_id = $1 AND item_type = $2 AND item_name = $3 AND level = $4",
        user_id, item_type, item_name, level
    )
    
    if new_item:
        if new_item['quantity'] > 1:
            await conn.execute(
                "UPDATE inventory SET quantity = quantity - 1, equipped = TRUE WHERE id = $1",
                new_item['id']
            )
        else:
            await conn.execute(
                "UPDATE inventory SET quantity = 0, equipped = TRUE WHERE id = $1",
                new_item['id']
            )
    
    await conn.close()
    return {"can": True, "message": f"✅ {item_name} تجهیز شد!"}

async def use_consumable(user_id: int, item_name: str, level: int = 1):
    conn = await get_db()
    
    item = await conn.fetchrow(
        "SELECT * FROM inventory WHERE user_id = $1 AND item_type = 'consumable' AND item_name = $2 AND level = $3",
        user_id, item_name, level
    )
    
    if not item or item['quantity'] <= 0:
        await conn.close()
        return None
    
    new_qty = item['quantity'] - 1
    if new_qty <= 0:
        await conn.execute("DELETE FROM inventory WHERE id = $1", item['id'])
    else:
        await conn.execute(
            "UPDATE inventory SET quantity = $1 WHERE id = $2",
            new_qty, item['id']
        )
    
    await conn.close()
    return item

# ========================================
# 4. SHOP FUNCTIONS
# ========================================
async def get_shop_items_by_category(category: str):
    conn = await get_db()
    items = await conn.fetch(
        "SELECT * FROM shop_items WHERE category = $1 ORDER BY price",
        category
    )
    await conn.close()
    return items

async def get_shop_armors(page: int = 0, per_page: int = 5):
    conn = await get_db()
    offset = page * per_page
    items = await conn.fetch(
        "SELECT * FROM shop_items WHERE item_type = 'armor' ORDER BY price LIMIT $1 OFFSET $2",
        per_page, offset
    )
    total = await conn.fetchval("SELECT COUNT(*) FROM shop_items WHERE item_type = 'armor'")
    await conn.close()
    return items, total

async def get_shop_consumables():
    conn = await get_db()
    items = await conn.fetch(
        "SELECT * FROM shop_items WHERE item_type = 'consumable' ORDER BY price"
    )
    await conn.close()
    return items

async def get_shop_item_by_name(item_name: str):
    conn = await get_db()
    item = await conn.fetchrow(
        "SELECT * FROM shop_items WHERE item_name = $1",
        item_name
    )
    await conn.close()
    return item

async def buy_item(user_id: int, item_name: str):
    conn = await get_db()
    
    shop_item = await conn.fetchrow(
        "SELECT * FROM shop_items WHERE item_name = $1",
        item_name
    )
    
    if not shop_item:
        await conn.close()
        return {"success": False, "message": "❌ آیتم مورد نظر در شاپ موجود نیست!"}
    
    user_gold = await conn.fetchval(
        "SELECT gold FROM users WHERE user_id = $1",
        user_id
    )
    
    if user_gold < shop_item['price']:
        await conn.close()
        return {"success": False, "message": f"❌ سکه کافی نیست! نیاز: {shop_item['price']}، داری: {user_gold}"}
    
    await conn.execute(
        "UPDATE users SET gold = gold - $1 WHERE user_id = $2",
        shop_item['price'], user_id
    )
    
    item_type = shop_item['item_type']
    level = 1
    if "لول" in item_name:
        try:
            level = int(item_name.split("لول")[-1].strip())
        except:
            level = 1
    
    existing = await conn.fetchrow(
        "SELECT id, quantity FROM inventory WHERE user_id = $1 AND item_type = $2 AND item_name = $3 AND level = $4",
        user_id, item_type, item_name, level
    )
    
    if existing:
        await conn.execute(
            "UPDATE inventory SET quantity = quantity + 1 WHERE id = $1",
            existing['id']
        )
    else:
        await conn.execute(
            "INSERT INTO inventory (user_id, item_type, item_name, quantity, level) VALUES ($1, $2, $3, $4, $5)",
            user_id, item_type, item_name, 1, level
        )
    
    new_gold = await conn.fetchval(
        "SELECT gold FROM users WHERE user_id = $1",
        user_id
    )
    
    await conn.close()
    return {
        "success": True,
        "message": f"✅ {item_name} خریداری شد!",
        "new_gold": new_gold,
        "price": shop_item['price']
    }

async def sell_item(user_id: int, item_name: str, level: int = 1):
    conn = await get_db()
    
    inv_item = await conn.fetchrow(
        "SELECT * FROM inventory WHERE user_id = $1 AND item_name = $2 AND level = $3",
        user_id, item_name, level
    )
    
    if not inv_item or inv_item['quantity'] <= 0:
        await conn.close()
        return {"success": False, "message": "❌ این آیتم را نداری!"}
    
    if inv_item['equipped']:
        await conn.close()
        return {"success": False, "message": "❌ نمی‌تونی آیتم تجهیز شده رو بفروشی! اول آنرا تجهیز کن."}
    
    shop_item = await conn.fetchrow(
        "SELECT price FROM shop_items WHERE item_name = $1",
        item_name
    )
    
    if not shop_item:
        await conn.close()
        return {"success": False, "message": "❌ این آیتم قابل فروش نیست!"}
    
    sell_price = int(shop_item['price'] * 0.5)
    
    new_qty = inv_item['quantity'] - 1
    if new_qty <= 0:
        await conn.execute("DELETE FROM inventory WHERE id = $1", inv_item['id'])
    else:
        await conn.execute(
            "UPDATE inventory SET quantity = $1 WHERE id = $2",
            new_qty, inv_item['id']
        )
    
    await conn.execute(
        "UPDATE users SET gold = gold + $1 WHERE user_id = $2",
        sell_price, user_id
    )
    
    new_gold = await conn.fetchval(
        "SELECT gold FROM users WHERE user_id = $1",
        user_id
    )
    
    await conn.close()
    return {
        "success": True,
        "message": f"💰 {item_name} با قیمت {sell_price} سکه فروخته شد!",
        "new_gold": new_gold,
        "sell_price": sell_price
    }

async def can_equip_item(user_id: int, item_name: str) -> dict:
    conn = await get_db()
    
    shop_item = await conn.fetchrow(
        "SELECT * FROM shop_items WHERE item_name = $1",
        item_name
    )
    
    if not shop_item:
        await conn.close()
        return {"can": False, "message": "❌ آیتم نامعتبر!"}
    
    user = await conn.fetchrow(
        "SELECT atk, def, spd, lck FROM users WHERE user_id = $1",
        user_id
    )
    
    await conn.close()
    
    requirements = []
    
    if shop_item['level_required_atk'] > 0:
        if user['atk'] < shop_item['level_required_atk']:
            requirements.append(f"⚔️ اتک: نیاز {shop_item['level_required_atk']}، داری {user['atk']}")
    
    if shop_item['level_required_def'] > 0:
        if user['def'] < shop_item['level_required_def']:
            requirements.append(f"🛡️ دفاع: نیاز {shop_item['level_required_def']}، داری {user['def']}")
    
    if shop_item['level_required_spd'] > 0:
        if user['spd'] < shop_item['level_required_spd']:
            requirements.append(f"💨 سرعت: نیاز {shop_item['level_required_spd']}، داری {user['spd']}")
    
    if shop_item['level_required_lck'] > 0:
        if user['lck'] < shop_item['level_required_lck']:
            requirements.append(f"🍀 شانس: نیاز {shop_item['level_required_lck']}، داری {user['lck']}")
    
    if requirements:
        return {
            "can": False,
            "message": "❌ لول‌هات برای تجهیز این آیتم کافی نیست:\n" + "\n".join(requirements)
        }
    
    return {"can": True, "message": "✅ می‌تونی این آیتم رو تجهیز کنی!"}

async def get_sellable_items(user_id: int, item_type: str):
    conn = await get_db()
    items = await conn.fetch(
        "SELECT * FROM inventory WHERE user_id = $1 AND item_type = $2 AND equipped = FALSE AND quantity > 0",
        user_id, item_type
    )
    await conn.close()
    return items

# ========================================
# 5. DUNGEON FUNCTIONS
# ========================================
async def start_dungeon(user_id: int, dungeon_type: str):
    conn = await get_db()
    
    active = await conn.fetchval(
        "SELECT id FROM dungeons WHERE user_id = $1 AND is_active = TRUE",
        user_id
    )
    
    if active:
        await conn.close()
        return False
    
    await conn.execute(
        "DELETE FROM dungeons WHERE user_id = $1",
        user_id
    )
    
    dungeon_data = DUNGEONS.get(dungeon_type)
    if not dungeon_data:
        await conn.close()
        return False
    
    user = await conn.fetchrow(
        "SELECT hp, max_hp, atk, def, spd, lck FROM users WHERE user_id = $1",
        user_id
    )
    
    if not user:
        await conn.close()
        return False
    
    await conn.execute("""
        INSERT INTO dungeons (
            user_id, dungeon_type, stage, 
            current_hp, enemy_hp, is_active, cooldown_until
        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
    """,
        user_id, dungeon_type, 1,
        user['hp'], dungeon_data['enemy_hp'], True,
        datetime.now() + timedelta(seconds=dungeon_data['base_cooldown'])
    )
    
    await conn.close()
    return True

async def get_dungeon(user_id: int):
    conn = await get_db()
    dungeon = await conn.fetchrow(
        "SELECT * FROM dungeons WHERE user_id = $1 AND is_active = TRUE",
        user_id
    )
    await conn.close()
    return dungeon

async def update_dungeon_hp(user_id: int, current_hp: int, enemy_hp: int):
    conn = await get_db()
    await conn.execute(
        "UPDATE dungeons SET current_hp = $1, enemy_hp = $2 WHERE user_id = $3 AND is_active = TRUE",
        current_hp, enemy_hp, user_id
    )
    await conn.close()

async def update_dungeon_stage(user_id: int, stage: int):
    conn = await get_db()
    await conn.execute(
        "UPDATE dungeons SET stage = $1 WHERE user_id = $2 AND is_active = TRUE",
        stage, user_id
    )
    await conn.close()

async def end_dungeon(user_id: int):
    conn = await get_db()
    await conn.execute(
        "UPDATE dungeons SET is_active = FALSE WHERE user_id = $1",
        user_id
    )
    await conn.close()

async def get_cooldown_remaining(user_id: int, dungeon_type: str) -> int:
    conn = await get_db()
    cooldown_until = await conn.fetchval(
        "SELECT cooldown_until FROM dungeons WHERE user_id = $1 AND dungeon_type = $2 ORDER BY created_at DESC LIMIT 1",
        user_id, dungeon_type
    )
    await conn.close()
    
    if cooldown_until:
        remaining = (cooldown_until - datetime.now()).total_seconds()
        return max(0, int(remaining))
    return 0

async def add_upgrade_points(user_id: int, amount: int):
    conn = await get_db()
    await conn.execute(
        "UPDATE users SET upgrade_points = upgrade_points + $1 WHERE user_id = $2",
        amount, user_id
    )
    await conn.close()

async def add_item_to_inventory(user_id: int, item_name: str, item_type: str):
    conn = await get_db()
    
    level = 1
    if "لول" in item_name:
        try:
            level = int(item_name.split("لول")[-1].strip())
        except:
            level = 1
    
    existing = await conn.fetchrow(
        "SELECT id, quantity FROM inventory WHERE user_id = $1 AND item_type = $2 AND item_name = $3 AND level = $4",
        user_id, item_type, item_name, level
    )
    
    if existing:
        await conn.execute(
            "UPDATE inventory SET quantity = quantity + 1 WHERE id = $1",
            existing['id']
        )
    else:
        await conn.execute(
            "INSERT INTO inventory (user_id, item_type, item_name, quantity, level) VALUES ($1, $2, $3, $4, $5)",
            user_id, item_type, item_name, 1, level
        )
    
    await conn.close()

async def check_active_dungeon(user_id: int) -> bool:
    conn = await get_db()
    dungeon = await conn.fetchval(
        "SELECT id FROM dungeons WHERE user_id = $1 AND is_active = TRUE",
        user_id
    )
    await conn.close()
    return dungeon is not None

async def set_bleed(user_id: int, amount: int):
    conn = await get_db()
    await conn.execute(
        "UPDATE dungeons SET bleed = $1 WHERE user_id = $2 AND is_active = TRUE",
        amount, user_id
    )
    await conn.close()

async def get_bleed(user_id: int) -> int:
    conn = await get_db()
    bleed = await conn.fetchval(
        "SELECT bleed FROM dungeons WHERE user_id = $1 AND is_active = TRUE",
        user_id
    )
    await conn.close()
    return bleed or 0

async def clear_bleed(user_id: int):
    conn = await get_db()
    await conn.execute(
        "UPDATE dungeons SET bleed = 0 WHERE user_id = $1 AND is_active = TRUE",
        user_id
    )
    await conn.close()

# ========================================
# 6. RESPAWN FUNCTIONS
# ========================================
async def player_died(user_id: int):
    conn = await get_db()
    
    await conn.execute(
        "UPDATE dungeons SET is_active = FALSE WHERE user_id = $1",
        user_id
    )
    
    max_hp = await conn.fetchval(
        "SELECT max_hp FROM users WHERE user_id = $1",
        user_id
    )
    
    if not max_hp:
        max_hp = 100
    
    half_hp = max_hp // 2
    if half_hp < 1:
        half_hp = 1
    
    respawn_time = datetime.now() + timedelta(seconds=3600)
    
    await conn.execute(
        "UPDATE users SET respawn_until = $1, hp = $2 WHERE user_id = $3",
        respawn_time, half_hp, user_id
    )
    
    await conn.close()

async def check_respawn(user_id: int):
    conn = await get_db()
    
    respawn_until = await conn.fetchval(
        "SELECT respawn_until FROM users WHERE user_id = $1",
        user_id
    )
    
    if respawn_until:
        if isinstance(respawn_until, str):
            respawn_until = datetime.fromisoformat(respawn_until)
        
        if datetime.now() >= respawn_until:
            max_hp = await conn.fetchval(
                "SELECT max_hp FROM users WHERE user_id = $1",
                user_id
            )
            
            if not max_hp:
                max_hp = 100
            
            await conn.execute(
                "UPDATE users SET respawn_until = NULL, hp = $1 WHERE user_id = $2",
                max_hp, user_id
            )
            
            await conn.close()
            return True
    
    await conn.close()
    return False

async def is_player_dead(user_id: int) -> bool:
    conn = await get_db()
    respawn_until = await conn.fetchval(
        "SELECT respawn_until FROM users WHERE user_id = $1",
        user_id
    )
    await conn.close()
    
    if respawn_until:
        if isinstance(respawn_until, str):
            respawn_until = datetime.fromisoformat(respawn_until)
        if datetime.now() < respawn_until:
            return True
    return False

async def get_respawn_time(user_id: int) -> int:
    conn = await get_db()
    respawn_until = await conn.fetchval(
        "SELECT respawn_until FROM users WHERE user_id = $1",
        user_id
    )
    await conn.close()
    
    if respawn_until:
        if isinstance(respawn_until, str):
            respawn_until = datetime.fromisoformat(respawn_until)
        remaining = (respawn_until - datetime.now()).total_seconds()
        return max(0, int(remaining))
    return 0

# ========================================
# 7. PANEL FUNCTIONS (جدید برای قفل پنل)
# ========================================
import uuid

async def generate_panel_id() -> str:
    """تولید یک panel_id تصادفی ۸ کاراکتری"""
    return str(uuid.uuid4())[:8]

async def create_panel(user_id: int, panel_type: str, chat_id: int) -> str:
    """
    ایجاد یک پنل جدید در دیتابیس
    برمیگردونه: panel_id
    """
    panel_id = await generate_panel_id()
    
    conn = await get_db()
    await conn.execute("""
        INSERT INTO panels (panel_id, user_id, chat_id, panel_type, created_at)
        VALUES ($1, $2, $3, $4, NOW())
    """, panel_id, user_id, chat_id, panel_type)
    await conn.close()
    
    return panel_id

async def get_panel_owner(panel_id: str) -> int:
    """دریافت owner_id یک پنل از دیتابیس"""
    conn = await get_db()
    owner_id = await conn.fetchval(
        "SELECT user_id FROM panels WHERE panel_id = $1",
        panel_id
    )
    await conn.close()
    return owner_id

async def delete_panel(panel_id: str):
    """حذف پنل از دیتابیس"""
    conn = await get_db()
    await conn.execute(
        "DELETE FROM panels WHERE panel_id = $1",
        panel_id
    )
    await conn.close()

async def clear_user_panels(user_id: int, chat_id: int):
    """پاک کردن همه پنل‌های یک کاربر در یک چت"""
    conn = await get_db()
    await conn.execute(
        "DELETE FROM panels WHERE user_id = $1 AND chat_id = $2",
        user_id, chat_id
    )
    await conn.close()

async def cleanup_expired_panels(minutes: int = 30):
    """پاک کردن پنل‌های منقضی شده (بیش از X دقیقه)"""
    conn = await get_db()
    await conn.execute(
        "DELETE FROM panels WHERE created_at < NOW() - INTERVAL '$1 minutes'",
        minutes
    )
    await conn.close()

# ========================================
# 8. EXP & LEVEL FUNCTIONS
# ========================================
async def add_exp(user_id: int, amount: int):
    conn = await get_db()
    
    user = await conn.fetchrow(
        "SELECT exp, level, max_exp FROM users WHERE user_id = $1",
        user_id
    )
    
    if not user:
        await conn.close()
        return None
    
    new_exp = user['exp'] + amount
    current_level = user['level']
    max_exp = user['max_exp']
    leveled_up = False
    
    while new_exp >= max_exp:
        new_exp -= max_exp
        current_level += 1
        max_exp = int(max_exp * 1.5) + 50
        leveled_up = True
    
    await conn.execute(
        "UPDATE users SET exp = $1, level = $2, max_exp = $3 WHERE user_id = $4",
        new_exp, current_level, max_exp, user_id
    )
    
    await conn.close()
    
    return {
        "new_exp": new_exp, 
        "new_level": current_level, 
        "new_max_exp": max_exp,
        "leveled_up": leveled_up
    }

# ========================================
# 9. UPGRADE FUNCTIONS
# ========================================
def get_upgrade_cost(total_upgrades: int) -> int:
    if total_upgrades < 10:
        return total_upgrades + 1
    elif total_upgrades < 20:
        return 10 + (total_upgrades - 9) * 2
    elif total_upgrades < 30:
        return 30 + (total_upgrades - 19) * 4
    elif total_upgrades < 40:
        return 66 + (total_upgrades - 29) * 6
    elif total_upgrades < 50:
        return 126 + (total_upgrades - 39) * 7
    else:
        return 196 + (total_upgrades - 49) * 9

async def get_user_upgrade_info(user_id: int):
    conn = await get_db()
    user = await conn.fetchrow("""
        SELECT 
            upgrade_points, total_upgrades,
            hp_level, atk_level, def_level, spd_level, lck_level,
            hp, max_hp, atk, def, spd, lck
        FROM users WHERE user_id = $1
    """, user_id)
    await conn.close()
    return user

async def apply_upgrade(user_id: int, stat_type: str):
    conn = await get_db()
    
    user = await conn.fetchrow("""
        SELECT 
            upgrade_points, total_upgrades,
            hp_level, atk_level, def_level, spd_level, lck_level,
            hp, max_hp, atk, def, spd, lck
        FROM users WHERE user_id = $1
    """, user_id)
    
    if not user:
        await conn.close()
        return {"success": False, "message": "کاربر یافت نشد!"}
    
    cost = get_upgrade_cost(user['total_upgrades'])
    
    if user['upgrade_points'] < cost:
        await conn.close()
        return {"success": False, "message": f"پوینت کافی نیست! نیاز: {cost}"}
    
    new_value = 0
    new_level = 0
    new_max_hp = user['max_hp']
    new_hp = user['hp']
    
    if stat_type == "hp":
        new_level = user['hp_level'] + 1
        new_max_hp = user['max_hp'] + 150
        new_hp = user['hp'] + 150
        await conn.execute("""
            UPDATE users SET 
                hp_level = $1, max_hp = $2, hp = $3,
                upgrade_points = upgrade_points - $4,
                total_upgrades = total_upgrades + 1
            WHERE user_id = $5
        """, new_level, new_max_hp, new_hp, cost, user_id)
        new_value = new_max_hp
        
    elif stat_type == "atk":
        new_level = user['atk_level'] + 1
        new_value = user['atk'] + 2
        await conn.execute("""
            UPDATE users SET 
                atk_level = $1, atk = $2,
                upgrade_points = upgrade_points - $3,
                total_upgrades = total_upgrades + 1
            WHERE user_id = $4
        """, new_level, new_value, cost, user_id)
        
    elif stat_type == "def":
        new_level = user['def_level'] + 1
        new_value = user['def'] + 2
        await conn.execute("""
            UPDATE users SET 
                def_level = $1, def = $2,
                upgrade_points = upgrade_points - $3,
                total_upgrades = total_upgrades + 1
            WHERE user_id = $4
        """, new_level, new_value, cost, user_id)
        
    elif stat_type == "spd":
        new_level = user['spd_level'] + 1
        new_value = user['spd'] + 2
        await conn.execute("""
            UPDATE users SET 
                spd_level = $1, spd = $2,
                upgrade_points = upgrade_points - $3,
                total_upgrades = total_upgrades + 1
            WHERE user_id = $4
        """, new_level, new_value, cost, user_id)
        
    elif stat_type == "lck":
        new_level = user['lck_level'] + 1
        new_value = user['lck'] + 2
        await conn.execute("""
            UPDATE users SET 
                lck_level = $1, lck = $2,
                upgrade_points = upgrade_points - $3,
                total_upgrades = total_upgrades + 1
            WHERE user_id = $4
        """, new_level, new_value, cost, user_id)
    
    await conn.close()
    
    return {
        "success": True,
        "stat_type": stat_type,
        "new_level": new_level,
        "new_value": new_value,
        "cost": cost,
        "new_hp": new_hp if stat_type == "hp" else user['hp'],
        "new_max_hp": new_max_hp if stat_type == "hp" else user['max_hp']
    }

# ========================================
# 10. LEADERBOARD FUNCTIONS
# ========================================
async def get_leaderboard_global(stat_type: str, limit: int = 10, offset: int = 0):
    conn = await get_db()
    
    if stat_type == "gold":
        query = """
            SELECT user_id, character_name, class, level, gold, atk
            FROM users 
            WHERE is_registered = TRUE 
            ORDER BY gold DESC, level DESC 
            LIMIT $1 OFFSET $2
        """
    elif stat_type == "level":
        query = """
            SELECT user_id, character_name, class, level, gold, atk
            FROM users 
            WHERE is_registered = TRUE 
            ORDER BY level DESC, gold DESC 
            LIMIT $1 OFFSET $2
        """
    elif stat_type == "power":
        query = """
            SELECT user_id, character_name, class, level, gold, atk
            FROM users 
            WHERE is_registered = TRUE 
            ORDER BY atk DESC, level DESC 
            LIMIT $1 OFFSET $2
        """
    else:
        await conn.close()
        return []
    
    users = await conn.fetch(query, limit, offset)
    await conn.close()
    return users

async def get_leaderboard_group(chat_id: int, stat_type: str, limit: int = 10, offset: int = 0):
    conn = await get_db()
    
    if stat_type == "gold":
        query = """
            SELECT u.user_id, u.character_name, u.class, u.level, u.gold, u.atk
            FROM users u
            INNER JOIN group_members gm ON u.user_id = gm.user_id
            WHERE u.is_registered = TRUE AND gm.chat_id = $1
            ORDER BY u.gold DESC, u.level DESC 
            LIMIT $2 OFFSET $3
        """
    elif stat_type == "level":
        query = """
            SELECT u.user_id, u.character_name, u.class, u.level, u.gold, u.atk
            FROM users u
            INNER JOIN group_members gm ON u.user_id = gm.user_id
            WHERE u.is_registered = TRUE AND gm.chat_id = $1
            ORDER BY u.level DESC, u.gold DESC 
            LIMIT $2 OFFSET $3
        """
    elif stat_type == "power":
        query = """
            SELECT u.user_id, u.character_name, u.class, u.level, u.gold, u.atk
            FROM users u
            INNER JOIN group_members gm ON u.user_id = gm.user_id
            WHERE u.is_registered = TRUE AND gm.chat_id = $1
            ORDER BY u.atk DESC, u.level DESC 
            LIMIT $2 OFFSET $3
        """
    else:
        await conn.close()
        return []
    
    users = await conn.fetch(query, chat_id, limit, offset)
    await conn.close()
    return users

async def get_user_global_rank(user_id: int, stat_type: str) -> int:
    conn = await get_db()
    
    if stat_type == "gold":
        rank = await conn.fetchval("""
            SELECT COUNT(*) + 1 
            FROM users 
            WHERE is_registered = TRUE AND gold > (SELECT gold FROM users WHERE user_id = $1)
        """, user_id)
    elif stat_type == "level":
        rank = await conn.fetchval("""
            SELECT COUNT(*) + 1 
            FROM users 
            WHERE is_registered = TRUE AND level > (SELECT level FROM users WHERE user_id = $1)
        """, user_id)
    elif stat_type == "power":
        rank = await conn.fetchval("""
            SELECT COUNT(*) + 1 
            FROM users 
            WHERE is_registered = TRUE AND atk > (SELECT atk FROM users WHERE user_id = $1)
        """, user_id)
    else:
        await conn.close()
        return 0
    
    await conn.close()
    return rank or 0

async def get_user_group_rank(user_id: int, chat_id: int, stat_type: str) -> int:
    conn = await get_db()
    
    if stat_type == "gold":
        rank = await conn.fetchval("""
            SELECT COUNT(*) + 1 
            FROM users u
            INNER JOIN group_members gm ON u.user_id = gm.user_id
            WHERE u.is_registered = TRUE 
                AND gm.chat_id = $1 
                AND u.gold > (SELECT gold FROM users WHERE user_id = $2)
        """, chat_id, user_id)
    elif stat_type == "level":
        rank = await conn.fetchval("""
            SELECT COUNT(*) + 1 
            FROM users u
            INNER JOIN group_members gm ON u.user_id = gm.user_id
            WHERE u.is_registered = TRUE 
                AND gm.chat_id = $1 
                AND u.level > (SELECT level FROM users WHERE user_id = $2)
        """, chat_id, user_id)
    elif stat_type == "power":
        rank = await conn.fetchval("""
            SELECT COUNT(*) + 1 
            FROM users u
            INNER JOIN group_members gm ON u.user_id = gm.user_id
            WHERE u.is_registered = TRUE 
                AND gm.chat_id = $1 
                AND u.atk > (SELECT atk FROM users WHERE user_id = $2)
        """, chat_id, user_id)
    else:
        await conn.close()
        return 0
    
    await conn.close()
    return rank or 0

async def add_group_member(user_id: int, chat_id: int):
    conn = await get_db()
    await conn.execute(
        "INSERT INTO group_members (user_id, chat_id) VALUES ($1, $2) ON CONFLICT (user_id, chat_id) DO NOTHING",
        user_id, chat_id
    )
    await conn.close()

async def get_total_users_global() -> int:
    conn = await get_db()
    total = await conn.fetchval("SELECT COUNT(*) FROM users WHERE is_registered = TRUE")
    await conn.close()
    return total or 0

async def get_total_users_group(chat_id: int) -> int:
    conn = await get_db()
    total = await conn.fetchval("""
        SELECT COUNT(*) 
        FROM users u
        INNER JOIN group_members gm ON u.user_id = gm.user_id
        WHERE u.is_registered = TRUE AND gm.chat_id = $1
    """, chat_id)
    await conn.close()
    return total or 0

# ========================================
# 11. WEAPON BONUS FUNCTIONS
# ========================================
def get_weapon_category(item_name: str) -> str:
    from config import SHOP_ITEMS
    for category, items in SHOP_ITEMS.items():
        if category in ["sword", "katana", "dagger", "axe"]:
            for item in items:
                if item['name'] == item_name:
                    return category
    return None

async def apply_weapon_bonus(user_id: int, damage: int, enemy_hp: int, enemy_def: int) -> dict:
    from config import WEAPON_BONUSES, ITEM_STATS
    import random
    
    equipped = await get_equipped(user_id)
    equipped_weapon = next((Item(**dict(item)) for item in equipped if item['item_type'] == 'weapon'), None)
    
    if not equipped_weapon:
        return {"damage": damage, "message": "", "extra_effects": {}}
    
    weapon_name = equipped_weapon.item_name
    category = get_weapon_category(weapon_name)
    
    if not category or category not in WEAPON_BONUSES:
        return {"damage": damage, "message": "", "extra_effects": {}}
    
    bonus = WEAPON_BONUSES[category]
    result = {"damage": damage, "message": "", "extra_effects": {}}
    messages = []
    
    if bonus['type'] == "critical":
        chance = bonus['chances'].get(weapon_name, 0.20)
        if random.random() < chance:
            result['damage'] = damage * 2
            messages.append(f"💥 **دمیج دو برابر!** ({bonus['emoji']} {bonus['name']})")
        
        lifesteal_chance = bonus.get('lifesteal', {}).get(weapon_name, 0)
        if lifesteal_chance > 0 and random.random() < lifesteal_chance:
            result['extra_effects']['lifesteal'] = int(damage * 0.15)
            messages.append(f"🩸 **لایف استیل!** +{int(damage * 0.15)} جون")

    elif bonus['type'] == "execute":
        chance = bonus['chances'].get(weapon_name, 0)
        if chance > 0 and random.random() < chance:
            result['damage'] = enemy_hp // 2
            messages.append(f"🗡️ **ضربه مرگبار!** نصف جون ({enemy_hp//2}) ({bonus['emoji']} {bonus['name']})")

    elif bonus['type'] == "deep_wound":
        chance = bonus['chances'].get(weapon_name, 0)
        if chance > 0 and random.random() < chance:
            if "چوبی" in weapon_name:
                bleed_damage = 20
            elif "برنزی" in weapon_name:
                bleed_damage = 40
            elif "آهنی" in weapon_name:
                bleed_damage = 60
            elif "فولادی" in weapon_name:
                bleed_damage = 80
            elif "الماسی" in weapon_name:
                bleed_damage = 100
            elif "افسانه‌ای" in weapon_name:
                bleed_damage = 150
            else:
                bleed_damage = 50
            
            current_bleed = await get_bleed(user_id)
            new_bleed = current_bleed + bleed_damage
            result['extra_effects']['bleed'] = new_bleed
            messages.append(f"🩸 **زخم عمیق!** خونریزی +{bleed_damage} (مجموع: {new_bleed}) ({bonus['emoji']} {bonus['name']})")

    elif bonus['type'] == "armor_pierce":
        if random.random() < bonus['chance']:
            result['damage'] = damage + enemy_def
            messages.append(f"🛡️ **نادیده گرفتن دفاع!** (+{enemy_def} دمیج) ({bonus['emoji']} {bonus['name']})")
    
    result['message'] = " ".join(messages)
    return result

# ========================================
# 12. DAILY QUEST FUNCTIONS
# ========================================
QUEST_TYPES = {
    "kill_goblin": {
        "name": "گابلین بکش",
        "emoji": "🗡️",
        "easy": {"target": 2, "gold": 100, "upgrade": 1},
        "normal": {"target": 4, "gold": 200, "upgrade": 2},
        "hard": {"target": 7, "gold": 350, "upgrade": 4}
    },
    "kill_troll": {
        "name": "ترول بکش",
        "emoji": "🪓",
        "easy": {"target": 1, "gold": 150, "upgrade": 2},
        "normal": {"target": 2, "gold": 300, "upgrade": 3},
        "hard": {"target": 4, "gold": 550, "upgrade": 6}
    },
    "duel": {
        "name": "دوئل کن",
        "emoji": "⚔️",
        "easy": {"target": 1, "gold": 100, "upgrade": 1},
        "normal": {"target": 2, "gold": 200, "upgrade": 2},
        "hard": {"target": 4, "gold": 400, "upgrade": 4}
    },
    "shop": {
        "name": "از شاپ بخر",
        "emoji": "🛒",
        "easy": {"target": 1, "gold": 50, "upgrade": 1},
        "normal": {"target": 3, "gold": 150, "upgrade": 2},
        "hard": {"target": 5, "gold": 300, "upgrade": 4}
    },
    "upgrade": {
        "name": "آپگرید کن",
        "emoji": "⭐",
        "easy": {"target": 1, "gold": 100, "upgrade": 2},
        "normal": {"target": 2, "gold": 200, "upgrade": 3},
        "hard": {"target": 4, "gold": 400, "upgrade": 5}
    }
}

DIFFICULTY_NAMES = {
    "easy": "🟢 ساده",
    "normal": "🟡 متوسط",
    "hard": "🔴 سخت"
}

async def generate_daily_quests(user_id: int):
    conn = await get_db()
    
    await conn.execute(
        "DELETE FROM daily_quests WHERE user_id = $1 AND quest_completed = FALSE",
        user_id
    )
    
    quest_keys = list(QUEST_TYPES.keys())
    selected_quests = random.sample(quest_keys, 3)
    
    difficulties = ["easy", "normal", "hard"]
    
    for i, quest_key in enumerate(selected_quests):
        difficulty = difficulties[i] if i < len(difficulties) else "normal"
        quest_data = QUEST_TYPES[quest_key][difficulty]
        
        await conn.execute("""
            INSERT INTO daily_quests (
                user_id, quest_type, quest_target, 
                quest_reward_gold, quest_reward_upgrade, 
                quest_difficulty, quest_date
            ) VALUES ($1, $2, $3, $4, $5, $6, $7)
        """, 
            user_id, quest_key, quest_data["target"],
            quest_data["gold"], quest_data["upgrade"],
            difficulty, datetime.now()
        )
    
    await conn.close()
    return True

async def get_user_quests(user_id: int):
    conn = await get_db()
    
    quests = await conn.fetch(
        "SELECT * FROM daily_quests WHERE user_id = $1 ORDER BY quest_completed DESC, id",
        user_id
    )
    
    if not quests:
        await conn.close()
        await generate_daily_quests(user_id)
        conn = await get_db()
        quests = await conn.fetch(
            "SELECT * FROM daily_quests WHERE user_id = $1 ORDER BY quest_completed DESC, id",
            user_id
        )
    
    await conn.close()
    return quests

async def update_quest_progress(user_id: int, quest_type: str, amount: int = 1):
    conn = await get_db()
    
    quest = await conn.fetchrow(
        "SELECT * FROM daily_quests WHERE user_id = $1 AND quest_type = $2 AND quest_completed = FALSE",
        user_id, quest_type
    )
    
    if not quest:
        await conn.close()
        return None
    
    new_progress = quest['quest_progress'] + amount
    if new_progress >= quest['quest_target']:
        new_progress = quest['quest_target']
        await conn.execute(
            "UPDATE daily_quests SET quest_progress = $1, quest_completed = TRUE WHERE id = $2",
            new_progress, quest['id']
        )
        await conn.close()
        return {"completed": True, "quest": quest}
    else:
        await conn.execute(
            "UPDATE daily_quests SET quest_progress = $1 WHERE id = $2",
            new_progress, quest['id']
        )
        await conn.close()
        return {"completed": False, "quest": quest}

async def claim_quest_reward(user_id: int, quest_id: int):
    conn = await get_db()
    
    quest = await conn.fetchrow(
        "SELECT * FROM daily_quests WHERE id = $1 AND user_id = $2 AND quest_completed = TRUE",
        quest_id, user_id
    )
    
    if not quest:
        await conn.close()
        return {"success": False, "message": "این کوئست کامل نشده یا وجود ندارد!"}
    
    await conn.execute(
        "UPDATE users SET gold = gold + $1, upgrade_points = upgrade_points + $2 WHERE user_id = $3",
        quest['quest_reward_gold'], quest['quest_reward_upgrade'], user_id
    )
    
    await conn.execute(
        "DELETE FROM daily_quests WHERE id = $1",
        quest_id
    )
    
    await conn.close()
    return {
        "success": True,
        "gold": quest['quest_reward_gold'],
        "upgrade": quest['quest_reward_upgrade'],
        "quest_name": QUEST_TYPES.get(quest['quest_type'], {}).get('name', quest['quest_type'])
    }

async def claim_all_quests(user_id: int):
    conn = await get_db()
    
    quests = await conn.fetch(
        "SELECT * FROM daily_quests WHERE user_id = $1 AND quest_completed = TRUE",
        user_id
    )
    
    if not quests:
        await conn.close()
        return {"success": False, "message": "هیچ کوئست کامل‌شده‌ای وجود ندارد!"}
    
    total_gold = 0
    total_upgrade = 0
    quest_names = []
    
    for quest in quests:
        total_gold += quest['quest_reward_gold']
        total_upgrade += quest['quest_reward_upgrade']
        quest_names.append(QUEST_TYPES.get(quest['quest_type'], {}).get('name', quest['quest_type']))
        await conn.execute(
            "DELETE FROM daily_quests WHERE id = $1",
            quest['id']
        )
    
    await conn.execute(
        "UPDATE users SET gold = gold + $1, upgrade_points = upgrade_points + $2 WHERE user_id = $3",
        total_gold, total_upgrade, user_id
    )
    
    await conn.close()
    return {
        "success": True,
        "gold": total_gold,
        "upgrade": total_upgrade,
        "count": len(quests),
        "quest_names": quest_names
    }

async def reset_daily_quests():
    """ریست کوئست‌های قدیمی‌تر از ۱ ساعت"""
    conn = await get_db()
    cutoff_time = datetime.now() - timedelta(hours=1)
    await conn.execute(
        "DELETE FROM daily_quests WHERE quest_date < $1 AND quest_completed = FALSE",
        cutoff_time
    )
    await conn.close()

async def get_quest_time_remaining():
    """زمان تا ریست بعدی (هر ساعت یک بار)"""
    now = datetime.now()
    next_reset = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    remaining = (next_reset - now).total_seconds()
    return max(0, int(remaining))


# ========================================
# 13. KEYWORD REWARD FUNCTIONS
# ========================================
async def can_claim_keyword_reward(user_id: int) -> bool:
    conn = await get_db()
    
    result = await conn.fetchval(
        "SELECT last_claim FROM keyword_rewards WHERE user_id = $1",
        user_id
    )
    
    if not result:
        await conn.close()
        return True
    
    time_diff = (datetime.now() - result).total_seconds()
    await conn.close()
    return time_diff >= 180

async def claim_keyword_reward(user_id: int) -> dict:
    conn = await get_db()
    
    user_exists = await conn.fetchval(
        "SELECT user_id FROM users WHERE user_id = $1",
        user_id
    )
    
    if not user_exists:
        await conn.close()
        return {"success": False, "message": "شما ثبت‌نام نکردید!"}
    
    can_claim = await can_claim_keyword_reward(user_id)
    if not can_claim:
        await conn.close()
        return {"success": False, "message": "⏱️ هنوز ۳ دقیقه نشده!"}
    
    reward = random.randint(100, 150)
    
    await conn.execute(
        "UPDATE users SET gold = gold + $1 WHERE user_id = $2",
        reward, user_id
    )
    
    await conn.execute(
        "INSERT INTO keyword_rewards (user_id, last_claim) VALUES ($1, $2) ON CONFLICT (user_id) DO UPDATE SET last_claim = $2",
        user_id, datetime.now()
    )
    
    new_gold = await conn.fetchval(
        "SELECT gold FROM users WHERE user_id = $1",
        user_id
    )
    
    await conn.close()
    return {
        "success": True,
        "reward": reward,
        "new_gold": new_gold
    }

async def get_keyword_cooldown(user_id: int) -> int:
    conn = await get_db()
    
    last_claim = await conn.fetchval(
        "SELECT last_claim FROM keyword_rewards WHERE user_id = $1",
        user_id
    )
    
    if not last_claim:
        await conn.close()
        return 0
    
    time_diff = (datetime.now() - last_claim).total_seconds()
    remaining = 180 - time_diff
    await conn.close()
    return max(0, int(remaining))

# ========================================
# 14. DUEL FUNCTIONS
# ========================================
async def create_duel(chat_id: int, creator_id: int, creator_name: str, amount: int, message_id: int):
    """ایجاد دوئل جدید در دیتابیس"""
    conn = await get_db()
    
    await conn.execute(
        "DELETE FROM duel_requests WHERE chat_id = $1 AND accepted = FALSE",
        chat_id
    )
    
    await conn.execute("""
        INSERT INTO duel_requests (chat_id, creator_id, creator_name, amount, message_id)
        VALUES ($1, $2, $3, $4, $5)
    """, chat_id, creator_id, creator_name, amount, message_id)
    
    await conn.close()

async def get_active_duel(chat_id: int):
    """دریافت دوئل فعال در یک چت"""
    conn = await get_db()
    duel = await conn.fetchrow(
        "SELECT * FROM duel_requests WHERE chat_id = $1 AND accepted = FALSE ORDER BY created_at DESC LIMIT 1",
        chat_id
    )
    await conn.close()
    return duel

async def accept_duel(chat_id: int, winner_id: int):
    """قبول کردن دوئل"""
    conn = await get_db()
    
    await conn.execute(
        "UPDATE duel_requests SET accepted = TRUE, winner_id = $1 WHERE chat_id = $2 AND accepted = FALSE",
        winner_id, chat_id
    )
    
    await conn.close()

async def delete_duel(chat_id: int):
    """حذف دوئل از دیتابیس"""
    conn = await get_db()
    await conn.execute(
        "DELETE FROM duel_requests WHERE chat_id = $1",
        chat_id
    )
    await conn.close()

async def get_duel_creator(chat_id: int):
    """دریافت سازنده دوئل"""
    conn = await get_db()
    creator = await conn.fetchval(
        "SELECT creator_id FROM duel_requests WHERE chat_id = $1 AND accepted = FALSE",
        chat_id
    )
    await conn.close()
    return creator
