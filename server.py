import random
import socket
import time
import traceback


MAP_W = 16
MAP_H = 8


class Player:
    def __init__(self, x, y, color):
        self.x, self.y, self.color = x, y, color
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

level = {}
level: {(int, int): str}

changedBlocks = []


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

        print("Client #" + str(self.i) + " connected: ", self.a)

    def update(self) -> None:
        global changedBlocks

        if not self.disconnected:
            global players
            global bullets

            if not self.disconnected:
                try:
                    msg = self.s.recv(131072).decode('utf-8')

                    for message in msg.split(';'):
                        if message:
                            if message == 'disconnect':
                                self.disconnected = True
                                players[self.i].active = False
                                self.s.close()
                                print("Client #" + str(self.i) + " disconnected: ", self.a)

                            elif message == 'get_level':
                                self.dataToSend.append('map' + str(level))

                            elif message == 'get_objects':
                                m = ''

                                for p in range(len(players)):
                                    if p != self.i:
                                        player = players[p]
                                        m += 'p/' + str(p) + '/' + str(player.x) + '/' + str(player.y)\
                                             + '/' + str(player.color) + '/' + str(player.active) + ';'

                                for bullet in range(len(bullets)):
                                    b = bullets[bullet]
                                    m += 'b/' + str(bullets.index(b)) + '/' + str(b.x) + '/' + str(b.y)\
                                        + '/' + str(b.movX) + '/' + str(b.movY)\
                                        + '/' + str(b.color) + '/' + str(b.active) + ';'

                                for block in range(len(self.changedBlocks)):
                                    b = self.changedBlocks[block]
                                    m += 'cb/' + str(b[0]) + '/' + str(b[1]) + '/' + b[2] + ';'

                                if m:
                                    self.dataToSend.append(m)
                                    self.changedBlocks.clear()
                            elif 'set_player' in message:
                                # print(message)

                                message = message.replace('set_player', '').split('/')

                                p = Player(int(message[0]), int(message[1]), eval(message[2]))

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

                            else:
                                if message: print("Message from client:", message)
                except socket.error:
                    pass
                except Exception as e:
                    self.disconnected = True

                    print("Exception in Client.update():", e)

                    """
                    print("Disconnecting this client")
                    try:
                        self.s.close()
                    except Exception as e:
                        print("Exception while disconnecting client:", e)
                    """

                try:
                    d = len(self.dataToSend)-1

                    if d >= 0:
                        self.s.send(self.dataToSend[d].encode('utf-8'))
                        self.s.send(';'.encode('utf-8'))

                        self.dataToSend.pop(d)
                except socket.error:
                    pass
                except Exception as e:
                    print("Ex", e)

    def disconnect(self):
        if not self.disconnected:
            try:
                self.s.setblocking(True)
                self.s.send('disconnect/Server was shut down.;'.encode('utf-8'))
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
            if self.port == '': self.port = 25000
            else: self.port = int(self.port)
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
                    players[i] = Player(0, 0, (0, 0, 0))

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

                if time.time()-self.lastBulletUpdate >= 1/5:
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
                                    if player.x == bullet.x and player.y == bullet.y\
                                            and not (j.i == bullet.owner) and player.active:
                                        # Processing hit
                                        j.dataToSend.append('bullet_hit')
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
                    time.sleep(1/(80*len(self.clients)))
                else:
                    time.sleep(1/60)
            except KeyboardInterrupt:
                print("\nShutting down server.")
                for client in self.clients:
                    client.disconnect()
                self.alive = False
            except Exception as e:
                print("CRITICAL SERVER ERROR: ", e)
                traceback.print_exc()


if __name__ == '__main__':
    t_start = time.time()
    main = Main()
    t_end = time.time()

    print("Server was running for", (t_end-t_start)//60, "minutes and",
          round((t_end-t_start) % 60, 1), "seconds!")
