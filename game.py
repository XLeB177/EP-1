import tkinter as tk
from tkinter import messagebox
from units import Unit

WIDTH = 1800
HEIGHT = 1000
FPS = 60


class GameScene:

    def __init__(self, root, canvas):

        self.root = root
        self.canvas = canvas

        self.paused = False
        self.game_over = False

        self.units = []

        # экономика
        self.money = 50
        self.money_level = 1
        self.money_income = 1
        self.money_timer = 0

        # экономика бота
        self.enemy_money = 50
        self.enemy_income = 1
        self.enemy_money_timer = 0

        self.enemy_spawn_cooldown = 0

        # хп
        self.player_hp = 1000
        self.enemy_hp = 1000
        self.max_hp = 1000

        # QTE
        self.qte_active = False
        self.qte_value = 0
        self.qte_direction = 1
        self.qte_speed = 0.02
        self.qte_elements = []

        self.load_sprites()
        self.create_scene()
        self.game_loop()

    def load_sprites(self):

        self.bg = tk.PhotoImage(file="assets/background.png")
        self.tower_player = tk.PhotoImage(file="assets/tower_player.png")
        self.tower_enemy = tk.PhotoImage(file="assets/tower_enemy.png")

    def create_scene(self):

        self.canvas.delete("all")

        self.canvas.create_image(0, 0, anchor="nw", image=self.bg)

        self.canvas.create_image(140, 720, anchor="s", image=self.tower_player)
        self.canvas.create_image(WIDTH - 140, 720, anchor="s", image=self.tower_enemy)

        self.player_hp_bar = self.canvas.create_rectangle(40, 80, 340, 110, fill="green")

        self.enemy_hp_bar = self.canvas.create_rectangle(
            WIDTH - 340, 80,
            WIDTH - 40, 110,
            fill="green"
        )

        self.money_text = self.canvas.create_text(
            80, 40,
            text=f"Деньги: {self.money}",
            font=("Arial", 22, "bold"),
            fill="white",
            anchor="w"
        )

        self.upgrade_btn = tk.Button(
            self.root,
            text="Прокачка дохода (30)",
            font=("Arial", 14),
            command=self.upgrade_income
        )

        self.canvas.create_window(420, 40, window=self.upgrade_btn)

        self.shoot_btn = tk.Button(
            self.root,
            text="Выстрел (20)",
            font=("Arial", 14),
            command=self.start_qte
        )

        self.canvas.create_window(650, 40, window=self.shoot_btn)

        self.pause_btn = tk.Button(
            self.root,
            text="Пауза",
            font=("Arial", 14),
            command=self.toggle_pause
        )

        self.canvas.create_window(WIDTH - 120, 40, window=self.pause_btn)

        self.create_unit_buttons()

    def create_unit_buttons(self):

        self.unit1_btn = tk.Button(
            self.root,
            text="Доходяга (30)",
            command=lambda: self.spawn_unit(30, 120, 6, 1.8, 1, "blue", "melee")
        )

        self.unit2_btn = tk.Button(
            self.root,
            text="Лучник (70)",
            command=lambda: self.spawn_unit(70, 90, 16, 1.4, 1.2, "purple", "archer")
        )

        self.unit3_btn = tk.Button(
            self.root,
            text="Меражирнич (120)",
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

        # базовая точка спавна у игрока
        spawn_x = 260

        # если враг уже прошёл дальше вперёд к нашей башне,
        # спавнимся между башней и этим врагом, чтобы защитить её
        enemy_units = [u for u in self.units if getattr(u, "is_enemy", False)]
        if enemy_units:
            # враг, который ближе всего к нашей башне (минимальный x)
            front_enemy = min(
                enemy_units,
                key=lambda u: u.get_coords()[0] if hasattr(u, "get_coords") else WIDTH
            )
            ex1, _, ex2, _ = front_enemy.get_coords()
            enemy_center = (ex1 + ex2) / 2

            # если враг уже "впереди" стандартной точки спавна
            if enemy_center < spawn_x:
                # ставим юнита между башней (примерно x=140–200) и врагом
                spawn_x = max(180, enemy_center - 60)

        unit = Unit(
            self.canvas,
            spawn_x,
            720,
            hp,
            damage,
            speed,
            attack_speed,
            color,
            False,
            kind
        )

        self.units.append(unit)

    def update_units(self):

        # сбрасываем флаги движения и боя для всех юнитов
        for unit in self.units:
            if hasattr(unit, "resume"):
                unit.resume()
            if hasattr(unit, "in_combat"):
                unit.in_combat = False

        # сортируем юнитов по позиции по X для поиска столкновений
        units_sorted = sorted(self.units, key=lambda u: u.get_coords()[0] if hasattr(u, "get_coords") else 0)

        # ближний / дальний бой юнитов (как в battle cats)
        processed_pairs = set()

        for i in range(len(units_sorted) - 1):

            u1 = units_sorted[i]
            u2 = units_sorted[i + 1]

            # интересуют только юниты противоположных сторон
            if getattr(u1, "is_enemy", False) == getattr(u2, "is_enemy", False):
                continue

            x1_1, y1_1, x2_1, y2_1 = u1.get_coords()
            x1_2, y1_2, x2_2, y2_2 = u2.get_coords()

            # центры по X для расчёта дистанции
            c1 = (x1_1 + x2_1) / 2
            c2 = (x1_2 + x2_2) / 2
            dist = abs(c1 - c2)

            # базовое условие ближнего боя (касание)
            touching = not (x2_1 < x1_2 or x2_2 < x1_1)

            # увеличенный радиус атаки для лучников
            archer_range = 260
            archer_involved = getattr(u1, "kind", "melee") == "archer" or getattr(u2, "kind", "melee") == "archer"

            in_range = touching or (archer_involved and dist <= archer_range)

            if in_range:

                pair_id = tuple(sorted((id(u1), id(u2))))

                if pair_id in processed_pairs:
                    continue

                processed_pairs.add(pair_id)

                # оба юнита останавливаются
                if hasattr(u1, "stop"):
                    u1.stop()
                if hasattr(u2, "stop"):
                    u2.stop()

                # помечаем как участвующих в бою
                if hasattr(u1, "in_combat"):
                    u1.in_combat = True
                if hasattr(u2, "in_combat"):
                    u2.in_combat = True

                # атака друг по другу с учётом скорости атаки
                if u1.can_attack():
                    self._deal_damage_with_splash(u1, u2)
                if u2.can_attack():
                    self._deal_damage_with_splash(u2, u1)

        # обновляем юнитов (движение / смерть)
        for unit in self.units[:]:

            alive = unit.update()

            if not alive:
                self.units.remove(unit)
                continue

            x1, y1, x2, y2 = unit.get_coords()

            # атаки по башням (если юнит не занят боем с другим юнитом)
            if not getattr(unit, "in_combat", False):

                if getattr(unit, "is_enemy", False):
                    # вражеский юнит у башни игрока
                    if x1 <= 200 and unit.can_attack():

                        self.player_hp -= unit.damage

                        if self.player_hp < 0:
                            self.player_hp = 0

                        self.update_hp_bars()
                        self.check_game_over()

                else:
                    # юнит игрока у башни врага
                    if x2 >= WIDTH - 220 and unit.can_attack():

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

        if not self.paused and not self.game_over:

            self.update_money()
            self.update_enemy_money()
            self.enemy_ai()
            self.update_units()

            if self.qte_active:
                self.update_qte()

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

        self.enemy_spawn_cooldown += 1

        # временно: один юнит врага каждые ~15 секунд
        if self.enemy_spawn_cooldown < FPS * 15:  # 60 * 15 = 900 тиков
            return

        self.enemy_spawn_cooldown = 0

        # бот выбирает случайного юнита
        import random
        choice = random.randint(1, 3)

        # базовая точка спавна врага
        spawn_x = WIDTH - 260

        # если наш юнит уже прошёл вперёд к вражеской башне,
        # спавним врага между своей башней и этим юнитом
        player_units = [u for u in self.units if not getattr(u, "is_enemy", False)]
        if player_units:
            # наш юнит, который ближе всего к вражеской башне (максимальный x)
            front_player = max(
                player_units,
                key=lambda u: u.get_coords()[2] if hasattr(u, "get_coords") else 0
            )
            px1, _, px2, _ = front_player.get_coords()
            player_center = (px1 + px2) / 2

            # если наш юнит уже "впереди" стандартной точки спавна врага
            if player_center > spawn_x:
                # ставим врага между своей башней (примерно WIDTH-140..WIDTH-220) и нашим юнитом
                spawn_x = min(WIDTH - 180, player_center + 60)

        if choice == 1 and self.enemy_money >= 30:

            self.enemy_money -= 30

            unit = Unit(
                self.canvas,
                spawn_x,
                720,
                120,
                6,
                -1.8,
                1,
                "red",
                True,
                "melee"
            )

            self.units.append(unit)

        elif choice == 2 and self.enemy_money >= 70:

            self.enemy_money -= 70

            unit = Unit(
                self.canvas,
                spawn_x,
                720,
                90,
                16,
                -1.4,
                1.2,
                "darkred",
                True,
                "archer"
            )

            self.units.append(unit)

        elif choice == 3 and self.enemy_money >= 120:

            self.enemy_money -= 120

            unit = Unit(
                self.canvas,
                spawn_x,
                720,
                420,
                28,
                -0.8,
                2,
                "black",
                True,
                "splash"
            )

            self.units.append(unit)

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

        btn1 = tk.Button(frame, text="Продолжить", width=20, command=self.resume_game)
        btn1.pack(pady=10)

        btn2 = tk.Button(frame, text="Об игре", width=20, command=self.show_about)
        btn2.pack(pady=10)

        btn3 = tk.Button(frame, text="Выйти в меню", width=20, command=self.confirm_exit)
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
            "Игра \"Стреляющие башни\".\n"
            "Написана на Python с использованием библиотеки Tkinter.\n\n"
            "В режиме игры вы управляете юнитами и башней,\n"
            "стараясь разрушить вражескую башню до того,\n"
            "как противник уничтожит вашу."
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

        red = self.canvas.create_rectangle(
            WIDTH // 2 - 200,
            HEIGHT // 2 - 30,
            WIDTH // 2 - 80,
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
            WIDTH // 2 - 40,
            HEIGHT // 2 - 30,
            WIDTH // 2 + 40,
            HEIGHT // 2 + 30,
            fill="green"
        )

        self.qte_elements.extend([red, yellow, green])

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

        if abs(x - center) <= 40:
            damage = 120
        elif abs(x - center) <= 80:
            damage = 60
        else:
            damage = 0

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

        self.canvas.create_rectangle(
            0, 0, WIDTH, HEIGHT,
            fill="black",
            stipple="gray50"
        )

        text = "Вы победили!" if win else "Вы проиграли..."

        self.canvas.create_text(
            WIDTH // 2,
            HEIGHT // 2 - 50,
            text=text,
            font=("Arial", 48, "bold"),
            fill="white"
        )

        btn = tk.Button(
            self.root,
            text="Выйти в меню",
            font=("Arial", 18),
            command=self.return_to_menu
        )

        self.canvas.create_window(
            WIDTH // 2,
            HEIGHT // 2 + 40,
            window=btn
        )

    def return_to_menu(self):

        self.root.destroy()

        from menu import MainMenu
        MainMenu()
