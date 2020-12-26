import socket
import time


class Player:
    def __init__(self, x, y, color):
        self.x, self.y, self.color = x, y, color
        self.active = True


class Bullet:
    def __init__(self, x, y, movX, movY, color):
        self.x, self.y, self.movX, self.movY, self.color = x, y, movX, movY, color
        self.active = False


players = {}
players: {int: Player}

bullets = []
bullets: [Bullet]


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

        print("Client #" + str(self.i) + " connected: ", self.a)

    def update(self) -> None:
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

                                if m:
                                    self.dataToSend.append(m)
                            elif 'set_player' in message:
                                # print(message)

                                message = message.replace('set_player', '').split('/')

                                p = Player(int(message[0]), int(message[1]), eval(message[2]))

                                players[self.i] = p
                            elif 'shoot' in message:
                                message = message.replace('shoot', '').split('/')

                                b = Bullet(int(message[0]), int(message[1]),
                                           int(message[2]), int(message[3]), eval(message[4]))
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


class Main:
    def __init__(self):
        # Creating socket object
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Reading user's ip and port
        self.ip = input("Your ip address: ")
        if self.ip == '': self.ip = socket.gethostbyname(socket.gethostname())

        self.port = input("Your port: ")
        if self.port == '': self.port = 25000
        else: self.port = int(self.port)

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

        # Entering main loop
        self.mainLoop()

    def mainLoop(self) -> None:
        global players
        global bullets

        while True:
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

            if time.time()-self.lastBulletUpdate >= 1/5:
                for i in range(len(bullets)):
                    bullet = bullets[i]
                    if bullet.active:
                        # Checking if bullet is within borders of map
                        if 0 <= bullet.x < 8 and 0 <= bullet.y < 6:
                            # Checking if bullet hits someone
                            j: Client
                            for j in self.clients:
                                player = players[j.i]
                                if player.x == bullet.x and player.y == bullet.y:
                                    # Processing hit
                                    j.dataToSend.append('bullet_hit')
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


if __name__ == '__main__':
    main = Main()
