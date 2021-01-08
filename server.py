import random
import socket
import time
import traceback

MAP_W = 16
MAP_H = 8


class Player:
    def __init__(self, x, y, texture, health):
        self.x, self.y, self.texture = x, y, texture
        self.active = True
        self.health = health


class Object:
    def __init__(self, x, y, texture):
        self.x, self.y, self.texture = x, y, texture
        self.active = True


class Bullet:
    def __init__(self, x, y, movX, movY, color, owner):
        self.owner = owner
        self.x, self.y, self.movX, self.movY, self.color = x, y, movX, movY, color
        self.active = False


players = {}
players: {int: Player}

bullets = []
bullets: [Bullet]

objects = {}
objects: {(int, int): Object}

level = {}
level: {(int, int): str}

changedBlocks = []
changedObjects = []

playersDamaged = []
playersLeft = []


class Client:
    def __init__(self, sock: socket.socket, addr: tuple, i: int):
        self.s = sock
        self.s: socket.socket

        self.a = addr
        self.a: tuple

        self.i = i
        self.i: int

        self.disconnected = False

        self.dataToSend = []
        self.dataToSend: [str]

        self.changedBlocks = []
        self.changedObjects = []

        self.playersLeft = []

        self.lastAliveMessage = time.time()

        print("Client #" + str(self.i) + " connected: ", self.a)

    def update(self) -> None:
        global changedBlocks
        global playersLeft
        global objects
        global players
        global bullets

        if not self.disconnected:
            try:
                msg = self.s.recv(1048576).decode('utf-8')
                # print(self.i, msg)

                for message in msg.split(';'):
                    if message:
                        if message == 'alive':
                            self.lastAliveMessage = time.time()

                        elif message == 'disconnect':
                            self.disconnected = True
                            players[self.i].active = False
                            playersLeft.append(self.i)
                            self.s.close()
                            print("Client #" + str(self.i) + " disconnected: ", self.a)

                        elif message == 'get_level':
                            self.dataToSend.append('map' + str(level))

                        elif message == 'get_objects':
                            m = ''

                            for p in range(len(self.playersLeft)):
                                m += 'p/' + str(self.playersLeft[p]) + '/0/0/mage/False/0;'

                            for p in range(len(players)):
                                if p != self.i and players[p].active:
                                    player = players[p]
                                    m += 'p/' + str(p) + '/' + str(player.x) + '/' + str(player.y) \
                                         + '/' + str(player.texture) + '/' + str(player.active) + '/' + str(player.health) + ';'

                            for bullet in range(len(bullets)):
                                b = bullets[bullet]
                                m += 'b/' + str(bullets.index(b)) + '/' + str(b.x) + '/' + str(b.y) \
                                     + '/' + str(b.movX) + '/' + str(b.movY) \
                                     + '/' + str(b.color) + '/' + str(b.active) + ';'

                            for block in range(len(self.changedBlocks)):
                                b = self.changedBlocks[block]
                                m += 'cb/' + str(b[0]) + '/' + str(b[1]) + '/' + b[2] + ';'

                            for b in self.changedObjects:
                                m += 'o/' + str(b[0]) + '/' + str(b[1]) + '/' + str(b[2]) + '/' + str(b[3]) + ';'

                            if m == '':
                                m = 'nothing'

                            self.dataToSend.append(m)
                            self.changedBlocks.clear()
                            self.changedObjects.clear()
                            self.playersLeft.clear()
                        elif 'set_player' in message:
                            # print(message)

                            message = message.replace('set_player', '').split('/')

                            p = Player(int(message[0]), int(message[1]), message[2], int(message[3]))

                            players[self.i] = p
                        elif 'set_block' in message:
                            message = message.replace('set_block', '').split('/')

                            level[int(message[0]), int(message[1])] = message[2]

                            changedBlocks.append([int(message[0]), int(message[1]), message[2]])
                        elif 'shoot' in message:
                            message = message.replace('shoot', '').split('/')

                            b = Bullet(int(message[0]), int(message[1]),
                                       int(message[2]), int(message[3]), eval(message[4]),
                                       self.i)
                            b.active = True

                            # Checking if there's aren't any bullets that are in the same position as ours
                            same_pos = False
                            for bullet in bullets:
                                if bullet.x == b.x and bullet.y == b.y:
                                    same_pos = True

                            if not same_pos:
                                bullets.append(b)
                        elif 'create_object' in message:
                            message = message.replace('create_object', '').split('/')

                            objects[int(message[0]), int(message[1])] = Object(int(message[0]), int(message[1]),
                                                                               message[2])

                            changedObjects.append([int(message[0]), int(message[1]), message[2], True])
                        elif 'remove_object' in message:
                            message = message.replace('remove_object', '').split('/')

                            objects[int(message[0]), int(message[1])].active = False

                            changedObjects.append([int(message[0]), int(message[1]), '', False])
                        elif 'attack' in message:
                            message = message.replace('attack', '').split('/')
                            global playersDamaged

                            playersDamaged.append([int(message[0]), int(message[1])])

                        else:
                            if message: print("Message from client:", message)

                if time.time()-self.lastAliveMessage >= 10:
                    print("Client #"+str(self.i)+" has been not responding for 10 seconds! Disconnecting him/her.")

                    try:
                        self.disconnect(reason='Timed out.')
                    except Exception as e:
                        print("Error while trying to send disconnect message:", e)

                    self.disconnected = True
                    players[self.i].active = False
                    playersLeft.append(self.i)
                    self.s.close()
                    print("Client #" + str(self.i) + " disconnected: ", self.a)

            except socket.error:
                pass
            except Exception as e:
                self.disconnected = True

                print("Exception in Client.update():", e)
                traceback.print_exc()

                """
                print("Disconnecting this client")
                try:
                    self.s.close()
                except Exception as e:
                    print("Exception while disconnecting client:", e)
                """

            try:
                if len(self.dataToSend) > 0:
                    m = ''
                    d: str
                    for d in self.dataToSend:
                        if not d.endswith(';'):
                            d += ';'
                        m += d

                    # print(m)

                    try:
                        self.s.send(m.encode('utf-8'))
                        self.dataToSend.clear()
                    except socket.error:
                        pass
                    except Exception as e:
                        print("Error while sending data to client: ", e)
            except socket.error:
                pass
            except Exception as e:
                print("Ex", e)
        else:
            players[self.i].active = False

    def disconnect(self, reason='Server was shut down.'):
        if not self.disconnected:
            try:
                self.s.setblocking(True)

                msg = 'disconnect/' + reason + ';'
                self.s.send(msg.encode('utf-8'))
                self.s.close()
                self.disconnected = True
            except Exception as e:
                print("Exception while trying to disconnect client" + str(self.i), e)


class Main:
    def __init__(self):
        global level

        # Generating level
        for x in range(MAP_W):
            for y in range(MAP_H):
                r = random.randint(0, 7)
                b = 'grass'
                if r == 0:
                    b = 'wall'
                if r == 1:
                    b = 'tree'
                level[x, y] = b
        level[0, 0] = 'grass'

        # Creating socket object
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Reading user's ip and port from settings file
        try:
            f = open('server_settings.txt', 'r')
            self.settings = eval(f.read())
            f.close()

            self.ip = self.settings['ip']
            if self.ip == '': self.ip = socket.gethostbyname(socket.gethostname())

            self.port = self.settings['port']
            if self.port == '':
                self.port = 25000
            else:
                self.port = int(self.port)
        except:
            print("Error while reading settings:")
            traceback.print_exc()
            self.ip = socket.gethostbyname(socket.gethostname())
            self.port = 25000

        print("Starting server on:\nip", self.ip, "\nport", self.port)

        # Binding socket
        self.s.bind((self.ip, self.port))

        # Starting to listen to new clients
        self.s.listen(16384)

        # Setting socket mode to "non-blocking" which allows us to skip waiting for a new message
        # If there's no messages from client, an error will be thrown
        self.s.setblocking(False)

        # List for all clients
        self.clients = []
        self.clients: [Client]

        self.lastBulletUpdate = time.time()

        self.alive = True

        # Entering main loop
        self.mainLoop()

    def mainLoop(self) -> None:
        global players
        global bullets
        global level

        while self.alive:
            try:
                # Accepting clients
                try:
                    sock, addr = self.s.accept()
                    sock.setblocking(False)

                    i = len(players)
                    players[i] = Player(0, 0, 'grass', 100)

                    c = Client(sock, addr, i)

                    self.clients.append(c)

                except socket.error:
                    pass

                # Receiving new messages from clients
                client: Client
                for client in self.clients:
                    try:
                        client.update()
                    except Exception as e:
                        print("Exception was thrown while updating clients:\n", e)

                for block in changedBlocks:
                    for client in self.clients:
                        client.changedBlocks.append(block)
                changedBlocks.clear()

                for obj in changedObjects:
                    for client in self.clients:
                        client.changedObjects.append(obj)
                changedObjects.clear()

                for player in playersDamaged:
                    self.clients[player[0]].dataToSend.append('bullet_hit/' + str(player[1]))
                playersDamaged.clear()

                for player in playersLeft:
                    for client in self.clients:
                        client.playersLeft.append(player)
                playersLeft.clear()

                if time.time() - self.lastBulletUpdate >= 1 / 5:
                    for i in range(len(bullets)):
                        bullet = bullets[i]
                        if bullet.active:
                            # Checking if bullet is within borders of map
                            if 0 <= bullet.x < MAP_W and 0 <= bullet.y < MAP_H and \
                                    level[bullet.x, bullet.y] in ['grass', 'wood']:
                                # Checking if bullet hits someone
                                hit = False

                                j: Client
                                for j in self.clients:
                                    player = players[j.i]
                                    if player.x == bullet.x and player.y == bullet.y \
                                            and not (j.i == bullet.owner) and player.active:
                                        # Processing hit
                                        j.dataToSend.append('bullet_hit/10')
                                        bullets[i].active = False
                                        hit = True

                                if not hit and level[bullet.x, bullet.y] == 'wood' and random.randint(0, 9) == 0:
                                    level[bullet.x, bullet.y] = 'grass'
                                    changedBlocks.append([bullet.x, bullet.y, 'grass'])
                                    bullets[i].active = False
                                elif not level[bullet.x, bullet.y] == 'grass':
                                    bullets[i].active = False

                                bullet.x += bullet.movX
                                bullet.y += bullet.movY
                            else:
                                bullets[i].active = False

                    for bullet in bullets:
                        if not bullet.active: bullets.remove(bullet)

                    self.lastBulletUpdate = time.time()

                if len(self.clients) > 0:
                    time.sleep(1 / (30 * len(self.clients)))
                else:
                    time.sleep(1 / 60)

            except KeyboardInterrupt:
                print("\nShutting down server.")
                for client in self.clients:
                    client.disconnect()
                self.alive = False
                self.s.close()
            except Exception as e:
                print("CRITICAL SERVER ERROR: ", e)
                traceback.print_exc()


if __name__ == '__main__':
    t_start = time.time()
    main = Main()
    t_end = time.time()

    print("Server was running for", (t_end - t_start) // 60, "minutes and",
          round((t_end - t_start) % 60, 1), "seconds!")
