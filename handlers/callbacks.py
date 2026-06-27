from telegram import Update
from telegram.ext import ContextTypes
from handlers.start import select_class_callback
from handlers.inventory import (
    equip_weapon_menu, equip_armor_menu, use_item_menu,
    execute_equip_weapon, execute_equip_armor, confirm_use_consumable,
    show_inventory_panel, close_inventory
)
from handlers.shop import (
    shop_buy_weapon_category, shop_buy_weapons,
    shop_buy_armors, shop_buy_item_category, shop_buy_consumables,
    shop_sell_category, shop_sell_items,
    execute_buy, execute_sell, shop_back_to_main, shop_close,
    shop_buy_quantity, shop_cancel_buy
)
from handlers.dungeon import (
    dungeon_start_panel, dungeon_battle_start,
    dungeon_attack, dungeon_flee, dungeon_potion_menu,
    dungeon_use_potion, dungeon_continue, dungeon_next_stage,
    dungeon_back_to_battle, dungeon_back, dungeon_close, dungeon_locked,
    dungeon_level_locked
)
from handlers.upgrade import (
    upgrade_back, upgrade_close, execute_upgrade
)
from handlers.leaderboard import (
    show_leaderboard, my_rank, lb_back, lb_close
)
from handlers.duel import duel_accept, duel_close
from handlers.daily import daily_claim, daily_claim_all, daily_back, daily_close
from handlers.help import help_close
from handlers.panel_utils import check_panel_ownership, set_panel_owner, clear_panel_owner

# ========================================
# کالبک اصلی
# ========================================

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت همه کلیک‌های دکمه"""
    query = update.callback_query
    data = query.data
    
    print(f"🔍 کالبک دریافت شد: {data}")
    
    # ==========================================
    # 1. انتخاب کلاس (ثبت‌نام) - بدون قفل
    # ==========================================
    if data.startswith("class_") or data == "cancel_registration":
        await select_class_callback(update, context)
        return
    
    # ==========================================
    # 2. دکمه‌های قفل شده دانجن - بدون قفل
    # ==========================================
    if data == "dungeon_level_locked":
        await query.answer("🔒 لول شما برای این ماموریت کافی نیست!", show_alert=True)
        return
    
    if data == "dungeon_locked":
        await query.answer("⛔ این ماموریت در حال حاضر در دسترس نیست!", show_alert=True)
        return
    
    # ==========================================
    # 3. دکمه‌های دوئل - بدون قفل
    # ==========================================
    if data == "duel_accept":
        print("🚨 دکمه قبول دوئل در callbacks شناسایی شد!")
        await duel_accept(update, context)
        return
    
    if data == "duel_close":
        print("🚨 دکمه بستن دوئل در callbacks شناسایی شد!")
        await duel_close(update, context)
        return
    
    if data == "test_button":
        print("🧪 دکمه تست کلیک شد!")
        await query.answer("✅ دکمه تست کار کرد!", show_alert=True)
        await query.edit_message_text("✅ دکمه تست با موفقیت کار کرد!")
        return
    
    # ==========================================
    # 4. دکمه‌های باز کردن پنل جدید - با set_panel_owner
    # ==========================================
    
    # ----- دانجن -----
    if data.startswith("dungeon_start_"):
        panel_id = await set_panel_owner(update, context, "dungeon")
        if not panel_id:
            return
        dungeon_type = data.replace("dungeon_start_", "")
        await dungeon_start_panel(update, context, dungeon_type, panel_id)
        return
    
    # ----- شاپ - ورود به بخش‌های اصلی -----
    if data == "shop_buy_weapon":
        panel_id = await set_panel_owner(update, context, "shop")
        if not panel_id:
            return
        await shop_buy_weapon_category(update, context, panel_id)
        return
    
    if data == "shop_buy_armor":
        panel_id = await set_panel_owner(update, context, "shop")
        if not panel_id:
            return
        await shop_buy_armors(update, context, 0, panel_id)
        return
    
    if data == "shop_buy_item":
        panel_id = await set_panel_owner(update, context, "shop")
        if not panel_id:
            return
        await shop_buy_item_category(update, context, panel_id)
        return
    
    if data == "shop_sell":
        panel_id = await set_panel_owner(update, context, "shop")
        if not panel_id:
            return
        await shop_sell_category(update, context, panel_id)
        return
    
    # ----- اینونتوری - ورود به بخش‌های اصلی -----
    if data == "inv_equip_weapon":
        panel_id = await set_panel_owner(update, context, "inventory")
        if not panel_id:
            return
        await equip_weapon_menu(update, context, 0, panel_id)
        return
    
    if data == "inv_equip_armor":
        panel_id = await set_panel_owner(update, context, "inventory")
        if not panel_id:
            return
        await equip_armor_menu(update, context, 0, panel_id)
        return
    
    if data == "inv_use_item":
        panel_id = await set_panel_owner(update, context, "inventory")
        if not panel_id:
            return
        await use_item_menu(update, context, 0, panel_id)
        return
    
    # ==========================================
    # 5. بقیه دکمه‌ها - با check_panel_ownership
    # ==========================================
    if not await check_panel_ownership(update, context):
        return
    
    # ==========================================
    # 6. دکمه‌های بستن پنل - با clear_panel_owner
    # ==========================================
    if data == "inv_close":
        await clear_panel_owner(update, context)
        await close_inventory(update, context)
        return
    
    if data == "shop_close":
        await clear_panel_owner(update, context)
        await shop_close(update, context)
        return
    
    if data == "dungeon_close":
        await dungeon_close(update, context)
        return
    
    if data == "upgrade_close":
        await upgrade_close(update, context)
        return
    
    if data == "lb_close":
        await lb_close(update, context)
        return
    
    if data == "daily_close":
        await daily_close(update, context)
        return
    
    if data == "help_close":
        await help_close(update, context)
        return
    
    # ==========================================
    # 7. دکمه‌های برگشت به پنل اصلی
    # ==========================================
    if data == "inv_back_to_inventory":
        await show_inventory_panel(update, context)
        return
    
    if data == "shop_back_to_main":
        await shop_back_to_main(update, context)
        return
    
    if data == "dungeon_back":
        await dungeon_back(update, context)
        return
    
    if data == "upgrade_back":
        await upgrade_back(update, context)
        return
    
    if data == "lb_back":
        await lb_back(update, context)
        return
    
    if data == "daily_back":
        await daily_back(update, context)
        return
    
    # ==========================================
    # 8. دکمه‌های صفحه‌بندی اینونتوری
    # ==========================================
    if data.startswith("inv_weapon_page_"):
        page = int(data.split("_")[-1])
        panel_id = context.user_data.get('current_panel_id')
        if not panel_id:
            await query.answer("❌ پنل شما منقضی شده است!", show_alert=True)
            return
        await equip_weapon_menu(update, context, page, panel_id)
        return
    
    if data.startswith("inv_armor_page_"):
        page = int(data.split("_")[-1])
        panel_id = context.user_data.get('current_panel_id')
        if not panel_id:
            await query.answer("❌ پنل شما منقضی شده است!", show_alert=True)
            return
        await equip_armor_menu(update, context, page, panel_id)
        return
    
    if data.startswith("inv_consumable_page_"):
        page = int(data.split("_")[-1])
        panel_id = context.user_data.get('current_panel_id')
        if not panel_id:
            await query.answer("❌ پنل شما منقضی شده است!", show_alert=True)
            return
        await use_item_menu(update, context, page, panel_id)
        return
    
    # ==========================================
    # 9. دکمه‌های اجرایی اینونتوری
    # ==========================================
    if data.startswith("inv_equip_weapon_"):
        await execute_equip_weapon(update, context)
        return
    
    if data.startswith("inv_equip_armor_"):
        await execute_equip_armor(update, context)
        return
    
    if data.startswith("inv_use_consumable_"):
        await confirm_use_consumable(update, context)
        return
    
    # ==========================================
    # 10. دکمه‌های شاپ - خرید سلاح
    # ==========================================
    if data.startswith("shop_buy_weapons_"):
        if "_page_" in data:
            parts = data.split("_page_")
            category = parts[0].replace("shop_buy_weapons_", "")
            page = int(parts[1])
            panel_id = context.user_data.get('current_panel_id')
            if not panel_id:
                await query.answer("❌ پنل شما منقضی شده است!", show_alert=True)
                return
            await shop_buy_weapons(update, context, page, panel_id)
        else:
            panel_id = context.user_data.get('current_panel_id')
            if not panel_id:
                await query.answer("❌ پنل شما منقضی شده است!", show_alert=True)
                return
            await shop_buy_weapons(update, context, 0, panel_id)
        return
    
    # ==========================================
    # 11. دکمه‌های شاپ - خرید زره
    # ==========================================
    if data.startswith("shop_buy_armor_page_"):
        page = int(data.replace("shop_buy_armor_page_", ""))
        panel_id = context.user_data.get('current_panel_id')
        if not panel_id:
            await query.answer("❌ پنل شما منقضی شده است!", show_alert=True)
            return
        await shop_buy_armors(update, context, page, panel_id)
        return
    
    # ==========================================
    # 12. دکمه‌های شاپ - خرید آیتم
    # ==========================================
    if data == "shop_buy_consumables":
        panel_id = context.user_data.get('current_panel_id')
        if not panel_id:
            await query.answer("❌ پنل شما منقضی شده است!", show_alert=True)
            return
        await shop_buy_consumables(update, context, panel_id)
        return
    
    if data.startswith("shop_buy_quantity_"):
        await shop_buy_quantity(update, context)
        return
    
    if data == "shop_cancel_buy":
        await shop_cancel_buy(update, context)
        return
    
    # ==========================================
    # 13. دکمه‌های شاپ - فروش
    # ==========================================
    if data.startswith("shop_sell_weapon"):
        if "_page_" in data:
            page = int(data.replace("shop_sell_weapon_page_", ""))
            panel_id = context.user_data.get('current_panel_id')
            if not panel_id:
                await query.answer("❌ پنل شما منقضی شده است!", show_alert=True)
                return
            await shop_sell_items(update, context, "weapon", page, panel_id)
        else:
            panel_id = context.user_data.get('current_panel_id')
            if not panel_id:
                await query.answer("❌ پنل شما منقضی شده است!", show_alert=True)
                return
            await shop_sell_items(update, context, "weapon", 0, panel_id)
        return
    
    if data.startswith("shop_sell_armor"):
        if "_page_" in data:
            page = int(data.replace("shop_sell_armor_page_", ""))
            panel_id = context.user_data.get('current_panel_id')
            if not panel_id:
                await query.answer("❌ پنل شما منقضی شده است!", show_alert=True)
                return
            await shop_sell_items(update, context, "armor", page, panel_id)
        else:
            panel_id = context.user_data.get('current_panel_id')
            if not panel_id:
                await query.answer("❌ پنل شما منقضی شده است!", show_alert=True)
                return
            await shop_sell_items(update, context, "armor", 0, panel_id)
        return
    
    if data.startswith("shop_sell_consumable"):
        if "_page_" in data:
            page = int(data.replace("shop_sell_consumable_page_", ""))
            panel_id = context.user_data.get('current_panel_id')
            if not panel_id:
                await query.answer("❌ پنل شما منقضی شده است!", show_alert=True)
                return
            await shop_sell_items(update, context, "consumable", page, panel_id)
        else:
            panel_id = context.user_data.get('current_panel_id')
            if not panel_id:
                await query.answer("❌ پنل شما منقضی شده است!", show_alert=True)
                return
            await shop_sell_items(update, context, "consumable", 0, panel_id)
        return
    
    # ==========================================
    # 14. دکمه‌های شاپ - اجرای خرید/فروش
    # ==========================================
    if data.startswith("shop_buy_execute_"):
        await execute_buy(update, context)
        return
    
    if data.startswith("shop_sell_execute_"):
        await execute_sell(update, context)
        return
    
    # ==========================================
    # 15. دکمه‌های دانجن - نبرد
    # ==========================================
    if data.startswith("dungeon_battle_start_"):
        await dungeon_battle_start(update, context)
        return
    
    if data == "dungeon_attack":
        await dungeon_attack(update, context)
        return
    
    if data == "dungeon_flee":
        await dungeon_flee(update, context)
        return
    
    if data == "dungeon_potion":
        await dungeon_potion_menu(update, context)
        return
    
    if data.startswith("dungeon_use_potion_"):
        await dungeon_use_potion(update, context)
        return
    
    if data.startswith("dungeon_continue_"):
        await dungeon_continue(update, context)
        return
    
    if data.startswith("dungeon_next_stage_"):
        await dungeon_next_stage(update, context)
        return
    
    if data == "dungeon_back_to_battle":
        await dungeon_back_to_battle(update, context)
        return
    
    # ==========================================
    # 16. دکمه‌های آپگرید
    # ==========================================
    if data.startswith("upgrade_"):
        await execute_upgrade(update, context)
        return
    
    # ==========================================
    # 17. دکمه‌های لیدربرد
    # ==========================================
    if data == "lb_my_rank":
        await my_rank(update, context)
        return
    
    if data.startswith("lb_type_"):
        mode = data.replace("lb_type_", "")
        context.user_data['lb_mode'] = mode
        await query.answer(f"🌍 حالت: {mode}")
        return
    
    if data.startswith("lb_page_"):
        parts = data.replace("lb_page_", "").split("_")
        mode = parts[0]
        stat_type = parts[1]
        page = int(parts[2])
        await show_leaderboard(update, context, stat_type, mode, page)
        return
    
    if data in ["lb_gold", "lb_level", "lb_power"]:
        stat_type = data.replace("lb_", "")
        mode = context.user_data.get('lb_mode', 'global')
        await show_leaderboard(update, context, stat_type, mode, 0)
        return
    
    # ==========================================
    # 18. دکمه‌های دیلی کوئست
    # ==========================================
    if data.startswith("daily_claim_"):
        if data == "daily_claim_all":
            await daily_claim_all(update, context)
        else:
            await daily_claim(update, context)
        return
    
    # ==========================================
    # 19. دکمه ادمین
    # ==========================================
    if data == "admin_close":
        await query.answer()
        await query.delete_message()
        return
    
    # ==========================================
    # 20. پیش‌فرض
    # ==========================================
    await query.answer("⏳ در حال توسعه...")

