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
    def __init__(self, x, y, color, active):
        self.x, self.y, self.color = x, y, color
        self.active = active


class Bullet:
    def __init__(self, x, y, movX, movY, color, active):
        self.x, self.y, self.movX, self.movY, self.color = x, y, movX, movY, color
        self.active = active


players = {}
players: {int: Player}

bullets = []
bullets: [Bullet]

level = {}
level: {(int, int): str}

health = 100

RECONNECTING = False


class Client:
    def __init__(self, sip, sport):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

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
                            players[int(s[1])] = Player(int(s[2]), int(s[3]), eval(s[4]), eval(s[5]))
                        elif s[0] == 'cb':
                            level[int(s[1]), int(s[2])] = s[3]

                        elif s[0] == 'bullet_hit':
                            health -= 10
                        elif s[0] == 'disconnect':
                            self.disconnectReason = s[1]
                            self.disconnected = True
        except Exception as e:
            print("Client.update() exc2:\n", e)
            traceback.print_exc()

        try:
            self.sendMessage('get_objects')
            objects = self.getMessages()

            if objects:

                for obj in objects:
                    if obj:
                        s = obj.split('/')
                        if s[0] == 'b':
                            # print(s)
                            bullets.append(Bullet(int(s[2]), int(s[3]), int(s[4]), int(s[5]), eval(s[6]),
                                                  eval(s[7])))
                        elif s[0] == 'p':
                            players[int(s[1])] = Player(int(s[2]), int(s[3]), eval(s[4]), eval(s[5]))
                        elif s[0] == 'cb':
                            level[int(s[1]), int(s[2])] = s[3]

                        elif s[0] == 'bullet_hit':
                            health -= 10
                        elif s[0] == 'disconnect':
                            self.disconnectReason = s[1]
                            self.disconnected = True
        except Exception as e:
            print("Client.update() exc:\n", e)
            traceback.print_exc()

    def getMessages(self) -> list:
        try:
            message = self.s.recv(16384).decode('utf-8')
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
            self.sendMessage('disconnect')
            self.disconnected = True


class Main:
    def __init__(self, sip, sport):
        pygame.init()

        try:
            f = open('client_settings.txt', 'r')
            self.settings = eval(f.read())
            f.close()

            f = open('localizations.txt', 'r')
            self.localization = eval(f.read())[self.settings['localization']]
            f.close()
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
            'wood': pygame.image.load('textures/wood.png').convert_alpha()
        }

        self.font = pygame.font.SysFont("Arial", 36)

        self.x, self.y = 0, 0
        self.color = (random.randint(0, 255),
                      random.randint(0, 255),
                      random.randint(0, 255))

        self.running = True

        self.connectionError = False
        self.connectionErrorTraceback = ''

        try:
            self.c = Client(sip, sport)
            self.c.loadLevel()
        except:
            self.connectionError = True
            f = open('last_err_code.txt', 'w')
            traceback.print_exc(16384, f)
            f.close()

            f = open('last_err_code.txt', 'r')
            err = f.read()
            f.close()

            self.connectionErrorTraceback = err

        self.slots = ['grass', 'wall', 'wood']
        self.selectedSlot = 0

        # For fps
        self.prevFrame = time.time()
        self.fps = 1

        self.mainLoop()

    def mainLoop(self):
        global RECONNECTING

        while self.running:
            if not self.connectionError:
                self.c.sendMessage('set_player' + str(self.x) + '/' + str(self.y) + '/' + str(self.color))

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
                            self.selectedSlot = len(self.slots)-1
                    if e.key == pygame.K_e or e.key == pygame.K_RIGHT:
                        if self.selectedSlot < len(self.slots)-1:
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

                    for p in players:
                        player = players[p]
                        if player.active:
                            pygame.draw.rect(self.sc, player.color, (player.x*BLOCK_W, player.y*BLOCK_H,
                                                                     BLOCK_W, BLOCK_H))

                    pygame.draw.rect(self.sc, self.color, (self.x * BLOCK_W, self.y * BLOCK_H, BLOCK_W, BLOCK_H))

                    pygame.draw.line(self.sc, (0, 0, 0), [0, MAP_H*BLOCK_H], [MAP_W*BLOCK_W, MAP_H*BLOCK_H])
                    pygame.draw.rect(self.sc, (255, 255, 255), (0, MAP_H*BLOCK_W, SCREEN_W, BLOCK_H))

                    for slot in range(len(self.slots)):
                        if slot == self.selectedSlot:
                            self.sc.blit(self.textures[self.slots[slot]],
                                         self.textures[self.slots[slot]].get_rect(topleft=(slot*BLOCK_W, MAP_H*BLOCK_H)))
                        else:
                            t = pygame.transform.scale(self.textures[self.slots[slot]], (BLOCK_W//2, BLOCK_H//2))
                            r = t.get_rect(center=(slot*BLOCK_W+BLOCK_W//2, MAP_H*BLOCK_H+BLOCK_H//2))
                            self.sc.blit(t, r)

                    t = self.font.render(self.localization['health'] + str(health), True, (0, 0, 0))
                    r = t.get_rect(topleft=(0, 0))
                    self.sc.blit(t, r)

                    t = self.font.render("FPS: " + str(self.fps), True, (0, 0, 0))
                    r = t.get_rect(topleft=(0, BLOCK_H))
                    self.sc.blit(t, r)

                    mouse = pygame.mouse.get_pos()
                    x, y = mouse[0], mouse[1]

                    pygame.draw.rect(self.sc, (255, 0, 0), (mouse[0]-10, mouse[1]-10, BLOCK_W//4, BLOCK_H//4))

                    pressed = pygame.mouse.get_pressed(3)
                    if pressed[0] or pressed[2]:
                        movX = 0
                        movY = 0

                        if x//BLOCK_W < self.x:
                            movX = -1
                        elif x//BLOCK_W == self.x:
                            movX = 0
                        elif x//BLOCK_W > self.x:
                            movX = 1

                        if y//BLOCK_H < self.y:
                            movY = -1
                        elif y//BLOCK_H == self.y:
                            movY = 0
                        elif y//BLOCK_H > self.y:
                            movY = 1

                        # For block placing
                        resX = self.x+movX
                        resY = self.y+movY

                        if not (movX == 0 and movY == 0):
                            if pressed[0]:
                                self.c.sendMessage('shoot' + str(self.x+movX) + '/' + str(self.y+movY)
                                                   + '/' + str(movX) + '/' + str(movY) + '/(0,0,0)')
                            elif pressed[2]:
                                if 0 <= resX <= MAP_W and 0 <= resY <= MAP_H:
                                    self.c.sendMessage('set_block' + str(resX) + '/' + str(resY) + '/' +
                                                       self.slots[self.selectedSlot])

                elif health == 0:
                    self.c.disconnect()
                    t = self.font.render(self.localization['game_over'], True, (255, 0, 0))
                    r = t.get_rect(center=(SCREEN_W//2, SCREEN_H//2))
                    self.sc.blit(t, r)
                else:
                    t = self.font.render(self.localization['disconnected'], True, (0, 0, 0))
                    t1 = self.font.render(
                        self.localization['disconnected_reason'] + self.c.disconnectReason + "'", True, (0, 0, 0))
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

            v = 1/80
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
        pygame.display.quit()

        players = {}
        players: {int: Player}

        bullets = []
        bullets: [Bullet]

        health = 100
