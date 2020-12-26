import pygame
import socket
import random
import time


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

health = 100


class Client:
    def __init__(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.s.connect((input("Server ip: "), int(input("Server port: "))))
        self.s.setblocking(False)

        self.disconnected = False

    def update(self):
        global players
        global health
        global bullets

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
                        elif s[0] == 'bullet_hit':
                            health -= 10
        except Exception as e:
            print("Client.update() exc2:\n", e)

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
                        elif s[0] == 'bullet_hit':
                            health -= 10
        except Exception as e:
            print("Client.update() exc:\n", e)

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
    def __init__(self):
        self.c = Client()

        pygame.init()

        self.sc = pygame.display.set_mode((640, 480))

        self.font = pygame.font.SysFont("Arial", 36)

        self.x, self.y = 0, 0
        self.color = (random.randint(0, 255),
                      random.randint(0, 255),
                      random.randint(0, 255))

        self.mainLoop()

    def mainLoop(self):
        while True:
            self.c.sendMessage('set_player' + str(self.x) + '/' + str(self.y) + '/' + str(self.color))

            self.c.update()

            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    self.c.disconnect()
                    exit()
                elif e.type == pygame.KEYDOWN:
                    if e.key == pygame.K_w:
                        self.y -= 1
                    if e.key == pygame.K_a:
                        self.x -= 1
                    if e.key == pygame.K_s:
                        self.y += 1
                    if e.key == pygame.K_d:
                        self.x += 1

                    if e.key == pygame.K_SPACE:
                        self.c.sendMessage('shoot'+str(self.x)+'/'+str(self.y+1)+'/0/1/(0,0,0)')

            self.sc.fill((255, 255, 255))

            if health > 0:
                pygame.draw.rect(self.sc, self.color, (self.x*80, self.y*80, 80, 80))

                for p in players:
                    player = players[p]
                    if player.active:
                        pygame.draw.rect(self.sc, player.color, (player.x*80, player.y*80, 80, 80))

                for bullet in bullets:
                    if bullet.active:
                        pygame.draw.rect(self.sc, bullet.color, (bullet.x*80+20, bullet.y*80+20, 40, 40))

                t = self.font.render("Your health: " + str(health), True, (0, 0, 0))
                r = t.get_rect(topleft=(0, 0))
                self.sc.blit(t, r)

                mouse = pygame.mouse.get_pos()
                x, y = mouse[0], mouse[1]

                pygame.draw.rect(self.sc, (255, 0, 0), (mouse[0]-10, mouse[1]-10, 20, 20))

                if pygame.mouse.get_pressed(3)[0]:
                    movX = 0
                    movY = 0

                    if x//80 < self.x:
                        movX = -1
                    elif x//80 == self.x:
                        movX = 0
                    elif x//80 > self.x:
                        movX = 1

                    if y//80 < self.y:
                        movY = -1
                    elif y//80 == self.y:
                        movY = 0
                    elif y//80 > self.y:
                        movY = 1

                    if not (movX == 0 and movY == 0):
                        self.c.sendMessage('shoot' + str(self.x+movX) + '/' + str(self.y+movY)
                                           + '/' + str(movX) + '/' + str(movY) + '/(0,0,0)')

            elif health == 0:
                self.c.disconnect()
                t = self.font.render("Game over!", True, (255, 0, 0))
                r = t.get_rect(center=(320, 240))
                self.sc.blit(t, r)

            pygame.display.update()

            time.sleep(1/60)


if __name__ == '__main__':
    main = Main()
