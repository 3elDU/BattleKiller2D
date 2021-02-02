import random
import socket
import time
import traceback
from tkinter import *

MAP_W = 16
MAP_H = 8


class Player:
    def __init__(self, x, y, texture, health=100, nickname=''):
        self.x, self.y, self.texture = x, y, texture
        self.active = True
        self.health = health
        self.nickname = nickname


class Object:
    def __init__(self, x, y, texture):
        self.x, self.y, self.texture = x, y, texture
        self.active = True


class Bullet:
    def __init__(self, x, y, movX, movY, color, owner):
        self.owner = owner
        self.x, self.y, self.movX, self.movY, self.color = x, y, movX, movY, color
        self.active = False


class Damage:
    def __init__(self, damageAmount, receiver, damager):
        self.damageAmount = damageAmount
        self.receiver = receiver
        self.damager = damager


players = {}
players: {int: Player}

bullets = []
bullets: [Bullet]

objects = {}
objects: {(int, int): Object}

changedBlocks = []
changedObjects = []
newMessages = []

playersDamaged: [Damage]
playersDamaged = []
playersLeft = []

commandsFromClients = []
serviceMessages = []


class Client:
    def __init__(self, sock: socket.socket, addr: tuple, i: int):
        # all this sockety things
        self.s = sock
        self.s: socket.socket

        self.a = addr
        self.a: tuple

        self.clientID = i
        self.clientID: int

        self.disconnected = False

        # Messages received from client, waiting for server to handle them
        self.__messagesFromClient = []

        # Messages from server for client.
        self.dataToSend = []
        self.dataToSend: [str]

        self.changedBlocks = []
        self.changedObjects = []
        self.newMessages = []
        self.serviceMessages = []
        self.playersLeft = []

        # Messages here will be sended to client as-is
        self.rawDataToSend = []

        self.lastAliveMessage = time.time()

        print("Client #" + str(self.clientID) + " connected: ", self.a)

        self.sendMessage(main.config.get('welcome_message'))

    def sendMessage(self, msg: str, color=(0, 0, 255), prefix=False):
        if prefix:
            msg = main.config.get('service_message_prefix') + msg
        self.serviceMessages.append([msg, color])

    def setPosition(self, x: int, y: int):
        self.rawDataToSend.append('setpos/' + str(x) + '/' + str(y))

    def getNickname(self) -> str:
        return players[self.clientID].nickname

    def setNickname(self, nickname: str):
        players[self.clientID].nickname = nickname


    def __receiveMessages(self) -> None:
        try:
            dataRaw = self.s.recv(1073741824).decode('utf-8')

            for message in dataRaw.split(';'):
                if message:
                    self.__messagesFromClient.append(message)
        except socket.error:
            pass
        except Exception as e:
            print("Exception while receiving messages from client:", e)

    def __handleMessages(self) -> None:
        try:
            for message in self.__messagesFromClient:
                if message == 'alive':
                    self.lastAliveMessage = time.time()

                elif '/command' in message:
                    print("Command from ", self.getNickname(), message)
                    cmd = message.replace('/command ', '')
                    commandsFromClients.append([self.clientID, cmd])

                elif message == 'disconnect':
                    self.disconnected = True
                    players[self.clientID].active = False
                    playersLeft.append(self.clientID)
                    self.s.close()
                    print(self.getNickname(), "with address", self.a, "disconnected.")

                elif message == 'get_level':
                    print(self.getNickname(), "loaded the map.")
                    self.dataToSend.append('map' + str(main.level.level))

                elif message == 'get_objects':
                    m = ''

                    m += 'yourid/' + str(self.clientID) + ';'

                    for p in range(len(self.playersLeft)):
                        m += 'p/' + str(self.playersLeft[p]) + '/0/0/mage/False/0;'

                    for p in range(len(players)):
                        if p != self.clientID and players[p].active:
                            player = players[p]
                            m += 'p/' + str(p) + '/' + str(player.x) + '/' + str(player.y) \
                                 + '/' + str(player.texture) + '/' + str(player.active) + '/' \
                                 + str(player.health) + ';'

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

                    for b in self.newMessages:
                        if b[0] != self.clientID:
                            m += 'msg/' + str(b[0]) + '/' + str(b[1]) + ';'

                    for b in self.serviceMessages:
                        m += 'service/' + str(b[0]) + '/' + str(b[1]) + ';'

                    for b in self.rawDataToSend:
                        m += b + ';'

                    if m == '':
                        m = 'nothing'

                    self.dataToSend.append(m)
                    self.changedBlocks.clear()
                    self.changedObjects.clear()
                    self.newMessages.clear()
                    self.serviceMessages.clear()
                    self.rawDataToSend.clear()
                    self.playersLeft.clear()
                elif 'set_nick' in message:
                    message = message.replace('set_nick/', '').split('/')

                    players[self.clientID].nickname = message[0]
                    print('Client #', self.clientID, 'set his nickname to', message[0])
                elif 'set_player' in message:
                    # print(message)

                    message = message.replace('set_player', '').split('/')

                    p = Player(float(message[0]), float(message[1]), message[2], int(message[3]),
                               nickname=players[self.clientID].nickname)

                    players[self.clientID] = p
                elif 'set_block' in message:
                    message = message.replace('set_block', '').split('/')

                    main.level.level[int(message[0]), int(message[1])] = message[2]

                    changedBlocks.append([int(message[0]), int(message[1]), message[2]])
                elif 'shoot' in message:
                    message = message.replace('shoot', '').split('/')

                    b = Bullet(int(message[0]), int(message[1]),
                               int(message[2]), int(message[3]), eval(message[4]),
                               self.clientID)
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

                    playersDamaged.append(Damage(int(message[1]), int(message[0]), self.clientID))

                else:
                    if message:
                        print(self.getNickname(), ":", message)
                        newMessages.append([self.clientID, message])

            self.__messagesFromClient.clear()

        except Exception as e:
            print("Exception while handling", self.getNickname(), "'s messages:\n", e)
            print()
            traceback.print_exc()


    def getPlayer(self) -> Player:
        return players[self.clientID]

    def update(self) -> None:
        global commandsFromClients
        global changedBlocks
        global newMessages
        global playersLeft
        global objects
        global players
        global bullets

        if self.disconnected:
            players[self.clientID].active = False
        else:
            # Disconnecting client if it is not responding for 10 seconds.
            if time.time() - self.lastAliveMessage >= 10:
                print(self.getNickname(), "has been not responding for 10 seconds! Disconnecting him/her.")

                try:
                    self.disconnect(reason='Timed out.')
                except Exception as e:
                    print("Error while trying to send disconnect message:", e)

                self.disconnected = True
                players[self.clientID].active = False
                playersLeft.append(self.clientID)
                self.s.close()
                print("Client #" + str(self.clientID) + " disconnected: ", self.a)

                return

            try:
                self.__receiveMessages()

                self.__handleMessages()
            except Exception as e:
                print("Exception in Client.update():", e)
                traceback.print_exc()

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
                        print("Error while sending data to", self.getNickname(), e)
            except socket.error:
                pass
            except Exception as e:
                print("Ex", e)

    def disconnect(self, reason=None):
        if reason is None:
            reason = main.config.get('shutdown_message')

        global players
        try:
            players[self.clientID].active = False
            playersLeft.append(self.clientID)

            self.s.setblocking(True)

            msg = 'disconnect/' + reason + ';'
            self.s.send(msg.encode('utf-8'))
            self.disconnected = True
        except Exception as e:
            print("Exception while trying to disconnect", self.getNickname(), e)


class Level:
    def __init__(self):
        self.level: {(int, int): str}
        self.level = {}

        self.__generated = False

    def setBlock(self, x: int, y: int, block: str):
        self.level[x, y] = block
        changedBlocks.append([x, y, block])

    def generateBlock(self, x, y):
        r = random.randint(0, 7)
        b = 'grass'
        if r == 0:
            b = 'wall'
        if r == 1:
            b = 'tree'
        if r == 2 and random.randint(0, 3) == 0:
            b = self.createChest(x, y)
        if r == 3 and random.randint(0, 3) == 0:
            b = 'heart'
        self.level[x, y] = b

        if self.__generated:
            changedBlocks.append([x, y, b])

    def generateLevel(self):
        gen_start = time.time()

        for x in range(MAP_W):
            for y in range(MAP_H):
                self.generateBlock(x, y)
        self.level[0, 0] = 'grass'

        gen_end = time.time()

        self.__generated = True

        # print(self.level)

        print("Level has been successfully generated in", gen_end-gen_start, "seconds")

    def createChest(self, x, y,
                    lootTable=None, maxItems=8) -> str:
        if lootTable is None:
            # First is item itself, second is max possible items that can be generated,
            # third is spawn chance ( from 0 to 1 )
            lootTable = [
                ['pickaxe', 1, 5],
                ['hammer', 1, 15],
                ['magic_stick', 1, 10],
                ['candle', 1, 25],
                ['sniper_rifle', 1, 0.025],
                ['knife', 1, 0.5],
                ['wood', 15, 100],
                ['wall', 15, 100],
                ['tree', 15, 100]
            ]

        m = 'chest'
        for item in range(random.randint(1, maxItems//2) * 2):
            created = False

            while not created:
                i = random.randint(0, len(lootTable)-1)
                item = lootTable[i]

                if random.randint(0, 100000)/1000 <= item[2]:
                    itemName = item[0]
                    itemCount = random.randint(1, item[1])

                    m += ',' + itemName + '=' + str(itemCount)

                    created = True

        print(m)

        self.level[x, y] = m
        if self.__generated:
            changedBlocks.append([x, y, m])

        return m


class Spawnpoint:
    def __init__(self, x, y):
        self.x, self.y = x, y


class Config:
    def __init__(self, filename=''):
        try:
            f = open(filename, 'r', encoding='utf-8')
            self.__config = eval(f.read())
            f.close()
        except Exception as e:
            print("Exception while reading config:", e)

    def get(self, v) -> str:
        try:
            return self.__config[v]
        except:
            return ''


class Main:
    def __init__(self):
        global main
        main = self

        # Generating level
        print("Initializing level")
        self.level = Level()
        print("Generating level")
        self.level.generateLevel()

        # Creating socket object
        print("Creating socket")
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Reading user's ip and port from settings file
        print("Reading server preferences")
        self.config = Config('server_settings.txt')
        try:
            self.ip = self.config.get('ip')
            if self.ip == '':
                self.ip = socket.gethostbyname(socket.gethostname())

            self.port = self.config.get('port')
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
        print("Binding socket")
        self.s.bind((self.ip, self.port))

        # Starting to listen to new clients
        print("Starting to listen to clients")
        self.s.listen(16384)

        # Setting socket mode to "non-blocking" which allows us to skip waiting for a new message
        # If there's no messages from client, an error will be thrown
        self.s.setblocking(False)

        # List for all clients
        self.clients = []
        self.clients: [Client]

        # Spawnpoint where joined players will appear
        print("Creating spawnpoint ", end='')
        self.spawn = Spawnpoint(random.randint(0, MAP_W-1), random.randint(0, MAP_H-1))
        self.level.level[self.spawn.x, self.spawn.y] = 'grass'
        print("at", self.spawn.x, self.spawn.y)

        self.lastBulletUpdate = time.time()
        self.lastBoostSpawn = time.time()

    def getPlayersOnline(self) -> int:
        playersOnline = 0
        for client in self.clients:
            if players[client.clientID].active: playersOnline += 1

        return playersOnline

    def broadcastMessage(self, msg: str):
        client: Client
        for client in self.clients:
            client.sendMessage(msg)


    def handleCommand(self, command: str) -> str:
        try:
            cmd = command.split(' ')
            if cmd[0] == 'kick':
                client: Client
                for client in self.clients:
                    if client.clientID == int(cmd[1]):
                        client.disconnect(reason=''.join([s + ' ' for s in cmd[2::]]))
                        return 'Successfully kicked player #' + str(cmd[1])
                return 'No player found with id #' + str(cmd[1])
            else:
                return 'Unknown command.'
        except Exception as e:
            return 'Exception has occurred: ' + str(e)

    def __acceptNewClients(self):
        try:
            sock, addr = self.s.accept()
            sock.setblocking(False)

            print("New player has joined, initializing player and client")

            i = len(players)
            players[i] = Player(0, 0, 'grass', 100, str(i))

            client = Client(sock, addr, i)
            client.setPosition(self.spawn.x, self.spawn.y)
            self.clients.append(client)

        except socket.error:
            pass

    def __updateClients(self):
        # Receiving new messages from clients
        client: Client
        for client in self.clients:
            try:
                client.update()
            except Exception as e:
                print("Exception was thrown while updating clients:\n", e)

    def __updateChangedData(self):
        for block in changedBlocks:
            for client in self.clients:
                client.changedBlocks.append(block)
        changedBlocks.clear()

        for obj in changedObjects:
            for client in self.clients:
                client.changedObjects.append(obj)
        changedObjects.clear()

        for msg in newMessages:
            for client in self.clients:
                client.newMessages.append(msg)
        newMessages.clear()

        player: Damage
        for player in playersDamaged:
            print(player.damageAmount, player.damager, player.receiver)
            self.clients[player.receiver].dataToSend.append('bullet_hit/' + str(player.damageAmount))
            if players[player.receiver].health-player.damageAmount <= 0:
                self.broadcastMessage(
                    players[player.receiver].nickname + ' was killed by ' + players[player.damager].nickname)
        playersDamaged.clear()

        for player in playersLeft:
            for client in self.clients:
                client.playersLeft.append(player)
        playersLeft.clear()

    def __processCommands(self):
        for command in commandsFromClients:
            print(command)
            response = self.handleCommand(command[1])
            print(response)
            for client in self.clients:
                if client.clientID == command[0]:
                    print(client.clientID)
                    client.serviceMessages.append(response)
        commandsFromClients.clear()

    def __updateBullets(self):
        if time.time() - self.lastBulletUpdate >= 1 / 5:
            for i in range(len(bullets)):
                bullet = bullets[i]
                if bullet.active:
                    # Checking if bullet is within borders of map
                    if 0 <= bullet.x < MAP_W and 0 <= bullet.y < MAP_H and \
                            main.level.level[bullet.x, bullet.y] in ['grass', 'wood']:
                        # Checking if bullet hits someone
                        hit = False

                        j: Client
                        for j in self.clients:
                            player = players[j.clientID]
                            if player.x == bullet.x and player.y == bullet.y \
                                    and not (j.clientID == bullet.owner) and player.active:
                                # Processing hit
                                j.dataToSend.append('bullet_hit/10')
                                bullets[i].active = False
                                hit = True

                        if not hit and main.level.level[bullet.x, bullet.y] == 'wood' and random.randint(0, 9) == 0:
                            main.level.level[bullet.x, bullet.y] = 'grass'
                            changedBlocks.append([bullet.x, bullet.y, 'grass'])
                            bullets[i].active = False
                        elif not main.level.level[bullet.x, bullet.y] == 'grass':
                            bullets[i].active = False

                        bullet.x += bullet.movX
                        bullet.y += bullet.movY
                    else:
                        bullets[i].active = False

            for bullet in bullets:
                if not bullet.active:
                    bullets.remove(bullet)

            self.lastBulletUpdate = time.time()

    def update(self) -> None:
        global players
        global bullets

        try:
            # Regenerating spawn point if there's a block at spawnpoint coordinates.
            if self.level.level[self.spawn.x, self.spawn.y] != 'grass':
                print("Spawnpoint was blocked, regenerating it")
                created = False
                while not created:
                    x, y = random.randint(0, MAP_W - 1), random.randint(0, MAP_H - 1)
                    if self.level.level[x, y] in ['grass', 'wooden_door_opened']:
                        self.spawn = Spawnpoint(x, y)
                        created = True

            # Accepting clients
            self.__acceptNewClients()
            self.__updateClients()
            self.__updateChangedData()
            self.__processCommands()

            # Spawning chests ( only if there is at least one player online )
            if time.time() - self.lastBoostSpawn >= 60 and self.getPlayersOnline() > 0:
                print("Spawning new ", end='')
                spawned = False
                while not spawned:
                    x, y = random.randint(0, MAP_W-1), random.randint(0, MAP_H-1)
                    if self.level.level[x, y] == 'grass':
                        if random.randint(0, 4) == 0:
                            print("health boost")
                            self.level.setBlock(x, y, 'heart')
                        else:
                            print("chest")
                            self.level.createChest(x, y)
                        spawned = True

                self.lastBoostSpawn = time.time()

            self.__updateBullets()

            if len(self.clients) > 0:
                time.sleep(1 / (30 * len(self.clients)))
            else:
                time.sleep(1 / 60)

        except Exception as e:
            print("CRITICAL SERVER ERROR: ", e)
            traceback.print_exc()

    def shutDown(self):
        print("\nShutting down server.")
        for client in self.clients:
            client.disconnect()
        self.s.close()
        self.s.detach()


class GUI:
    def stopServer(self):
        self.alive = False

    def sendClientMessage(self):
        if len(self.main.clients) >= int(self.entry1.get()):
            self.main.clients[int(self.entry1.get())].dataToSend.append('service/'+self.entry2.get())

    def evalMessage(self):
        self.result['text'] = 'Result: ' + str(exec(self.entry3.get('0.0', END)))

    def __init__(self):
        print("Creating window")
        self.root = Tk()

        print("Initializing Main")
        self.main = Main()

        print("Creating widgets")
        self.button = Button(text="Stop the server.", command=self.stopServer, width=25)
        self.button.grid(row=0, column=0, padx=10, pady=10)

        self.clientMessageFrame = Frame(self.root)

        self.label1 = Label(self.clientMessageFrame, text="Client ID")
        self.label1.grid(row=0, column=0)
        self.entry1 = Entry(self.clientMessageFrame, width=10)
        self.entry1.grid(row=0, column=1)

        self.label2 = Label(self.clientMessageFrame, text="Message")
        self.label2.grid(row=1, column=0)
        self.entry2 = Entry(self.clientMessageFrame, width=10)
        self.entry2.grid(row=1, column=1)

        self.button1 = Button(self.clientMessageFrame, text="Send message", command=self.sendClientMessage)
        self.button1.grid(row=2, column=0, columnspan=2)

        self.clientMessageFrame.grid(row=1, column=0, padx=10, pady=30)


        self.evalFrame = Frame(self.root)

        self.label3 = Label(self.evalFrame, text="Expression")
        self.label3.grid(row=1, column=0, columnspan=2)
        self.entry3 = Text(self.evalFrame, width=120, height=20)
        self.entry3.grid(row=2, column=1)

        self.button2 = Button(self.evalFrame, text="Evaluate", command=self.evalMessage)
        self.button2.grid(row=3, column=0, columnspan=2)

        self.result = Label(self.evalFrame)
        self.result.grid(row=4, column=0, columnspan=2)

        self.evalFrame.grid(row=2, column=0, padx=10, pady=30)

        self.root.protocol("WM_DELETE_WINDOW", self.stopServer)

        print("Entering loop")
        self.alive = True
        self.loop()

    def loop(self):
        while self.alive:
            try:
                self.main.update()
                self.root.update()
            except KeyboardInterrupt:
                break

        self.main.shutDown()
        self.root.destroy()


if __name__ == '__main__':
    print("Reading server config at server_settings.txt")
    __f = open('server_settings.txt', 'r', encoding='utf-8')
    __c = eval(__f.read())
    __f.close()

    __t_start = 0
    __t_end = 0

    if __c['start_gui'] == 'yes':
        print("Stating with gui")
        __t_start = time.time()
        gui = GUI()
        __t_end = time.time()
    elif __c['start_gui'] == 'no':
        print("Starting without gui")
        __t_start = time.time()
        main = Main()
        print("Entering loop")
        while True:
            try:
                main.update()
            except KeyboardInterrupt:
                main.shutDown()
                break
        __t_end = time.time()
    else:
        print("Invalid config!")

    print("Server was running for", (__t_end - __t_start) // 60, "minutes and",
          round((__t_end - __t_start) % 60, 1), "seconds!")
