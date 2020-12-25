import pygame
import socket
import random
import time


class Player:
    def __init__(self, x, y, color):
        self.x, self.y, self.color = x, y, color


players = []
players: [Player]


class Client:
    def __init__(self):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.s.connect((input("Server ip: "), int(input("Server port: "))))
        self.s.setblocking(False)

    def update(self):
        global players

        try:
            self.sendMessage('get_players')
            people = self.getMessages()

            if people:
                # print(people)

                players.clear()

                for person in people:
                    if person:
                        p = person.split('/')
                        players.append(Player(int(p[0]), int(p[1]), eval(p[2])))
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
            self.s.send(message.encode('utf-8'))
            self.s.send(';'.encode('utf-8'))

            return True, None
        except Exception as e:
            return False, e

    def disconnect(self):
        pass


class Main:
    def __init__(self):
        self.c = Client()

        self.sc = pygame.display.set_mode((640, 480))

        self.x, self.y = 0, 0
        self.color = (random.randint(0, 255),
                      random.randint(0, 255),
                      random.randint(0, 255))

        self.mainLoop()

    def mainLoop(self):
        while True:
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

            self.c.sendMessage('set_player' + str(self.x) + '/' + str(self.y) + '/' + str(self.color))

            self.sc.fill((255, 255, 255))

            pygame.draw.rect(self.sc, self.color, (self.x*80, self.y*80, 80, 80))

            for player in players:
                pygame.draw.rect(self.sc, player.color, (player.x*80, player.y*80, 80, 80))

            pygame.display.update()

            time.sleep(1/60)


if __name__ == '__main__':
    m = Main()
