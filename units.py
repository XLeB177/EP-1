import time

WIDTH = 1800
# высота канваса — как в game.py (от неё зависит AABB башен)
HEIGHT = 1000

_TOWER_BODY_HALF_W = 100
_PLAYER_TOWER_X = 140
_ENEMY_TOWER_X = WIDTH - 140


def player_tower_body_box():
    """AABB башни игрока (цель для вражеских атак)."""
    x = _PLAYER_TOWER_X
    return (x - _TOWER_BODY_HALF_W, 0, x + _TOWER_BODY_HALF_W, HEIGHT)


def enemy_tower_body_box():
    """AABB башни противника (цель для атак игрока)."""
    x = _ENEMY_TOWER_X
    return (x - _TOWER_BODY_HALF_W, 0, x + _TOWER_BODY_HALF_W, HEIGHT)


# горизонтальная дальность атаки от передней границы модели (пиксели)
_ATTACK_REACH = {
    "melee": 28,
    "archer": 260,
    "splash": 48,
}


def aabb_intersect(a, b):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    return not (ax2 < bx1 or bx2 < ax1 or ay2 < by1 or by2 < ay1)


class Unit:

    def __init__(
        self,
        canvas,
        x,
        y,
        hp,
        damage,
        speed,
        attack_speed,
        color,
        is_enemy=False,
        kind="melee",
        sprite_idle=None,
        sprite_attack=None,
    ):

        self.canvas = canvas

        self.x = x
        self.y = y

        self.hp = hp
        self.damage = damage
        self.speed = speed
        self.attack_speed = attack_speed

        self.is_enemy = is_enemy
        self.kind = kind
        self.attack_range = _ATTACK_REACH.get(kind, _ATTACK_REACH["melee"])

        self.base_speed = speed
        self.can_move = True
        self.in_combat = False

        self.last_attack = 0

        self.size = 20

        self.sprite_idle = sprite_idle
        self.sprite_attack = sprite_attack
        self.uses_sprite = bool(sprite_idle and sprite_attack)
        self.attack_anim_until = 0.0

        if self.uses_sprite:
            w = max(sprite_idle.width(), sprite_attack.width())
            h = max(sprite_idle.height(), sprite_attack.height())
            self._hit_half_w = w / 2.0
            self._sprite_h = float(h)
            self.id = self.canvas.create_image(
                self.x, self.y, anchor="s", image=self.sprite_idle
            )
            # Врагов просто зеркалим по горизонтали на уровне Canvas-элемента,
            # так сохраняется прозрачность (в отличие от PhotoImage.get/put).
            if self.is_enemy:
                try:
                    self.canvas.scale(self.id, self.x, self.y, -1, 1)
                except Exception:
                    pass
        else:
            self.id = self.canvas.create_rectangle(
                self.x - self.size,
                self.y - self.size,
                self.x + self.size,
                self.y + self.size,
                fill=color,
            )

    def note_attack(self):
        if self.uses_sprite:
            self.attack_anim_until = time.time() + 0.25

    def _refresh_sprite_frame(self):
        if not self.uses_sprite:
            return
        img = self.sprite_attack if time.time() < self.attack_anim_until else self.sprite_idle
        self.canvas.itemconfig(self.id, image=img)

    def update(self):

        if self.hp <= 0:
            self.canvas.delete(self.id)
            return False

        if self.can_move:

            if self.is_enemy:
                if not aabb_intersect(self.get_attack_box(), player_tower_body_box()):
                    self.x += self.speed
            else:
                if not aabb_intersect(self.get_attack_box(), enemy_tower_body_box()):
                    self.x += self.speed

        if self.uses_sprite:
            self.canvas.coords(self.id, self.x, self.y)
        else:
            self.canvas.coords(
                self.id,
                self.x - self.size,
                self.y - self.size,
                self.x + self.size,
                self.y + self.size,
            )

        self._refresh_sprite_frame()

        return True

    def get_coords(self):

        if self.uses_sprite:
            x1 = self.x - self._hit_half_w
            x2 = self.x + self._hit_half_w
            y2 = self.y
            y1 = y2 - self._sprite_h
            return [x1, y1, x2, y2]
        return self.canvas.coords(self.id)

    def get_body_box(self):
        """AABB модели (тело) для урона и коллизий."""
        x1, y1, x2, y2 = self.get_coords()
        return (x1, y1, x2, y2)

    def get_attack_box(self):
        """
        AABB зоны дальности атаки: от передней границы модели в сторону противника.
        Игрок смотрит вправо — зона вправо; враг — влево.
        """
        x1, y1, x2, y2 = self.get_body_box()
        r = self.attack_range
        if self.is_enemy:
            return (x1 - r, y1, x1, y2)
        return (x2, y1, x2 + r, y2)

    def can_attack(self):

        now = time.time()

        if now - self.last_attack >= self.attack_speed:
            self.last_attack = now
            return True

        return False

    def stop(self):
        self.can_move = False

    def resume(self):
        self.can_move = True
