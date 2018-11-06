import pygame
from pygame.locals import *
import os
import math
import random

# constants
GAME_NAME = "Stick Gun"
GAME_VER = "0.1"
RES = os.path.join(os.path.dirname(os.path.realpath(__file__)), "res")

# return path for res file
def res(f_name):
    return os.path.join(RES, f_name)

# initiate pygame display
pygame.init()

display_w, display_h = (1280, 720)
display = pygame.display.set_mode((display_w, display_h))

pygame.display.set_caption(GAME_NAME + ' ' + GAME_VER)
icon_img = pygame.image.load(res("icon.png"))
pygame.display.set_icon(icon_img)

# load images
player_img = {"run1": pygame.image.load(res("player_run_1.png")),
              "run2": pygame.image.load(res("player_run_2.png")),
              "climb1": pygame.image.load(res("player_climb_1.png")),
              "climb2": pygame.image.load(res("player_climb_2.png"))}
gun_img = {"rifle": pygame.image.load(res("gun_rifle.png")),
           "rifle_reload": pygame.image.load(res("reload_rifle.png")),
           "sniper": pygame.image.load(res("gun_sniper.png")),
           "sniper_reload": pygame.image.load(res("reload_sniper.png"))}
enemy_img = {"slime": pygame.image.load(res("slime.png"))}

# clock object
clock = pygame.time.Clock()
FPS = 40

# color constants
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
DIRT = (153, 102, 51)
GREEN = (153, 255, 102)
ORANGE = (204, 51, 0)
TRANSPARENT = pygame.Color(255, 255, 255, 0)

# other constants
STROKE = 3
ANIMATE = 0.3
FONT = pygame.font.Font(None, 28)

# gun constants
RIFLE = ()
SNIPER = ("sniper", 100, (-8, -3), 3, FPS * 3, 3)


class GameObj(pygame.sprite.Sprite):
    family = pygame.sprite.OrderedUpdates()

    def __init__(self):
        super().__init__()
        GameObj.family.add(self)


class Cursor(GameObj):
    RADIUS = 15
    DIAMETER = 2 * RADIUS
    GAP = 3
    SHAKE_RANGE = 8
    SHAKE = 2

    r = None

    def __init__(self):
        super().__init__()
        pygame.mouse.set_visible(False)
        self.image = pygame.Surface((Cursor.DIAMETER, Cursor.DIAMETER),
                                  pygame.SRCALPHA,
                                  32)
        self.color = ORANGE
        pygame.draw.circle(self.image,
                           self.color,
                           (Cursor.RADIUS, Cursor.RADIUS),
                           Cursor.RADIUS,
                           STROKE)
        pygame.draw.line(self.image,
                         self.color,
                         (Cursor.RADIUS, 0),
                         (Cursor.RADIUS, Cursor.DIAMETER),
                         STROKE)
        pygame.draw.line(self.image,
                         self.color,
                         (0, Cursor.RADIUS),
                         (Cursor.DIAMETER, Cursor.RADIUS),
                         STROKE)
        pygame.draw.circle(self.image,
                           TRANSPARENT,
                           (Cursor.RADIUS, Cursor.RADIUS),
                           Cursor.GAP)
        self.rect = self.image.get_rect()
        self.shaked = 0
        self.shake_dir = Cursor.SHAKE
        Cursor.r = self

    def update(self):
        mouse_pos = pygame.mouse.get_pos()
        mouse_press = pygame.mouse.get_pressed()
        self.rect.center = mouse_pos
        if mouse_press[0]:
            Player.r.fire()

    def shift(self, x_shift, y_shift):
        mouse_pos = list(pygame.mouse.get_pos())
        mouse_pos[0] += x_shift
        mouse_pos[1] += y_shift
        if mouse_pos[0] <= 0:
            mouse_pos[0] = 1
        if mouse_pos[1] <= 0:
            mouse_pos[1] = 1
        pygame.mouse.set_pos(mouse_pos)

    def shake(self):
        print(self.shaked)
        if abs(self.shaked) >= Cursor.SHAKE_RANGE:
            self.shake_dir = Cursor.SHAKE if self.shaked < 0 else -Cursor.SHAKE
        self.shaked += self.shake_dir
        self.shift(0, self.shake_dir)


class Block(GameObj):
    family = pygame.sprite.Group()

    def __init__(self, x, y, w, h):
        super().__init__()
        self.image = pygame.Surface((w, h))
        self.image.fill(DIRT)
        self.rect = self.image.get_rect()
        self.rect.left, self.rect.top = x, y
        Block.family.add(self)

    def update(self):
        pass

    def show(self):
        pass


class Ladder(GameObj):
    family = pygame.sprite.Group()

    def __init__(self, x, y, w, h):
        super().__init__()
        self.image = pygame.Surface((w, h))
        self.image.fill(GREEN)
        self.rect = self.image.get_rect()
        self.rect.left, self.rect.top = x, y
        Ladder.family.add(self)

    def update(self):
        pass

    def show(self):
        pass


class Enemy(GameObj):
    family = pygame.sprite.Group()

    def __init__(self, name="slime", life=3):
        super().__init__()
        self.image = enemy_img[name]
        self.rect = self.image.get_rect()
        self.depend = random.choice(Block.family.sprites()).rect
        self.rect.bottom = self.depend.top
        self.x_range = (self.depend.left, self.depend.right - self.rect.width)
        self.rect.left = random.randint(*self.x_range)
        self.life = life
        Enemy.family.add(self)

    def update(self):
        if pygame.sprite.spritecollide(self, Bullet.family, True):
            self.life -= 1
            if self.life <= 0:
                self.kill()
                Enemy()


class Gun(GameObj):
    ICON_GAP = 10

    family = pygame.sprite.Group()

    def __init__(self, master, name="rifle", acc=97, recoil=(-3, 0),\
                 ammo_max=45, fire_rate=FPS/20, reload=2):
        super().__init__()
        self.name = name
        self.image_ori = gun_img[name]
        self.image = self.image_ori
        self.rect = self.image.get_rect()
        self.master = master
        self.acc = acc
        self.recoil = recoil
        self.ammo_max = ammo_max
        self.ammo = ammo_max
        self.treload = reload
        self.fire_rate = fire_rate
        self._reloading = 0
        Gun.family.add(self)

    def update(self):
        if not self.master:
            return

        # calculate pointing direction
        target = Cursor.r.rect.center
        master = self.master
        if master.rect.collidepoint(target):
            return
        else:
            if target[0] < master.rect.centerx:
                gunpos = master.rect.midleft
            else:
                gunpos = master.rect.midright
            if target[1] > gunpos[1]:
                dir = 90 - math.degrees(math.atan(\
                      (target[0] - gunpos[0]) / (target[1] - gunpos[1])))
            elif target[1] == gunpos[1]:
                if target[0] > gunpos[0]:
                    dir = 0
                else:
                    dir = 180
            else:
                dir = 270 - math.degrees(math.atan(\
                      (target[0] - gunpos[0]) / (target[1] - gunpos[1])))
            if self._reloading >= 0:
                self._reloading -= 1
                if self._reloading < 0:
                    self.image_ori = gun_img[self.name]
                    self.ammo = self.ammo_max
                if 90 < dir <= 270:
                    dir = 170
                else:
                    dir = 10
                gunpos = master.rect.center
            elif master.climb:
                dir = 80
                gunpos = master.rect.center


        # update gun attributes
        self.dir = dir
        self.pos = gunpos

        # move and rotate gun image
        self.rect.center = self.pos
        if 90 <= dir % 360 <= 270:
            self.image = pygame.transform.flip(self.image_ori, True, False)
            self.image = pygame.transform.rotate(self.image, -dir + 180)
        else:
            self.image = pygame.transform.rotate(self.image_ori, -dir)

    def reload(self):
        if self._reloading <= 0:
            self.image_ori = gun_img[self.name + "_reload"]
            self._reloading = FPS * self.treload

    @classmethod
    def show_icon(cls, display):
        pos = [10, 10]
        for sprite in cls.family.sprites():
            rect = sprite.image_ori.get_rect()
            rect.topleft = pos
            pos[0] += rect.width + cls.ICON_GAP
            display.blit(sprite.image_ori, rect)
            if sprite.name == Player.r.gun.name:
                rect.top -= cls.ICON_GAP / 2
                rect.left -= cls.ICON_GAP / 2
                rect.width += cls.ICON_GAP
                rect.height += cls.ICON_GAP
                pygame.draw.rect(display, ORANGE, rect, STROKE)
                rect.top = rect.bottom
                bit_map = FONT.render(sprite.name, True, BLACK)
                display.blit(bit_map, rect)
                rect.top += 20
                bit_map = FONT.render(str(sprite.ammo) + '/'\
                 + str(sprite.ammo_max), True, BLACK)
                display.blit(bit_map, rect)


class Player(GameObj):
    RUN_ACC = 1
    RUN_LIM = 6
    AIR_LIM = 3
    CLIMB_X = 2
    CLIMB_Y = 5
    JUMP = 18
    GRAVITY = 1.2
    DROP_LIM = -JUMP
    BOUNCE = 0.5
    FRICTION = 0.3

    r = None

    def __init__(self):
        super().__init__()
        self.images = player_img
        self.image = self.images["run1"]
        self.rect = self.image.get_rect()
        self.rect.left, self.rect.bottom = 0, display_h - 10
        self.speed_x = 0
        self.speed_y = 0
        self.air = False
        self.animate = 0
        self.fire_time = 0
        gun = Gun.family.sprites()[0]
        self.gun = gun # gun and master pairing up
        gun.master = self # gun and master pairing up
        Player.r = self

    def update(self):
        # animation update
        self.animate += ANIMATE
        img_index = int(self.animate) % 2 + 1

        # climb ladder
        climb = pygame.sprite.spritecollide(self, Ladder.family, False)
        self.climb = bool(climb)

        # keyboard control
        x_change = False
        if not climb:
            if keystate[K_a]:
                self.speed_x -= Player.RUN_ACC
                x_change = True
            if keystate[K_d]:
                self.speed_x += Player.RUN_ACC
                x_change = True
            # run regulation
            if not x_change and self.speed_x != 0:
                self.speed_x *= Player.FRICTION
            if abs(self.speed_x) > Player.RUN_LIM:
                if self.speed_x < 0:
                    self.speed_x = -Player.RUN_LIM
                else:
                    self.speed_x = Player.RUN_LIM
            # animate image
            if x_change and not self.air:
                Cursor.r.shake()
                self.image = self.images["run" + str(img_index)]
            else:
                self.image = self.images["run1"]
        else:
            self.speed_x, self.speed_y = 0, 0
            if keystate[K_a]:
                self.speed_x = -Player.CLIMB_X
            if keystate[K_d]:
                self.speed_x = Player.CLIMB_X
            if keystate[K_w]:
                self.speed_y = Player.CLIMB_Y
            if keystate[K_s]:
                self.speed_y = -Player.CLIMB_Y
            if not (self.speed_x or self.speed_y):
                self.animate -= ANIMATE
            else:
                self.image = self.images["climb" + str(img_index)]

        # gravity
        self.speed_y -= Player.GRAVITY

        # move regulation
        if self.speed_y < Player.DROP_LIM:
            self.speed_y = Player.DROP_LIM
        self.rect.move_ip(self.speed_x, -self.speed_y)

        # block crash
        crash = pygame.sprite.spritecollide(self, Block.family, False)
        self.air = True
        if crash:
            for block in crash:
                if block.rect.collidepoint(self.rect.bottomleft)\
                 or block.rect.collidepoint(self.rect.bottomright):
                    self.rect.bottom = block.rect.top
                    self.air = False
                    self.speed_y = 0
                elif block.rect.collidepoint(self.rect.topleft)\
                 or block.rect.collidepoint(self.rect.topright):
                    self.rect.top = block.rect.bottom
                    self.speed_y = -self.speed_y * Player.BOUNCE
                else:
                    if self.speed_x < 0:
                        self.rect.left = block.rect.right
                    elif self.speed_x > 0:
                        self.rect.right = block.rect.left
                    self.speed_x = -self.speed_x * Player.BOUNCE
                    self.speed_y = 0
        if self.fire_time > 0:
            self.fire_time -= 1

    def fire(self):
        gun = self.gun
        if self.gun.ammo <= 0:
            self.gun.reload()
        if self.gun._reloading >= 0 or self.climb\
         or self.fire_time > 0 or self.gun.ammo <= 0:
            return

        dir = gun.dir
        acc_fix = 100 - gun.acc
        dir += random.randint(-acc_fix, acc_fix)
        recoil = (random.randint(-1, 1),
                  random.randint(*gun.recoil))
        gunpos = self.gun.pos
        self.fire_time = self.gun.fire_rate
        self.gun.ammo -= 1
        Bullet(*gunpos, dir)
        Cursor.r.shift(*recoil)


class Bullet(GameObj):
    WIDTH = 3
    LENGTH = 20
    INIT_SPEED = 20
    RESIST = 0.001
    GRAVITY = 0.01

    family = pygame.sprite.Group()

    def __init__(self, x, y ,dir):
        super().__init__()
        self.image_ori = pygame.Surface((Bullet.WIDTH, Bullet.LENGTH), SRCALPHA)
        self.image_ori.fill(BLACK)
        self.dir = dir
        self.image = pygame.transform.rotate(self.image_ori, -self.dir + 90)
        self.rect = self.image.get_rect()
        self.rect.center = (x, y)
        self.x = x
        self.y = y
        self.speed = Bullet.INIT_SPEED * random.randint(95, 105) / 100
        Bullet.family.add(self)

    def update(self):
        x_shift = math.cos(math.radians(self.dir)) * self.speed
        y_shift = math.sin(math.radians(self.dir)) * self.speed
        self.x += x_shift
        self.y += y_shift
        self.rect.center = (self.x ,self.y)
        self.speed *= 1 - Bullet.RESIST
        crash = pygame.sprite.spritecollide(self, Block.family, False)
        if crash:
            self.kill()


def main():
    global events, modstate, keystate

    Block(0, display_h - 10, display_w, 20)
    Block(200, display_h - 310, display_w - 400, 20)
    Block(400, display_h - 430, display_w - 800, 20)
    Block(600, display_h - 500, display_w - 1200, 70)
    Ladder(160, display_h - 310, 40, 200)
    Ladder(display_w - 200, display_h - 310, 40, 200)
    rifle = Gun(None, *RIFLE)
    sniper = Gun(None, *SNIPER)
    player = Player()
    cursor = Cursor()

    background = pygame.Surface((display_w, display_h))
    background.fill(WHITE)
    display.blit(background, background.get_rect())

    while True:
        events = pygame.event.get()
        modstate = pygame.key.get_mods()
        keystate = pygame.key.get_pressed()

        for event in events:
            if event.type == QUIT:
                quit_all()
            if event.type == KEYDOWN:
                if modstate & KMOD_META and event.key == K_q:
                    quit_all()
                elif event.key == K_SPACE:
                    Player.r.fire()
                elif event.key == K_r:
                    Player.r.gun.reload()
                elif event.key == K_e:
                    Enemy()
                elif event.key == K_w:
                    if not player.climb and not player.air:
                        player.speed_y = Player.JUMP
                        player.air = True


        display.fill(WHITE)

        GameObj.family.update()
        print(clock.get_fps())

        GameObj.family.draw(display)
        Gun.show_icon(display)
        pygame.display.flip()
        clock.tick(FPS)


def quit_all():
    pygame.quit()
    quit()


main()
