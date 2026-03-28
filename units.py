import time

WIDTH = 1800


class Unit:

    def __init__(self, canvas, x, y, hp, damage, speed, attack_speed, color, is_enemy=False, kind="melee"):

        self.canvas = canvas

        self.x = x
        self.y = y

        self.hp = hp
        self.damage = damage
        self.speed = speed
        self.attack_speed = attack_speed

        # принадлежность юнита (игрок / враг)
        self.is_enemy = is_enemy

        # тип юнита: melee / archer / splash
        self.kind = kind

        # базовая скорость (для восстановления после остановки)
        self.base_speed = speed

        # может ли юнит двигаться в этом тике
        self.can_move = True

        # участвует ли юнит сейчас в ближнем бою
        self.in_combat = False

        self.last_attack = 0

        self.size = 20

        self.id = self.canvas.create_rectangle(
            self.x - self.size,
            self.y - self.size,
            self.x + self.size,
            self.y + self.size,
            fill=color
        )

    def update(self):

        if self.hp <= 0:
            self.canvas.delete(self.id)
            return False

        # координаты юнита
        x1, y1, x2, y2 = self.canvas.coords(self.id)

        # двигаемся только если движение разрешено (не в ближнем бою)
        if self.can_move:

            # позиция башни в зависимости от стороны
            if self.is_enemy:
                # башня игрока находится слева
                tower_x = 200

                # вражеский юнит двигается влево, пока не упрётся в башню игрока
                if x1 > tower_x:
                    self.x += self.speed
            else:
                # башня врага находится справа
                tower_x = WIDTH - 220

                # юнит игрока двигается вправо, пока не упрётся в башню врага
                if x2 < tower_x:
                    self.x += self.speed

        self.canvas.coords(
            self.id,
            self.x - self.size,
            self.y - self.size,
            self.x + self.size,
            self.y + self.size
        )

        return True

    def get_coords(self):

        return self.canvas.coords(self.id)

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