import traceback
import pygame
import socket
import random
import time

BLOCK_W = 80
BLOCK_H = 80

MAP_W = 16
MAP_H = 8

SCREEN_W = MAP_W * BLOCK_W
SCREEN_H = (MAP_H + 1) * BLOCK_H


class Player:
    def __init__(self, x, y, texture, active, phealth):
        self.x, self.y, self.texture = x, y, texture
        self.active = active
        self.health = phealth


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
        if level[ox, oy].split('/')[0] == 'chest':
            items = level[ox, oy].split('/')[1::]
            itemslist = []
            for item in items:
                i = item.split('=')
                if len(i) == 2:
                    itemslist.append([i[0], int(i[1])])

            ChestMenu(main.sc, itemslist, ox, oy)
        elif level[ox, oy] == 'heart':
            main.defenceLevel += 10
            MapManager.setBlock(ox, oy, 'grass')

    def attack(self, bx, by, ox, oy):
        if level[ox, oy].split('/')[0] == 'chest':
            items = level[ox, oy].split('/')[1::]
            itemslist = []
            for item in items:
                i = item.split('=')
                if len(i) == 2:
                    itemslist.append([i[0], int(i[1])])

            ChestMenu(main.sc, itemslist, ox, oy)
        elif level[ox, oy] == 'heart':
            main.defenceLevel += 10
            MapManager.setBlock(ox, oy, 'grass')


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
        main.c.sendMessage('set_block' + str(bx) + '/' + str(by) + '/grass')


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
            msg = 'attack' + str(hit) + '/' + str(random.randint(5, 20))
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
        if (ox * BLOCK_W, oy * BLOCK_H) in objects:
            if not objects[ox * BLOCK_W, oy * BLOCK_H].active:
                MapManager.createObject(ox * BLOCK_W, oy * BLOCK_H, 'fire')
            else:
                print("removing")
                MapManager.removeObject(ox * BLOCK_W, oy * BLOCK_H, 'fire')
        else:
            MapManager.createObject(ox * BLOCK_W, oy * BLOCK_H, 'fire')


class Knife(Item):
    def __init__(self):
        super().__init__('knife', '', 1)
        self.specialItem = True
        InventoryManager.addInventoryItem(self)

    def use(self, bx, by, ox, oy):
        super().attack(bx, by, ox, oy)

    def attack(self, bx, by, ox, oy):
        hit = None
        for player in players:
            if players[player].x == bx and players[player].y == by:
                hit = player
        if hit is not None:
            print("I'm attacking!")
            msg = 'attack' + str(hit) + '/' + str('100')
            print(msg)
            main.c.sendMessage(msg)


class SniperRifle(Item):
    def __init__(self):
        super().__init__('sniper_rifle', '', 1)
        self.specialItem = True
        InventoryManager.addInventoryItem(self)

    def use(self, bx, by, ox, oy):
        super().attack(bx, by, ox, oy)

    def attack(self, bx, by, ox, oy):
        global level

        vertical = False

        try:
            m = (oy-main.y) / (ox-main.x)
        except ZeroDivisionError:
            m = 0
            vertical = True

        b = main.y - (m * main.x)

        print('x1: ', main.x, 'y1: ', main.y, 'x2: ', ox, 'y2: ', oy)
        print('m: ', m)
        print('b: ', b)

        step = 1
        if ox > main.x and oy > main.y:
            step = 1
        elif ox < main.x or oy > main.y:
            step = -1

        changedBlocks = []

        if not vertical:
            for xx in range(main.x*20, ox*20, step):
                x = xx/20

                y = m * x + b

                if 0 <= int(x) <= MAP_W and 0 <= int(y) <= MAP_H:
                    if not level[int(x), int(y)] == 'grass':
                        print(int(x), int(y), level[int(x), int(y)])
                        return

                if not (int(x), int(y)) in changedBlocks:
                    changedBlocks.append((int(x), int(y)))
        else:
            print("Vertical")

            if main.y > oy:
                step = -1
            else:
                step = 1

            for y in range(main.y, oy, step):
                print(y)
                if not level[main.x, y] == 'grass':
                    print(main.x, y, level[main.x, y])
                    return

                if not (main.x, y) in changedBlocks:
                    changedBlocks.append((main.x, y))

        print('Changed blocks: ', len(changedBlocks))

        # for block in changedBlocks:
        #     print(block[0], block[1])
        #     level[block[0], block[1]] = 'wood'

        hit = None
        for player in players:
            if players[player].x == ox and players[player].y == oy:
                hit = player
        if hit is not None:
            print("I'm attacking!")
            msg = 'attack' + str(hit) + '/' + str(random.randint(20, 40))
            print(msg)
            main.c.sendMessage(msg)


specialItemList = {'pickaxe': Pickaxe, 'hammer': Hammer,
                   'magic_stick': MagicStick, 'candle': Candle,
                   'knife': Knife, 'sniper_rifle': SniperRifle}


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
            if i.name == name:
                return True

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

        self.clientId = -1

        self.disconnected = False
        self.disconnectReason = ''

        self.newMessages = []

        self.sent = False

    def loadLevel(self):
        global level

        received = False
        while not received:
            self.sendMessage('get_level')
            time.sleep(1 / 10)
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
                self.sendMessage("alive")
            except Exception as e:
                print("Exception client.update() 3:", e)
                traceback.print_exc()

            try:
                msg = self.getMessages()

                if msg:
                    for obj in msg:
                        if obj:
                            s = obj.split('/')
                            if s[0] == 'yourid':
                                self.clientId = int(s[1])

                            elif s[0] == 'b':
                                # print(s)
                                bullets.append(Bullet(int(s[2]), int(s[3]), int(s[4]), int(s[5]), eval(s[6]),
                                                      eval(s[7])))
                            elif s[0] == 'p':
                                players[int(s[1])] = Player(int(s[2]), int(s[3]), s[4], eval(s[5]), int(s[6]))
                            elif s[0] == 'cb':
                                level[int(s[1]), int(s[2])] = s[3]
                            elif s[0] == 'o':
                                objects[int(s[1]), int(s[2])] = Object(int(s[1]), int(s[2]), s[3])
                                objects[int(s[1]), int(s[2])].active = eval(s[4])
                            elif s[0] == 'msg':
                                self.newMessages.append([int(s[1]), str(s[2]), (0, 0, 0)])
                            elif s[0] == 'service':
                                self.newMessages.append([0, str(s[1]), (255, 0, 0)])

                            elif s[0] == 'bullet_hit':
                                health -= int(abs(int(s[1]) - int(s[1])*main.defenceLevel*0.01))
                            elif s[0] == 'disconnect':
                                print("Disconnected from the server.")
                                print(s)
                                self.disconnectReason = s[1]
                                self.disconnected = True

                    self.sent = False

                if not self.sent:
                    self.sendMessage('get_objects')
                    self.sent = True
            except Exception as e:
                print("Client.update() exc2:\n", e)
                traceback.print_exc()
                print(msg)

    def getMessages(self) -> list:
        try:
            message = self.s.recv(1048576).decode('utf-8')
            if message == '':
                return []
            else:
                # print(len(message))
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
            self.sendMessage('disconnect')
            self.disconnected = True


class ChestMenu:
    def __init__(self, sc: pygame.Surface, itemsList: list, ox, oy):
        self.sc = sc
        self.items = itemsList
        self.selected = 0
        self.x, self.y = ox, oy

        self.gray = pygame.Surface((SCREEN_W, SCREEN_H))
        self.gray.fill((0, 0, 0))
        self.gray.set_alpha(128)

        self.mainloop()

    def mainloop(self):
        while True:
            main.c.update()

            if level[self.x, self.y].split('/')[0] != 'chest':
                return

            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    return
                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_ESCAPE:
                        return

                    elif e.key == pygame.K_LEFT:
                        if self.selected == 0:
                            self.selected = len(self.items)-1
                        else:
                            self.selected -= 1
                    elif e.key == pygame.K_RIGHT:
                        if self.selected == len(self.items)-1:
                            self.selected = 0
                        else:
                            self.selected += 1

                    elif e.key == pygame.K_RETURN or e.key == pygame.K_SPACE:
                        for item in self.items:
                            if item[0] in specialItemList and not specialItemList[item[0]] in inventoryItems:
                                InventoryManager.addInventoryItem(specialItemList[item[0]]())
                            else:
                                InventoryManager.addInventoryItem(Item(item[0], item[0], int(item[1])))
                        MapManager.setBlock(self.x, self.y, 'grass')
                        return

            main.renderGame()
            self.sc.blit(self.gray, self.gray.get_rect(topleft=(0, 0)))

            pygame.draw.rect(self.sc, (255, 255, 255), (SCREEN_W//2-len(self.items)//2*BLOCK_W,
                                                        SCREEN_H//2-BLOCK_H//2,
                                                        len(self.items)*BLOCK_W,
                                                        BLOCK_H))

            for item in range(len(self.items)):
                p = SCREEN_W//2-len(self.items)//2*BLOCK_W + item*BLOCK_W
                if self.selected != item:
                    t = pygame.transform.scale(main.textures[self.items[item][0]], (BLOCK_W//2, BLOCK_H//2))
                else:
                    t = main.textures[self.items[item][0]]
                self.sc.blit(t, t.get_rect(center=(p+BLOCK_W//2, SCREEN_H//2)))

                t = main.font.render(str(self.items[item][1]), True, (0, 0, 0))
                r = t.get_rect(center=(p+BLOCK_W//2, SCREEN_H//2+BLOCK_H//2))
                self.sc.blit(t, r)

            pygame.display.update()


class ChatMenu:
    def __init__(self, c: Client, sc: pygame.Surface, quickMenu=False):
        self.sc = sc
        self.c = c

        self.userMessage = ''
        self.messages = []

        self.font = pygame.font.SysFont('Arial', 36)

        self.quickMessage = quickMenu

        self.mainloop()

    def mainloop(self):
        while True:
            self.c.update()
            if self.c.newMessages:
                self.messages.extend(self.c.newMessages)
                self.c.newMessages.clear()

            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self.c.disconnect()
                    exit()
                elif e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_ESCAPE or e.key == pygame.K_TAB:
                        return
                    elif e.key == pygame.K_RETURN:
                        self.c.sendMessage(self.userMessage)
                        main.messages.append([main.c.clientId, self.userMessage, time.time(), 255, (0, 0, 0)])
                        self.messages.append([main.c.clientId, self.userMessage, (0, 0, 0)])
                        self.userMessage = ''
                        if self.quickMessage and not e.mod & pygame.KMOD_CTRL and not e.mod & pygame.KMOD_SHIFT:
                            return
                    elif e.key == pygame.K_BACKSPACE:
                        self.userMessage = self.userMessage[:len(self.userMessage) - 1]
                    else:
                        self.userMessage += e.unicode

            if not self.quickMessage:
                self.sc.fill((170, 170, 170))
            else:
                main.renderGame()
                self.sc.blit(main.sc, main.sc.get_rect(topleft=(0, 0)))

            pygame.draw.rect(self.sc, (100, 100, 100), (0, SCREEN_H - BLOCK_H, SCREEN_W, BLOCK_H))

            if len(self.messages) > 16:
                self.messages = self.messages[len(self.messages) - 16::]

            for message in range(len(self.messages)):
                if self.messages[message][2] == (0, 0, 0):
                    s = self.font.render("Player #" + str(self.messages[message][0]) + " : " + self.messages[message][1],
                                         True, self.messages[message][2])
                else:
                    s = self.font.render(
                        "[SERVER] " + str(self.messages[message][0]) + " : " + self.messages[message][1],
                        True, self.messages[message][2])

                if not self.quickMessage:
                    r = s.get_rect(midleft=(BLOCK_W // 2, BLOCK_H // 2 + (message * BLOCK_H // 2)))
                else:
                    r = s.get_rect(midleft=(BLOCK_W // 2, BLOCK_H + BLOCK_H // 2 + (message * BLOCK_H // 2)))
                self.sc.blit(s, r)

            s = self.font.render(self.userMessage, True, (0, 0, 0))
            r = s.get_rect(midleft=(BLOCK_W // 2, SCREEN_H - BLOCK_H // 2))
            self.sc.blit(s, r)

            # Text cursor
            pygame.draw.rect(self.sc, (0, 0, 0), (
                BLOCK_W // 2 + s.get_width(), SCREEN_H - BLOCK_H + BLOCK_H // 4, BLOCK_W // 8, BLOCK_H - BLOCK_W // 2))

            pygame.display.update()


class Main:
    def classChooser(self) -> [str, str, [Item]]:
        # [className, classTexture, defaultItems: [Item]]
        classes = [
            ['builder', 'builder_texture', [Hammer, Pickaxe]],
            ['mage', 'mage_texture', [MagicStick, Candle]],
            ['sniper', 'sniper_texture', [Knife, SniperRifle]]
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
                            variant = len(classes) - 1
                    if e.key == pygame.K_RIGHT:
                        if variant < len(classes) - 1:
                            variant += 1
                        else:
                            variant = 0
                    if e.key == pygame.K_RETURN:
                        choosed = True

            self.sc.fill((255, 255, 255))

            t = self.font.render(self.localization['selectclass'], True, (0, 0, 0))
            self.sc.blit(t, t.get_rect(topleft=(BLOCK_W, SCREEN_H // 4)))

            for x in range(len(classes)):
                if x == variant:
                    t = self.textures[classes[x][0]]
                    r = t.get_rect(center=(BLOCK_W + x * BLOCK_W + BLOCK_W // 2, SCREEN_H // 2))
                    self.sc.blit(t, r)
                else:
                    t = pygame.transform.scale(self.textures[classes[x][0]], (BLOCK_W // 2, BLOCK_H // 2))
                    r = t.get_rect(center=(BLOCK_W + x * BLOCK_W + BLOCK_W // 2, SCREEN_H // 2))
                    self.sc.blit(t, r)

            pygame.display.update()

        classes[variant][2][1]()
        return PlayerClass(classes[variant][2][0](), classes[variant][1], classes[variant][0])

    def __init__(self, surface):
        pygame.init()

        try:
            file = open('client_settings.txt', 'r', encoding='utf-8')
            self.settings = eval(file.read())
            file.close()
            self.serverIp, self.serverPort = self.settings['server_ip'], self.settings['server_port']

            file = open('localizations.txt', 'r', encoding='utf-8')
            self.localization = eval(file.read())[self.settings['localization']]
            file.close()
        except:
            print("Error while trying to read localization or settings:")
            traceback.print_exc()
            exit(1)

        self.fullscreen = False

        self.sc = surface
        pygame.display.set_caption("BattleKiller 2D")

        self.textures = {
            'grass': pygame.image.load('textures/grass.png').convert_alpha(),
            'wall': pygame.image.load('textures/wall.png').convert_alpha(),
            'wood': pygame.image.load('textures/wood.png').convert_alpha(),
            'cross': pygame.image.load('textures/cross.png').convert_alpha(),
            'tree': pygame.image.load('textures/tree.png').convert_alpha(),
            'builder': pygame.image.load('textures/builder.png').convert_alpha(),
            'mage': pygame.image.load('textures/mage.png').convert_alpha(),
            'sniper': pygame.image.load('textures/sniper.png').convert_alpha(),
            'builder_texture': pygame.image.load('textures/builder_texture.png').convert_alpha(),
            'mage_texture': pygame.image.load('textures/mage_texture.png').convert_alpha(),
            'sniper_texture': pygame.image.load('textures/sniper_texture.png').convert_alpha(),
            'pickaxe': pygame.image.load('textures/pickaxe.png').convert_alpha(),
            'hammer': pygame.image.load('textures/hammer.png').convert_alpha(),
            'magic_stick': pygame.image.load('textures/magic_stick.png').convert_alpha(),
            'candle': pygame.image.load('textures/candle.png').convert_alpha(),
            'knife': pygame.image.load('textures/knife.png').convert_alpha(),
            'sniper_rifle': pygame.image.load('textures/sniper_rifle.png').convert_alpha(),
            'fire': pygame.image.load('textures/fire.png').convert_alpha(),
            'arrow': pygame.image.load('textures/arrow.png').convert_alpha(),
            'chest': pygame.image.load('textures/chest.png').convert_alpha(),
            'heart': pygame.image.load('textures/heart.png').convert_alpha()
        }

        self.font = pygame.font.SysFont("Arial", 36)

        self.playerClass: PlayerClass
        self.playerClass = self.classChooser()

        self.x, self.y = 0, 0
        # For continuous movement
        self.lastMovement = time.time()

        self.running = True

        self.connectionError = False
        self.connectionErrorTraceback = ''

        try:
            self.c = Client(self.serverIp, self.serverPort)
            self.c.loadLevel()
        except:
            self.connectionError = True
            file = open('last_err_code.txt', 'w', encoding='utf-8')
            traceback.print_exc(16384, file)
            file.close()

            file = open('last_err_code.txt', 'r', encoding='utf-8')
            err = file.read()
            file.close()

            self.connectionErrorTraceback = err

        self.selectedSlot = 0

        self.messages = []

        # For fps
        self.prevFrame = time.time()
        self.fps = 1

        self.defenceLevel = 0

    def mainLoop(self):
        global RECONNECTING
        global inventoryItems
        global objects

        try:
            self.c.sendMessage('get_objects')
        except:
            pass

        while self.running:
            if not self.connectionError and not self.c.disconnected:
                self.c.sendMessage(
                    'set_player' + str(self.x) + '/' + str(self.y) + '/' + str(self.playerClass.texture) + '/' + str(
                        health))

                self.c.update()

                if self.c.newMessages:
                    for msg in self.c.newMessages:
                        self.messages.append([msg[0], msg[1], time.time(), 255, msg[2]])
                    self.c.newMessages.clear()

            # listening for the events
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self.c.disconnect()
                    return
                elif e.type == pygame.KEYDOWN and not self.connectionError and not self.c.disconnected:
                    if e.key == pygame.K_SPACE:
                        self.c.sendMessage('shoot' + str(self.x) + '/' + str(self.y + 1) + '/0/1/(0,0,0)')

                    if e.key == pygame.K_q or e.key == pygame.K_LEFT:
                        if self.selectedSlot > 0:
                            self.selectedSlot -= 1
                        else:
                            self.selectedSlot = len(inventoryItems) - 1
                    if e.key == pygame.K_e or e.key == pygame.K_RIGHT:
                        if self.selectedSlot < len(inventoryItems) - 1:
                            self.selectedSlot += 1
                        else:
                            self.selectedSlot = 0

                    if e.key == pygame.K_c:
                        ChatMenu(self.c, self.sc)
                    elif e.key == pygame.K_m:
                        ChatMenu(self.c, self.sc, quickMenu=True)

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

                    if x < MAP_W * BLOCK_W and y < MAP_H * BLOCK_H:
                        pygame.draw.rect(self.sc, (255, 0, 0),
                                         (mouse[0] - 10, mouse[1] - 10, BLOCK_W // 4, BLOCK_H // 4))

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
                                    inventoryItems[self.selectedSlot].attack(resX, resY, x // BLOCK_W, y // BLOCK_H)

                                    # self.c.sendMessage('shoot' + str(self.x + movX) + '/' + str(self.y + movY)
                                    #                    + '/' + str(movX) + '/' + str(movY) + '/(0,0,0)')
                                elif pressed[2]:
                                    if not inventoryItems[self.selectedSlot].specialItem:
                                        if level[resX, resY] == 'grass' and inventoryItems[self.selectedSlot].count > 0:
                                            self.c.sendMessage('set_block' + str(resX) + '/' + str(resY) + '/' +
                                                               inventoryItems[self.selectedSlot].name)

                                            InventoryManager.removeInventoryItem(
                                                Item(inventoryItems[self.selectedSlot].name,
                                                     '',
                                                     1))
                                    else:
                                        inventoryItems[self.selectedSlot].use(resX, resY, x // BLOCK_W, y // BLOCK_H)

                elif e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_r:
                        RECONNECTING = True
                        self.running = False

            self.sc.fill((255, 255, 255))

            if self.c.disconnected:
                t = self.font.render(self.localization['disconnected'], True, (0, 0, 0))
                t1 = self.font.render(
                    self.localization['disconnected_reason'] + self.c.disconnectReason, True, (0, 0, 0))
                self.sc.blit(t, t.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - BLOCK_H)))
                self.sc.blit(t1, t1.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 + BLOCK_H)))
            elif self.connectionError:
                t = self.font.render(self.localization['server_connection_error'], True, (255, 0, 0))
                self.sc.blit(t, t.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - BLOCK_H)))

                err = self.connectionErrorTraceback.split('\n')
                for line in range(len(err)):
                    t1 = self.font.render(err[line], True, (0, 0, 0))
                    self.sc.blit(t1, t1.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 + (line * 38))))

                t2 = self.font.render(self.localization['try_connect_again'], True, (20, 141, 192))
                self.sc.blit(t2, t2.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 + ((len(err) + 1) * 38))))
            else:
                # movement
                if time.time() - self.lastMovement > 1 / 5:  # 1/(blocksPerSecond)
                    keys = pygame.key.get_pressed()

                    if keys[pygame.K_w]:
                        if self.y > 0:
                            if level[self.x, self.y - 1] == 'grass':
                                self.y -= 1
                                self.lastMovement = time.time()
                    if keys[pygame.K_a]:
                        if self.x > 0:
                            if level[self.x - 1, self.y] == 'grass':
                                self.x -= 1
                                self.lastMovement = time.time()
                    if keys[pygame.K_s]:
                        if self.y < MAP_H - 1:
                            if level[self.x, self.y + 1] == 'grass':
                                self.y += 1
                                self.lastMovement = time.time()
                    if keys[pygame.K_d]:
                        if self.x < MAP_W - 1:
                            if level[self.x + 1, self.y] == 'grass':
                                self.x += 1
                                self.lastMovement = time.time()

                if health > 0:
                    self.renderGame()
                else:
                    self.c.disconnect()
                    t = self.font.render(self.localization['game_over'], True, (255, 0, 0))
                    r = t.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2))
                    self.sc.blit(t, r)

            pygame.display.update()

            v = 1 / 160
            # print(v)
            if v > 0:
                time.sleep(v)

            self.fps = 1 / (time.time() - self.prevFrame)

            self.prevFrame = time.time()

    def renderGame(self):
        for x in range(MAP_W):
            for y in range(MAP_H):
                t = self.textures[level[x, y].split('/')[0]]
                self.sc.blit(t, t.get_rect(topleft=(x * BLOCK_W, y * BLOCK_H)))

        for bullet in bullets:
            if bullet.active:
                pygame.draw.rect(self.sc, bullet.color, (bullet.x * BLOCK_W + (BLOCK_W // 4),
                                                         bullet.y * BLOCK_H + (BLOCK_H // 4),
                                                         40, 40))

        for p in players:
            player = players[p]
            if player.active:
                self.sc.blit(self.textures[player.texture],
                             self.textures[player.texture].get_rect(topleft=(player.x * BLOCK_W,
                                                                             player.y * BLOCK_H)))
                pygame.draw.rect(self.sc, (0, 0, 0), (
                    player.x * BLOCK_W - 3, player.y * BLOCK_H - (BLOCK_H // 8) - 3, BLOCK_W + 6, BLOCK_H // 8 + 6))
                pygame.draw.rect(self.sc, (255, 0, 0), (
                    player.x * BLOCK_W, player.y * BLOCK_H - (BLOCK_H // 8), int(player.health * 0.8),
                    BLOCK_H // 8))

        self.sc.blit(self.textures['arrow'],
                     self.textures['arrow'].get_rect(center=(self.x * BLOCK_W + BLOCK_W // 2,
                                                             self.y * BLOCK_H + BLOCK_H // 2)))

        self.sc.blit(self.textures[self.playerClass.texture],
                     self.textures[self.playerClass.texture].get_rect(
                         topleft=(self.x * BLOCK_W, self.y * BLOCK_H)
                     ))
        pygame.draw.rect(self.sc, (0, 0, 0),
                         (self.x * BLOCK_W - 3, self.y * BLOCK_H - (BLOCK_H // 8) - 3, BLOCK_W + 6,
                          BLOCK_H // 8 + 6))
        pygame.draw.rect(self.sc, (0, 255, 0), (
            self.x * BLOCK_W, self.y * BLOCK_H - (BLOCK_H // 8), int(health * 0.8), BLOCK_H // 8))

        for obj in objects:
            if objects[obj].active:
                self.sc.blit(self.textures[objects[obj].texture],
                             self.textures[objects[obj].texture].get_rect(
                                 topleft=(objects[obj].x, objects[obj].y)))

        pygame.draw.line(self.sc, (0, 0, 0), [0, MAP_H * BLOCK_H], [MAP_W * BLOCK_W, MAP_H * BLOCK_H])
        pygame.draw.rect(self.sc, (255, 255, 255), (0, MAP_H * BLOCK_W, SCREEN_W, BLOCK_H))

        for slot in range(len(inventoryItems)):
            if slot == self.selectedSlot:
                self.sc.blit(self.textures[inventoryItems[slot].name.split('/')[0]],
                             self.textures[inventoryItems[slot].name.split('/')[0]].get_rect(
                                 topleft=(slot * BLOCK_W, MAP_H * BLOCK_H)))
            else:
                t = pygame.transform.scale(self.textures[inventoryItems[slot].name.split('/')[0]],
                                           (BLOCK_W // 2, BLOCK_H // 2))
                r = t.get_rect(center=(slot * BLOCK_W + BLOCK_W // 2, MAP_H * BLOCK_H + BLOCK_H // 2))
                self.sc.blit(t, r)

            if not inventoryItems[slot].specialItem:
                t = self.font.render(str(inventoryItems[slot].count), True, (0, 0, 0))
                r = t.get_rect(center=(slot * BLOCK_W + BLOCK_W // 2, MAP_H * BLOCK_H + 18))
                self.sc.blit(t, r)

        t = self.font.render(self.localization['health'] + str(health), True, (0, 0, 0))
        r = t.get_rect(topleft=(0, 0))
        self.sc.blit(t, r)

        t = self.font.render("FPS: " + str(self.fps), True, (0, 0, 0))
        r = t.get_rect(topleft=(0, BLOCK_H // 2))
        self.sc.blit(t, r)

        t = self.font.render("Defence level: " + str(self.defenceLevel), True, (0, 0, 0))
        r = t.get_rect(topleft=(4*BLOCK_W, 0))
        self.sc.blit(t, r)

        for message in self.messages:
            if message[4] == (0, 0, 0):
                t = self.font.render("Player #" + str(message[0]) + " : " + message[1], True, message[4])
            else:
                t = self.font.render("[SERVER] " + str(message[0]) + " : " + message[1], True, message[4])

            t.set_alpha(int(message[3]))
            r = t.get_rect(topleft=(0, BLOCK_H // 2 * (2 + self.messages.index(message))))
            self.sc.blit(t, r)
            # self.messages[self.messages.index(message)][3] -= 0.5 + 2 * (1 / (len(message[1]) / 5))
            self.messages[self.messages.index(message)][3] -= 1

        for message in self.messages:
            if message[3] <= 32:
                self.messages.remove(message)

        mouse = pygame.mouse.get_pos()
        pygame.draw.rect(self.sc, (255, 0, 0), (mouse[0] - 10, mouse[1] - 10, BLOCK_W // 4, BLOCK_H // 4))


class StartMenu:
    def __init__(self):
        self.sc = pygame.display.set_mode((SCREEN_W, SCREEN_H))

        # loading button's textures
        self.playButton = pygame.image.load('textures/play_button.png').convert_alpha()
        self.exitButton = pygame.image.load('textures/exit_button.png').convert_alpha()
        # rescaling textures
        self.playButton = pygame.transform.scale(self.playButton, (320 * (BLOCK_W // 80), 80 * (BLOCK_H // 80)))
        self.exitButton = pygame.transform.scale(self.exitButton, (320 * (BLOCK_W // 80), 80 * (BLOCK_H // 80)))
        # defining coordinates
        self.playButtonCoords = [SCREEN_W // 2 - self.playButton.get_width() // 2, SCREEN_H // 2 - BLOCK_H]
        self.exitButtonCoords = [SCREEN_W // 2 - self.playButton.get_width() // 2, SCREEN_H // 2 + BLOCK_H]

        self.loop()

    def loop(self):
        global main

        while True:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    exit()
                elif e.type == pygame.MOUSEBUTTONDOWN:
                    x, y = e.pos

                    # Checking if player clicked one of the buttons
                    if self.playButtonCoords[0] <= x <= self.playButtonCoords[0] + self.playButton.get_width() and \
                            self.playButtonCoords[1] <= y <= self.playButtonCoords[1] + self.playButton.get_height():
                        resetGlobals()
                        main = Main(self.sc)
                        main.mainLoop()
                        resetGlobals()
                    elif self.exitButtonCoords[0] <= x <= self.exitButtonCoords[0] + self.exitButton.get_width() and \
                            self.exitButtonCoords[1] <= y <= self.exitButtonCoords[1] + self.exitButton.get_height():
                        exit()

            self.sc.fill((0, 76, 153))

            self.sc.blit(self.playButton,
                         self.playButton.get_rect(topleft=self.playButtonCoords))

            self.sc.blit(self.exitButton,
                         self.exitButton.get_rect(topleft=self.exitButtonCoords))

            pygame.display.update()


RECONNECTING = False

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

main: Main


def resetGlobals():
    global players, bullets, objects, level, inventoryItems, nextFrameUpdate, health, RECONNECTING, main

    RECONNECTING = False
    players = {}
    bullets = []
    objects = {}
    level = {}
    inventoryItems = []
    nextFrameUpdate = False
    health = 100
    main = None


if __name__ == '__main__':
    resetGlobals()
    startMenu = StartMenu()
