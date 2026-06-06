import random
from typing import Optional

FPS = 60

SHOOT_COST = 20
UNIT_COSTS = (0, 30, 70, 120)

SHOT_DAMAGE_NORMAL = 32
SHOT_DAMAGE_CRIT = 56

BASE_SPAWN_FRAMES = int(FPS * 11)
BASE_SHOOT_FRAMES = int(FPS * 12)

MIN_SPAWN_FRAMES = int(FPS * 2.8)
MIN_SHOOT_FRAMES = int(FPS * 4.5)

# минуты матча, с которых бот может вызывать тип юнита
UNIT_UNLOCK_MINUTES = {1: 0.0, 2: 2.0, 3: 4.0}

MAX_TIME_PRESSURE = 1.0
TIME_PRESSURE_PER_MIN = 0.14
LEVEL_PRESSURE_PER_STEP = 0.16


class EnemyBotController:
    def __init__(self):
        self._rng = random.Random()
        self._roll_personality()

        self._spawn_accum = 0
        self._shoot_accum = 0
        self._frames = 0

    def _roll_personality(self):
        self.shoot_emphasis = self._rng.uniform(0.22, 0.78)
        r = self._rng.random()
        if r < 0.34:
            self.unit_cost_profile = "cheap"
        elif r < 0.67:
            self.unit_cost_profile = "balanced"
        else:
            self.unit_cost_profile = "expensive"

    def _game_minutes(self) -> float:
        return self._frames / (FPS * 60.0)

    def _difficulty_multiplier(self, scene) -> float:
        lvl = max(1, getattr(scene, "enemy_money_level", 1))
        time_part = min(MAX_TIME_PRESSURE, self._game_minutes() * TIME_PRESSURE_PER_MIN)
        level_part = LEVEL_PRESSURE_PER_STEP * (lvl - 1)
        return 1.0 + time_part + level_part

    def _spawn_interval(self, scene) -> int:
        speed = self._difficulty_multiplier(scene)
        style = 0.82 + 0.55 * self.shoot_emphasis
        raw = BASE_SPAWN_FRAMES / (speed * style)
        return max(MIN_SPAWN_FRAMES, int(raw))

    def _shoot_interval(self, scene) -> int:
        speed = self._difficulty_multiplier(scene)
        style = 1.18 - 0.50 * self.shoot_emphasis
        raw = BASE_SHOOT_FRAMES / (speed * style)
        return max(MIN_SHOOT_FRAMES, int(raw))

    def _unlocked_unit_types(self):
        mins = self._game_minutes()
        return [t for t in (1, 2, 3) if mins >= UNIT_UNLOCK_MINUTES[t]]

    def _unit_choice_weights(self):
        mins = self._game_minutes()
        weights = {1: 3, 2: 1, 3: 1}

        if mins >= UNIT_UNLOCK_MINUTES[2]:
            weights[2] = 4
            weights[1] = 2
        if mins >= UNIT_UNLOCK_MINUTES[3]:
            weights[3] = 5
            weights[2] = 3
            weights[1] = 1

        if self.unit_cost_profile == "cheap":
            weights[1] += 2
            weights[3] = max(1, weights[3] - 1)
        elif self.unit_cost_profile == "expensive":
            weights[3] += 2
            weights[1] = max(1, weights[1] - 1)

        return weights

    def _pick_unit_choice(self, scene) -> Optional[int]:
        money = scene.enemy_money
        weights = self._unit_choice_weights()
        unlocked = set(self._unlocked_unit_types())
        options = [
            c for c in (1, 2, 3)
            if c in unlocked and money >= UNIT_COSTS[c]
        ]
        if not options:
            return None
        w = [weights[c] for c in options]
        return self._rng.choices(options, weights=w, k=1)[0]

    def _upgrade_chance(self) -> float:
        base = 0.62
        return min(0.92, base + self._game_minutes() * 0.04)

    def _try_upgrade_income(self, scene) -> None:
        max_level = 4
        lvl = getattr(scene, "enemy_money_level", 1)
        if lvl >= max_level:
            return
        cost = 30 * lvl
        if scene.enemy_money < cost:
            return
        if self._rng.random() > self._upgrade_chance():
            return
        scene.enemy_money -= cost
        scene.enemy_money_level = lvl + 1
        scene.enemy_income = scene.enemy_money_level

    def _roll_shot_damage(self) -> int:
        mins = self._game_minutes()
        crit_chance = min(0.42, 0.22 + mins * 0.035)
        miss_chance = max(0.06, 0.30 - mins * 0.03)

        r = self._rng.random()
        if r < crit_chance:
            return SHOT_DAMAGE_CRIT
        if r < 1.0 - miss_chance:
            return SHOT_DAMAGE_NORMAL
        return 0

    def _try_shoot(self, scene) -> bool:
        if scene.enemy_money < SHOOT_COST:
            return False
        scene.enemy_money -= SHOOT_COST
        dmg = self._roll_shot_damage()
        scene._enemy_tower_resolve_shot(dmg)
        return True

    def _try_combo_turn(self, scene) -> bool:
        if scene.enemy_money < SHOOT_COST:
            return False
        self._try_shoot(scene)
        ch = self._pick_unit_choice(scene)
        if ch is not None:
            scene.spawn_enemy_by_type(ch)
        return True

    def tick(self, scene) -> None:
        if scene.game_over or scene.paused:
            return

        self._frames += 1
        self._spawn_accum += 1
        self._shoot_accum += 1

        if self._frames % FPS == 0:
            self._try_upgrade_income(scene)

        si = self._spawn_interval(scene)
        hi = self._shoot_interval(scene)
        pressure = self._difficulty_multiplier(scene)

        shoot_ready = self._shoot_accum >= hi
        spawn_ready = self._spawn_accum >= si

        if not shoot_ready and not spawn_ready:
            return

        if shoot_ready and spawn_ready:
            can_shoot = scene.enemy_money >= SHOOT_COST
            can_spawn = self._pick_unit_choice(scene) is not None

            combo_chance = min(0.45, 0.12 + (pressure - 1.0) * 0.22)
            if pressure >= 1.45 and can_shoot and can_spawn and self._rng.random() < combo_chance:
                self._shoot_accum = 0
                self._spawn_accum = 0
                self._try_combo_turn(scene)
                return

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
