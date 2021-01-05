import traceback
import pygame
import socket
import random
import time


BLOCK_W = 80
BLOCK_H = 80

MAP_W = 16
MAP_H = 8

SCREEN_W = MAP_W*BLOCK_W
SCREEN_H = (MAP_H+1)*BLOCK_H


class Player:
    def __init__(self, x, y, texture, active):
        self.x, self.y, self.texture = x, y, texture
        self.active = active


class Object:
    def __init__(self, x, y, texture):
        self.x, self.y, self.texture = x, y, texture
        self.active = True


class Bullet:
    def __init__(self, x, y, movX, movY, color, active):
        self.x, self.y, self.movX, self.movY, self.color = x, y, movX, movY, color
        self.active = active


class Item:
    def __init__(self, name, texture, count):
        self.name, self.texture, self.count = name, texture, count
        self.specialItem = False

    def use(self, bx, by, ox, oy):
        pass

    def attack(self, bx, by, ox, oy):
        pass


class Pickaxe(Item):
    def __init__(self):
        super().__init__('pickaxe', '', 1)
        self.specialItem = True
        InventoryManager.addInventoryItem(self)

    def use(self, bx, by, ox, oy):
        global level
        if not level[bx, by] == 'grass':
            InventoryManager.addInventoryItem(Item(level[bx, by], '', 1))
        level[bx, by] = 'grass'
        main.c.sendMessage('set_block'+str(bx)+'/'+str(by)+'/grass')


class Hammer(Item):
    def __init__(self):
        super().__init__('hammer', '', 1)
        self.specialItem = True
        InventoryManager.addInventoryItem(self)

    def use(self, bx, by, ox, oy):
        global level
        level[bx, by] = 'wood'
        main.c.sendMessage('set_block' + str(bx) + '/' + str(by) + '/wood')

    def attack(self, bx, by, ox, oy):
        hit = None
        for player in players:
            if players[player].x == bx and players[player].y == by:
                hit = player
        if hit is not None:
            print("I'm attacking!")
            msg = 'attack'+str(hit)+'/'+str(random.randint(5, 20))
            print(msg)
            main.c.sendMessage(msg)


class MagicStick(Item):
    def __init__(self):
        super().__init__('magic_stick', '', 1)
        self.specialItem = True
        InventoryManager.addInventoryItem(self)

    def use(self, bx, by, ox, oy):
        b = random.choice(['wall', 'grass', 'wood'])
        if b != 'grass':
            MapManager.setBlock(ox, oy, b)


class Candle(Item):
    def __init__(self):
        super().__init__('candle', '', 1)
        self.specialItem = True
        InventoryManager.addInventoryItem(self)

    def use(self, bx, by, ox, oy):
        if (ox*BLOCK_W, oy*BLOCK_H) in objects:
            if not objects[ox*BLOCK_W, oy*BLOCK_H].active:
                MapManager.createObject(ox * BLOCK_W, oy * BLOCK_H, 'fire')
            else:
                print("removing")
                MapManager.removeObject(ox*BLOCK_W, oy*BLOCK_H, 'fire')
        else:
            MapManager.createObject(ox*BLOCK_W, oy*BLOCK_H, 'fire')


class Weapon:
    def __init__(self, maxAmmo, shootingSpeed, shootingDamage, bulletColor):
        self.ammo = maxAmmo
        self.maxAmmo = maxAmmo

        self.shootingSpeed = shootingSpeed
        self.shootingDamage = shootingDamage

        self.bulletColor = bulletColor


class PlayerClass:
    def __init__(self, weapon, texture, className):
        self.weapon = weapon

        self.instruments = []
        self.instruments: [Item]

        self.texture = texture
        self.className = className


players = {}
players: {int: Player}

bullets = []
bullets: [Bullet]

objects = {}
objects: {(int, int): Object}

level = {}
level: {(int, int): str}

inventoryItems = []
inventoryItems: [Item]

nextFrameUpdate = False

health = 100

RECONNECTING = False


class InventoryManager:
    @staticmethod
    def addInventoryItem(item: Item):
        global inventoryItems

        i: Item
        for i in inventoryItems:
            if i.name == item.name:
                i.count += item.count
                return

        inventoryItems.append(item)

    @staticmethod
    def removeInventoryItem(item: Item):
        global inventoryItems
        global main

        i: Item
        for i in inventoryItems:
            if i.name == item.name and i.count >= item.count:
                i.count -= item.count

                if i.count == 0:
                    inventoryItems.remove(i)
                    if main.selectedSlot >= len(inventoryItems):
                        main.selectedSlot -= 1

                return

    @staticmethod
    def isItemInInventory(name: str) -> bool:
        global inventoryItems
        global main

        i: Item
        for i in inventoryItems:
            if i.name == name: return True

        return False


class MapManager:
    @staticmethod
    def setBlock(x, y, block):
        global level

        level[x, y] = block
        main.c.sendMessage('set_block' + str(x) + '/' + str(y) + '/' + str(block))

    @staticmethod
    def createObject(x, y, texture):
        global objects

        objects[x, y] = Object(x, y, texture)
        main.c.sendMessage('create_object' + str(x) + '/' + str(y) + '/' + texture)

    @staticmethod
    def removeObject(x, y, texture):
        main.c.sendMessage('remove_object' + str(x) + '/' + str(y) + '/' + texture)
        objects[x, y].active = False


class Client:
    def __init__(self, sip, sport):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        print("Connecting to server at", sip, sport)
        self.s.connect((sip, sport))
        self.s.setblocking(False)

        self.disconnected = False
        self.disconnectReason = ''

    def loadLevel(self):
        global level

        received = False
        while not received:
            self.sendMessage('get_level')
            time.sleep(1/10)
            m = self.getMessages()
            for msg in m:
                if 'map' in msg:
                    msg = msg.replace('map', '')
                    try:
                        level = eval(msg)
                        received = True
                        print("Level loaded.")
                    except Exception as e:
                        print("Error while trying to load level:", e)

    def update(self):
        global players
        global health
        global bullets
        global level
        global objects
        global nextFrameUpdate

        msg = ''
        if not nextFrameUpdate:
            bullets.clear()

            try:
                msg = self.getMessages()

                if msg:
                    for obj in msg:
                        if obj:
                            s = obj.split('/')
                            if s[0] == 'b':
                                # print(s)
                                bullets.append(Bullet(int(s[2]), int(s[3]), int(s[4]), int(s[5]), eval(s[6]),
                                               eval(s[7])))
                            elif s[0] == 'p':
                                players[int(s[1])] = Player(int(s[2]), int(s[3]), s[4], eval(s[5]))
                            elif s[0] == 'cb':
                                level[int(s[1]), int(s[2])] = s[3]
                            elif s[0] == 'o':
                                objects[int(s[1]), int(s[2])] = Object(int(s[1]), int(s[2]), s[3])
                                objects[int(s[1]), int(s[2])].active = eval(s[4])

                            elif s[0] == 'bullet_hit':
                                health -= int(s[1])
                            elif s[0] == 'disconnect':
                                self.disconnectReason = s[1]
                                self.disconnected = True
            except Exception as e:
                print("Client.update() exc2:\n", e)
                traceback.print_exc()
                print(msg)

            try:
                self.sendMessage('get_objects')
                msg = self.getMessages()

                if msg:

                    for obj in msg:
                        if obj:
                            s = obj.split('/')
                            if s[0] == 'b':
                                # print(s)
                                bullets.append(Bullet(int(s[2]), int(s[3]), int(s[4]), int(s[5]), eval(s[6]),
                                                      eval(s[7])))
                            elif s[0] == 'p':
                                players[int(s[1])] = Player(int(s[2]), int(s[3]), s[4], eval(s[5]))
                            elif s[0] == 'cb':
                                level[int(s[1]), int(s[2])] = s[3]
                            elif s[0] == 'o':
                                objects[int(s[1]), int(s[2])] = Object(int(s[1]), int(s[2]), s[3])
                                objects[int(s[1]), int(s[2])].active = eval(s[4])

                            elif s[0] == 'bullet_hit':
                                health -= int(s[1])
                            elif s[0] == 'disconnect':
                                self.disconnectReason = s[1]
                                self.disconnected = True
            except Exception as e:
                print("Client.update() exc:\n", e)
                traceback.print_exc()
                print(msg)
        else:
            nextFrameUpdate = True

    def getMessages(self) -> list:
        try:
            message = self.s.recv(1048576).decode('utf-8')
            if message == '':
                return []
            else:
                message = message.split(';')
                return message
        except socket.error:
            pass
        except Exception as e:
            print("Exception has been thrown while trying to receive new messages from the server:\n", e)

        return []

    def sendMessage(self, message: str) -> (bool, Exception):
        try:
            m = message + ';'
            self.s.send(m.encode('utf-8'))

            return True, None
        except Exception as e:
            return False, e

    def disconnect(self):
        if not self.disconnected:
            r = (False, None)
            while r != (True, None):
                r = self.sendMessage('disconnect')
                self.disconnected = True


class Main:
    def classChooser(self) -> [str, str, [Item]]:
        # [className, classTexture, defaultItems: [Item]]
        classes = [
            ['builder', 'builder_texture', [Hammer, Pickaxe]],
            ['mage', 'mage_texture', [MagicStick, Candle]]
        ]

        choosed = False
        variant = 0
        while not choosed:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    exit()
                elif e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_LEFT:
                        if variant > 0:
                            variant -= 1
                        else:
                            variant = len(classes)-1
                    if e.key == pygame.K_RIGHT:
                        if variant < len(classes)-1:
                            variant += 1
                        else:
                            variant = 0
                    if e.key == pygame.K_RETURN:
                        choosed = True

            self.sc.fill((255, 255, 255))

            t = self.font.render(self.localization['selectclass'], True, (0, 0, 0))
            self.sc.blit(t, t.get_rect(topleft=(BLOCK_W, SCREEN_H//4)))

            for x in range(len(classes)):
                if x == variant:
                    t = self.textures[classes[x][0]]
                    r = t.get_rect(center=(BLOCK_W+x*BLOCK_W+BLOCK_W//2, SCREEN_H//2))
                    self.sc.blit(t, r)
                else:
                    t = pygame.transform.scale(self.textures[classes[x][0]], (BLOCK_W//2, BLOCK_H//2))
                    r = t.get_rect(center=(BLOCK_W+x*BLOCK_W+BLOCK_W//2, SCREEN_H//2))
                    self.sc.blit(t, r)

            pygame.display.update()

        classes[variant][2][1]()
        return PlayerClass(classes[variant][2][0](), classes[variant][1], classes[variant][0])

    def __init__(self, sip, sport):
        pygame.init()

        try:
            file = open('client_settings.txt', 'r')
            self.settings = eval(file.read())
            file.close()

            file = open('localizations.txt', 'r')
            self.localization = eval(file.read())[self.settings['localization']]
            file.close()
        except:
            print("Error while trying to read localization or settings:")
            traceback.print_exc()
            exit(1)

        self.fullscreen = False

        self.sc = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("BattleKiller 2D")

        self.textures = {
            'grass': pygame.image.load('textures/grass.png').convert_alpha(),
            'wall': pygame.image.load('textures/wall.png').convert_alpha(),
            'wood': pygame.image.load('textures/wood.png').convert_alpha(),
            'cross': pygame.image.load('textures/cross.png').convert_alpha(),
            'tree': pygame.image.load('textures/tree.png').convert_alpha(),
            'builder': pygame.image.load('textures/builder.png').convert_alpha(),
            'mage': pygame.image.load('textures/mage.png').convert_alpha(),
            'builder_texture': pygame.image.load('textures/builder_texture.png').convert_alpha(),
            'mage_texture': pygame.image.load('textures/mage_texture.png').convert_alpha(),
            'pickaxe': pygame.image.load('textures/pickaxe.png').convert_alpha(),
            'hammer': pygame.image.load('textures/hammer.png').convert_alpha(),
            'magic_stick': pygame.image.load('textures/magic_stick.png').convert_alpha(),
            'candle': pygame.image.load('textures/candle.png').convert_alpha(),
            'fire': pygame.image.load('textures/fire.png').convert_alpha()
        }

        self.font = pygame.font.SysFont("Arial", 36)

        self.playerClass: PlayerClass
        self.playerClass = self.classChooser()

        self.x, self.y = 0, 0

        self.running = True

        self.connectionError = False
        self.connectionErrorTraceback = ''

        try:
            self.c = Client(sip, sport)
            self.c.loadLevel()
        except:
            self.connectionError = True
            file = open('last_err_code.txt', 'w')
            traceback.print_exc(16384, file)
            file.close()

            file = open('last_err_code.txt', 'r')
            err = file.read()
            file.close()

            self.connectionErrorTraceback = err

        self.selectedSlot = 0

        # For fps
        self.prevFrame = time.time()
        self.fps = 1

    def mainLoop(self):
        global RECONNECTING
        global inventoryItems
        global objects

        while self.running:
            if not self.connectionError:
                self.c.sendMessage('set_player' + str(self.x) + '/' + str(self.y) + '/' + str(self.playerClass.texture))

                self.c.update()

            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self.c.disconnect()
                    exit()
                elif e.type == pygame.KEYDOWN and not self.connectionError:
                    if e.key == pygame.K_w:
                        if self.y > 0:
                            if level[self.x, self.y-1] == 'grass':
                                self.y -= 1
                    if e.key == pygame.K_a:
                        if self.x > 0:
                            if level[self.x-1, self.y] == 'grass':
                                self.x -= 1
                    if e.key == pygame.K_s:
                        if self.y < MAP_H-1:
                            if level[self.x, self.y+1] == 'grass':
                                self.y += 1
                    if e.key == pygame.K_d:
                        if self.x < MAP_W-1:
                            if level[self.x+1, self.y] == 'grass':
                                self.x += 1

                    if e.key == pygame.K_SPACE:
                        self.c.sendMessage('shoot'+str(self.x)+'/'+str(self.y+1)+'/0/1/(0,0,0)')

                    if e.key == pygame.K_q or e.key == pygame.K_LEFT:
                        if self.selectedSlot > 0:
                            self.selectedSlot -= 1
                        else:
                            self.selectedSlot = len(inventoryItems)-1
                    if e.key == pygame.K_e or e.key == pygame.K_RIGHT:
                        if self.selectedSlot < len(inventoryItems)-1:
                            self.selectedSlot += 1
                        else:
                            self.selectedSlot = 0

                    if e.key == pygame.K_f:
                        self.fullscreen = not self.fullscreen
                        if self.fullscreen:
                            pygame.display.quit()
                            self.sc = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.FULLSCREEN)
                        else:
                            pygame.display.quit()
                            self.sc = pygame.display.set_mode((SCREEN_W, SCREEN_H))

                    if e.key == pygame.K_r and self.c.disconnected:
                        RECONNECTING = True
                        self.running = False
                elif e.type == pygame.MOUSEBUTTONDOWN and not self.connectionError:
                    mouse = pygame.mouse.get_pos()
                    x, y = mouse[0], mouse[1]

                    if x < MAP_W*BLOCK_W and y < MAP_H*BLOCK_H:
                        pygame.draw.rect(self.sc, (255, 0, 0), (mouse[0] - 10, mouse[1] - 10, BLOCK_W // 4, BLOCK_H // 4))

                        pressed = pygame.mouse.get_pressed(3)
                        if pressed[0] or pressed[2]:
                            movX = 0
                            movY = 0

                            if x // BLOCK_W < self.x:
                                movX = -1
                            elif x // BLOCK_W == self.x:
                                movX = 0
                            elif x // BLOCK_W > self.x:
                                movX = 1

                            if y // BLOCK_H < self.y:
                                movY = -1
                            elif y // BLOCK_H == self.y:
                                movY = 0
                            elif y // BLOCK_H > self.y:
                                movY = 1

                            # For block placing
                            resX = self.x + movX
                            resY = self.y + movY

                            if not (movX == 0 and movY == 0) and 0 <= resX <= MAP_W and 0 <= resY <= MAP_H:
                                if pressed[0]:
                                    inventoryItems[self.selectedSlot].attack(resX, resY, x//BLOCK_W, y//BLOCK_H)

                                    # self.c.sendMessage('shoot' + str(self.x + movX) + '/' + str(self.y + movY)
                                    #                    + '/' + str(movX) + '/' + str(movY) + '/(0,0,0)')
                                elif pressed[2]:
                                    if not inventoryItems[self.selectedSlot].specialItem:
                                        if level[resX, resY] == 'grass' and inventoryItems[self.selectedSlot].count > 0:
                                            self.c.sendMessage('set_block' + str(resX) + '/' + str(resY) + '/' +
                                                               inventoryItems[self.selectedSlot].name)

                                            InventoryManager.removeInventoryItem(Item(inventoryItems[self.selectedSlot].name,
                                                                                      '',
                                                                                      1))
                                    else:
                                        inventoryItems[self.selectedSlot].use(resX, resY, x//BLOCK_W, y//BLOCK_H)

                elif e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_r:
                        RECONNECTING = True
                        self.running = False

            self.sc.fill((255, 255, 255))

            if not self.connectionError:
                if health > 0 and not self.c.disconnected:
                    for x in range(MAP_W):
                        for y in range(MAP_H):
                            self.sc.blit(self.textures[level[x, y]],
                                         self.textures[level[x, y]].get_rect(topleft=(x*BLOCK_W, y*BLOCK_H)))

                    for bullet in bullets:
                        if bullet.active:
                            pygame.draw.rect(self.sc, bullet.color, (bullet.x*BLOCK_W+(BLOCK_W//4),
                                                                     bullet.y*BLOCK_H+(BLOCK_H//4),
                                                                     40, 40))

                    for obj in objects:
                        if objects[obj].active:
                            self.sc.blit(self.textures[objects[obj].texture],
                                         self.textures[objects[obj].texture].get_rect(
                                             topleft=(objects[obj].x, objects[obj].y)))

                    for p in players:
                        player = players[p]
                        if player.active:
                            self.sc.blit(self.textures[player.texture],
                                         self.textures[player.texture].get_rect(topleft=(player.x*BLOCK_W,
                                                                                         player.y*BLOCK_H)))

                    self.sc.blit(self.textures[self.playerClass.texture], self.textures[self.playerClass.texture].get_rect(
                        topleft=(self.x*BLOCK_W, self.y*BLOCK_H)
                    ))

                    pygame.draw.line(self.sc, (0, 0, 0), [0, MAP_H*BLOCK_H], [MAP_W*BLOCK_W, MAP_H*BLOCK_H])
                    pygame.draw.rect(self.sc, (255, 255, 255), (0, MAP_H*BLOCK_W, SCREEN_W, BLOCK_H))

                    for slot in range(len(inventoryItems)):
                        if slot == self.selectedSlot:
                            self.sc.blit(self.textures[inventoryItems[slot].name],
                                         self.textures[inventoryItems[slot].name].get_rect(topleft=(slot*BLOCK_W, MAP_H*BLOCK_H)))
                        else:
                            t = pygame.transform.scale(self.textures[inventoryItems[slot].name], (BLOCK_W//2, BLOCK_H//2))
                            r = t.get_rect(center=(slot*BLOCK_W+BLOCK_W//2, MAP_H*BLOCK_H+BLOCK_H//2))
                            self.sc.blit(t, r)

                        if not inventoryItems[slot].specialItem:
                            t = self.font.render(str(inventoryItems[slot].count), True, (0, 0, 0))
                            r = t.get_rect(center=(slot*BLOCK_W+BLOCK_W//2, MAP_H*BLOCK_H+18))
                            self.sc.blit(t, r)

                    t = self.font.render(self.localization['health'] + str(health), True, (0, 0, 0))
                    r = t.get_rect(topleft=(0, 0))
                    self.sc.blit(t, r)

                    t = self.font.render("FPS: " + str(self.fps), True, (0, 0, 0))
                    r = t.get_rect(topleft=(0, BLOCK_H))
                    self.sc.blit(t, r)

                    mouse = pygame.mouse.get_pos()
                    pygame.draw.rect(self.sc, (255, 0, 0), (mouse[0] - 10, mouse[1] - 10, BLOCK_W // 4, BLOCK_H // 4))

                elif health <= 0:
                    self.c.disconnect()
                    t = self.font.render(self.localization['game_over'], True, (255, 0, 0))
                    r = t.get_rect(center=(SCREEN_W//2, SCREEN_H//2))
                    self.sc.blit(t, r)
                else:
                    t = self.font.render(self.localization['disconnected'], True, (0, 0, 0))
                    t1 = self.font.render(
                        self.localization['disconnected_reason'] + self.c.disconnectReason, True, (0, 0, 0))
                    self.sc.blit(t, t.get_rect(center=(SCREEN_W//2, SCREEN_H//2-BLOCK_H)))
                    self.sc.blit(t1, t1.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 + BLOCK_H)))
            else:
                t = self.font.render(self.localization['server_connection_error'], True, (255, 0, 0))
                self.sc.blit(t, t.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - BLOCK_H)))

                err = self.connectionErrorTraceback.split('\n')
                for line in range(len(err)):
                    t1 = self.font.render(err[line], True, (0, 0, 0))
                    self.sc.blit(t1, t1.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 + (line*38))))

                t2 = self.font.render(self.localization['try_connect_again'], True, (20, 141, 192))
                self.sc.blit(t2, t2.get_rect(center=(SCREEN_W//2, SCREEN_H//2 + ((len(err)+1)*38))))

            pygame.display.update()

            v = 1/160
            # print(v)
            if v > 0:
                time.sleep(v)

            self.fps = 1/(time.time()-self.prevFrame)

            self.prevFrame = time.time()


if __name__ == '__main__':
    f = open('client_settings.txt', 'r')
    c = eval(f.read())
    f.close()

    ip = c['server_ip']
    port = int(c['server_port'])

    a = 1

    while RECONNECTING or a == 1:
        a = 0

        main = Main(ip, port)
        main.mainLoop()

        pygame.display.quit()

        players = {}
        players: {int: Player}

        bullets = []
        bullets: [Bullet]

        objects = {}
        objects: {(int, int): Object}

        level = {}
        level: {(int, int): str}

        inventoryItems = []
        inventoryItems: [Item]

        nextFrameUpdate = False

        health = 100
