import os
import math
import traceback
import pygame
import socket
import random
import time
from threading import Thread

BLOCK_W = 80
BLOCK_H = 80

MAP_W = 16
MAP_H = 8

LEVEL_W = 1025
LEVEL_H = 1025

SCREEN_W = MAP_W * BLOCK_W
SCREEN_H = (MAP_H + 1) * BLOCK_H

ORIG_SCREEN_W = SCREEN_W
ORIG_SCREEN_H = SCREEN_H


class CustomFont:
    def __init__(self, size=12):
        self.__arial = pygame.font.SysFont("Arial", 8)

        self.size = size
        self.alphabet = list("""abcdefghijklmnopqrstuvwxyz1234567890                !@#$%^&*()-=_+[]{},./\\?"'|:;""")
        try:
            self.__texture = pygame.image.load('textures/alphabet.png').convert_alpha()
        except Exception as e:
            print("Failed to load alphabet.txt ( custom font texture atlas )")
            self.__texture = pygame.Surface((130, 32)).convert_alpha()

    def __replaceColor(self, surface: pygame.Surface, color, newColor):
        for x in range(surface.get_width()):
            for y in range(surface.get_height()):
                if surface.get_at((x, y)) == color:
                    surface.set_at((x, y), newColor)

    def __image_at(self, rectangle, bg=None, colorkey=None):
        if bg is None:
            bg = (255, 255, 255)

        """Load a specific image from a specific rectangle."""
        # Loads image from x, y, x+offset, y+offset.
        rect = pygame.Rect(rectangle)
        image = pygame.Surface(rect.size)
        image.fill(bg)
        image.blit(self.__texture, (0, 0), rect)
        if colorkey is not None:
            if colorkey == -1:
                colorkey = image.get_at((0, 0))
            image.set_colorkey(colorkey, pygame.RLEACCEL)
        return image

    def __notEqualColor(self, origColor: (int, int, int)) -> (int, int, int):
        generated, bg = False, (0, 0, 0)
        while not generated:
            bg = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
            if bg != origColor and bg != (0, 0, 0):
                generated = True
        return bg

    def render(self, text: str, _, foreground: (int, int, int), background: (int, int, int) = None) -> pygame.Surface:
        surf = pygame.Surface((len(text)*6, 8))
        if background is None:
            background = self.__notEqualColor(foreground)
            surf.fill(background)
            surf.set_colorkey(background)
        else:
            surf.fill(background)

        for i in range(len(text)):
            char = text[i].lower()
            # if char != ' ': print(char, char in self.alphabet)
            if char in self.alphabet:
                j = self.alphabet.index(char)

                x = j % 26
                y = j // 26
                # print(char, j, x, y)

                # Generating background color that willn't match text color and foreground color
                bg = self.__notEqualColor(foreground)

                image = self.__image_at((x * 5, y * 8, 5, 8), colorkey=(255, 255, 255))
                # self.__replaceColor(image, (0, 0, 0), foreground)
                # self.__replaceColor(image, bg, background)
            else:
                image = self.__arial.render(char.upper(), False, foreground, background)

            surf.blit(image, image.get_rect(topleft=(i*6, 0)))

        if self.size != 8:
            surf = pygame.transform.scale(surf, (int(surf.get_width()*(self.size//8)),
                                                 int(surf.get_height()*(self.size//8))))

        return surf


# For raytracing
class Ray:
    def __init__(self, startx, starty, angle, speed, processor):
        self.startx, self.starty = startx, starty
        self.x, self.y = self.startx, self.starty
        self.blockx, self.blocky = int(round(self.x, 0)), int(round(self.y, 0))
        self.angle = angle
        self.speed = speed
        self.proc = processor

        self.distanceTravelled = 0

        self.alive = True

    def tick(self):
        b: Block
        while self.alive:
            self.x += self.speed * math.cos(self.angle*(math.pi/180))
            self.y += self.speed * math.sin(self.angle*(math.pi/180))

            self.distanceTravelled += abs(self.speed * math.cos(self.angle*(math.pi/180)))
            self.distanceTravelled += abs(self.speed * math.sin(self.angle*(math.pi/180)))

            self.blockx, self.blocky = self.x//self.proc.lightMapResolution, \
                                       self.y//self.proc.lightMapResolution

            if self.blockx < 0 or self.blockx >= MAP_W or self.blocky < 0 or self.blocky >= MAP_H:
                self.alive = False
                return
            else:
                if not main.map.level[self.blockx, self.blocky].transparentForLight:
                    self.alive = False
                    return

            pygame.draw.rect(main.map.level[self.x//self.proc.lightMapResolution,
                                            self.y//self.proc.lightMapResolution].templightmap,
                             (255, 255, 0),
                             (int(self.x%self.proc.lightMapResolution), int(self.y%self.proc.lightMapResolution),
                             1, 1))


class RayThread(Thread):
    def __init__(self, x, y, rays, angleFrom, angleTo, raySpeed, processor):
        Thread.__init__(self)

        # Starting point
        self.x, self.y = x, y

        self.nrays = rays
        self.anglefrom = angleFrom
        self.angleto = angleTo

        self.speed = raySpeed

        self.proc = processor

        self.rays: [Ray]
        self.rays = []

        self.done = False

    def run(self) -> None:
        curangle = self.anglefrom
        while curangle <= self.angleto:
            self.rays.append(Ray(self.x * self.proc.lightMapResolution,
                                 self.y * self.proc.lightMapResolution,
                                 curangle, self.speed, self.proc))

            curangle += (self.angleto - self.anglefrom) / self.nrays

        while not self.done:
            for ray in self.rays:
                ray.tick()
                if not ray.alive:
                    self.rays.remove(ray)

            if len(self.rays) == 0: break

        self.done = True

        exit()


class LightProcessor:
    def __init__(self):
        # Resolution of light map for each block. N by N pixels
        self.lightMapResolution = 4

        # Some settings
        self.nthreads = 2
        self.rays = 240
        self.rayMultiplier = 360/self.rays
        self.raysperthread = self.rays // self.nthreads
        self.rayspeed = 1

        self.threads: [RayThread]
        self.threads = []

        self.prevFrame: {(int, int): {str, bool, bool}}
        self.prevFrame = {}
        for x in range(MAP_W):
            for y in range(MAP_H):
                self.prevFrame[x, y] = ['', False, False]

        self.lastLightCalculation = time.time()

    def calcLight(self, force=False):
        for thread in self.threads:
            if thread.done: self.threads.remove(thread)
        if len(self.threads) == 0:
            b: Block
            for x in range(MAP_W):
                for y in range(MAP_H):
                    try:
                        main.map.level[x, y].lightmap.blit(main.map.level[x, y].templightmap, (0, 0))
                    except Exception as e:
                        print("Failed to render lightmap at", x, y, e)
            main.renderer.renderLightmap()

            currentFrame = {}
            for x in range(MAP_W):
                for y in range(MAP_H):
                    currentFrame[x, y] = main.map.level[x, y].texture, \
                                         main.map.level[x, y].emittingLight, \
                                         main.map.level[x, y].transparentForLight

            if currentFrame != self.prevFrame or force:
                self.threads.clear()

                b: Block
                for x in range(MAP_W):
                    for y in range(MAP_H):
                        b = main.map.level[x, y]
                        b.templightmap.fill((0, 0, 0))

                for x in range(MAP_W):
                    for y in range(MAP_H):
                        if main.map.level[x,y].emittingLight:
                            for thread in range(self.nthreads):
                                t = RayThread(x+0.5, y+0.5, self.raysperthread,
                                              thread*self.raysperthread*self.rayMultiplier,
                                              (thread+1)*self.raysperthread*self.rayMultiplier,
                                              self.rayspeed, self)
                                t.start()
                                self.threads.append(t)

                self.prevFrame = currentFrame.copy()

                self.lastLightCalculation = time.time()


def clamp(val, minimum, maximum):
    if val < minimum:
        return minimum
    elif val > maximum:
        return maximum
    else:
        return val


class SoundStub:
    def play(self, duration=0): pass


class Block:
    @staticmethod
    def getBlockFromID(x, y, blockID: str, attributes=None):
        if attributes is None:
            attributes = {}
        try:
            if blockID == 'wall':
                return StoneWall(x, y)
            elif blockID == 'spawnpoint':
                return Spawnpoint(x, y)
            elif blockID == 'barrier':
                return Barrier(x, y)
            elif blockID == 'tree':
                return Block(x, y, collidable=False, transparentForLight=True, movementSpeedMultiplier=0.5,
                             name='Tree', texture='tree')
            elif blockID == 'wooden_door_closed':
                return Door(x, y)
            elif blockID == 'wooden_door_opened':
                d = Door(x, y, True)
                return d
            elif blockID == 'heart':
                return Heart(x, y)
            elif blockID.split(',')[0] == 'chest':
                return Chest(x, y, attribs=attributes)
            elif blockID == 'grass':
                return Block(x, y, False, False, transparentForLight=True, texture='grass',
                             name='How you have mined grass block?')
            elif 'wire' in blockID:
                return Wire(x, y, attributes)
            elif 'lamp' in blockID:
                return Lamp(x, y, attributes)
            elif 'switch' in blockID:
                return Switch(x, y, attributes)
            elif 'computer' in blockID:
                return Computer(x, y, attributes)
            else:
                return Block(x, y, name=blockID, texture=blockID)
        except Exception as e:
            print("Exception in Block.getBlockFromID():", e)
            traceback.print_exc()
            return Block(x, y, name='wall', texture='wall')

    def __setitem__(self, key, value):
        self.attributes[key] = value
        main.map.updateBlock(self.x, self.y, self)

    def __getitem__(self, item):
        if item in self.attributes:
            return self.attributes[item]
        else:
            return ''

    def __eq__(self, other):
        return self.attributes == other.attributes and self.texture == other.texture and \
               self.name == other.name and self.collidable == other.collidable and \
               self.x == other.x and self.y == other.y and self.breakable == other.breakable and \
               self.visible == other.visible and self.emittingLight == other.emittingLight and \
               self.transparentForLight == other.transparentForLight

    def __init__(self, x, y, collidable=True, breakable=True, visible=True,
                 emittingLight=False, transparentForLight = False,
                 texture='wall', name='Stone wall',
                 attributes=None, movementSpeedMultiplier=1.0):
        if attributes is None:
            self.attributes = {}
        else:
            self.attributes = attributes

        self.collidable = collidable
        # (works only if block is not collidable). How fast player could walk through this block. 1 is normal speed,
        # <1 is slower, >1 is faster
        self.movementSpeedMultiplier = movementSpeedMultiplier
        self.breakable = breakable
        self.visible = visible
        self.emittingLight = emittingLight
        self.transparentForLight = transparentForLight

        self.texture = texture
        self.name = name

        self.__surf = pygame.Surface((BLOCK_W, BLOCK_H))
        self.__surf.fill((128, 128, 128))

        self.lightmap = pygame.Surface((main.lightProcessor.lightMapResolution,
                                        main.lightProcessor.lightMapResolution))
        self.lightmap.fill((0, 0, 0))
        # self.lightmap.set_colorkey((255, 255, 0))
        # self.lightmap.set_alpha(128)

        self.templightmap = pygame.Surface((main.lightProcessor.lightMapResolution,
                                            main.lightProcessor.lightMapResolution))
        self.templightmap.fill((0, 0, 0))

        self.x, self.y = x, y

    def renderBlock(self, dest: pygame.Surface, topleftx: int, toplefty: int):
        dest.blit(main.textures16['grass'], main.textures16['grass'].get_rect(topleft=(topleftx, toplefty)))

        dest.blit(main.textures16[self.texture.split(',')[0]],
                  main.textures16[self.texture.split(',')[0]].get_rect(topleft=(topleftx, toplefty)))

    def renderLightmap(self, dest: pygame.Surface, topleftx: int, toplefty: int):
        t = pygame.transform.scale(self.lightmap, (BLOCK_W, BLOCK_H))
        main.renderer.mapsc.blit(t, t.get_rect(topleft=(topleftx, toplefty)))

    def getSurface(self) -> pygame.Surface:
        return self.__surf

    def updateBlock(self) -> None:
        pass
        #self.renderBlock(main.renderer.mapsc, self.x*BLOCK_W, self.y*BLOCK_H)

    def breakBlock(self) -> bool:
        if self.breakable:
            main.inventory.addInventoryItem(Item(name=self.name, texture=self.texture, count=1, specialItem=False,
                                                 attributes=self.attributes))
            self.replaceWith(Block.getBlockFromID(self.x, self.y, 'grass'))
            return True
        return False

    def interact(self):
        pass

    def replaceWith(self, block) -> None:
        main.map.setBlock(self.x, self.y, block)


class Spawnpoint(Block):
    def __init__(self, x, y):
        Block.__init__(self, x, y, collidable=False, breakable=False,
                       texture='spawnpoint', name='Spawnpoint flag')


class Barrier(Block):
    def __init__(self, x, y):
        Block.__init__(self, x, y, collidable=True, breakable=False,
                       texture='barrier', name='Barrier block')


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
    def __init__(self, x, y, attribs):
        Block.__init__(self, x, y, texture='chest', name='Chest', attributes=attribs)

        # [['hammer', 1], ['planks', 25]]
        self.items = self.attributes['items']

        print(self.items, self.texture)

    def breakBlock(self) -> bool:
        main.inventory.addInventoryItem(Item('Chest', 'chest', 1, False, True, {'items': []}))
        self.replaceWith(Block.getBlockFromID(self.x, self.y, 'grass'))
        return True

    def interact(self):
        ChestMenu(main.sc, self.items, self.x, self.y)


class Heart(Block):
    def __init__(self, x, y):
        Block.__init__(self, x, y, breakable=False, texture='heart', transparentForLight=True)

    def interact(self):
        main.defenceLevel += 10
        main.map.setBlock(self.x, self.y, 'grass')


class Wire(Block):
    # Attributes must be:
    # {
    # energy: (level of energy. from 0 to 5),
    # rotation: (from ffff to tttt, t means that wire in this size ( nswe ) is connected to something.
    # }
    def __init__(self, x, y, attributes: dict = None):
        if attributes == {} or attributes is None or not attributes:
            attributes = {'electrical': True, 'energy': 0, 'rotation': 'tttt'}

        Block.__init__(self, x, y, name='wire', movementSpeedMultiplier=0.8, collidable=False, transparentForLight=True,
                       texture='wire' + attributes['rotation'], attributes=attributes)

        self.energy = self.attributes['energy']

    def breakBlock(self) -> None:
        self.replaceWith(Block.getBlockFromID(self.x, self.y, 'grass'))
        main.inventory.addInventoryItem(Item('Wire', 'wirefftt', 1, False,
                                             attributes={'electrical': True, 'energy': 0, 'rotation': 'ffff'}))

    def interact(self):
        # self.attributes['energy_source'] = (self.x, self.y)
        # self.attributes['energy'] += 1
        # main.map.updateBlock(self.x, self.y, self)
        pass

    def renderBlock(self, dest: pygame.Surface, topleftx: int, toplefty: int) -> None:
        dest.blit(main.textures16['grass'], main.textures16['grass'].get_rect(topleft=(topleftx, toplefty)))
        dest.blit(main.textures16[self.texture], main.textures16[self.texture].get_rect(topleft=(topleftx, toplefty)))
        pygame.draw.rect(dest, (clamp(self.attributes['energy']*255, 0, 255), 0, 0), (topleftx+7,
                                                                                      toplefty+7,
                                                                                      2, 2))
    def renderLightmap(self, dest: pygame.Surface, topleftx: int, toplefty: int) -> None:
        t = pygame.transform.scale(self.lightmap, (BLOCK_W, BLOCK_H))
        dest.blit(t, t.get_rect(topleft=(topleftx, toplefty)))


class Lamp(Block):
    def __init__(self, x, y, attributes: dict = None):
        if attributes == {} or attributes is None or not attributes:
            attributes = {'electrical': True, 'energy': 0}

        t = 'lampoff'
        e = False
        if attributes['energy'] > 0:
            t = 'lampon'
            e = True
        Block.__init__(self, x, y, name='lamp', texture=t, attributes=attributes, transparentForLight=True)
        self.emittingLight = e

        self.prevFrameState = self.emittingLight

    def updateBlock(self) -> None:
        if self.attributes['energy'] > 0:
            self.texture = 'lampon'
            self.emittingLight = True
        else:
            self.texture = 'lampoff'
            self.emittingLight = False


class Switch(Block):
    def __init__(self, x, y, attributes: dict = None):
        if attributes == {} or attributes is None or not attributes:
            attributes = {'electrical': True, 'on': False, 'energy_source': True, 'energy': 0}

        Block.__init__(self, x, y, name='switch', texture='switchoff', attributes=attributes, transparentForLight=True)

        if self.attributes['on']: self.texture = 'switchon'

    def interact(self):
        self.attributes['on'] = not self.attributes['on']
        self.attributes['energy'] = int(self.attributes['on'])

        if self.attributes['on']:
            self.texture = 'switchon'
        else:
            self.texture = 'switchoff'

        main.map.setBlock(self.x, self.y, self)


class Computer(Block):
    def __init__(self, x, y, attributes: dict = None):
        if attributes == {} or attributes is None or not attributes:
            attributes = {'electrical': True, 'energy': 0}

        Block.__init__(self, x, y, name='Computer', texture='computer', breakable=False, attributes=attributes)

        # if 'screen' in self.attributes:
        #     print(self.attributes['screen'])

    def interact(self):
        if self.attributes['energy'] > 0:
            m = ComputerScreen(main.sc, self.x, self.y)


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
    def __init__(self, name, texture, count, specialItem=False, stackable=True, attributes=None):
        self.name, self.texture, self.count = name, texture, count
        self.stackable = stackable
        self.specialItem = specialItem

        if attributes is None:
            self.attributes = {}
        else: self.attributes = attributes

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
        self.interactWithBlock(bx, by)

    def attack(self, bx, by, ox, oy):
        self.interactWithBlock(bx, by)


class Pickaxe(Item):
    def __init__(self):
        super().__init__('Pickaxe', 'pickaxe', 1, specialItem=True)
        self.specialItem = True

    def use(self, bx, by, ox, oy):
        if not main.map.level[bx, by].texture == 'grass':
            main.map.level[bx, by].breakBlock()


"""
class Hammer(Item):
    def __init__(self):
        super().__init__('Hammer', 'hammer', 1, specialItem=True)
        self.specialItem = True

    def use(self, bx, by, ox, oy):
        if main.map.level[bx, by].texture == 'grass':
            main.map.setBlock(bx, by, 'wood')
            if main.movement.playerIsCollidingWith(bx,by, main.x,main.y):
                main.map.level[bx, by].breakBlock()

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
"""


class MagicStick(Item):
    def __init__(self):
        super().__init__('Magical stick', 'magic_stick', 1, specialItem=True)
        self.specialItem = True

    def use(self, bx, by, ox, oy):
        b = random.choice(['wall', 'grass', 'wood'])
        if b != 'grass':
            main.map.setBlock(ox, oy, b)


class Candle(Item):
    def __init__(self):
        super().__init__('Candle', 'candle', 1, specialItem=True)
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
        super().__init__('Knife', 'knife', 1, specialItem=True)
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
        super().__init__('Sniper rifle', 'sniper_rifle', 1, specialItem=True)
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


specialItemList = {'pickaxe': Pickaxe,
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
            if i.name == item.name or i.texture == item.name and i.attributes == item.attributes and i.stackable:
                i.count += item.count
                return

        self.inventoryItems.append(item)

    def removeItem(self, item: Item):
        global main

        i: Item
        for i in self.inventoryItems:
            if i.name == item.name and i.count >= item.count and item.attributes == i.attributes:
                i.count -= item.count

                if i.count == 0:
                    self.inventoryItems.remove(i)
                    if main.selectedSlot >= len(self.inventoryItems):
                        main.selectedSlot -= 1

                return

    def removeItemByName(self, name: str, count: int):
        for i in self.inventoryItems:
            if i.name == name and i.count >= count and i.count >= item.count and (item.attributes == i.attributes):
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
            if i.name == name or i.texture == name:
                return True

        return False


class ChunkLoader:
    def __init__(self):
        self.level = main.map.level

        self.visibleChunks = []

    def update(self):
        points = [
            (main.x-8, main.y-8), (main.x, main.y-8), (main.x+8, main.y-8),
            (main.x-8, main.y),   (main.x, main.y),   (main.x+8, main.y),
            (main.x-8, main.y+8), (main.x, main.y+8), (main.x+8, main.y+8)
        ]

        chunksToLoad = []
        self.visibleChunks.clear()
        for x,y in points:
            self.visibleChunks.append((x//8, y//8))
            if not (x,y) in self.level.lvl:
                chunksToLoad.append((x//8, y//8))

        for x,y in chunksToLoad:
            # print("Loading chunk", x, y)
            main.c.sendMessage('load_chunk/' + str(x) + '/' + str(y))


class Level:
    def __init__(self):
        self.lvl = {}

    def __getitem__(self, item: (int, int)) -> Block:
        try:
            if item in self.lvl:
                return self.lvl[item]
            else:
                # print("Index out of bounds error. Tried to access block at", item)
                return Block.getBlockFromID(item[0], item[1], 'grass')
        except:
            print("Level.__getitem__(item) error. item:", item)
            traceback.print_exc()
            return Block.getBlockFromID(0, 0, 'grass')

    def __setitem__(self, key: (int, int), value: Block):
        self.lvl[key] = value



class MapManager:
    def __init__(self):
        self.level = Level()
        self.objects = {}

    def loadChunk(self, x: int, y: int) -> None:
        pass

    def unloadChunk(self, x: int, y: int):
        pass

    def updateBlock(self, x, y, block: Block):
        self.level[x, y] = block
        main.c.sendMessage('set_block' + str(x) + '/' + str(y) + '/' + str(block.texture) + '/' + str(block.attributes))

    def updateMap(self):
        for x in range(MAP_W):
            for y in range(MAP_H):
                self.level[x, y].updateBlock()


    def setBlock(self, x, y, block):
        try:
            x = int(x)
            y = int(y)

            if type(block) == str:
                if block == 'wooden_door_closed':
                    bl = Door(x, y)
                elif block == 'wooden_door_opened':
                    bl = Door(x, y, True)
                else:
                    bl = Block.getBlockFromID(x, y, block, {})
            else:
                bl = block
                bl.x, bl.y = x, y

            # Playing sound if we break block
            if bl.texture == 'grass':
                main.sounds['block_break'].play()
            else:
                main.sounds['block_place'].play()

            self.level[x, y] = bl
            main.c.sendMessage('set_block' + str(x) + '/' + str(y) + '/' + str(bl.texture) + '/' + str(bl.attributes))
        except:
            print("MapManager.setBlock() exception:")
            traceback.print_exc()

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

        self.rx, self.tx = 0, 0

        try:
            self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

            print("Connecting to server at", sip, sport)
            self.s.connect((sip, sport))
            self.s.setblocking(False)

            self.clientId = -1
            self.playerInLobby = True

            self.lobbyMenu()
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

            errorscreen = ShowErrorMessage(self.disconnectReason)
            errorscreen.display()

        self.newMessages = []
        self.sent = False
        self.lastUpdate = 0

    def lobbyMenu(self):
        # Structure is [[gameTitle, playersInGame]]
        games: [str, int, str]
        games = []

        selectedGame = 0
        joinedGame = False

        lastGamesRequest = 0
        viewingArchivedGames = False
        while not joinedGame:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self.sendMessage('disconnect')
                    time.sleep(0.1)
                    exit()
                elif e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_a:
                        viewingArchivedGames = not viewingArchivedGames
                        games.clear()

                    if e.key == pygame.K_UP:
                        if selectedGame > 0: selectedGame -= 1
                        else: selectedGame = len(games)-1

                    elif e.key == pygame.K_DOWN:
                        if selectedGame < len(games)-1: selectedGame += 1
                        else: selectedGame = 0

                    if e.key == pygame.K_c:
                        gamename = InputPrompt('Choose a name for the battle:', default=main.nickname+"'s game")
                        gamename.show()
                        self.sendMessage('create_game/' + gamename.getInput())
                        return

                    elif e.key == pygame.K_RETURN:
                        if len(games) == 0:
                            gamename = InputPrompt('Choose a name for the battle:', default=main.nickname+"'s game")
                            gamename.show()
                            self.sendMessage('create_game/' + gamename.getInput())
                            return

                        if viewingArchivedGames:
                            self.sendMessage('join_archived_game/' + games[selectedGame][2] + '/' + str(main.nickname))
                        else:
                            self.sendMessage('join_game/' + games[selectedGame][2] + '/' + str(main.nickname))
                        return

            if selectedGame > len(games) and selectedGame != 0:
                selectedGame = len(games)-1

            if time.time() - lastGamesRequest >= 0.5:
                if viewingArchivedGames: self.sendMessage('get_archived_games')
                else: self.sendMessage('get_games')
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

            if viewingArchivedGames: t = main.font.render("Archived games: ", True, (153, 0, 0))
            else: t = main.font.render("Active games: ", True, (0, 128, 0))
            r = t.get_rect(topleft=(10, 0))
            main.sc.blit(t, r)

            if len(games) > 0:
                for i in range(len(games)):
                    if viewingArchivedGames:
                        t = main.font.render(str(games[i][0]), True, (0, 0, 0))
                    else:
                        t = main.font.render(str(games[i][0]) + '; ' + str(games[i][1]) + ' Players.', True, (0, 0, 0))

                    if i == selectedGame:
                        pygame.draw.rect(main.sc, (170, 170, 170), (10, 46+i*56, t.get_width()+40, t.get_height()))
                    else:
                        pygame.draw.rect(main.sc, (70, 70, 70), (10, 46+i*56, t.get_width()+40, t.get_height()))

                    r = t.get_rect(topleft=(20, 46+i*56))
                    main.sc.blit(t, r)
            else:
                if viewingArchivedGames:
                    t = main.font.render("Currently there are no archived battles. Why not create one?",
                                         True, (0, 0, 0))
                else:
                    t = main.font.render("Currently there are no active battles. Why not create one?", True, (0, 0, 0))
                r = t.get_rect(center=(SCREEN_W//2, SCREEN_H//2))
                main.sc.blit(t, r)

            pygame.display.update()

    def setNickname(self, nickname: str):
        self.sendMessage('set_nick/' + str(nickname))

    def update(self):
        global players
        global health
        global bullets
        global nextFrameUpdate

        if time.time() - self.lastUpdate >= 1/30:
            msg = ''
            if not nextFrameUpdate:
                bullets.clear()

                try:
                    msg = ['hello']
                    while msg != []:
                        msg = self.getMessages()

                        if msg:
                            for obj in msg:
                                if obj:
                                    self.rx += 1
                                    s = obj.split('/')
                                    if s[0] == 'timeofday':
                                        main.timeofday = float(s[1])
                                    elif s[0] == 'yourid':
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
                                        x, y = int(s[1]), int(s[2])
                                        origb = main.map.level[x, y]
                                        b = Block.getBlockFromID(x, y, s[3],
                                            eval(s[4]))

                                        if b != origb:
                                            # print("Changed block id", s[3], ", attribs", s[4])
                                            main.map.level[x, y] = b
                                            main.map.level[x, y].lightmap = origb.lightmap.copy()
                                            main.map.level[x, y].templightmap = origb.templightmap.copy()
                                    elif s[0] == 'chunk':
                                        blocks = eval(s[1])
                                        attributes = eval(s[2])

                                        for x, y in blocks:
                                            origb = main.map.level[x, y]
                                            b = Block.getBlockFromID(x, y, blocks[x, y], attributes[x, y])
                                            main.map.level[x, y] = b

                                        # print("Chunk loaded from server")
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

            self.lastUpdate = time.time()

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
            if message:
                self.tx += 1

                m = str(message) + ';'
                self.s.send(m.encode('utf-8'))
            else: return False, None

            return True, None
        except Exception as e:
            return False, e

    def disconnect(self):
        if not self.disconnected:
            self.sendMessage('disconnect')
            self.disconnected = True


class ComputerScreen:
    def __init__(self, sc, x, y):
        self.sc = sc
        self.x, self.y = x, y

        self.charWidth, self.charHeight = 6, 9
        self.screenWidth, self.screenHeight = 24, 4
        self.prevFrameScreenSize = (24, 4)
        self.screen = pygame.Surface((24*6, 4*9))

        self.prevFrameScreen = ''

        self.loop()

    def loop(self):
        while True:
            main.update(False)

            if type(main.map.level[self.x, self.y]) != Computer:
                return

            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    main.c.disconnect()
                    time.sleep(0.1)
                    exit(0)
                elif e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_ESCAPE:
                        return
                    elif e.key not in [pygame.K_TAB, pygame.K_BACKSPACE]:
                        c = e.unicode
                        if e.key == pygame.K_RETURN:
                            c = '\n'
                        main.c.sendMessage('computer_input' + str(self.x) + '/' + str(self.y) + '/' + c)

            main.renderer.renderGame()

            # self.screen.fill((128, 128, 128))
            # print(self.computer.attributes['screen'], '\n')

            if 'screen' in main.map.level[self.x, self.y].attributes and \
               main.map.level[self.x, self.y].attributes['screen'] != self.prevFrameScreen:
                self.screen.fill((128, 128, 128))

                width, height, screen, background, foreground = main.map.level[self.x, self.y].attributes['screen'].split('-')
                width, height, screen, background, foreground = int(width), int(height), eval(screen), eval(background), eval(foreground)

                if (width, height) != self.prevFrameScreenSize:
                    self.screenWidth, self.screenHeight = width, height
                    self.screen = pygame.Surface((self.screenWidth*self.charWidth, self.screenHeight*self.charHeight))

                for y in range(self.screenHeight):
                    for x in range(self.screenWidth):
                        t = main.customfont.render(
                            screen[y*self.screenWidth+x], True,
                            foreground[y*self.screenWidth+x], background[y*self.screenWidth+x])
                        r = t.get_rect(topleft=(x*self.charWidth, y*self.charHeight))

                        pygame.draw.rect(self.screen, background[y*self.screenWidth+x],
                                         (x*self.charWidth, y*self.charHeight, self.charWidth, self.charHeight))
                        self.screen.blit(t, r)

            if 'screen' in main.map.level[self.x, self.y].attributes:
                self.prevFrameScreen = main.map.level[self.x, self.y].attributes['screen']
            self.prevFrameScreenSize = (self.screenWidth, self.screenHeight)

            # Multipliying screen size by these 2 variables, for screen to fill the whole screen
            multX, multY = 16, 16
            while (self.screen.get_width()*multX > SCREEN_W or self.screen.get_height()*multY > SCREEN_H ) and \
                  0 < multX and 0 < multY:
                multX -= 1
                multY -= 1
            screen = pygame.transform.scale(self.screen, (self.screen.get_width()*multX, self.screen.get_height()*multY))

            self.sc.blit(screen, screen.get_rect(center=(SCREEN_W//2, SCREEN_H//2)))

            pygame.display.update()


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
            main.update(acceptEvents=False)

            if type(main.map.level[self.x, self.y]) != Chest:
                return
            elif main.map.level[self.x, self.y].items != self.items:
                print(self.items, main.map.level[self.x, self.y].items)
                self.items = main.map.level[self.x, self.y].items

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
                        main.map.setBlock(self.x, self.y, Chest(self.x, self.y, {'items':[]}))
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

                            main.map.setBlock(self.x, self.y, Chest(self.x, self.y, {'items':self.items}))

                            if self.selected > len(self.items) - 1:
                                print("large")
                                self.selected = len(self.items) - 1


                    # Adding selected item(s) to the chest
                    if len(main.inventory.inventoryItems) > 0:
                        if e.key == pygame.K_h:
                            name = main.inventory.inventoryItems[main.selectedSlot].texture
                            count = main.inventory.inventoryItems[main.selectedSlot].count

                            # Chesking if there already is item with same id in the chest
                            foundSame = False
                            for item in self.items:
                                if item[0] == name:
                                    foundSame = True
                                    item[1] += count
                            if not foundSame:
                                self.items.append([name, count])

                            main.inventory.removeItem(Item(main.inventory.inventoryItems[main.selectedSlot].name, name, count))

                            main.map.setBlock(self.x, self.y, Chest(self.x, self.y, {'items':self.items}))

                            if main.selectedSlot > len(main.inventory.inventoryItems):
                                main.selectedSlot = len(main.inventory.inventoryItems) - 1

                        # Adding one selected item to the chest
                        elif e.key == pygame.K_n:
                            name = main.inventory.inventoryItems[main.selectedSlot].texture

                            # Chesking if there already is item with same id in the chest
                            foundSame = False
                            for item in self.items:
                                if item[0] == name:
                                    foundSame = True
                                    item[1] += 1
                            if not foundSame:
                                self.items.append([name, 1])

                            main.inventory.removeItem(Item(main.inventory.inventoryItems[main.selectedSlot].name, name, 1))

                            main.map.setBlock(self.x, self.y, Chest(self.x, self.y, {'items':self.items}))

                            if main.selectedSlot > len(main.inventory.inventoryItems):
                                main.selectedSlot = len(main.inventory.inventoryItems) - 1

            main.renderer.renderGame()
            self.sc.blit(self.gray, self.gray.get_rect(topleft=(0, 0)))

            pygame.draw.rect(self.sc, (255, 255, 255), (int(SCREEN_W / 2 - len(self.items) / 2 * BLOCK_W),
                                                        SCREEN_H // 2 - BLOCK_H // 2,
                                                        len(self.items) * BLOCK_W,
                                                        BLOCK_H))

            if len(self.items) > 0:
                for item in range(len(self.items)):
                    p = int(SCREEN_W / 2 - len(self.items) / 2 * BLOCK_W + item * BLOCK_W)
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


class ShowErrorMessage:
    def __init__(self, error='', title='connection error.'):
        self.msg = error.split('\n')
        self.title = title

        self.sc: pygame.Surface
        self.sc = main.sc

    def display(self):
        while True:
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    exit()
                elif e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_r:
                        main.running = False
                        self.sc.fill((128,128,128))
                        pygame.display.update()
                        return

            self.sc.fill((128, 128, 128))

            t = main.font.render(self.title, True, (128, 0, 0))
            r = t.get_rect(center=(SCREEN_W//2, SCREEN_H//2-BLOCK_H*2.5))
            self.sc.blit(t, r)

            t = main.font.render("Press R to exit to main menu", True, (0, 0, 128))
            r = t.get_rect(center=(SCREEN_W//2, SCREEN_H//2-BLOCK_H*2))
            self.sc.blit(t, r)

            for line in self.msg:
                t = main.font.render(line, True, (0, 0, 0))
                if t.get_width() > SCREEN_W: t = pygame.transform.scale(t, (SCREEN_W, t.get_height()))
                r = t.get_rect(center=(SCREEN_W//2, SCREEN_H//2+self.msg.index(line)*40-BLOCK_H))
                self.sc.blit(t, r)

            pygame.display.update()


class InputPrompt:
    def __init__(self, message='', default=''):
        self.sc = main.sc

        self.__default = default
        self.__prompt = message
        self.__input = ''

    def getInput(self):
        if len(self.__input) == 0: return self.__default
        else: return self.__input

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

        # self.font = pygame.font.SysFont('Arial', 36)
        self.font = main.font

        self.quickMessage = quickMenu

        self.mainloop()

    def mainloop(self):
        while True:
            main.update(False)

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
            main.update(False)

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
            # If left mouse button is clicked, then checking if user clicked any of buttons on the screen
            if clicked[0]:
                if self.continuebutton.checkClick(x, y):
                    return
                elif self.lobbybutton.checkClick(x, y):
                    main.c.disconnect()
                    time.sleep(0.1)
                    main.setup(nickname=main.nickname)
                    return
                elif self.exitbutton.checkClick(x, y):
                    main.c.disconnect()
                    time.sleep(0.1)
                    main.running = False
                    return

            pygame.display.update()


class EventHandler:
    def __init__(self):
        self.lastMovement = 0

        # The block the mouse is pointing at
        self.resx, self.resy = 0, 0
        self.px, self.py = 0, 0

    def handleEvents(self):
        global SCREEN_W, SCREEN_H

        # Transfering screen mouse corrdinates to world coordinates

        mouse = pygame.mouse.get_pos()
        x, y = int(mouse[0] / (main.curWidth / SCREEN_W)), \
               int(mouse[1] / (main.curHeight / SCREEN_H))

        movX = 0
        movY = 0

        if x < SCREEN_W // 2 - BLOCK_W // 2:
            movX = -1
        elif SCREEN_W // 2 - BLOCK_W // 2 <= x <= SCREEN_W // 2 + BLOCK_W // 2:
            movX = 0
        elif x > SCREEN_W // 2 + BLOCK_W // 2:
            movX = 1

        if y < SCREEN_H // 2 - BLOCK_H // 2:
            movY = -1
        elif SCREEN_H // 2 - BLOCK_H // 2 <= y <= SCREEN_H // 2 + BLOCK_H // 2:
            movY = 0
        elif y > SCREEN_H // 2 + BLOCK_H // 2:
            movY = 1

        ox = (x - (SCREEN_W // 2 - main.pixelx)) // BLOCK_W
        oy = (y - (SCREEN_H // 2 - main.pixely)) // BLOCK_H
        self.px, self.py = ox, oy

        resX = clamp(ox, main.x-1, main.x+1)
        resY = clamp(oy, main.y-1, main.y+1)
        self.resx, self.resy = resX, resY

        for e in pygame.event.get():

            if e.type == pygame.QUIT:
                main.c.disconnect()
                time.sleep(0.1)
                exit()
                return

            # When user resizes the window
            elif e.type == pygame.VIDEORESIZE:
                main.curWidth = e.w
                main.curHeight = e.h

            elif e.type == pygame.KEYDOWN and not main.c.disconnected:

                # Displaying pause menu when user presses Escape
                if e.key == pygame.K_ESCAPE:
                    PauseMenu(main.sc)

                # Displaying various debug info like fps and player position
                if e.key == pygame.K_F3:
                    main.displayingDebugInfo = not main.displayingDebugInfo

                # When users presses Lshift+Space, bullet will fly down from the player
                # This is very old function, now we have sniper class, so I may remove this functionality later
                if e.key == pygame.K_SPACE and e.mod == pygame.KMOD_LSHIFT:
                    main.c.sendMessage('shoot' + str(main.x) + '/' + str(main.y + 1) + '/0/1/(0,0,0)')

                # Inventory slots. Q - move selection left, E - move selection right
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

                # When pressed "c", opening fullscreen chat menu, but if presses m,
                # opening "portable" chat menu, which takes a lot less space on the screen,
                # so you can see the game itself
                if e.key == pygame.K_c:
                    ChatMenu(main.c, main.sc)
                elif e.key == pygame.K_m:
                    ChatMenu(main.c, main.sc, quickMenu=True)

                # Very buggy fullscreen mode, please don't uncomment this.
                """
                if e.key == pygame.K_f:
                    main.fullscreen = not main.fullscreen
                    if main.fullscreen:
                        pygame.display.quit()
                        main.sc = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.FULLSCREEN)
                    else:
                        pygame.display.quit()
                        main.sc = pygame.display.set_mode((SCREEN_W, SCREEN_H))
                """

                # Reconnecting if you are disconnected from the server ( kicked for example ) and press R key
                if e.key == pygame.K_r and main.c.disconnected:
                    global RECONNECTING
                    RECONNECTING = True
                    main.running = False

            # Handling mouse button presses
            elif e.type == pygame.MOUSEBUTTONDOWN and not main.c.disconnected:
                pressed = pygame.mouse.get_pressed(3)
                if pressed[0] or pressed[2]:
                    # print("resX:", resX, "; resY:", resY)
                    # print("ox:", ox, "; oy:", oy)

                    # Handling left and right mouse buttons presses
                    if not (movX == 0 and movY == 0):
                        # If there's no item in inventory, using "imaginary" pickaxe
                        if len(main.inventory.inventoryItems) == 0:
                            i = Item('pickaxe', 'pickaxe', 1)
                            if pressed[0]:
                                i.attack(resX, resY, ox, oy)
                            elif pressed[2]:
                                i.use(resX, resY, ox, oy)
                        else:
                            # If left button was pressed
                            if pressed[0]:
                                main.inventory.inventoryItems[main.selectedSlot].attack(
                                    resX, resY, ox, oy
                                )

                            # If right button was pressed
                            elif pressed[2]:

                                # If this is just a block, not a special item, then placing it.
                                # If it is an item, using it.
                                if main.inventory.inventoryItems[main.selectedSlot].specialItem:
                                    main.inventory.inventoryItems[main.selectedSlot].use(
                                        resX, resY, ox, oy)
                                else:

                                    # We will place the block only on grass, we won't replace other blocks
                                    if main.map.level[resX, resY].texture == 'grass' and \
                                       main.inventory.inventoryItems[main.selectedSlot].count > 0:

                                        # Checking if newly placed block won't overlap player's hitbox, so
                                        # player won't get stuck in the block
                                        origCollidable = main.map.level[resX, resY].collidable
                                        main.map.level[resX, resY].collidable = \
                                            Block.getBlockFromID(
                                                resX, resY,
                                                main.inventory.inventoryItems[main.selectedSlot].texture,
                                                main.inventory.inventoryItems[main.selectedSlot].attributes
                                            ).collidable

                                        if main.movement.canStepOn(main.pixelx, main.pixely):
                                            # If everything's alright, placing the block,
                                            # and decrementing it's count in inventory
                                            main.map.setBlock(
                                                resX, resY,
                                                Block.getBlockFromID(resX, resY,
                                                                     main.inventory.inventoryItems[main.selectedSlot].texture,
                                                                     main.inventory.inventoryItems[main.selectedSlot].attributes)
                                            )

                                            main.inventory.removeItem(
                                                Item(main.inventory.inventoryItems[main.selectedSlot].name,
                                                     main.inventory.inventoryItems[main.selectedSlot].texture, 1,
                                                     attributes=main.inventory.inventoryItems[main.selectedSlot].attributes))
                                        else:
                                            main.map.level[resX, resY].collidable = origCollidable

            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_r:
                    RECONNECTING = True
                    main.running = False

        # movement
        if time.time() - self.lastMovement > 1 / 5 and not main.c.disconnected:  # 1/(blocksPerSecond)
            keys = pygame.key.get_pressed()

            if keys[pygame.K_w]:    main.movement.addVelocity(0, -1)
            if keys[pygame.K_a]:    main.movement.addVelocity(-1, 0)
            if keys[pygame.K_s]:    main.movement.addVelocity(0, 1)
            if keys[pygame.K_d]:    main.movement.addVelocity(1, 0)


class Renderer:
    def __init__(self):
        self.sc: pygame.Surface
        self.sc = pygame.Surface((SCREEN_W, SCREEN_H))

        self.screen: pygame.Surface
        self.screen = main.sc

        self.chunks: {(int, int): pygame.Surface}
        self.chunks = {}
        self.renderedChunks = []

        self.objsc: pygame.Surface
        self.objsc = pygame.Surface((MAP_W*BLOCK_W, MAP_H*BLOCK_H))
        self.objsc.fill((255, 0, 255))
        self.objsc.set_colorkey((255, 0, 255))

        self.lightsc: pygame.Surface
        self.lightsc = pygame.Surface((MAP_W*BLOCK_W, MAP_H*BLOCK_H))
        self.lightsc.set_alpha(128)
        self.lightsc.set_colorkey((255, 255, 0))

        self.blackScreen = pygame.Surface((BLOCK_W, BLOCK_H))
        self.blackScreen.fill((0, 0, 0))

        self.blackScreenAlpha = 0

    def renderBlock(self, x, y, dest=None):
        if dest is None:
            dest = self.sc

        if 0 <= x <= MAP_W-1 and 0 <= y <= MAP_H-1:
            b = main.map.level[x, y]
            #self.mapsc.blit(main.textures['grass'], main.textures['grass'].get_rect(topleft=(x * BLOCK_W,
            #                                                                                 y * BLOCK_H)))

            b.lightmap.set_alpha(self.blackScreenAlpha)
            b.renderBlock(dest, x * BLOCK_W, y * BLOCK_H)

    def renderChunk(self, cx, cy):
        for x in range(cx*8, cx*8+8):
            for y in range(cy*8, cy*8+8):
                b = main.map.level[x, y]
                #self.mapsc.blit(main.textures['grass'], main.textures['grass'].get_rect(topleft=(x * BLOCK_W,
                #                                                                                 y * BLOCK_H)))

                b.lightmap.set_alpha(self.blackScreenAlpha)
                b.renderBlock(self.chunks[cx, cy], (x%8) * 16, (y%8) * 16)

    def renderMap(self):
        for x in range(MAP_W):
            for y in range(MAP_H):
                self.renderBlock(x, y)

    def renderLightmap(self):
        return

        # for x in range(MAP_W):
        #     for y in range(MAP_H):
        #         main.map.level[x, y].renderLightmap(self.lightsc, x*BLOCK_W, y*BLOCK_H)

    def renderGame(self):
        self.blackScreenAlpha = clamp((math.sin(main.timeofday * math.pi)) * 128, 0, 255)
        self.blackScreen.set_alpha(self.blackScreenAlpha)

        # Drawing water background
        coef = clamp(1.5 - clamp(self.blackScreenAlpha, 0.1, 128) / 128, 0.5, 1)
        r, g, b = 155*coef, 227*coef, 206*coef
        # print(r, g, b, coef)
        self.sc.fill((int(r), int(g), int(b)))

        self.renderedChunks.clear()
        for x, y in main.chunks.visibleChunks:
            if not (x, y) in self.chunks:
                self.chunks[x, y] = pygame.Surface((128, 128))

            if not (x, y) in self.renderedChunks:
                self.renderChunk(x, y)
                self.renderedChunks.append((x, y))

        self.objsc.fill((255, 0, 255))

        # Rendering bullets
        for bullet in bullets:
            if bullet.active:
                pygame.draw.rect(self.objsc, bullet.color, (bullet.x * BLOCK_W + (BLOCK_W // 4),
                                                            bullet.y * BLOCK_H + (BLOCK_H // 4),
                                                            40, 40))

        # Rendering objects
        for obj in main.map.objects:
            if main.map.objects[obj].active:
                self.objsc.blit(main.textures[main.map.objects[obj].texture],
                                main.textures[main.map.objects[obj].texture].get_rect(
                                    topleft=(main.map.objects[obj].x, main.map.objects[obj].y)))

        for x,y in main.chunks.visibleChunks:
            chunk = pygame.transform.scale(self.chunks[x, y], (8*BLOCK_W, 8*BLOCK_H))
            self.sc.blit(chunk, chunk.get_rect(
                topleft=(
                    SCREEN_W//2 + (x*8*BLOCK_W - main.pixelx),
                    SCREEN_H//2 + (y*8*BLOCK_H - main.pixely)
                )
            ))

        # Rendering enemies ( other players )
        for p in players:
            player = players[p]
            if player.active:
                x = (SCREEN_W // 2 + (player.x - main.pixelx))
                y = (SCREEN_H // 2 + (player.y - main.pixely))

                self.sc.blit(main.textures[player.texture],
                                main.textures[player.texture].get_rect(center=(x, y)))
                pygame.draw.rect(self.sc, (0, 0, 0),
                                 (x - 3 - BLOCK_W // 2, y - 3 - BLOCK_H // 2, BLOCK_W + 6,
                                  BLOCK_H // 8 + 6))
                pygame.draw.rect(self.sc, (255, 0, 0), (
                    x - BLOCK_W // 2, y - BLOCK_H // 2, int(player.health * 0.8), BLOCK_H // 8))

        # Rendering "cursor"
        t = main.textures['cursor']
        if main.eventhandler.resx != main.eventhandler.px or \
           main.eventhandler.resy != main.eventhandler.py:
            t = main.textures['cursor_far']

        self.sc.blit(t, t.get_rect(
            topleft=(SCREEN_W//2 + (main.eventhandler.px * BLOCK_W - main.pixelx),
                     SCREEN_H//2 + (main.eventhandler.py * BLOCK_H - main.pixely))
        ))

        # self.sc.blit(self.mapsc, self.mapsc.get_rect(topleft=(SCREEN_W // 2 - main.pixelx,
        #                                                       SCREEN_H // 2 - main.pixely)))

        self.sc.blit(self.objsc, self.objsc.get_rect(topleft=(SCREEN_W // 2 - main.pixelx,
                                                              SCREEN_H // 2 - main.pixely)))

        # self.sc.blit(self.lightsc, self.lightsc.get_rect(topleft=(SCREEN_W // 2 - main.pixelx,
        #                                                           SCREEN_H // 2 - main.pixely)))

        # self.lightsc.set_alpha(blackScreenAlpha)
        # self.sc.blit(self.lightsc, self.lightsc.get_rect(topleft=(SCREEN_W // 2 - main.pixelx,
        #                                                           SCREEN_H // 2 - main.pixely)))

        # Rendering "Shadow" under the player to see him easily.
        self.sc.blit(main.textures['arrow'],
                     main.textures['arrow'].get_rect(center=(SCREEN_W//2, SCREEN_H//2)))

        # Rendering our player
        self.sc.blit(main.textures[main.playerClass.texture],
                     main.textures[main.playerClass.texture].get_rect(
                         center=(SCREEN_W//2, SCREEN_H//2)
                         # center=(main.pixelx, main.pixely)
                     ))

        # Rendering our player HP indicator ( on his head )
        pygame.draw.rect(self.sc, (0, 0, 0),
                         (SCREEN_W//2 - 3 - BLOCK_W // 2, SCREEN_H//2 - 3 - BLOCK_H // 2, BLOCK_W + 6,
                          BLOCK_H // 8 + 6))
        pygame.draw.rect(self.sc, (0, 255, 0), (
            SCREEN_W//2 - BLOCK_W // 2, SCREEN_H//2 - BLOCK_H // 2, int(health * 0.8), BLOCK_H // 8))

        # Rendering inventory background
        pygame.draw.line(self.sc, (0, 0, 0), [0, MAP_H * BLOCK_H], [MAP_W * BLOCK_W, MAP_H * BLOCK_H])
        pygame.draw.rect(self.sc, (255, 255, 255), (0, MAP_H * BLOCK_W, SCREEN_W, BLOCK_H))

        # Rendering inventory items
        for slot in range(len(main.inventory.inventoryItems)):
            if slot == main.selectedSlot:
                t = main.font.render(main.inventory.inventoryItems[slot].name, True, (0, 0, 0))
                r = t.get_rect(bottomleft=(0, SCREEN_H-BLOCK_H))
                self.sc.blit(t, r)
                self.sc.blit(main.textures[main.inventory.inventoryItems[slot].texture.split(',')[0]],
                             main.textures[main.inventory.inventoryItems[slot].texture.split(',')[0]].get_rect(
                                 topleft=(slot * BLOCK_W, MAP_H * BLOCK_H)))
            else:
                t = pygame.transform.scale(main.textures[main.inventory.inventoryItems[slot].texture.split(',')[0]],
                                           (BLOCK_W // 2, BLOCK_H // 2))
                r = t.get_rect(center=(slot * BLOCK_W + BLOCK_W // 2, MAP_H * BLOCK_H + BLOCK_H // 2))
                self.sc.blit(t, r)

            if not main.inventory.inventoryItems[slot].specialItem:
                t = main.font.render(str(main.inventory.inventoryItems[slot].count), True, (0, 0, 0))
                r = t.get_rect(center=(slot * BLOCK_W + BLOCK_W // 2, MAP_H * BLOCK_H + 18))
                self.sc.blit(t, r)

        # Displaying player stats
        t = main.font.render(main.localization['health'] + str(health), True, (0, 0, 0))
        r = t.get_rect(topleft=(0, 0))
        self.sc.blit(t, r)

        t = main.font.render("Defence level: " + str(main.defenceLevel), True, (0, 0, 0))
        r = t.get_rect(topleft=(4 * BLOCK_W, 0))
        self.sc.blit(t, r)

        if main.displayingDebugInfo:
            t = main.font.render("FPS: " + str(main.fps), True, (0, 0, 0))
            r = t.get_rect(topright=(SCREEN_W, 0))
            self.sc.blit(t, r)

            t = main.font.render("pixelx: " + str(round(main.pixelx, 1)), True, (0, 0, 0))
            r = t.get_rect(topright=(SCREEN_W, BLOCK_H*0.5))
            self.sc.blit(t, r)

            t = main.font.render("pixely: " + str(round(main.pixely, 1)), True, (0, 0, 0))
            r = t.get_rect(topright=(SCREEN_W, BLOCK_H))
            self.sc.blit(t, r)

            t = main.font.render("x: " + str(main.x) + ", y: " + str(main.y), True, (0, 0, 0))
            r = t.get_rect(topright=(SCREEN_W, BLOCK_H*1.5))
            self.sc.blit(t, r)

            t = main.font.render("rx: " + str(main.rx) + ", tx: " + str(main.tx), True, (0, 0, 0))
            r = t.get_rect(topright=(SCREEN_W, BLOCK_H*2))
            self.sc.blit(t, r)

            t = main.font.render('timeofday: ' + str(round(main.timeofday, 2)), True, (0, 0, 0))
            r = t.get_rect(topright=(SCREEN_W, BLOCK_H*2.5))
            self.sc.blit(t, r)

            t = main.font.render('name ' + str(main.inventory.inventoryItems[main.selectedSlot].name), True, (0, 0, 0))
            r = t.get_rect(topright=(SCREEN_W, BLOCK_H*3))
            self.sc.blit(t, r)

            t = main.font.render('texture ' + str(main.inventory.inventoryItems[main.selectedSlot].texture), True,
                                 (0, 0, 0))
            r = t.get_rect(topright=(SCREEN_W, BLOCK_H*3.5))
            self.sc.blit(t, r)

            t = main.font.render('attrs ' + str(main.inventory.inventoryItems[main.selectedSlot].attributes), True,
                                 (0, 0, 0))
            r = t.get_rect(topright=(SCREEN_W, BLOCK_H * 4))
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

        if main.curWidth != SCREEN_W or main.curHeight != SCREEN_H:
            t = pygame.transform.scale(self.sc, (main.curWidth, main.curHeight))
        else:
            t = self.sc
        r = t.get_rect(topleft=(0, 0))
        self.screen.blit(t, r)


class ClassChooser:
    def __init__(self):
        self.sc = main.sc

    def classChooser(self) -> [str, str, [Item]]:
        # [className, classTexture, defaultItems: [Item]]
        classes = [
            ['builder', 'builder_texture', [Pickaxe]],
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

        # Giving some items for debug purposes.
        main.inventory.addInventoryItem(Item('wooden_door_closed', 'wooden_door_closed', 10))
        main.inventory.addInventoryItem(Item('wirefftt', 'wirefftt', 64))
        main.inventory.addInventoryItem(Item('lampoff', 'lampoff', 64))
        main.inventory.addInventoryItem(Item('switchoff', 'switchoff', 64))
        main.inventory.addInventoryItem(Item('Computer', 'computer', 64))

        return PlayerClass(classes[variant][2][0](), classes[variant][1], classes[variant][0])


class CollisionDetection:
    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y

        self.xvel = 0  # X velocity
        self.yvel = 0  # Y velocity

        # Movement speed ( measures in pixels per second )
        self.defaultMovementSpeed = 0.7 * BLOCK_W
        self.__currentMovementSpeed = self.defaultMovementSpeed

    def addVelocity(self, x=0, y=0):
        self.xvel += x
        self.yvel += y

    def update(self):
        # print(self.xvel, self.yvel, end=' ')

        delta = main.getDeltaTime()

        self.xvel = self.clamp(self.xvel, -2, 2)
        self.yvel = self.clamp(self.yvel, -2, 2)

        # print(self.xvel, self.yvel)

        movX = self.xvel * delta * self.defaultMovementSpeed
        movY = self.yvel * delta * self.defaultMovementSpeed

        futureX = self.clamp(self.x + (movX * self.getMovementSpeed(self.x+movX, self.y+movY)), 0, LEVEL_W*BLOCK_W)
        futureY = self.clamp(self.y + (movY * self.getMovementSpeed(self.x+movY, self.y+movY)), 0, LEVEL_H*BLOCK_H)

        canstep = False
        if self.canStepOn(futureX, self.y):
            self.x = futureX
            canstep = True
        if self.canStepOn(self.x, futureY):
            self.y = futureY
            canstep = True

        if not canstep and self.canStepOn(futureX, futureY):
            self.x, self.y = futureX, futureY

        self.xvel *= 0.9
        self.yvel *= 0.9

        # if -0.01 <= self.xvel <= 0.01: self.xvel = 0
        # if -0.01 <= self.yvel <= 0.01: self.yvel = 0

        self.x = self.clamp(self.x, 0, LEVEL_W * BLOCK_W)
        self.y = self.clamp(self.y, 0, LEVEL_H * BLOCK_H)

    def getMovementSpeed(self, x, y) -> float:
        points = [
            (x - BLOCK_W / 2.5, y - BLOCK_H / 2.5),  # Upleft
            (x + BLOCK_W / 2.5, y - BLOCK_H / 2.5),  # Upright
            (x - BLOCK_W / 2.5, y + BLOCK_H / 2.5),  # Downleft
            (x + BLOCK_W / 2.5, y + BLOCK_H / 2.5)  # Downright
        ]

        movementSpeeds = []
        for point in points:
            movementSpeeds.append(main.map.level[
                                      int(point[0] / BLOCK_W), int(point[1] / BLOCK_H)].movementSpeedMultiplier)

        if len(movementSpeeds) == 0: movementSpeeds = [1]
        # print(movementSpeeds)
        return min(movementSpeeds)

    def getPos(self) -> (float, float):
        return self.x, self.y

    @staticmethod
    def playerIsCollidingWith(x, y, playerX, playerY):
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
            (x - BLOCK_W / 2.5, y - BLOCK_H / 2.5),  # Upleft
            (x + BLOCK_W / 2.5, y - BLOCK_H / 2.5),  # Upright
            (x - BLOCK_W / 2.5, y + BLOCK_H / 2.5),  # Downleft
            (x + BLOCK_W / 2.5, y + BLOCK_H / 2.5)  # Downright
        ]

        canStep = True
        for point in points:
            if main.map.level[int(point[0] / BLOCK_W), int(point[1] / BLOCK_H)].collidable:
                return False

        return True


class TextureManager:
    def __init__(self, path: str, width=BLOCK_W, height=BLOCK_H):
        files = os.listdir(path)
        self.__textures = {}
        for filename in files:
            self.__textures[filename.replace('.png', '')] = \
                pygame.transform.scale(pygame.image.load('textures/' + filename).convert_alpha(), (width, height))

        self.__errortexture = pygame.Surface((BLOCK_W, BLOCK_H))
        self.__errortexture.fill((255, 0, 255))

    def __getitem__(self, item: str):
        if item in self.__textures:
            return self.__textures[item]
        else:
            # print("Unknown texture:", item)
            return self.__errortexture


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
        self.textures = TextureManager('textures/')

        self.textures16 = TextureManager('textures/', width=16, height=16)

    def loadSounds(self):
        files = os.listdir('sounds/')
        self.sounds = {}
        for filename in files:
            if not self.settings['disable_sound']:
                self.sounds[filename.split('.')[0]] = pygame.mixer.Sound('sounds/' + filename)
            else:
                self.sounds[filename.split('.')[0]] = SoundStub()

    def __init__(self, surface):
        self.initialized = False

        global main
        main = self

        pygame.init()
        self.fullscreen = False

        self.curWidth = SCREEN_W
        self.curHeight = SCREEN_H

        self.sc = surface
        pygame.display.set_caption("BattleKiller 2D " + GAME_VERSION)

        self.setup()

    def getDeltaTime(self):
        return self.__deltaTime

    def setup(self, playerClass=None, nickname=None):
        self.loadConfig()

        self.loadTextures()
        self.loadSounds()

        # self.font = pygame.font.SysFont("Arial", 36)
        self.customfont = CustomFont()
        self.font = CustomFont(30)

        t = self.font.render("Hello, world", True, (255, 255, 255))

        self.map = MapManager()
        self.chunks = ChunkLoader()
        self.inventory = Inventory()

        if playerClass is None:
            self.chooser = ClassChooser()
            self.playerClass: PlayerClass
            self.playerClass = self.chooser.classChooser()
        else:
            self.chooser = ClassChooser()
            self.playerClass: PlayerClass
            self.playerClass = playerClass

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
        if nickname is None:
            self.nicknamePrompt.show()
            self.nickname = self.nicknamePrompt.getInput()
        else:
            self.nickname = nickname

        self.lightProcessor = LightProcessor()

        # rx - received packets from the server,
        # tx - packets send to the server
        # prevNetworkCheck - when was the last time measurements were taken
        self.rx, self.tx = 0, 0
        self.prevNetworkCheck = time.time()

        # Connecting to the server
        self.c = Client(self.serverIp, self.serverPort)
        self.c.setNickname(self.nickname)

        # 0 is day, 0.5 is night, 1 is again day
        self.timeofday = 0

        # Currently selected inventory slot
        self.selectedSlot = 0

        # Storing chat messages
        self.messages = []

        # For fps displaying
        self.prevFpsCheck = time.time()
        self.fps = 0
        self.__frames = 0

        # For light optimization
        self.mustCalcLight = True

        # For fps-independent movement ( movement speed will be the same with low or high fps )
        self.prevFrame = time.time()
        self.__deltaTime = 0

        # To save bandwidth ( sending local player to the server only if it was changed )
        self.prevx, self.prevy, self.prevtexture, self.prevhealth = \
            self.pixelx, self.pixely, self.playerClass.texture, health
        self.lastTimePlayerDataSent = time.time()

        self.displayingDebugInfo = False

        self.defenceLevel = 0

        self.initialized = True

    def update(self, acceptEvents=True):
        global RECONNECTING

        self.pixelx, self.pixely = self.movement.getPos()
        x, y = int(self.pixelx / BLOCK_W), int(self.pixely / BLOCK_H)
        self.x, self.y = x, y

        # listening for the events
        if acceptEvents:
            self.eventhandler.handleEvents()

        self.movement.update()

        if not self.c.disconnected:
            if time.time() - self.lastTimePlayerDataSent >= 1/30:
                if self.prevx != self.pixelx or self.prevy != self.pixely or \
                   self.playerClass.texture != self.prevtexture or health != self.prevhealth:
                    self.c.sendMessage(
                        'set_player' + str(self.pixelx) + '/' + str(self.pixely) + '/' +
                        str(self.playerClass.texture) + '/' + str(health)
                    )

                    self.prevx, self.prevy, self.prevtexture, self.prevhealth = \
                        self.pixelx, self.pixely, self.playerClass.texture, health

            self.c.update()
            self.map.updateMap()
            self.chunks.update()

            if self.c.newMessages:
                for msg in self.c.newMessages:
                    alpha = 256
                    if msg[2] == (255, 0, 0): alpha = 1024

                    self.messages.append(ChatMessage(msg[1], msg[0], msg[2], True, alpha))
                self.c.newMessages.clear()

            if health > 0:
                # self.lightProcessor.calcLight()
                self.renderer.renderGame()
            else:
                self.c.disconnect()

        elif health <= 0:
            t = self.font.render(self.localization['game_over'], True, (255, 0, 0))
            r = t.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2))
            self.sc.blit(t, r)
        else:
            t = self.font.render(self.localization['disconnected'], True, (0, 0, 0))
            t1 = self.font.render(
                self.localization['disconnected_reason'] + self.c.disconnectReason, True, (0, 0, 0))
            self.sc.blit(t, t.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - BLOCK_H)))
            self.sc.blit(t1, t1.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 + BLOCK_H)))

        # v = 1 / 160
        # print(v)
        # if v > 0:
        #     time.sleep(v)

        if time.time() - self.prevNetworkCheck >= 1:
            self.rx, self.tx = self.c.rx, self.c.tx
            self.c.rx, self.c.tx = 0, 0
            self.prevNetworkCheck = time.time()

        if time.time() - self.prevFpsCheck >= 1:
            self.fps = self.__frames
            self.__frames = 0
            self.prevFpsCheck = time.time()

        self.__frames += 1

        self.__deltaTime = time.time() - self.prevFrame
        self.prevFrame = time.time()

    def mainLoop(self):
        try:
            # Updating all map
            self.map.updateMap()
            self.renderer.renderMap()
            # self.lightProcessor.calcLight(force=True)
            self.c.sendMessage('get_objects')
        except:
            pass

        while self.running:
            self.sc.fill((255, 255, 255))

            self.update(acceptEvents=True)

            pygame.display.update()


class StartMenu:
    def __init__(self):
        self.blitsc = pygame.Surface((SCREEN_W, SCREEN_H))
        self.origsc = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.RESIZABLE)
        pygame.display.set_caption('BattleKiller 2D ' + str(GAME_VERSION))

        self.curWidth, self.curHeight = SCREEN_W, SCREEN_H

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

                elif e.type == pygame.VIDEORESIZE:
                    self.curWidth = e.w
                    self.curHeight = e.h

                elif e.type == pygame.MOUSEBUTTONDOWN:
                    x, y = e.pos

                    # Checking if player clicked one of the buttons
                    if self.playButtonCoords[0] <= x <= self.playButtonCoords[0] + self.playButton.get_width() and \
                            self.playButtonCoords[1] <= y <= self.playButtonCoords[1] + self.playButton.get_height():
                        resetGlobals()
                        main = Main(self.origsc)
                        main.curWidth, main.curHeight = self.curWidth, self.curHeight
                        main.mainLoop()
                        resetGlobals()
                    elif self.exitButtonCoords[0] <= x <= self.exitButtonCoords[0] + self.exitButton.get_width() and \
                            self.exitButtonCoords[1] <= y <= self.exitButtonCoords[1] + self.exitButton.get_height():
                        exit()

            self.blitsc.fill((0, 76, 153))

            self.blitsc.blit(self.playButton,
                             self.playButton.get_rect(topleft=self.playButtonCoords))

            self.blitsc.blit(self.exitButton,
                             self.exitButton.get_rect(topleft=self.exitButtonCoords))

            if self.curWidth != SCREEN_W or self.curHeight != SCREEN_H:
                t = pygame.transform.scale(self.blitsc, (self.curWidth, self.curHeight))
                r = t.get_rect(topleft=(0, 0))
            else:
                t = self.blitsc
                r = t.get_rect(topleft=(0, 0))

            self.origsc.blit(t, r)

            pygame.display.update()


GAME_VERSION = 'version UNDEFINED'

RECONNECTING = False

players = {}
#

bullets = []
# bullets: [Bullet]

nextFrameUpdate = False

health = 100

main: Main


def resetGlobals():
    global players, bullets, nextFrameUpdate, health, RECONNECTING, main, GAME_VERSION

    try:
        __f = open('version.txt', 'r', encoding='utf-8')
        GAME_VERSION = __f.read()
        __f.close()
    except Exception as __e:
        print("Failed to read game version from the file version.txt. Exception", __e)
        GAME_VERSION = 'version UNKNOWN'

    RECONNECTING = False
    players = {}
    bullets = []
    nextFrameUpdate = False
    health = 100
    main = None


if __name__ == '__main__':
    resetGlobals()
    startMenu = StartMenu()
