import socket
import time


class Player:
    def __init__(self, x, y, color):
        self.x, self.y, self.color = x, y, color


players = []
players: [Player]


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

    def update(self) -> None:
        global players

        if not self.disconnected:
            try:
                msg = self.s.recv(131072).decode('utf-8')

                for message in msg.split(';'):
                    if message:
                        if message == 'get_players':
                            m = ''
                            for player in players:
                                if players.index(player) != self.i:
                                    m += str(player.x) + '/' + str(player.y) + '/' + str(player.color) + ';'

                            if m:
                                self.dataToSend.append(m)

                                # print(m)
                        elif 'set_player' in message:
                            # print(message)

                            message = message.replace('set_player', '').split('/')

                            p = Player(int(message[0]), int(message[1]), eval(message[2]))

                            players[self.i] = p

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

        # Entering main loop
        self.mainLoop()

    def mainLoop(self) -> None:
        global players

        while True:
            # Accepting clients
            try:
                sock, addr = self.s.accept()
                sock.setblocking(False)

                i = len(players)
                players.append(Player(0, 0, (0, 0, 0)))

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
                    print("Exception was thrown during listening to messages from clients:\n", e)

            if len(self.clients) > 0:
                time.sleep(1/(80*len(self.clients)))
            else:
                time.sleep(1/60)


if __name__ == '__main__':
    main = Main()
