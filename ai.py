"""
Поведение ИИ противника: спавн юнитов, выстрелы по башне игрока,
«личность» на сессию и прокачка дохода со временем.
"""

import random
from typing import Optional

FPS = 60

SHOOT_COST = 20
UNIT_COSTS = (0, 30, 70, 120)

# урон выстрела башни (игрок за идеальный QTE — до 120; бот слабее и рандомен)
SHOT_DAMAGE_NORMAL = 32
SHOT_DAMAGE_CRIT = 56

# базовые интервалы (кадры), сжимаются с уровнем дохода и «личностью»
BASE_SPAWN_FRAMES = int(FPS * 17)
BASE_SHOOT_FRAMES = int(FPS * 15)

# минимумы, чтобы поздней игрой бот не засыпал действиями
MIN_SPAWN_FRAMES = int(FPS * 7)
MIN_SHOOT_FRAMES = int(FPS * 9)


class EnemyBotController:
    """
    На каждую новую игру заново выбирается уклон: стрельба / юниты.
    Два независимых таймера: выстрел и спавн. Доход качается по мере накопления золота.
    """

    def __init__(self):
        self._rng = random.Random()
        self._roll_personality()

        self._spawn_accum = 0
        self._shoot_accum = 0
        self._frames = 0

    def _roll_personality(self):
        # 0 = упор на юнитов, 1 = упор на стрельбу
        self.shoot_emphasis = self._rng.uniform(0.22, 0.78)
        # при выборе юнита: склонность к дешёвым / сбалансированным / дорогим
        r = self._rng.random()
        if r < 0.34:
            self.unit_cost_profile = "cheap"
        elif r < 0.67:
            self.unit_cost_profile = "balanced"
        else:
            self.unit_cost_profile = "expensive"

    def _spawn_interval(self, scene) -> int:
        lvl = max(1, getattr(scene, "enemy_money_level", 1))
        speed = 1.0 + 0.11 * (lvl - 1)
        # чем выше shoot_emphasis, тем реже относительно спавн (дольше интервал)
        style = 0.82 + 0.55 * self.shoot_emphasis
        raw = BASE_SPAWN_FRAMES / (speed * style)
        return max(MIN_SPAWN_FRAMES, int(raw))

    def _shoot_interval(self, scene) -> int:
        lvl = max(1, getattr(scene, "enemy_money_level", 1))
        speed = 1.0 + 0.10 * (lvl - 1)
        # чем выше shoot_emphasis, тем чаще стрельба (короче интервал)
        style = 1.18 - 0.50 * self.shoot_emphasis
        raw = BASE_SHOOT_FRAMES / (speed * style)
        return max(MIN_SHOOT_FRAMES, int(raw))

    def _unit_choice_weights(self):
        if self.unit_cost_profile == "cheap":
            return {1: 4, 2: 2, 3: 1}
        if self.unit_cost_profile == "expensive":
            return {1: 1, 2: 2, 3: 4}
        return {1: 2, 2: 3, 3: 2}

    def _pick_unit_choice(self, scene) -> Optional[int]:
        money = scene.enemy_money
        weights = self._unit_choice_weights()
        options = [c for c in (1, 2, 3) if money >= UNIT_COSTS[c]]
        if not options:
            return None
        w = [weights[c] for c in options]
        return self._rng.choices(options, weights=w, k=1)[0]

    def _try_upgrade_income(self, scene) -> None:
        max_level = 4
        lvl = getattr(scene, "enemy_money_level", 1)
        if lvl >= max_level:
            return
        cost = 30 * lvl
        if scene.enemy_money < cost:
            return
        # не тратит всё мгновенно: небольшая задержка «решения», затем покупка
        if self._rng.random() > 0.55:
            return
        scene.enemy_money -= cost
        scene.enemy_money_level = lvl + 1
        scene.enemy_income = scene.enemy_money_level

    def _roll_shot_damage(self) -> int:
        r = self._rng.random()
        if r < 0.25:
            return SHOT_DAMAGE_CRIT
        if r < 0.75:
            return SHOT_DAMAGE_NORMAL
        return 0

    def _try_shoot(self, scene) -> bool:
        if scene.enemy_money < SHOOT_COST:
            return False
        scene.enemy_money -= SHOOT_COST
        dmg = self._roll_shot_damage()
        scene._enemy_tower_resolve_shot(dmg)
        return True

    def tick(self, scene) -> None:
        if scene.game_over or scene.paused:
            return

        self._frames += 1
        self._spawn_accum += 1
        self._shoot_accum += 1

        # прокачка дохода: проверка раз в секунду
        if self._frames % FPS == 0:
            self._try_upgrade_income(scene)

        si = self._spawn_interval(scene)
        hi = self._shoot_interval(scene)

        shoot_ready = self._shoot_accum >= hi
        spawn_ready = self._spawn_accum >= si

        if not shoot_ready and not spawn_ready:
            return

        # если оба готовы в один кадр — выбор по «личности» + доступности денег
        if shoot_ready and spawn_ready:
            can_shoot = scene.enemy_money >= SHOOT_COST
            can_spawn = self._pick_unit_choice(scene) is not None
            if can_shoot and can_spawn:
                if self._rng.random() < self.shoot_emphasis:
                    self._shoot_accum = 0
                    self._try_shoot(scene)
                else:
                    self._spawn_accum = 0
                    ch = self._pick_unit_choice(scene)
                    if ch is not None:
                        scene.spawn_enemy_by_type(ch)
            elif can_shoot:
                self._shoot_accum = 0
                self._try_shoot(scene)
            elif can_spawn:
                self._spawn_accum = 0
                ch = self._pick_unit_choice(scene)
                if ch is not None:
                    scene.spawn_enemy_by_type(ch)
            else:
                self._shoot_accum = 0
                self._spawn_accum = 0
            return

        if shoot_ready:
            self._shoot_accum = 0
            self._try_shoot(scene)
            return

        if spawn_ready:
            self._spawn_accum = 0
            ch = self._pick_unit_choice(scene)
            if ch is not None:
                scene.spawn_enemy_by_type(ch)
