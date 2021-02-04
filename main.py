import os
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


class SoundStub:
    def play(self, duration=0): pass


class Block:
    @staticmethod
    def getBlockFromID(x, y, blockID: str):
        if blockID == 'wall':
            return StoneWall(x, y)
        elif blockID == 'wooden_door_closed':
            return Door(x, y)
        elif blockID == 'wooden_door_opened':
            d = Door(x, y, True)
            return d
        elif blockID == 'heart':
            return Heart(x, y)
        elif blockID.split(',')[0] == 'chest':
            return Chest(x, y, blockID.replace('chest,', ''))
        elif blockID == 'grass':
            return Block(x, y, False, False, texture='grass',
                         name='How you have mined glass block?')
        else:
            return Block(x, y, name='Undefined', texture=blockID)

    def __init__(self, x, y, collidable=True, breakable=True, visible=True, texture='wall', name='Stone wall'):
        self.collidable = collidable
        self.breakable = breakable
        self.visible = visible
        self.texture = texture
        self.name = name

        self.x, self.y = x, y

    def breakBlock(self) -> None:
        main.inventory.addInventoryItem(Item(self.name, self.texture, 1, False))

    def interact(self):
        pass

    def replaceWith(self, block) -> None:
        main.map.setBlock(self.x, self.y, block)


class StoneWall(Block):
    def __init__(self, x, y):
        Block.__init__(self, x, y)


class Door(Block):
    def __init__(self, x, y, opened=False):
        Block.__init__(self, x, y, texture='wooden_door_closed', name='Wooden door')
        if opened:
            self.texture = 'wooden_door_opened'
            self.collidable = False

        # Door state. False is closed, True is opened
        self.state = opened

    def interact(self):
        # Opening door if it is closed
        if not self.state:
            self.state = True
            self.texture = 'wooden_door_opened'
            self.collidable = False
            main.map.updateBlock(self.x, self.y, self)
        # And closing, if it was opened
        else:
            self.state = False
            self.texture = 'wooden_door_closed'
            self.collidable = True
            main.map.updateBlock(self.x, self.y, self)


class Chest(Block):
    def __init__(self, x, y, items: str):
        Block.__init__(self, x, y, texture='chest', name='Chest')

        self.items = []
        for item in items.split(','):
            i = item.split('=')
            if len(i) == 2:
                self.items.append([i[0], int(i[1])])

    def interact(self):
        ChestMenu(main.sc, self.items, self.x, self.y)


class Heart(Block):
    def __init__(self, x, y):
        Block.__init__(self, x, y, breakable=False, texture='heart')

    def interact(self):
        main.defenceLevel += 10
        main.map.setBlock(self.x, self.y, 'grass')



class ChatMessage:
    def __init__(self, message: str, sender: str = '',
                 color: tuple = (0, 0, 0), serviceMessage: bool = False, alpha: int = 255):
        self.message = message
        self.sender = sender
        self.color = color
        self.serviceMessage = serviceMessage
        self.alpha = alpha


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
    def __init__(self, name, texture, count, specialItem=False):
        self.name, self.texture, self.count = name, texture, count
        self.specialItem = specialItem

    @staticmethod
    def interactWithBlock(x, y):
        main.map.level[x, y].interact()

        """
        elif main.map.level[x, y] == 'wooden_door_closed':
            main.map.setBlock(x, y, 'wooden_door_opened')
        elif main.map.level[x, y] == 'wooden_door_opened':
            main.map.setBlock(x, y, 'wooden_door_closed')
        elif main.map.level[x, y] == 'heart':
            main.defenceLevel += 10
            main.map.setBlock(x, y, 'grass')
        """

    def use(self, bx, by, ox, oy):
        self.interactWithBlock(ox, oy)

    def attack(self, bx, by, ox, oy):
        self.interactWithBlock(ox, oy)


class Pickaxe(Item):
    def __init__(self):
        super().__init__('pickaxe', 'pickaxe', 1, specialItem=True)
        self.specialItem = True

    def use(self, bx, by, ox, oy):
        if not main.map.level[bx, by].texture == 'grass':
            main.inventory.addInventoryItem(Item(main.map.level[bx, by].texture, '', 1))
        main.map.setBlock(bx, by, 'grass')


class Hammer(Item):
    def __init__(self):
        super().__init__('hammer', 'pickaxe', 1, specialItem=True)
        self.specialItem = True

    def use(self, bx, by, ox, oy):
        if main.map.level[bx, by] == 'grass':
            main.map.setBlock(bx, by, 'wood')

    def attack(self, bx, by, ox, oy):
        hit = None
        for p in players:
            player = players[p]
            if player.x // 80 == bx and player.y // 80 == by:
                hit = p
        if hit is not None:
            print("I'm attacking!")
            msg = 'attack' + str(hit) + '/' + str(random.randint(5, 20))
            print(msg)
            main.c.sendMessage(msg)


class MagicStick(Item):
    def __init__(self):
        super().__init__('magic_stick', 'magic_stick', 1, specialItem=True)
        self.specialItem = True

    def use(self, bx, by, ox, oy):
        b = random.choice(['wall', 'grass', 'wood'])
        if b != 'grass':
            main.map.setBlock(ox, oy, b)


class Candle(Item):
    def __init__(self):
        super().__init__('candle', 'candle', 1, specialItem=True)
        self.specialItem = True

    def use(self, bx, by, ox, oy):
        if (ox * BLOCK_W, oy * BLOCK_H) in main.map.objects:
            if not main.map.objects[ox * BLOCK_W, oy * BLOCK_H].active:
                main.map.createObject(ox * BLOCK_W, oy * BLOCK_H, 'fire')
            else:
                print("removing")
                main.map.removeObject(ox * BLOCK_W, oy * BLOCK_H, 'fire')
        else:
            main.map.createObject(ox * BLOCK_W, oy * BLOCK_H, 'fire')


class Knife(Item):
    def __init__(self):
        super().__init__('knife', 'knife', 1, specialItem=True)
        self.specialItem = True

    def use(self, bx, by, ox, oy):
        super().attack(bx, by, ox, oy)

    def attack(self, bx, by, ox, oy):
        hit = None
        for player in players:
            if players[player].x // BLOCK_W == bx and players[player].y // BLOCK_H == by:
                hit = player
        if hit is not None:
            print("I'm attacking!")
            msg = 'attack' + str(hit) + '/' + str('100')
            print(msg)
            main.c.sendMessage(msg)


class SniperRifle(Item):
    def __init__(self):
        super().__init__('sniper_rifle', 'sniper_rifle', 1, specialItem=True)
        self.specialItem = True

    def use(self, bx, by, ox, oy):
        super().attack(bx, by, ox, oy)

    def attack(self, bx, by, ox, oy):
        vertical = False

        try:
            m = (oy - main.y) / (ox - main.x)
        except ZeroDivisionError:
            m = 0
            vertical = True

        b = main.y - (m * main.x)

        print('x1: ', main.x, 'y1: ', main.y, 'x2: ', ox, 'y2: ', oy)
        print('m: ', m)
        print('b: ', b)
        print('vertical: ', vertical)

        step = 1
        if ox > main.x and oy > main.y:
            step = 1
        elif ox < main.x or oy > main.y:
            step = -1

        changedBlocks = []

        hitBlock = False

        if not vertical:
            for xx in range(int(main.x * 20), int(ox * 20), step):
                x = xx / 20

                y = m * x + b

                if 0 <= int(x) <= MAP_W and 0 <= int(y) <= MAP_H:
                    if not main.map.level[int(x), int(y)].texture == 'grass':
                        print(int(x), int(y), main.map.level[int(x), int(y)])
                        hitBlock = True
                        break

                if not (int(x), int(y)) in changedBlocks:
                    changedBlocks.append((int(x), int(y)))
        else:
            if main.y > oy:
                step = -1
            else:
                step = 1

            for y in range(int(main.y), int(oy), step):
                if not main.map.level[main.x, y].texture == 'grass':
                    print(main.x, y, main.map.level[main.x, y])
                    hitBlock = True
                    break

                if not (main.x, y) in changedBlocks:
                    changedBlocks.append((main.x, y))

        if hitBlock:
            main.sounds['sniper_rifle_wall_shot'].play()
        else:
            main.sounds['sniper_rifle_shot'].play()

        print('Hit block: ', hitBlock)
        print('Changed blocks: ', len(changedBlocks))

        # for block in changedBlocks:
        #     print(block[0], block[1])
        #     level[block[0], block[1]] = 'wood'

        if not hitBlock:
            hit = None
            for player in players:
                if players[player].x // BLOCK_W == ox and players[player].y // BLOCK_H == oy:
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


class Inventory:
    def __init__(self):
        self.inventoryItems = []
        self.inventoryItems: [Item]

    def addInventoryItem(self, item: Item):
        i: Item
        for i in self.inventoryItems:
            if i.name == item.name:
                i.count += item.count
                return

        self.inventoryItems.append(item)

    def removeItem(self, item: Item):
        global main

        i: Item
        for i in self.inventoryItems:
            if i.name == item.name and i.count >= item.count:
                i.count -= item.count

                if i.count == 0:
                    self.inventoryItems.remove(i)
                    if main.selectedSlot >= len(self.inventoryItems):
                        main.selectedSlot -= 1

                return

    def removeItemByName(self, name: str, count: int):
        for i in self.inventoryItems:
            if i.name == name and i.count >= count:
                i.count -= count

            if i.count <= 0:
                self.inventoryItems.remove(i)
                if main.selectedSlot >= len(self.inventoryItems):
                    main.selectedSlot -= 1

            break

    def isItemInInventory(self, name: str) -> bool:
        global main

        i: Item
        for i in self.inventoryItems:
            if i.name == name:
                return True

        return False


class MapManager:
    def __init__(self):
        self.level = {int: Block}
        self.level = {}
        self.objects = {}

    def updateBlock(self, x, y, block: Block):
        self.level[x, y] = block
        main.c.sendMessage('set_block' + str(x) + '/' + str(y) + str(block.texture))

    def setBlock(self, x, y, block):
        x = int(x)
        y = int(y)

        if type(block) == Block:
            bl = block
            bl.x, bl.y = x, y
        elif type(block) == str:
            if block == 'wooden_door_closed':
                bl = Door(x, y)
            elif block == 'wooden_door_opened':
                bl = Door(x, y, True)
            else:
                bl = Block.getBlockFromID(x, y, block)
        else:
            return

        # Playing sound if we break block
        if bl.texture == 'grass':
            main.sounds['block_break'].play()
        else:
            main.sounds['block_place'].play()

        self.level[x, y] = bl
        main.c.sendMessage('set_block' + str(x) + '/' + str(y) + '/' + str(bl.texture))

    def createObject(self, x, y, texture):
        self.objects[x, y] = Object(x, y, texture)
        main.c.sendMessage('create_object' + str(x) + '/' + str(y) + '/' + texture)

    def removeObject(self, x, y, texture):
        main.c.sendMessage('remove_object' + str(x) + '/' + str(y) + '/' + texture)
        self.objects[x, y].active = False


class Client:
    def __init__(self, sip, sport):
        self.disconnected = False
        self.disconnectReason = ''

        try:
            self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            print("Connecting to server at", sip, sport)
            self.s.connect((sip, sport))
            self.s.setblocking(False)

            self.clientId = -1
            self.playerInLobby = True

            self.lobbyMenu()

            self.loadLevel()
        except Exception as e:
            print("Error while connecting to the server:", e)
            traceback.print_exc()

            file = open('last_err_code.txt', 'w', encoding='utf-8')
            traceback.print_exc(16384, file)
            file.close()

            file = open('last_err_code.txt', 'r', encoding='utf-8')
            err = file.read()
            file.close()

            self.connectionError = True
            self.disconnectReason = 'Error:\n' + err

        self.newMessages = []

        self.sent = False

    def lobbyMenu(self):
        # Structure is [[gameTitle, playersInGame]]
        games: [str, int, str]
        games = []

        selectedGame = 0
        joinedGame = False

        lastGamesRequest = time.time()
        while not joinedGame:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self.sendMessage('disconnect')
                    exit()
                elif e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_UP:
                        if selectedGame > 0: selectedGame -= 1
                        else: selectedGame = len(games)-1

                    elif e.key == pygame.K_DOWN:
                        if selectedGame < len(games)-1: selectedGame += 1
                        else: selectedGame = 0

                    if e.key == pygame.K_c:
                        self.sendMessage('create_game')
                        return

                    elif e.key == pygame.K_RETURN:
                        if len(games) == 0:
                            self.sendMessage('create_game')
                            return

                        self.sendMessage('join_game/' + games[selectedGame][2])
                        return

            if selectedGame > len(games) and selectedGame != 0:
                selectedGame = len(games)-1

            if time.time() - lastGamesRequest >= 0.5:
                self.sendMessage('get_games')
                lastGamesRequest = time.time()

            msg = self.getMessages()
            if msg:
                games.clear()
                for obj in msg:
                    if obj:
                        o = obj.split('/')
                        if o[0] == 'g':
                            games.append([o[1], int(o[2]), o[3]])

            main.sc.fill((128, 128, 128))

            if len(games) > 0:
                for i in range(len(games)):
                    t = main.font.render(str(games[i][0]) + '; ' + str(games[i][1]) + ' Players.', True, (0, 0, 0))

                    if i == selectedGame:
                        pygame.draw.rect(main.sc, (170, 170, 170), (10, 10+i*56, t.get_width()+40, t.get_height()))
                    else:
                        pygame.draw.rect(main.sc, (70, 70, 70), (10, 10+i*56, t.get_width()+40, t.get_height()))

                    r = t.get_rect(topleft=(20, 10+i*56))
                    main.sc.blit(t, r)
            else:
                t = main.font.render("Currently there are no active battles. Why not create one?", True, (0, 0, 0))
                r = t.get_rect(center=(SCREEN_W//2, SCREEN_H//2))
                main.sc.blit(t, r)

            pygame.display.update()


    def loadLevel(self):
        print("Loading level")
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
                        for x, y in level:
                            main.map.level[x, y] = Block.getBlockFromID(x, y, level[x, y])

                        received = True
                        print("Level loaded.")
                    except Exception as e:
                        print("Error while trying to load level:", e)
                        traceback.print_exc()

    def setNickname(self, nickname: str):
        self.sendMessage('set_nick/' + str(nickname))

    def update(self):
        global players
        global health
        global bullets
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

                            elif s[0] == 'setpos':
                                main.movement.x = float(s[1]) * BLOCK_W + BLOCK_W // 2
                                main.movement.y = float(s[2]) * BLOCK_H + BLOCK_H // 2

                            elif s[0] == 'b':
                                bullets.append(Bullet(int(s[2]), int(s[3]), int(s[4]), int(s[5]), eval(s[6]),
                                                      eval(s[7])))
                            elif s[0] == 'p':
                                players[int(s[1])] = Player(float(s[2]), float(s[3]), s[4], eval(s[5]), int(s[6]))
                            elif s[0] == 'cb':
                                main.map.level[int(s[1]), int(s[2])] = Block.getBlockFromID(int(s[1]), int(s[2]), s[3])
                            elif s[0] == 'o':
                                main.map.objects[int(s[1]), int(s[2])] = Object(int(s[1]), int(s[2]), s[3])
                                main.map.objects[int(s[1]), int(s[2])].active = eval(s[4])
                            elif s[0] == 'msg':
                                self.newMessages.append([int(s[1]), str(s[2]), (0, 0, 0), False])
                            elif s[0] == 'service':
                                self.newMessages.append([0, str(s[1]), eval(s[2]), True])

                            elif s[0] == 'bullet_hit':
                                health -= int(abs(int(s[1]) - int(s[1]) * main.defenceLevel * 0.01))
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

        self.gray = pygame.Surface((MAP_W * BLOCK_W, MAP_H * BLOCK_H))
        self.gray.fill((0, 0, 0))
        self.gray.set_alpha(128)

        self.mainloop()

    def mainloop(self):
        while True:
            main.c.update()

            if main.map.level[self.x, self.y].texture != 'chest':
                return

            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    return
                if e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_ESCAPE:
                        return

                    elif e.key == pygame.K_LEFT:
                        if self.selected == 0:
                            self.selected = len(self.items) - 1
                        else:
                            self.selected -= 1
                    elif e.key == pygame.K_RIGHT:
                        if self.selected == len(self.items) - 1:
                            self.selected = 0
                        else:
                            self.selected += 1

                    if e.key == pygame.K_q:
                        if main.selectedSlot > 0:
                            main.selectedSlot -= 1
                        else:
                            main.selectedSlot = len(main.inventory.inventoryItems) - 1
                    if e.key == pygame.K_e:
                        if main.selectedSlot < len(main.inventory.inventoryItems) - 1:
                            main.selectedSlot += 1
                        else:
                            main.selectedSlot = 0

                    # Taking all items out of the chest
                    elif e.key == pygame.K_g:
                        for item in self.items:
                            if item[0] in specialItemList and not specialItemList[item[0]] \
                                                                  in main.inventory.inventoryItems:
                                main.inventory.addInventoryItem(specialItemList[item[0]]())
                            else:
                                main.inventory.addInventoryItem(Item(item[0], item[0], int(item[1])))
                        main.map.setBlock(self.x, self.y, 'chest')
                        return
                    # Taking selected item(s) from the chest
                    elif e.key == pygame.K_b:
                        if len(self.items) > 0:
                            item = self.items[self.selected]
                            if item[0] in specialItemList and \
                                    not specialItemList[item[0]] in main.inventory.inventoryItems:
                                main.inventory.addInventoryItem(specialItemList[item[0]]())
                            else:
                                main.inventory.addInventoryItem(Item(item[0], item[0], int(item[1])))
                            self.items.remove(item)

                            s = 'chest,'
                            for item in self.items:
                                s += item[0] + '=' + str(item[1]) + ','

                            main.map.setBlock(self.x, self.y, s)

                            if self.selected > len(self.items) - 1:
                                print("large")
                                self.selected = len(self.items) - 1

                    # Adding selected item(s) to the chest
                    if len(main.inventory.inventoryItems) > 0:
                        if e.key == pygame.K_h:
                            name = main.inventory.inventoryItems[main.selectedSlot].name
                            count = main.inventory.inventoryItems[main.selectedSlot].count

                            # Chesking if there already is item with same id in the chest
                            foundSame = False
                            for item in self.items:
                                if item[0] == name:
                                    foundSame = True
                                    item[1] += count
                            if not foundSame:
                                self.items.append([name, count])

                            main.inventory.removeItem(Item(name, name, count))

                            s = 'chest'
                            for item in self.items:
                                s += ',' + item[0] + '=' + str(item[1])

                            main.map.setBlock(self.x, self.y, s)

                            if main.selectedSlot > len(main.inventory.inventoryItems):
                                main.selectedSlot = len(main.inventory.inventoryItems) - 1
                        # Adding one selected item to the chest
                        elif e.key == pygame.K_n:
                            name = main.inventory.inventoryItems[main.selectedSlot].name

                            # Chesking if there already is item with same id in the chest
                            foundSame = False
                            for item in self.items:
                                if item[0] == name:
                                    foundSame = True
                                    item[1] += 1
                            if not foundSame:
                                self.items.append([name, 1])

                            main.inventory.removeItem(Item(name, name, 1))

                            s = 'chest'
                            for item in self.items:
                                s += ',' + item[0] + '=' + str(item[1])

                            main.map.setBlock(self.x, self.y, s)

                            if main.selectedSlot > len(main.inventory.inventoryItems):
                                main.selectedSlot = len(main.inventory.inventoryItems) - 1

            main.renderer.renderGame()
            self.sc.blit(self.gray, self.gray.get_rect(topleft=(0, 0)))

            pygame.draw.rect(self.sc, (255, 255, 255), (SCREEN_W // 2 - len(self.items) // 2 * BLOCK_W,
                                                        SCREEN_H // 2 - BLOCK_H // 2,
                                                        len(self.items) * BLOCK_W,
                                                        BLOCK_H))

            if len(self.items) > 0:
                for item in range(len(self.items)):
                    p = SCREEN_W // 2 - len(self.items) // 2 * BLOCK_W + item * BLOCK_W
                    if self.selected != item:
                        t = pygame.transform.scale(
                            main.textures[self.items[item][0].split(',')[0]], (BLOCK_W // 2, BLOCK_H // 2))
                    else:
                        t = main.textures[self.items[item][0]]
                    self.sc.blit(t, t.get_rect(center=(p + BLOCK_W // 2, SCREEN_H // 2)))

                    t = main.font.render(str(self.items[item][1]), True, (0, 0, 0))
                    r = t.get_rect(center=(p + BLOCK_W // 2, SCREEN_H // 2 + BLOCK_H // 2))
                    self.sc.blit(t, r)
            else:
                text = main.font.render('This chest is empty!', True, (0, 0, 0))
                r = text.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2))
                pygame.draw.rect(self.sc, (255, 255, 255),
                                 (SCREEN_W // 2 - text.get_width() // 2 - 10,
                                  SCREEN_H // 2 - text.get_height() // 2 - 10,
                                  text.get_width() + 20, text.get_height() + 20))
                self.sc.blit(text, r)

            pygame.display.update()


class InputPrompt:
    def __init__(self, message=''):
        self.sc = main.sc

        self.__prompt = message
        self.__input = ''

    def getInput(self):
        return self.__input

    def show(self):
        while True:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    exit()

                elif e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_RETURN:
                        return
                    elif e.key == pygame.K_ESCAPE or e.key == pygame.K_TAB:
                        return
                    elif e.key == pygame.K_BACKSPACE:
                        self.__input = self.__input[:len(self.__input) - 1]
                    else:
                        self.__input += e.unicode

            self.sc.fill((200, 200, 200))

            msg = main.font.render(self.__prompt, True, (0, 0, 0))
            msgr = msg.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - BLOCK_H))
            pygame.draw.rect(self.sc, (100, 100, 100),
                             (msgr.left - 20, msgr.top - 20, msgr.width + 40, msgr.height + 40))
            self.sc.blit(msg, msgr)

            inp = main.font.render(self.__input, True, (0, 0, 0))
            inpr = inp.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2))
            pygame.draw.rect(self.sc, (100, 100, 100),
                             (inpr.left - 20, inpr.top - 20, inpr.width + 40, inpr.height + 40))
            self.sc.blit(inp, inpr)

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
                        if self.quickMessage:
                            main.messages.append(ChatMessage(self.userMessage, str(main.c.clientId)))
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
                main.renderer.renderGame()
                self.sc.blit(main.sc, main.sc.get_rect(topleft=(0, 0)))

            pygame.draw.rect(self.sc, (100, 100, 100), (0, SCREEN_H - BLOCK_H, SCREEN_W, BLOCK_H))

            if len(self.messages) > 16:
                self.messages = self.messages[len(self.messages) - 16::]

            for message in range(len(self.messages)):
                if self.messages[message][2] == (0, 0, 0):
                    s = self.font.render(
                        "Player #" + str(self.messages[message][0]) + " : " + self.messages[message][1],
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


class UIButton:
    def __init__(self, centerx, centery, text: str, padding=20):
        self.text = main.font.render(text, True, (0, 0, 0))

        self.surface = pygame.Surface((self.text.get_width()+padding*2, self.text.get_height()+padding*2))
        self.surface.fill((128, 128, 128))
        self.surface.blit(self.text, self.text.get_rect(center=(self.surface.get_width()//2,
                                                                self.surface.get_height()//2)))

        self.topleftx = centerx - self.surface.get_width() // 2
        self.toplefty = centery - self.surface.get_height() // 2

    def getSurface(self): return self.surface

    def checkClick(self, x, y) -> bool:
        # Registering click
        if self.topleftx <= x <= self.topleftx+self.surface.get_width() and \
           self.toplefty <= y <= self.toplefty+self.surface.get_height():
            return True
        return False



class PauseMenu:
    def __init__(self, sc):
        self.sc = sc

        self.blackscreen = pygame.Surface((SCREEN_W, SCREEN_H))
        self.blackscreen.fill((0, 0, 0))
        self.blackscreen.set_alpha(128)

        self.continuebutton = UIButton(SCREEN_W//2, SCREEN_H//2-100, 'Continue')
        self.lobbybutton = UIButton(SCREEN_W//2, SCREEN_H//2, 'Back to lobby')
        self.exitbutton = UIButton(SCREEN_W//2, SCREEN_H//2+100, 'Exit')

        self.loop()

    def loop(self):
        while True:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    main.c.disconnect()
                    time.sleep(0.1)
                    exit()
                elif e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_ESCAPE: return

            self.sc.fill((255, 255, 255))

            main.renderer.renderGame()
            self.sc.blit(self.blackscreen, self.blackscreen.get_rect(topleft=(0, 0)))

            # Rendering buttons
            self.sc.blit(self.continuebutton.getSurface(), self.continuebutton.getSurface().get_rect(topleft=(
                self.continuebutton.topleftx, self.continuebutton.toplefty
            )))
            self.sc.blit(self.lobbybutton.getSurface(), self.lobbybutton.getSurface().get_rect(topleft=(
                self.lobbybutton.topleftx, self.lobbybutton.toplefty
            )))
            self.sc.blit(self.exitbutton.getSurface(), self.exitbutton.getSurface().get_rect(topleft=(
                self.exitbutton.topleftx, self.exitbutton.toplefty
            )))

            x, y = pygame.mouse.get_pos()
            clicked = pygame.mouse.get_pressed(3)
            # If left mouse button is clicked, then checking if we clicked any of buttons on the screen
            if clicked[0]:
                if self.continuebutton.checkClick(x, y):
                    return
                elif self.lobbybutton.checkClick(x, y):
                    main.c.disconnect()
                    main.c = Client(main.serverIp, main.serverPort)
                    main.c.setNickname(main.nickname)
                    return
                elif self.exitbutton.checkClick(x, y):
                    main.c.disconnect()
                    time.sleep(0.1)
                    exit()

            pygame.display.update()


class EventHandler:
    def __init__(self):
        self.lastMovement = 0

    def handleEvents(self):
        for e in pygame.event.get():

            if e.type == pygame.QUIT:
                main.c.disconnect()
                time.sleep(0.1)
                exit()
                return

            elif e.type == pygame.KEYDOWN and not main.c.disconnected:

                if e.key == pygame.K_ESCAPE:
                    PauseMenu(main.sc)

                if e.key == pygame.K_SPACE and e.mod == pygame.KMOD_LSHIFT:
                    main.c.sendMessage('shoot' + str(main.x) + '/' + str(main.y + 1) + '/0/1/(0,0,0)')

                if e.key == pygame.K_q or e.key == pygame.K_LEFT:
                    if main.selectedSlot > 0:
                        main.selectedSlot -= 1
                    else:
                        main.selectedSlot = len(main.inventory.inventoryItems) - 1
                if e.key == pygame.K_e or e.key == pygame.K_RIGHT:
                    if main.selectedSlot < len(main.inventory.inventoryItems) - 1:
                        main.selectedSlot += 1
                    else:
                        main.selectedSlot = 0

                if e.key == pygame.K_c:
                    ChatMenu(main.c, main.sc)
                elif e.key == pygame.K_m:
                    ChatMenu(main.c, main.sc, quickMenu=True)

                if e.key == pygame.K_f:
                    main.fullscreen = not main.fullscreen
                    if main.fullscreen:
                        pygame.display.quit()
                        main.sc = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.FULLSCREEN)
                    else:
                        pygame.display.quit()
                        main.sc = pygame.display.set_mode((SCREEN_W, SCREEN_H))

                if e.key == pygame.K_r and main.c.disconnected:
                    global RECONNECTING
                    RECONNECTING = True
                    main.running = False

            elif e.type == pygame.MOUSEBUTTONDOWN and not main.c.disconnected:
                mouse = pygame.mouse.get_pos()
                x, y = mouse[0], mouse[1]

                if x < MAP_W * BLOCK_W and y < MAP_H * BLOCK_H:
                    pygame.draw.rect(main.sc, (255, 0, 0),
                                     (mouse[0] - 10, mouse[1] - 10, BLOCK_W // 4, BLOCK_H // 4))

                    pressed = pygame.mouse.get_pressed(3)
                    if pressed[0] or pressed[2]:
                        movX = 0
                        movY = 0

                        if x // BLOCK_W < main.x:
                            movX = -1
                        elif x // BLOCK_W == main.x:
                            movX = 0
                        elif x // BLOCK_W > main.x:
                            movX = 1

                        if y // BLOCK_H < main.y:
                            movY = -1
                        elif y // BLOCK_H == main.y:
                            movY = 0
                        elif y // BLOCK_H > main.y:
                            movY = 1

                        # For block placing
                        resX = main.x + movX
                        resY = main.y + movY

                        # Handling left and right mouse buttons presses
                        if not (movX == 0 and movY == 0) and 0 <= resX <= MAP_W and 0 <= resY <= MAP_H:
                            # If there's no item in inventory, using "imaginary" pickaxe
                            if len(main.inventory.inventoryItems) == 0:
                                i = Item('pickaxe', 'pickaxe', 1)
                                if pressed[0]:
                                    i.attack(resX, resY, resX, resY)
                                elif pressed[2]:
                                    i.use(resX, resY, resX, resY)
                            else:
                                # If left button was pressed
                                if pressed[0]:
                                    main.inventory.inventoryItems[main.selectedSlot].attack(
                                        resX, resY, x // BLOCK_W, y // BLOCK_H
                                    )

                                # If right button was pressed
                                elif pressed[2]:

                                    # If this is just a block, not a special item, then placing it.
                                    # If it is an item, using it.
                                    if main.inventory.inventoryItems[main.selectedSlot].specialItem:
                                        main.inventory.inventoryItems[main.selectedSlot].use(
                                            resX, resY, x // BLOCK_W, y // BLOCK_H)
                                    else:

                                        # We will place the block only on grass, we won't replace other blocks
                                        if main.map.level[resX, resY].texture == 'grass' and \
                                                main.inventory.inventoryItems[main.selectedSlot].count > 0:

                                            # Checking if newly placed block won't overlap player's hitbox, so
                                            # player won't get stuck in the block
                                            main.map.level[resX, resY] = \
                                                Block.getBlockFromID(resX, resY,
                                                                     main.inventory.inventoryItems[
                                                                         main.selectedSlot].name)

                                            if main.movement.canStepOn(main.pixelx, main.pixely):
                                                # If everything's alright, placing the block,
                                                # and decrementing it's count in inventory
                                                main.map.setBlock(resX, resY,
                                                                  main.inventory.inventoryItems[main.selectedSlot].name)

                                                main.inventory.removeItem(
                                                    Item(main.inventory.inventoryItems[main.selectedSlot].name, '', 1))
                                            else:
                                                main.map.level[resX, resY] = Block.getBlockFromID(resX, resY, 'grass')

            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_r:
                    RECONNECTING = True
                    main.running = False

        # movement
        if time.time() - self.lastMovement > 1 / 5 and not main.c.disconnected:  # 1/(blocksPerSecond)
            keys = pygame.key.get_pressed()

            if keys[pygame.K_w]:
                if main.y > 0:
                    main.movement.addVelocity(0, -1)
            if keys[pygame.K_a]:
                if main.x > 0:
                    main.movement.addVelocity(-1, 0)
            if keys[pygame.K_s]:
                if main.y < MAP_H * BLOCK_H:
                    main.movement.addVelocity(0, 1)
            if keys[pygame.K_d]:
                if main.x < MAP_W * BLOCK_W:
                    main.movement.addVelocity(1, 0)


class Renderer:
    def __init__(self):
        self.sc = main.sc

    def renderGame(self):
        # Rendering map
        for x in range(MAP_W):
            for y in range(MAP_H):
                t = main.textures[main.map.level[x, y].texture.split(',')[0]]
                self.sc.blit(t, t.get_rect(topleft=(x * BLOCK_W, y * BLOCK_H)))

        # Rendering bullets
        for bullet in bullets:
            if bullet.active:
                pygame.draw.rect(self.sc, bullet.color, (bullet.x * BLOCK_W + (BLOCK_W // 4),
                                                         bullet.y * BLOCK_H + (BLOCK_H // 4),
                                                         40, 40))

        # Rendering enemies ( other players )
        for p in players:
            player = players[p]
            if player.active:
                self.sc.blit(main.textures[player.texture],
                             main.textures[player.texture].get_rect(center=(player.x, player.y)))
                pygame.draw.rect(self.sc, (0, 0, 0),
                                 (player.x - 3 - BLOCK_W // 2, player.y - 3 - BLOCK_H // 2, BLOCK_W + 6,
                                  BLOCK_H // 8 + 6))
                pygame.draw.rect(self.sc, (255, 0, 0), (
                    player.x - BLOCK_W // 2, player.y - BLOCK_H // 2, int(player.health * 0.8), BLOCK_H // 8))

        # Rendering "Shadow" under the player to see him easily.
        self.sc.blit(main.textures['arrow'],
                     main.textures['arrow'].get_rect(center=(main.pixelx,
                                                             main.pixely)))

        # Rendering our player
        self.sc.blit(main.textures[main.playerClass.texture],
                     main.textures[main.playerClass.texture].get_rect(
                         center=(main.pixelx, main.pixely)
                     ))

        # Rendering our player HP indicator ( on his head )
        pygame.draw.rect(self.sc, (0, 0, 0),
                         (main.pixelx - 3 - BLOCK_W // 2, main.pixely - 3 - BLOCK_H // 2, BLOCK_W + 6,
                          BLOCK_H // 8 + 6))
        pygame.draw.rect(self.sc, (0, 255, 0), (
            main.pixelx - BLOCK_W // 2, main.pixely - BLOCK_H // 2, int(health * 0.8), BLOCK_H // 8))

        # Rendering objects
        for obj in main.map.objects:
            if main.map.objects[obj].active:
                self.sc.blit(main.textures[main.map.objects[obj].texture],
                             main.textures[main.map.objects[obj].texture].get_rect(
                                 topleft=(main.map.objects[obj].x, main.map.objects[obj].y)))

        # Rendering inventory background
        pygame.draw.line(self.sc, (0, 0, 0), [0, MAP_H * BLOCK_H], [MAP_W * BLOCK_W, MAP_H * BLOCK_H])
        pygame.draw.rect(self.sc, (255, 255, 255), (0, MAP_H * BLOCK_W, SCREEN_W, BLOCK_H))

        # Rendering inventory items
        for slot in range(len(main.inventory.inventoryItems)):
            if slot == main.selectedSlot:
                self.sc.blit(main.textures[main.inventory.inventoryItems[slot].name.split(',')[0]],
                             main.textures[main.inventory.inventoryItems[slot].name.split(',')[0]].get_rect(
                                 topleft=(slot * BLOCK_W, MAP_H * BLOCK_H)))
            else:
                t = pygame.transform.scale(main.textures[main.inventory.inventoryItems[slot].name.split(',')[0]],
                                           (BLOCK_W // 2, BLOCK_H // 2))
                r = t.get_rect(center=(slot * BLOCK_W + BLOCK_W // 2, MAP_H * BLOCK_H + BLOCK_H // 2))
                self.sc.blit(t, r)

            if not main.inventory.inventoryItems[slot].specialItem:
                t = main.font.render(str(main.inventory.inventoryItems[slot].count), True, (0, 0, 0))
                r = t.get_rect(center=(slot * BLOCK_W + BLOCK_W // 2, MAP_H * BLOCK_H + 18))
                self.sc.blit(t, r)

        # Rendering various texts
        t = main.font.render(main.localization['health'] + str(health), True, (0, 0, 0))
        r = t.get_rect(topleft=(0, 0))
        self.sc.blit(t, r)

        t = main.font.render("FPS: " + str(main.fps), True, (0, 0, 0))
        r = t.get_rect(topleft=(0, BLOCK_H // 2))
        self.sc.blit(t, r)

        t = main.font.render("Defence level: " + str(main.defenceLevel), True, (0, 0, 0))
        r = t.get_rect(topleft=(4 * BLOCK_W, 0))
        self.sc.blit(t, r)

        # Rendering messages
        message: ChatMessage
        for message in main.messages:
            if not message.serviceMessage:
                t = main.font.render(str(message.sender) + " : " + message.message, True, message.color)
            else:
                t = main.font.render(str(message.message), True, message.color)

            if message.alpha <= 255:
                t.set_alpha(int(message.alpha))

            r = t.get_rect(topleft=(0, BLOCK_H // 2 * (2 + main.messages.index(message))))
            self.sc.blit(t, r)
            # self.messages[self.messages.index(message)][3] -= 0.5 + 2 * (1 / (len(message[1]) / 5))
            main.messages[main.messages.index(message)].alpha -= 1

        for message in main.messages:
            if message.alpha <= 0:
                main.messages.remove(message)

        # Rendering red "cursor" under the actual cursor.
        mouse = pygame.mouse.get_pos()
        pygame.draw.rect(self.sc, (255, 0, 0), (mouse[0] - 10, mouse[1] - 10, BLOCK_W // 4, BLOCK_H // 4))


class ClassChooser:
    def __init__(self):
        self.sc = main.sc

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

            t = main.font.render(main.localization['selectclass'], True, (0, 0, 0))
            self.sc.blit(t, t.get_rect(topleft=(BLOCK_W, SCREEN_H // 4)))

            for x in range(len(classes)):
                if x == variant:
                    t = main.textures[classes[x][0]]
                    r = t.get_rect(center=(BLOCK_W + x * BLOCK_W + BLOCK_W // 2, SCREEN_H // 2))
                    self.sc.blit(t, r)
                else:
                    t = pygame.transform.scale(main.textures[classes[x][0]], (BLOCK_W // 2, BLOCK_H // 2))
                    r = t.get_rect(center=(BLOCK_W + x * BLOCK_W + BLOCK_W // 2, SCREEN_H // 2))
                    self.sc.blit(t, r)

            pygame.display.update()

        # Adding items from player's class to inventory
        for item in classes[variant][2]:
            main.inventory.addInventoryItem(item())

        # Giving every player 10 wooden doors just for fun :)
        main.inventory.addInventoryItem(Item('wooden_door_closed', 'wooden_door_closed', 10))

        return PlayerClass(classes[variant][2][0](), classes[variant][1], classes[variant][0])


class CollisionDetection:
    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y

        self.xvel = 0  # X velocity
        self.yvel = 0  # Y velocity

    def addVelocity(self, x=0, y=0):
        self.xvel += x
        self.yvel += y

    def update(self):
        # print(self.xvel, self.yvel, end=' ')

        self.x = self.clamp(self.x, -1, MAP_W * BLOCK_W)
        self.y = self.clamp(self.y, -1, MAP_H * BLOCK_H)

        self.xvel = self.clamp(self.xvel, -2, 2)
        self.yvel = self.clamp(self.yvel, -2, 2)

        # print(self.xvel, self.yvel)

        if self.canStepOn(self.x + self.xvel, self.y):
            self.x += self.xvel
        else:
            self.xvel = 0
        if self.canStepOn(self.x, self.y + self.yvel):
            self.y += self.yvel
        else:
            self.yvel = 0

        self.xvel *= 0.9
        self.yvel *= 0.9

        if -0.01 <= self.xvel <= 0.01: self.xvel = 0
        if -0.01 <= self.yvel <= 0.01: self.yvel = 0

    def getPos(self) -> (int, int):
        return self.x, self.y

    @staticmethod
    def playerIsCollidingWith(x, y, playerX=None, playerY=None):
        points = [
            (playerX - BLOCK_W // 3, playerY - BLOCK_H // 3),  # Upleft
            (playerX + BLOCK_W // 3, playerY - BLOCK_H // 3),  # Upright
            (playerX - BLOCK_W // 3, playerY + BLOCK_H // 3),  # Downleft
            (playerX + BLOCK_W // 3, playerY + BLOCK_H // 3)  # Downright
        ]

        if (x, y) in points:
            return True
        else:
            return False

    @staticmethod
    def clamp(val, mn, mx):
        if val > mx:
            return mx
        elif val < mn:
            return mn
        else:
            return val

    @staticmethod
    def canStepOn(x, y):
        # p = []
        # if self.xvel > 0.1 and self.yvel == 0: # Moving right
        #     p.append([x + BLOCK_W//3, y - BLOCK_H//3])
        #     p.append([x + BLOCK_W//3, y + BLOCK_H//3])
        # if self.xvel > 0.1 and self.yvel > 0.1: # Moving downright
        #     p.append([])

        points = [
            (x - BLOCK_W // 3, y - BLOCK_H // 3),  # Upleft
            (x + BLOCK_W // 3, y - BLOCK_H // 3),  # Upright
            (x - BLOCK_W // 3, y + BLOCK_H // 3),  # Downleft
            (x + BLOCK_W // 3, y + BLOCK_H // 3)  # Downright
        ]

        for point in points:
            if 0 <= point[0] <= MAP_W * BLOCK_W and 0 <= point[1] <= MAP_H * BLOCK_H:
                if main.map.level[int(point[0] // BLOCK_W), int(point[1] // BLOCK_H)].collidable:
                    return False
            else:
                return False

        return True


class Main:
    def loadConfig(self):
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

    def loadTextures(self):
        files = os.listdir('textures/')
        self.textures = {}
        for filename in files:
            self.textures[filename.replace('.png', '')] = pygame.image.load('textures/' + filename).convert_alpha()

    def loadSounds(self):
        files = os.listdir('sounds/')
        self.sounds = {}
        for filename in files:
            if not self.settings['disable_sound']:
                self.sounds[filename.split('.')[0]] = pygame.mixer.Sound('sounds/' + filename)
            else:
                self.sounds[filename.split('.')[0]] = SoundStub()

    def __init__(self, surface):
        global main
        main = self

        pygame.init()
        self.fullscreen = False

        self.sc = surface
        pygame.display.set_caption("BattleKiller 2D")

        self.setup()

    def setup(self):
        self.loadConfig()

        self.loadTextures()
        self.loadSounds()

        self.font = pygame.font.SysFont("Arial", 36)

        self.map = MapManager()
        self.inventory = Inventory()

        self.chooser = ClassChooser()
        self.playerClass: PlayerClass
        self.playerClass = self.chooser.classChooser()

        self.eventhandler = EventHandler()
        self.renderer = Renderer()

        # Player position
        self.movement = CollisionDetection(0, 0)
        self.x, self.y = 0, 0
        self.pixelx, self.pixely = 0, 0
        # For continuous movement
        self.lastMovement = time.time()

        # Is game running?
        self.running = True

        # Asking player's nickname
        self.nicknamePrompt = InputPrompt('Please enter your nickname')
        self.nicknamePrompt.show()
        self.nickname = self.nicknamePrompt.getInput()

        # Connecting to the server
        self.c = Client(self.serverIp, self.serverPort)
        self.c.setNickname(self.nickname)

        # Currently selected inventory slot
        self.selectedSlot = 0

        # Storing chat messages
        self.messages = []

        # For fps displaying
        self.prevFrame = time.time()
        self.fps = 0
        self.__frames = 0

        self.defenceLevel = 0

    def mainLoop(self):
        global RECONNECTING

        try:
            self.c.sendMessage('get_objects')
        except:
            pass

        while self.running:
            self.pixelx, self.pixely = self.movement.getPos()
            x, y = int(self.pixelx // BLOCK_W), int(self.pixely // BLOCK_H)
            self.x, self.y = x, y

            # listening for the events
            self.eventhandler.handleEvents()

            self.movement.update()

            self.sc.fill((255, 255, 255))

            if not self.c.disconnected:
                self.c.sendMessage(
                    'set_player' + str(self.pixelx) + '/' + str(self.pixely) + '/' +
                    str(self.playerClass.texture) + '/' + str(health)
                )

                self.c.update()

                if self.c.newMessages:
                    for msg in self.c.newMessages:
                        alpha = 256
                        if msg[2] == (255, 0, 0): alpha = 1024

                        self.messages.append(ChatMessage(msg[1], msg[0], msg[2], True, alpha))
                    self.c.newMessages.clear()

                if health > 0:
                    self.renderer.renderGame()
                else:
                    self.c.disconnect()
                    t = self.font.render(self.localization['game_over'], True, (255, 0, 0))
                    r = t.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2))
                    self.sc.blit(t, r)
            else:
                t = self.font.render(self.localization['disconnected'], True, (0, 0, 0))
                t1 = self.font.render(
                    self.localization['disconnected_reason'] + self.c.disconnectReason, True, (0, 0, 0))
                self.sc.blit(t, t.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - BLOCK_H)))
                self.sc.blit(t1, t1.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 + BLOCK_H)))

            pygame.display.update()

            v = 1 / 160
            # print(v)
            if v > 0:
                time.sleep(v)

            if time.time() - self.prevFrame >= 1:
                self.fps = self.__frames
                self.__frames = 0
                self.prevFrame = time.time()

            self.__frames += 1


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

nextFrameUpdate = False

health = 100

main: Main


def resetGlobals():
    global players, bullets, nextFrameUpdate, health, RECONNECTING, main

    RECONNECTING = False
    players = {}
    bullets = []
    nextFrameUpdate = False
    health = 100
    main = None


if __name__ == '__main__':
    resetGlobals()
    startMenu = StartMenu()
