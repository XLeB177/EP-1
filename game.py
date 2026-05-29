import os
import sys
import tkinter as tk
from tkinter import messagebox
import resources
from ai import EnemyBotController
from units import (
    Unit,
    aabb_intersect,
    enemy_tower_body_box,
    player_tower_body_box,
)

WIDTH = 1800
HEIGHT = 1000
FPS = 60

# QTE: зелёная зона (крит) и жёлтая (половина ширины полосы от центра)
QTE_CRIT_HALF = 16
QTE_YELLOW_HALF = 80


class GameScene:

    def __init__(self, root, canvas):

        self.root = root
        self.canvas = canvas

        self.paused = False
        self.game_over = False

        self.units = []

        self.money = 50
        self.money_level = 1
        self.money_income = 1
        self.money_timer = 0

        self.enemy_money = 50
        self.enemy_money_level = 1
        self.enemy_income = 1
        self.enemy_money_timer = 0

        self.bot = EnemyBotController()

        self.player_hp = 1000
        self.enemy_hp = 1000
        self.max_hp = 1000

        self.qte_active = False
        self.qte_value = 0
        self.qte_direction = 1
        self.qte_speed = 0.034
        self.qte_elements = []

        self.font_money = resources.get_font(self.root, 18, "bold")
        self.font_ui = resources.get_font(self.root, 14)
        self.font_end_title = resources.get_font(self.root, 48, "bold")
        self.font_end_btn = resources.get_font(self.root, 18)

        self.load_sprites()
        self.create_scene()
        self.game_loop()

    def _destroy_widget_if_exists(self, widget):
        try:
            if widget is not None and widget.winfo_exists():
                widget.destroy()
        except Exception:
            pass

    def _reset_session_state(self):
        self.paused = False
        self.game_over = False

        self.units = []

        self.money = 50
        self.money_level = 1
        self.money_income = 1
        self.money_timer = 0

        self.enemy_money = 50
        self.enemy_money_level = 1
        self.enemy_income = 1
        self.enemy_money_timer = 0

        self.bot = EnemyBotController()

        self.player_hp = 1000
        self.enemy_hp = 1000
        self.max_hp = 1000

        # сбрасываем QTE (на случай если конец игры наступил во время него)
        self.qte_active = False
        self.qte_value = 0
        self.qte_direction = 1
        self.qte_elements.clear()
        try:
            self.root.unbind("<space>")
        except Exception:
            pass

    def load_sprites(self):

        assets_dir = resources.resolve_assets_dir()

        self.bg = tk.PhotoImage(file=os.path.join(assets_dir, "background.png"))
        self.tower_player = self._load_tower_sprite(assets_dir, "tower_player.png")
        self.tower_enemy = self._load_tower_sprite(assets_dir, "tower_enemy.png")
        self.tower_player_shoot = self._load_tower_shoot_variant(
            assets_dir, "tower_player_shoot.png", self.tower_player
        )
        self.tower_enemy_shoot = self._load_tower_shoot_variant(
            assets_dir, "tower_enemy_shoot.png", self.tower_enemy
        )

        # Союзные спрайты — как в PNG, без масштабирования в коде.
        self.unit1_idle, self.unit1_attack = self._load_sprite_pair(
            assets_dir, "unit_1_1.png", "unit_1_2.png"
        )
        self.unit2_idle, self.unit2_windup, self.unit2_attack = self._load_sprite_triple(
            assets_dir, "unit_2_1.png", "unit_2_2.png", "unit_2_3.png"
        )
        self.unit3_idle, self.unit3_attack = self._load_sprite_pair(
            assets_dir, "unit_3_1.png", "unit_3_2.png"
        )

        self.enemy_unit1_idle, self.enemy_unit1_attack = self._load_sprite_pair(
            assets_dir, "enemy_unit_1_1.png", "enemy_unit_1_2.png"
        )
        self.enemy_unit2_idle, self.enemy_unit2_windup, self.enemy_unit2_attack = (
            self._load_sprite_triple(
                assets_dir,
                "enemy_unit_2_1.png",
                "enemy_unit_2_2.png",
                "enemy_unit_2_3.png",
            )
        )
        self.enemy_unit3_idle, self.enemy_unit3_attack = self._load_sprite_pair(
            assets_dir, "enemy_unit_3_1.png", "enemy_unit_3_2.png"
        )

        self.money_bg = resources.load_photo(assets_dir, "money.png")
        self._money_panel_x = 24
        self._money_panel_y = 16

    _TOWER_ZOOM = 2

    def _load_tower_sprite(self, assets_dir, filename):
        path = os.path.join(assets_dir, filename)
        return self._zoom_sprite(tk.PhotoImage(file=path), self._TOWER_ZOOM)

    def _load_tower_shoot_variant(self, assets_dir, filename, fallback):
        path = os.path.join(assets_dir, filename)
        if not os.path.isfile(path):
            return fallback
        try:
            return self._load_tower_sprite(assets_dir, filename)
        except tk.TclError:
            return fallback

    def _zoom_sprite(self, photo, factor):
        """Увеличение PhotoImage (только 2x или 4x для пиксель-арта)."""
        if not factor or factor <= 1:
            return photo
        if int(factor) not in (2, 4):
            factor = 2
        try:
            return photo.zoom(int(factor), int(factor))
        except Exception:
            return photo

    def _load_sprite_pair(self, assets_dir, idle_name, attack_name, max_height=None):
        """Пара кадров: *_1 — спокойствие/ходьба, *_2 — удар/атака."""

        def load_one(filename):
            path = os.path.join(assets_dir, filename)
            if not os.path.isfile(path):
                return None
            try:
                img = tk.PhotoImage(file=path)
                if max_height is not None:
                    return self._scale_sprite_if_tall(img, max_height=max_height)
                return img
            except tk.TclError:
                return None

        idle = load_one(idle_name)
        attack = load_one(attack_name)

        if idle and not attack:
            attack = idle
        if attack and not idle:
            idle = attack

        return idle, attack

    def _load_sprite_triple(self, assets_dir, idle_name, windup_name, attack_name, max_height=None):
        """Три кадра: *_1 — покой, *_2 — подготовка, *_3 — удар."""

        def load_one(filename):
            path = os.path.join(assets_dir, filename)
            if not os.path.isfile(path):
                return None
            try:
                img = tk.PhotoImage(file=path)
                if max_height is not None:
                    return self._scale_sprite_if_tall(img, max_height=max_height)
                return img
            except tk.TclError:
                return None

        idle = load_one(idle_name)
        windup = load_one(windup_name)
        attack = load_one(attack_name)

        if idle and not windup:
            windup = attack or idle
        if idle and not attack:
            attack = windup or idle
        if attack and not idle:
            idle = attack
        if windup and not idle:
            idle = windup

        return idle, windup, attack

    def _scale_sprite_if_tall(self, photo, max_height=88):
        h = photo.height()
        if h <= max_height:
            return photo
        factor = max(2, (h + max_height - 1) // max_height)
        try:
            return photo.subsample(factor, factor)
        except tk.TclError:
            return photo

    def create_scene(self):

        # чтобы при перезапуске не копились старые кнопки
        for attr in (
            "upgrade_btn",
            "shoot_btn",
            "pause_btn",
            "unit1_btn",
            "unit2_btn",
            "unit3_btn",
        ):
            self._destroy_widget_if_exists(getattr(self, attr, None))

        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self.bg)

        self.tower_player_id = self.canvas.create_image(
            140, 720, anchor="s", image=self.tower_player
        )
        self.tower_enemy_id = self.canvas.create_image(
            WIDTH - 140, 720, anchor="s", image=self.tower_enemy
        )

        self.player_hp_bar = self.canvas.create_rectangle(40, 80, 340, 110, fill="green")

        self.enemy_hp_bar = self.canvas.create_rectangle(
            WIDTH - 340, 80,
            WIDTH - 40, 110,
            fill="green"
        )

        if self.money_bg:
            self.money_bg_id = self.canvas.create_image(
                self._money_panel_x,
                self._money_panel_y,
                anchor="nw",
                image=self.money_bg,
            )
            money_cx = self._money_panel_x + self.money_bg.width() // 2
            money_cy = self._money_panel_y + self.money_bg.height() // 2
        else:
            self.money_bg_id = None
            money_cx, money_cy = 80, 40

        self.money_text = self.canvas.create_text(
            money_cx,
            money_cy,
            text=f"Деньги: {self.money}",
            font=self.font_money,
            fill="white",
            anchor="center",
        )

        self.upgrade_btn = tk.Button(
            self.root,
            text="Прокачка дохода (30)",
            font=self.font_ui,
            command=self.upgrade_income
        )

        self.canvas.create_window(420, 40, window=self.upgrade_btn)

        self.shoot_btn = tk.Button(
            self.root,
            text="Выстрел (20)",
            font=self.font_ui,
            command=self.start_qte
        )

        self.canvas.create_window(650, 40, window=self.shoot_btn)

        self.pause_btn = tk.Button(
            self.root,
            text="Пауза",
            font=self.font_ui,
            command=self.toggle_pause
        )

        self.canvas.create_window(WIDTH - 120, 40, window=self.pause_btn)

        self.create_unit_buttons()

    def create_unit_buttons(self):

        self.unit1_btn = tk.Button(
            self.root,
            text="Доходяга (30)",
            font=self.font_ui,
            command=lambda: self.spawn_unit(30, 120, 6, 1.8, 1, "blue", "melee")
        )

        self.unit2_btn = tk.Button(
            self.root,
            text="Лучник (70)",
            font=self.font_ui,
            command=lambda: self.spawn_unit(70, 90, 16, 1.4, 1.2, "purple", "archer")
        )

        self.unit3_btn = tk.Button(
            self.root,
            text="Мегажирнич (120)",
            font=self.font_ui,
            command=lambda: self.spawn_unit(120, 420, 28, 0.8, 2, "orange", "splash")
        )

        self.canvas.create_window(500, HEIGHT - 60, window=self.unit1_btn)
        self.canvas.create_window(800, HEIGHT - 60, window=self.unit2_btn)
        self.canvas.create_window(1100, HEIGHT - 60, window=self.unit3_btn)

    def spawn_unit(self, cost, hp, damage, speed, attack_speed, color, kind):

        if self.money < cost or self.game_over:
            return
        self.money -= cost
        self.canvas.itemconfig(
            self.money_text,
            text=f"Деньги: {self.money}"
        )

        spawn_x = 260
        enemy_units = [u for u in self.units if getattr(u, "is_enemy", False)]
        if enemy_units:
            front_enemy = min(
                enemy_units,
                key=lambda u: u.get_coords()[0] if hasattr(u, "get_coords") else WIDTH
            )
            ex1, _, ex2, _ = front_enemy.get_coords()
            enemy_center = (ex1 + ex2) / 2
            if enemy_center < spawn_x:
                spawn_x = max(180, enemy_center - 60)

        if kind == "melee":
            sprites = self._unit1_sprite_pair(for_enemy=False)
        elif kind == "archer":
            sprites = self._unit2_sprites(for_enemy=False)
        elif kind == "splash":
            sprites = self._unit3_sprite_pair(for_enemy=False)
        else:
            sprites = (None, None, None)

        spawn_y = 720

        unit = Unit(
            self.canvas,
            spawn_x,
            spawn_y,
            hp,
            damage,
            speed,
            attack_speed,
            color,
            False,
            kind,
            sprite_idle=sprites[0],
            sprite_attack=sprites[2] if len(sprites) > 2 else sprites[1],
            sprite_windup=sprites[1] if len(sprites) > 2 and sprites[1] is not None else None,
        )
        self.units.append(unit)

    def _unit1_sprite_pair(self, for_enemy=False):
        if for_enemy:
            idle = getattr(self, "enemy_unit1_idle", None)
            attack = getattr(self, "enemy_unit1_attack", None)
        else:
            idle = getattr(self, "unit1_idle", None)
            attack = getattr(self, "unit1_attack", None)
        if idle and attack:
            return idle, attack
        return None, None

    def _unit2_sprites(self, for_enemy=False):
        if for_enemy:
            idle = getattr(self, "enemy_unit2_idle", None)
            windup = getattr(self, "enemy_unit2_windup", None)
            attack = getattr(self, "enemy_unit2_attack", None)
        else:
            idle = getattr(self, "unit2_idle", None)
            windup = getattr(self, "unit2_windup", None)
            attack = getattr(self, "unit2_attack", None)
        if idle and attack:
            return idle, windup, attack
        return None, None, None

    def _unit3_sprite_pair(self, for_enemy=False):
        if for_enemy:
            idle = getattr(self, "enemy_unit3_idle", None)
            attack = getattr(self, "enemy_unit3_attack", None)
        else:
            idle = getattr(self, "unit3_idle", None)
            attack = getattr(self, "unit3_attack", None)
        if idle and attack:
            return idle, None, attack
        return None, None, None

    def _flash_player_tower_shoot(self, duration_ms=250):
        if self.tower_player_shoot is self.tower_player:
            return

        self.canvas.itemconfig(self.tower_player_id, image=self.tower_player_shoot)

        def restore():
            try:
                if self.canvas.winfo_exists():
                    self.canvas.itemconfig(self.tower_player_id, image=self.tower_player)
            except tk.TclError:
                pass

        self.root.after(duration_ms, restore)

    def _flash_enemy_tower_shoot(self, duration_ms=250):
        if self.tower_enemy_shoot is self.tower_enemy:
            return

        self.canvas.itemconfig(self.tower_enemy_id, image=self.tower_enemy_shoot)

        def restore():
            try:
                if self.canvas.winfo_exists():
                    self.canvas.itemconfig(self.tower_enemy_id, image=self.tower_enemy)
            except tk.TclError:
                pass

        self.root.after(duration_ms, restore)

    def _enemy_tower_resolve_shot(self, damage):
        """Выстрел вражеской башни по игроку: анимация и урон (0 — промах)."""
        self._flash_enemy_tower_shoot()
        if damage <= 0:
            return
        self.player_hp -= damage
        if self.player_hp < 0:
            self.player_hp = 0
        self.update_hp_bars()
        self.check_game_over()

    def _enemy_spawn_x(self):
        spawn_x = WIDTH - 260
        player_units = [u for u in self.units if not getattr(u, "is_enemy", False)]
        if player_units:
            front_player = max(
                player_units,
                key=lambda u: u.get_coords()[2] if hasattr(u, "get_coords") else 0
            )
            px1, _, px2, _ = front_player.get_coords()
            player_center = (px1 + px2) / 2
            if player_center > spawn_x:
                spawn_x = min(WIDTH - 180, player_center + 60)
        return spawn_x

    def spawn_enemy_by_type(self, choice):
        """Спавн юнита бота по типу 1..3; False если не хватает денег."""
        spawn_x = self._enemy_spawn_x()

        if choice == 1 and self.enemy_money >= 30:
            self.enemy_money -= 30
            sp = self._unit1_sprite_pair(for_enemy=True)
            self.units.append(
                Unit(
                    self.canvas,
                    spawn_x,
                    720,
                    120,
                    6,
                    -1.8,
                    1,
                    "red",
                    True,
                    "melee",
                    sprite_idle=sp[0],
                    sprite_attack=sp[1],
                )
            )
            return True

        if choice == 2 and self.enemy_money >= 70:
            self.enemy_money -= 70
            sp = self._unit2_sprites(for_enemy=True)
            self.units.append(
                Unit(
                    self.canvas,
                    spawn_x,
                    720,
                    90,
                    16,
                    -1.4,
                    1.2,
                    "darkred",
                    True,
                    "archer",
                    sprite_idle=sp[0],
                    sprite_windup=sp[1],
                    sprite_attack=sp[2],
                )
            )
            return True

        if choice == 3 and self.enemy_money >= 120:
            self.enemy_money -= 120
            sp = self._unit3_sprite_pair(for_enemy=True)
            self.units.append(
                Unit(
                    self.canvas,
                    spawn_x,
                    720,
                    420,
                    28,
                    -0.8,
                    2,
                    "black",
                    True,
                    "splash",
                    sprite_idle=sp[0],
                    sprite_attack=sp[2],
                )
            )
            return True

        return False

    def update_units(self):


        for unit in self.units:
            if hasattr(unit, "resume"):
                unit.resume()
            if hasattr(unit, "in_combat"):
                unit.in_combat = False

        def _separate_overlapping_bodies(a, b, body_a, body_b):
            """

            """
            ax1, ay1, ax2, ay2 = body_a
            bx1, by1, bx2, by2 = body_b

            overlap = min(ax2, bx2) - max(ax1, bx1)
            if overlap <= 0:
                return

            ac = (ax1 + ax2) / 2
            bc = (bx1 + bx2) / 2
            if ac == bc:

                ac -= 0.5
                bc += 0.5

            a_w = max(1.0, (ax2 - ax1))
            b_w = max(1.0, (bx2 - bx1))
            a_half = a_w / 2.0
            b_half = b_w / 2.0

            if ac < bc:
                new_ac = (bc - (a_half + b_half)) - 0.1
                new_bc = (new_ac + (a_half + b_half)) + 0.1
            else:
                new_bc = (ac - (a_half + b_half)) - 0.1
                new_ac = (new_bc + (a_half + b_half)) + 0.1

            if hasattr(a, "x"):
                a.x = new_ac
            if hasattr(b, "x"):
                b.x = new_bc

        units_snapshot = list(self.units)
        for attacker in units_snapshot:
            if attacker not in self.units:
                continue

            enemies = [
                u for u in self.units
                if getattr(u, "is_enemy", False) != getattr(attacker, "is_enemy", False)
            ]
            if not enemies:
                continue

            atk_box = attacker.get_attack_box()

            in_range = []
            for cand in enemies:
                if cand is attacker:
                    continue
                if aabb_intersect(atk_box, cand.get_body_box()):
                    in_range.append(cand)

            if not in_range:
                continue

            if getattr(attacker, "is_enemy", False):
                target = max(in_range, key=lambda u: u.get_body_box()[2])
            else:
                target = min(in_range, key=lambda u: u.get_body_box()[0])

            if hasattr(attacker, "stop"):
                attacker.stop()
            if hasattr(attacker, "in_combat"):
                attacker.in_combat = True

            if attacker.can_attack():
                attacker.note_attack()
                self._deal_damage_with_splash(attacker, target)

        units_sorted = sorted(self.units, key=lambda u: u.get_coords()[0] if hasattr(u, "get_coords") else 0)
        for i in range(len(units_sorted) - 1):
            u1 = units_sorted[i]
            u2 = units_sorted[i + 1]

            if getattr(u1, "is_enemy", False) == getattr(u2, "is_enemy", False):
                continue

            body1 = u1.get_body_box()
            body2 = u2.get_body_box()
            if not aabb_intersect(body1, body2):
                continue

            if hasattr(u1, "stop"):
                u1.stop()
            if hasattr(u2, "stop"):
                u2.stop()
            if hasattr(u1, "in_combat"):
                u1.in_combat = True
            if hasattr(u2, "in_combat"):
                u2.in_combat = True
            _separate_overlapping_bodies(u1, u2, body1, body2)

        for unit in self.units[:]:

            alive = unit.update()

            if not alive:
                self.units.remove(unit)
                continue

            if not getattr(unit, "in_combat", False):

                atk = unit.get_attack_box()

                if getattr(unit, "is_enemy", False):
                    if aabb_intersect(atk, player_tower_body_box()) and unit.can_attack():

                        unit.note_attack()
                        self.player_hp -= unit.damage

                        if self.player_hp < 0:
                            self.player_hp = 0

                        self.update_hp_bars()
                        self.check_game_over()

                else:
                    if aabb_intersect(atk, enemy_tower_body_box()) and unit.can_attack():

                        unit.note_attack()
                        self.enemy_hp -= unit.damage

                        if self.enemy_hp < 0:
                            self.enemy_hp = 0

                        self.update_hp_bars()
                        self.check_game_over()

    def _deal_damage_with_splash(self, attacker, main_target):
        """Наносит урон основному цели и, при необходимости, по области."""

        # основной урон по выбранной цели
        main_target.hp -= attacker.damage

        # только мегажирнич / аналогичный юнит бьёт по площади
        if getattr(attacker, "kind", "melee") != "splash":
            return

        # радиус сплэша вокруг основной цели
        splash_radius = 80

        x1_t, y1_t, x2_t, y2_t = main_target.get_coords()
        center_target = (x1_t + x2_t) / 2

        for other in self.units:

            # тот же отряд, что и основная цель, и не она сама
            if other is main_target:
                continue

            if getattr(other, "is_enemy", False) != getattr(main_target, "is_enemy", False):
                continue

            x1_o, y1_o, x2_o, y2_o = other.get_coords()
            center_other = (x1_o + x2_o) / 2

            if abs(center_other - center_target) <= splash_radius:
                other.hp -= attacker.damage

    def game_loop(self):

        try:
            if not self.paused and not self.game_over:

                self.update_money()
                self.update_enemy_money()
                self.enemy_ai()
                self.update_units()

                if self.qte_active:
                    self.update_qte()
        except Exception:
            import traceback
            traceback.print_exc()

        self.root.after(int(1000 / FPS), self.game_loop)

    def update_money(self):

        self.money_timer += 1

        if self.money_timer >= FPS:
            self.money += self.money_income
            self.money_timer = 0

            self.canvas.itemconfig(
                self.money_text,
                text=f"Деньги: {self.money}"
            )

    def update_enemy_money(self):

        self.enemy_money_timer += 1

        if self.enemy_money_timer >= FPS:
            self.enemy_money += self.enemy_income
            self.enemy_money_timer = 0

    def enemy_ai(self):
        self.bot.tick(self)

    def upgrade_income(self):

        max_level = 4

        if self.money_level >= max_level:
            self.upgrade_btn.config(text="Доход MAX")
            return

        cost = 30 * self.money_level

        if self.money >= cost:

            self.money -= cost
            self.money_level += 1
            self.money_income = self.money_level

            self.canvas.itemconfig(
                self.money_text,
                text=f"Деньги: {self.money}"
            )

            # обновляем цену кнопки
            next_cost = 30 * self.money_level

            if self.money_level < max_level:
                self.upgrade_btn.config(
                    text=f"Прокачка дохода ({next_cost})"
                )
            else:
                self.upgrade_btn.config(text="Доход MAX")

    def toggle_pause(self):

        if self.game_over:
            return

        self.paused = True
        self.show_pause_menu()

    def show_pause_menu(self):

        self.pause_overlay = self.canvas.create_rectangle(
            0, 0, WIDTH, HEIGHT,
            fill="black",
            stipple="gray50"
        )

        frame = tk.Frame(self.root)

        btn1 = tk.Button(
            frame, text="Продолжить", width=20, font=self.font_ui, command=self.resume_game
        )
        btn1.pack(pady=10)

        btn2 = tk.Button(
            frame, text="Об игре", width=20, font=self.font_ui, command=self.show_about
        )
        btn2.pack(pady=10)

        btn3 = tk.Button(
            frame, text="Выйти в меню", width=20, font=self.font_ui, command=self.confirm_exit
        )
        btn3.pack(pady=10)

        self.pause_window = self.canvas.create_window(
            WIDTH // 2,
            HEIGHT // 2,
            window=frame
        )

    def resume_game(self):

        self.paused = False

        self.canvas.delete(self.pause_overlay)
        self.canvas.delete(self.pause_window)

    def confirm_exit(self):

        answer = messagebox.askyesno(
            "Выход",
            "Вы уверены что хотите выйти?\nПрогресс текущей сессии будет потерян."
        )

        if answer:
            self.root.destroy()
            from menu import MainMenu
            MainMenu()

    def show_about(self):
        text = (
            "«Стреляющие башни» — пошаговый экшен на одном экране: ваша башня слева, "
            "вражеская справа. Цель — обнулить HP вражеской башни раньше, чем падёт ваша.\n\n"
            "ТЕХНИЧЕСКИ\n"
            "Игра целиком на Python и Tkinter (без Pygame и сторонних движков).\n\n"
            "ЭКОНОМИКА\n"
            "Каждую секунду приходит золото; его можно потратить на юнитов и выстрелы. "
            "Кнопка «Прокачка дохода» повышает прибыль (до 4 уровней, цена растёт). "
            "У противника своя казна и такая же система дохода — бот со временем тоже качает экономику.\n\n"
            "ЮНИТЫ (стоимость в скобках)\n"
            "• Доходяга (30) — недорогой боец ближнего боя.\n"
            "• Лучник (70) — атакует с дистанции, пока зона досягаемости пересекается с врагом.\n"
            "• Мегажирнич (120) — тяжёлый боец; удары бьют по площади вокруг цели.\n"
            "Атака срабатывает, когда прямоугольник дальности атаки пересекается с телом цели "
            "(и с хитбоксом башни — дистанция та же, что и к юнитам).\n\n"
            "ВАША БАШНЯ — ВЫСТРЕЛ (20 золота)\n"
            "Запускается мини-игра: ползунок бегает по полосе. В зелёной зоне — максимальный урон "
            "по вражеской башне, в жёлтой — меньше, в красных краях — промах. "
            "Остановите маркер клавишей Пробел.\n\n"
            "ПРОТИВНИК\n"
            "ИИ в каждой партии ведёт себя по-разному: чаще стреляет из башни или чаще зовёт юнитов, "
            "по-разному выбирает дешёвых и дорогих бойцов. Башня бота тоже стреляет по вам: "
            "урон случайный (крит, обычный выстрел или промах). Со временем бот действует чаще.\n\n"
            "Пауза открывается кнопкой «Пауза»; здесь же этот текст «Об игре»."
        )

        messagebox.showinfo("Об игре", text)

    def update_hp_bars(self):

        player_ratio = self.player_hp / self.max_hp
        enemy_ratio = self.enemy_hp / self.max_hp

        self.canvas.coords(
            self.player_hp_bar,
            40, 80,
            40 + 300 * player_ratio, 110
        )

        self.canvas.coords(
            self.enemy_hp_bar,
            WIDTH - 340, 80,
            WIDTH - 340 + 300 * enemy_ratio, 110
        )

    def start_qte(self):

        cost = 20

        if self.money < cost or self.qte_active or self.game_over:
            return

        self.money -= cost

        self.canvas.itemconfig(
            self.money_text,
            text=f"Деньги: {self.money}"
        )

        self.qte_active = True
        self.qte_value = 0
        self.qte_direction = 1
        self.qte_elements.clear()

        bg = self.canvas.create_rectangle(
            WIDTH // 2 - 200,
            HEIGHT // 2 - 30,
            WIDTH // 2 + 200,
            HEIGHT // 2 + 30,
            fill="black"
        )

        self.qte_elements.append(bg)

        red_left = self.canvas.create_rectangle(
            WIDTH // 2 - 200,
            HEIGHT // 2 - 30,
            WIDTH // 2 - 80,
            HEIGHT // 2 + 30,
            fill="red"
        )

        red_right = self.canvas.create_rectangle(
            WIDTH // 2 + 80,
            HEIGHT // 2 - 30,
            WIDTH // 2 + 200,
            HEIGHT // 2 + 30,
            fill="red"
        )

        yellow = self.canvas.create_rectangle(
            WIDTH // 2 - 80,
            HEIGHT // 2 - 30,
            WIDTH // 2 + 80,
            HEIGHT // 2 + 30,
            fill="yellow"
        )

        green = self.canvas.create_rectangle(
            WIDTH // 2 - QTE_CRIT_HALF,
            HEIGHT // 2 - 30,
            WIDTH // 2 + QTE_CRIT_HALF,
            HEIGHT // 2 + 30,
            fill="green"
        )

        self.qte_elements.extend([red_left, red_right, yellow, green])

        self.qte_marker = self.canvas.create_rectangle(
            WIDTH // 2 - 200,
            HEIGHT // 2 - 40,
            WIDTH // 2 - 190,
            HEIGHT // 2 + 40,
            fill="white"
        )

        self.qte_elements.append(self.qte_marker)

        self.root.bind("<space>", self.resolve_qte)

    def update_qte(self):

        self.qte_value += self.qte_speed * self.qte_direction

        if self.qte_value >= 1:
            self.qte_value = 1
            self.qte_direction = -1

        if self.qte_value <= 0:
            self.qte_value = 0
            self.qte_direction = 1

        x = (WIDTH // 2 - 200) + 400 * self.qte_value

        self.canvas.coords(
            self.qte_marker,
            x - 5,
            HEIGHT // 2 - 40,
            x + 5,
            HEIGHT // 2 + 40
        )

    def resolve_qte(self, event):

        if not self.qte_active:
            return

        x = (WIDTH // 2 - 200) + 400 * self.qte_value
        center = WIDTH // 2

        if abs(x - center) <= QTE_CRIT_HALF:
            damage = 120
        elif abs(x - center) <= QTE_YELLOW_HALF:
            damage = 60
        else:
            damage = 0

        self._flash_player_tower_shoot()

        self.enemy_hp -= damage

        if self.enemy_hp < 0:
            self.enemy_hp = 0

        self.update_hp_bars()
        self.check_game_over()

        for element in self.qte_elements:
            self.canvas.delete(element)

        self.qte_elements.clear()
        self.qte_active = False

        self.root.unbind("<space>")

    def check_game_over(self):

        if self.enemy_hp <= 0:
            self.end_game(True)

        elif self.player_hp <= 0:
            self.end_game(False)

    def end_game(self, win):

        self.game_over = True
        self.paused = True

        self._end_overlay_id = self.canvas.create_rectangle(
            0, 0, WIDTH, HEIGHT,
            fill="black",
            stipple="gray50"
        )

        text = "Вы победили!" if win else "Вы проиграли..."

        self._end_text_id = self.canvas.create_text(
            WIDTH // 2,
            HEIGHT // 2 - 50,
            text=text,
            font=self.font_end_title,
            fill="white"
        )

        self._play_again_btn = tk.Button(
            self.root,
            text="Играть снова",
            font=self.font_end_btn,
            command=self.play_again,
        )

        self._return_to_menu_btn = tk.Button(
            self.root,
            text="Выйти в меню",
            font=self.font_end_btn,
            command=self.return_to_menu,
        )

        self._play_again_window_id = self.canvas.create_window(
            WIDTH // 2,
            HEIGHT // 2 + 20,
            window=self._play_again_btn,
        )

        self._return_to_menu_window_id = self.canvas.create_window(
            WIDTH // 2,
            HEIGHT // 2 + 90,
            window=self._return_to_menu_btn,
        )

    def play_again(self):
        # удаляем элементы экрана победы/поражения
        for cid in (
            getattr(self, "_play_again_window_id", None),
            getattr(self, "_return_to_menu_window_id", None),
            getattr(self, "_end_text_id", None),
            getattr(self, "_end_overlay_id", None),
        ):
            if cid:
                try:
                    self.canvas.delete(cid)
                except Exception:
                    pass

        self._destroy_widget_if_exists(getattr(self, "_play_again_btn", None))
        self._destroy_widget_if_exists(getattr(self, "_return_to_menu_btn", None))

        self._reset_session_state()
        self.create_scene()

    def return_to_menu(self):

        self.root.destroy()

        from menu import MainMenu
        MainMenu()
