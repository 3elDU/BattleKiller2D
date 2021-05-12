import random
import socket
import time
import traceback
import os
from tkinter import *

MAP_W = 1024
MAP_H = 1024


def clamp(val, mn, mx):
    if val < mn:
        return mn
    elif val > mx:
        return mx
    else:
        return val


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


class Colors:
    black = (0, 0, 0)
    white = (255, 255, 255)
    red = (200, 50, 50)
    green = (50, 200, 50)
    blue = (50, 50, 200)

    colors = {'black':black, 'white':white, 'red':red, 'green':green, 'blue':blue}


class Storage:
    def __init__(self, size):
        self.__memorySize = size
        self.__memory = []
        # Filling memory
        for i in range(size):
            self.__memory.append('')

    def getSize(self):
        return self.__memorySize
    def setSize(self, newSize: int):
        if newSize != 0:
            if newSize > self.__memorySize:
                newMem = self.__memory.copy()
                for i in range(newSize - self.__memorySize):
                    newMem.append('')
                self.__memory = newMem
                self.__memorySize = newSize
            elif newSize < self.__memorySize:
                self.__memory = self.getMemoryArea(0, newSize)
                self.__memorySize = newSize

    def setMemory(self, new: [str]):
        for i in range(self.__memorySize):
            if i < self.__memorySize:
                if i > len(new):
                    self.__memory[i] = ''
                elif i < len(new):
                    self.__memory[i] = new[i]
    def setMemoryArea(self, start: int, mem: [str]):
        if 0 <= start < self.__memorySize:
            for i in range(start, start+len(mem)):
                if i < self.__memorySize:
                    self.__memory[i] = mem[i]
    def setMemoryAt(self, index: int, value: str):
        if 0 <= index < self.__memorySize: self.__memory[index] = value

    def fillMemory(self, value: str):
        for i in range(self.__memorySize):
            self.__memory[i] = value
    def fillMemoryArea(self, indexfrom: int, indexto: int, value: str):
        if 0 <= indexfrom < indexto < self.__memorySize:
            for i in range(indexfrom, indexto):
                self.__memory[i] = value

    def getMemory(self) -> [str]: return self.__memory.copy()
    def getMemoryArea(self, indexfrom: int, indexto: int) -> [str]:
        mem = []
        if 0 <= indexfrom < indexto < self.__memorySize:
            for i in range(indexfrom, indexto):
                mem.append(self.__memory[i])
        if len(mem) == 0: mem = ['']
        return mem
    def getMemoryAt(self, index: int) -> str:
        if 0 <= index < self.__memorySize: return self.__memory[index]
        else: return ''

    def getFreeSpace(self) -> int:
        return self.__memory.count('')


class Screen:
    def __init__(self, width, height):
        self.width, self.height = width, height

        self.__background = Storage(self.width*self.height)
        self.__background.fillMemory(Colors.black)

        self.__foreground = Storage(self.width*self.height)
        self.__foreground.fillMemory(Colors.white)

        self.__screen = Storage(self.width*self.height)
        self.__screen.fillMemory('')

        self.cursorx = 0
        self.cursory = 0

        self.__curbg = Colors.black
        self.__curfg = Colors.white

    def setBackground(self, color: (int, int, int)): self.__curbg = color
    def setForeground(self, color: (int, int, int)): self.__curfg = color
    def setScreen(self, newScreen):
        self.__background.setMemory(newScreen.getBackgroundScreen().copy())
        self.__foreground.setMemory(newScreen.getForegroundScreen().copy())
        self.__screen.setMemory(newScreen.getScreen().copy())

    def fill(self, xfrom: int, yfrom: int, xto: int, yto: int, value: str):
        for y in range(yfrom, yto):
            for x in range(xfrom, xto):
                self.__background.setMemoryAt(y*self.width+x, self.__curbg)
                self.__foreground.setMemoryAt(y*self.width+x, self.__curfg)
                self.__screen.setMemoryAt(y*self.width+x, value)

    def print(self, text: str, x=None, y=None):
        if x is None: x = self.cursorx
        if y is None: y = self.cursory

        # print(text)

        for character in range(len(text)):
            if 0 <= x + character < self.width and 0 <= y < self.height:
                index = y * self.width + x + character
                self.__background.setMemoryAt(index, self.__curbg)
                self.__foreground.setMemoryAt(index, self.__curfg)
                self.__screen.setMemoryAt(index, text[character])

    def getScreen(self): return self.__screen.getMemory()
    def getBackgroundScreen(self): return self.__background.getMemory()
    def getForegroundScreen(self): return self.__foreground.getMemory()


class Interpreter:
    def __print(self, arguments: []):
        text = ''

        split = ' '
        for arg in range(len(arguments)):
            text += str(arguments[arg])
            if arg < len(arguments) - 1:
                text += split

        self.computer.tempScreen.print(text)

    def __setvar(self, arguments: []):
        if len(arguments) == 2 and type(arguments[0]) == str:
            self.variables[arguments[0]] = arguments[1]
            if self.log: print("Set variable", arguments[0], "to value", arguments[1])

    def __increment(self, arguments: []):
        if len(arguments) == 1:
            if arguments[0] in self.variables and type(self.variables[arguments[0]]) in [int, float]:
                self.variables[arguments[0]] += 1
                if self.log: print("Incrementing variable", arguments[0])

    def __setCursor(self, arguments: []):
        if len(arguments) == 2 and [type(arg) for arg in arguments] == [int, int]:
            try:
                x, y = arguments[0], arguments[1]

                if 0 <= x < self.computer.screenWidth:
                    self.computer.tempScreen.cursorx = x
                if 0 <= y < self.computer.screenHeight:
                    self.computer.tempScreen.cursory = y

                if self.log: print("Set cursor to ", x, y)
            except: pass
    def __setBackground(self, arguments: []):
        if len(arguments) == 1:
            if arguments[0] in Colors.colors:
                self.computer.tempScreen.setBackground(Colors.colors[arguments[0]])
    def __setForeground(self, arguments: []):
        if len(arguments) == 1:
            if arguments[0] in Colors.colors:
                self.computer.tempScreen.setForeground(Colors.colors[arguments[0]])
    def __clearScreen(self, arguments: []):
        self.computer.tempScreen.fill(0, 0, self.computer.tempScreen.width, self.computer.tempScreen.height, ' ')
    def __renderScreen(self, argments: []):
        self.computer.screen.setScreen(self.computer.tempScreen)

    def reset(self):
        self.variables: {str: any}
        self.variables = {}

        self.points: {str: int}
        self.points = {}

        self.functions = {}
        # {functionName: [lineWhereFunctionStarts, numberOfParameters, [functionCode]]}
        self.customFunctions: {str: [int, [str], [str]]}
        self.customFunctions = {}

        # Input that has been redirected from the client to here.
        self.input: [str]
        self.input = []

        self.currentCommand = [0]

        self.addFunction('print', self.__print)
        self.addFunction('setvar', self.__setvar)
        self.addFunction('increment', self.__increment)
        self.addFunction('setcursor', self.__setCursor)
        self.addFunction('setbackground', self.__setBackground)
        self.addFunction('setforeground', self.__setForeground)
        self.addFunction('clearscreen', self.__clearScreen)
        self.addFunction('renderscreen', self.__renderScreen)

    def __init__(self, log, computer):
        self.reset()

        self.log = log
        self.computer = computer

        # Storage with program data
        self.storage: Storage
        self.storage = self.computer.getStorageToLoadFrom()

    def tick(self):
        self.__execute(self.log)

    def addInput(self, string: str):
        self.input.append(string)

    # Used to add internal funcitons like print, and for user to add functions
    def addFunction(self, name: str, func):
        self.functions[name] = func

    def callFunction(self, name: str, arguments: list = []):
        if name in self.functions:
            self.functions[name](arguments)
        elif name in self.customFunctions:
            if len(arguments) == len(self.customFunctions[name][1]):
                if len(self.currentCommand) > 0:
                    self.currentCommand[len(self.currentCommand)-1] += 1
                self.currentCommand.append(self.customFunctions[name][0])

    # Received string arguments, returns python list with them
    # Example: (3.14, 'hello world', getvar variableName) return [3.14, 'hello, world', 5]
    def __parseArguments(self, args: str) -> list:
        resultArgs = []

        rawArgs = args.replace(', ', ',')
        if rawArgs.startswith('('): rawArgs = rawArgs[1::]
        if rawArgs.endswith(')'): rawArgs = rawArgs[:len(rawArgs)-1]
        rawArgs = rawArgs.replace('(', '').replace(')', '').split(',')

        if self.log: print("Arguments:", rawArgs, end=' ')

        for argument in rawArgs:
            if argument:
                if argument.startswith('"') or argument.startswith("'"):
                    string = ''
                    for i in range(args.index(argument)+1, len(args)):
                        if args[i] == '"' or args[i] == "'":
                            break
                        else:
                            string += args[i]
                    resultArgs.append(string)

                elif type(argument) == str and argument.startswith('getvar '):
                    if argument.replace('getvar ', '') in self.variables:
                        resultArgs.append(self.variables[argument.replace('getvar ', '')])
                    else:
                        resultArgs.append('undefined')
                elif argument == 'getinput':
                    if len(self.input) > 0:
                        resultArgs.append(self.input[0])
                        del self.input[0]
                elif argument == 'getinputline':
                    if self.log: print(self.input)
                    if len(self.input) > 0 and '\n' in self.input:
                        text = ''.join([i for i in self.input]).split('\n')[0]
                        resultArgs.append(text)
                        for char in text:
                            self.input.remove(char)
                        self.input.remove('\n')

                else:
                    if '"' in argument or "'" in argument:
                        s = str(argument)
                        s = s.replace(s[0], '')
                        resultArgs.append(s)
                    elif '.' in argument:
                        try:
                            resultArgs.append(float(argument))
                            continue
                        except: pass
                    else:
                        try:
                            resultArgs.append(int(argument))
                            continue
                        except: pass

                        try:
                            resultArgs.append(str(argument))
                            continue
                        except: pass

        if self.log: print("; Resulting arguments:", resultArgs)

        return resultArgs

    def __execute(self, log=False):
        try:
            self.variables['freespace'] = self.storage.getFreeSpace()

            curCommandLayer = self.currentCommand[len(self.currentCommand)-1]
            curCommand = self.currentCommand[len(self.currentCommand)-1]

            rawline = self.storage.getMemoryAt(curCommand).replace('\n', '')
            if rawline.startswith('    '):
                rawline = ''.join(rawline.split('    ')[1::])

            line = rawline.replace(';', '')
            line = line.replace('\n', '').split(' ')

            nextCommand = curCommand + 1

            lineIsComment = False
            for char in rawline:
                if char == '#': lineIsComment = True
                elif char != ' ': break

            if line and not lineIsComment:
                if self.log: print(self.currentCommand, line, '    ', self.variables)

                if len(line) >= 1:
                    # Processor will halt at current command, and won't go any further
                    if line[0].startswith('halt'):
                        if log: print("Halting")
                        nextCommand = curCommand
                    elif line[0] == 'point':
                        if len(line) == 2:
                            self.points[line[1]] = curCommand
                            if log: print("Created point with name", line[1], "at line", curCommand)
                    elif line[0] == 'jumpto':
                        if len(line) == 2 and line[1] in self.points:
                            nextCommand = self.points[line[1]]
                            if log: print("Jumping to point with name", line[1], "at line", self.points[line[1]])
                    elif line[0].startswith('function'):
                        try:
                            print(rawline)

                            functionName = ''
                            functionParameters = []
                            functionLines = []

                            # Scanning function name
                            for char in line[1]:
                                if char == '(': break
                                else: functionName += char

                            # Scanning function parameters
                            params = rawline.split('(')[1].replace(', ', ',')
                            params = params[0:len(params)-1]
                            functionParameters = params.split(',')

                            scanned = False
                            curline = curCommand
                            while not scanned:
                                if curline < self.storage.getSize():
                                    l = self.storage.getMemoryAt(curline).replace('\n', '')
                                    if l.startswith('end'): break
                                    else: functionLines.append('')
                                else:
                                    scanned = True

                                curline += 1

                            funcStart = curline-len(functionLines)+1
                            self.customFunctions[functionName] = [funcStart, functionParameters]

                            nextCommand = curline

                            print("Function name:", functionName)
                            print("Function parameters:", functionParameters)
                            print("Function code:", functionLines)
                        except:
                            print("Error while creating a function:")
                            traceback.print_exc()
                    # elif line[0] == 'if':
                    #     if len(line) == 2 and line[1] in self.variables:
                    #
                    elif line[0].startswith('end'):
                        if len(self.currentCommand) > 1:
                            self.currentCommand.pop()
                            nextCommand = self.currentCommand[len(self.currentCommand)-1]

                    else:
                        l = rawline.split('(')
                        if len(l) > 1:
                            functionName = l[0]
                            del l[0]
                            args = "".join(l)
                            args = args[0:len(args)-1]
                            if log: print("Calling function", functionName, "with arguments", args)
                            self.callFunction(functionName, self.__parseArguments(args))
                            if functionName in self.customFunctions:
                                nextCommand = self.customFunctions[functionName][0]

                    # elif line[0] == 'setcursor':
                    # elif line[0] == 'setbg' or line[0] == 'setfg':
                    #     pass
            self.currentCommand[len(self.currentCommand)-1] = nextCommand
        except Exception as e:
            print("Exception in Interpreter.__execute()", e)
            traceback.print_exc()

class Computer:
    def __init__(self, game, x, y):
        self.x, self.y = x, y
        self.game = game
        self.game.level.replaceBlockAttributes(self.x, self.y, {'electrical': True, 'energy': 0})

        self.on = False

        self.cursorx = 0
        self.cursory = 0

        self.screenWidth = 32
        self.screenHeight = 8

        self.screen = Screen(self.screenWidth, self.screenHeight)
        self.tempScreen = Screen(self.screenWidth, self.screenHeight)
        self.prevFrameScreen = self.screen.getScreen()
        self.prevFrameBackground = self.screen.getBackgroundScreen()
        self.prevFrameForeground = self.screen.getForegroundScreen()

        self.bootloader = Storage(512)
        self.bootloader.setMemory(
        """
function addSomething(a, b);
    setcursor(0, 2);
    print('printing something!');
    setvar(something, '123');
end;

clearscreen();

setcursor(0, 0);
print('before running:', getvar something);

addSomething(5, 6);

setcursor(0, 1);
print('after running:', getvar something);

renderscreen();

halt;
        """.split(';'))

        self.mainDrive = Storage(4096)
        self.disk = Storage(2048)

        # Storage which computer will load from
        self.__loadFromStorage = self.bootloader

        self.interpreter = Interpreter(True, self)

        self.changedPixels = []

    def startup(self):
        self.on = True
        self.interpreter.reset()

    def update(self):
        try:
            if 'energy' in self.game.level.attributes[self.x, self.y] and self.game.level.attributes[self.x, self.y]['energy'] <= 0:
                self.on = False
            elif self.on == False:
                self.interpreter.reset()

            if self.on:
                self.interpreter.tick()

                self.game.level.setBlockAttribute(self.x, self.y, 'screen',
                    str(self.screen.width) + '-' + str(self.screen.height) + '-' + str(self.screen.getScreen())+'-'+str(self.screen.getBackgroundScreen())+'-'+str(self.screen.getForegroundScreen())
                )

                if self.screen.getScreen() != self.prevFrameScreen or \
                   self.screen.getBackgroundScreen() != self.prevFrameBackground or \
                   self.screen.getForegroundScreen() != self.prevFrameForeground:
                    self.game.changedBlocks.append([self.x, self.y])

                self.prevFrameScreen = self.screen.getScreen()
                self.prevFrameBackground = self.screen.getBackgroundScreen()
                self.prevFrameForeground = self.screen.getForegroundScreen()

        except Exception as e:
            print("Exception in Computer.update()", e)
            traceback.print_exc()

    def getChangedPixels(self):
        return self.changedPixels

    def getScreen(self):
        return self.screen

    def getStorageToLoadFrom(self) -> Storage:
        return self.bootloader


class Game:
    @staticmethod
    def generateGameID() -> str:
        return ''.join([random.choice(list('abcdef0123456789')) for _ in range(6)])

    def getGameIDString(self):
        return '[ ' + self.name + '; ID ' + self.gameID + ' ]'

    """
    name is string, name of the game, which will be displayed to other clients.
    """

    def __init__(self, name: str, gameId=None):
        self.players: [Client]
        self.players = []
        # Storing timestamp when last player joined
        self.whenLastPlayerJoined = time.time()
        self.playerHasJoined = False

        self.name = name
        # Unique game id.
        if gameId is not None:
            self.gameID = gameId
        else:
            self.gameID = self.generateGameID()

        # 0 is day, 0.5 is night, 1 is again day
        self.timeofday = 0

        # Generating level
        self.blocksToUpdate: [(int, int)]
        self.blocksToUpdate = []

        self.savePath = main.config.get('saves_folder') + '/' + str(self.name) + '.' + str(self.gameID) + '/'
        try: os.mkdir(self.savePath)
        except: pass

        self.changedBlocks = []
        print("Initializing level for game", self.getGameIDString())
        self.level = Level(self)

        try:
            f = open(self.savePath + 'generated')
            self.level.generatedChunks = eval(f.read())
            f.close()
        except:
            f = open(self.savePath + 'generated', 'w')
            f.write('[]')
            f.close()

        self.computers: [Computer]
        self.computers = []
        self.computerUpdatesPerSecond = main.config.get('computerClockSpeed')
        self.__lastComputersUpdate = time.time()

        try:
            f = open(self.savePath + 'spawnpoint')
            x, y = eval(f.read())
            f.close()
        except:
            x, y = random.randint(0, MAP_W - 1), random.randint(0, MAP_H - 1)
            f = open(self.savePath + 'spawnpoint', 'w')
            f.write(str((x, y)))
            f.close()

        # Spawnpoint where joined players will appear
        print(self.getGameIDString(), "Creating spawnpoint ", end='')
        self.spawn = Spawnpoint(x, y)
        self.level.setBlock(x, y, 'spawnpoint')
        print("at", self.spawn.x, self.spawn.y)

        self.lastBulletUpdate = time.time()
        self.lastBoostSpawn = time.time()
        self.lastWireUpdate = time.time()
        self.lastAutosave = time.time()

        self.bullets = []
        self.bullets: [Bullet]

        self.objects = {}
        self.objects: {(int, int): Object}

        self.changedObjects = []
        self.newMessages = []

        self.playersDamaged: [Damage]
        self.playersDamaged = []
        self.playersLeft = []

        self.commandsFromClients = []
        self.serviceMessages = []

        self.__lastGameUpdate = time.time()
        self.gameUpdatesPerSecond = main.config.get('tickSpeed')

        # For storing and normal handling of players.
        # Each new player will be stored with key i+1
        # So, for example first player will have key 0, second will have 1, and so on.
        self.i = 0

    def stopGame(self):
        client: Client
        for client in self.players:
            client.disconnect('Game was shut down.')

        if main.config.get('saveGames'):
            print(self.getGameIDString(), "saving game level.")
            f = open('savedGames/' + self.name + '.' + self.gameID + '.level', 'w')
            f.write(str(self.level.level))
            f.close()

    def addPlayer(self, sock: socket.socket, addr: tuple, nickname=''):
        player = Player(0, 0, 'grass', 100, str(self.i))

        client = Client(sock, addr, player, self.i, self)
        client.setPosition(self.spawn.x, self.spawn.y)
        client.setNickname(nickname)
        self.players.append(client)

        self.i += 1

        self.whenLastPlayerJoined = time.time()
        self.playerHasJoined = True

        self.broadcastMessage('New player joined the game!')

    def getPlayersOnline(self) -> int:
        playersOnline = 0
        for client in self.players:
            if client.player.active: playersOnline += 1

        return playersOnline

    def broadcastMessage(self, msg: str):
        client: Client
        for client in self.players:
            client.sendMessage(msg)

    def handleCommand(self, command: str) -> str:
        try:
            command = command.lower()
            cmd = command.split(' ')
            if cmd[0] == '/kick':
                client: Client
                for client in self.players:
                    if client.clientID == int(cmd[1]):
                        client.disconnect(reason=''.join([s + ' ' for s in cmd[2::]]))
                        return 'Successfully kicked player #' + str(cmd[1])
                return 'No player found with id #' + str(cmd[1])
            elif cmd[0] == '/spawnchest':
                self.level.createChest(int(cmd[1]), int(cmd[2]))
                return 'Successfully generated loot chest at ' + cmd[1] + ', ' + cmd[2]
            elif cmd[0] == '/teleport':
                self.players[int(cmd[1])].setPosition(int(cmd[2]), int(cmd[3]))
                return 'Teleported player ' + str(cmd[1]) + ' to x ' + str(cmd[2]) + ', y ' + str(cmd[3])
            else:
                return 'Unknown command.'
        except Exception as e:
            return 'Exception has occurred: ' + str(e)

    def __updateClients(self):
        # Receiving new messages from clients
        client: Client
        for client in self.players:
            try:
                if client.player.active: client.update()
            except Exception as e:
                print("Exception was thrown while updating clients:\n", e)

    def __updateChangedData(self):
        for block in self.changedBlocks:
            for client in self.players:
                client.changedBlocks.append(block)
        self.changedBlocks.clear()

        for obj in self.changedObjects:
            for client in self.players:
                client.changedObjects.append(obj)
        self.changedObjects.clear()

        for msg in self.newMessages:
            for client in self.players:
                client.newMessages.append(msg)
        self.newMessages.clear()

        player: Damage
        for player in self.playersDamaged:
            print(player.damageAmount, player.damager, player.receiver)
            self.players[player.receiver].dataToSend.append('bullet_hit/' + str(player.damageAmount))
            if self.players[player.receiver].player.health - player.damageAmount <= 0:
                self.broadcastMessage(
                    self.players[player.receiver].getNickname() + ' was killed by ' +
                    self.players[player.damager].getNickname())
        self.playersDamaged.clear()

        for player in self.playersLeft:
            for client in self.players:
                client.playersLeft.append(player)
        self.playersLeft.clear()

    def __processCommands(self):
        for command in self.commandsFromClients:
            print(command)
            response = self.handleCommand(command[1])
            print(response)
            self.players[command[0]].sendMessage(str(response))

            """
            for client in self.players:
                if client.clientID == command[0]:
                    print(client.clientID)
                    client.serviceMessages.append(response)
            """
        self.commandsFromClients.clear()

    def __updateBullets(self):
        if time.time() - self.lastBulletUpdate >= 1 / 5:
            for i in range(len(self.bullets)):
                bullet = self.bullets[i]
                if bullet.active:
                    # Checking if bullet is within borders of map
                    if 0 <= bullet.x < MAP_W and 0 <= bullet.y < MAP_H and \
                            self.level.level[bullet.x, bullet.y] in ['grass', 'wood']:
                        # Checking if bullet hits someone
                        hit = False

                        j: Client
                        for j in self.players:
                            player = j.player
                            if player.x == bullet.x and player.y == bullet.y \
                                    and not (j.clientID == bullet.owner) and player.active:
                                # Processing hit
                                j.dataToSend.append('bullet_hit/10')
                                self.bullets[i].active = False
                                hit = True

                        if not hit and self.level.level[bullet.x, bullet.y] == 'wood' and random.randint(0, 9) == 0:
                            self.level.level[bullet.x, bullet.y] = 'grass'
                            self.changedBlocks.append([bullet.x, bullet.y, 'grass'])
                            self.bullets[i].active = False
                        elif not self.level.level[bullet.x, bullet.y] == 'grass':
                            self.bullets[i].active = False

                        bullet.x += bullet.movX
                        bullet.y += bullet.movY
                    else:
                        self.bullets[i].active = False

            for bullet in self.bullets:
                if not bullet.active:
                    self.bullets.remove(bullet)

            self.lastBulletUpdate = time.time()

    def __updateComputers(self):
        computer: Computer
        for computer in self.computers:
            computer.update()

    def __deleteDisconnectedPlayers(self):
        player: Client
        for player in self.players:
            if not player.player.active:
                print(self.getGameIDString(), "Disconnecting inactive player (", player.getNickname(), ")")
                self.players.remove(player)

    def save(self):
        f = open(self.savePath + 'generated', 'w')
        f.write(str(self.level.generatedChunks))
        for x, y in self.level.generatedChunks:
            blocks = {}
            attributes = {}

            for x1 in range(x * 8, x * 8 + 8):
                for y1 in range(y * 8, y * 8 + 8):
                    blocks[x1, y1] = self.level.level[x1, y1]
                    attributes[x1, y1] = self.level.attributes[x1, y1]

            f = open(self.savePath + str(x) + '.' + str(y) + '.region', 'w')
            f.write(str(blocks) + '\n' + str(attributes))

    def __autosave(self):
        if time.time() - self.lastAutosave >= main.config.get('autosave_delay'):
            self.save()
            print(self.getGameIDString(), "autosave completed.")
            self.lastAutosave = time.time()

    def __loadChunks(self):
        pass

    def update(self) -> None:
        try:
            # Regenerating spawn point if there's a block at spawnpoint coordinates.
            """
            if self.level.level[self.spawn.x, self.spawn.y] != 'grass':
                print("Spawnpoint was blocked, regenerating it")
                created = False
                while not created:
                    x, y = random.randint(0, MAP_W - 1), random.randint(0, MAP_H - 1)
                    if self.level.level[x, y] in ['grass', 'wooden_door_opened']:
                        self.spawn = Spawnpoint(x, y)
                        created = True
            """

            self.blocksToUpdate.clear()
            player: Client
            for player in self.players:
                x,y = int(player.player.x)//80, int(player.player.y)//80
                for x1 in range(x-10, x+11):
                    for y1 in range(y-6, y+7):
                        self.blocksToUpdate.append((x1, y1))
            # print(self.blocksToUpdate)

            if time.time() - self.lastWireUpdate >= 1/self.gameUpdatesPerSecond:
                self.level.updateLevel()
                self.lastWireUpdate = time.time()

            if time.time() - self.__lastComputersUpdate >= 1/self.computerUpdatesPerSecond:
                self.__updateComputers()
                self.__lastComputersUpdate = time.time()

            if time.time() - self.__lastGameUpdate >= 1/self.gameUpdatesPerSecond:
                self.__updateClients()
                self.__updateChangedData()
                self.__processCommands()
                self.__loadChunks()
                self.__autosave()

                # self.__deleteDisconnectedPlayers()

                # Spawning chests ( only if there is at least one player online )
                if time.time() - self.lastBoostSpawn >= 60 and self.getPlayersOnline() > 0:
                    print(self.getGameIDString(), "Spawning bonus chest ", end='')
                    spawned = False
                    while not spawned:
                        x, y = random.choice(self.blocksToUpdate)
                        if self.level.level[x, y] == 'grass':
                            print("at", x, y)
                            self.level.createChest(x, y)
                            spawned = True

                    self.lastBoostSpawn = time.time()

                self.timeofday += 1/main.config.get('tickSpeed')/100
                if self.timeofday >= 1: self.timeofday = 0

                self.__updateBullets()

                self.__lastGameUpdate = time.time()

        except Exception as e:
            print(self.getGameIDString(), "CRITICAL GAME ERROR: ", e)
            traceback.print_exc()


class Client:
    def __init__(self, sock: socket.socket, addr: tuple, player: Player, i: int, game: Game):
        # all this sockety things
        self.s = sock
        self.s: socket.socket

        self.a = addr
        self.a: tuple

        self.clientID = i
        self.clientID: int

        self.player = player
        self.game = game

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

        # Player's id and time of day will be send only one time in 5 seconds
        self.whenBasicDataSent = 0

        self.lastAliveMessage = time.time()

        print(self.game.getGameIDString(), "Client #" + str(self.clientID) + " connected: ", self.a)

        self.sendMessage(main.config.get('welcome_message'))

    def sendMessage(self, msg: str, color=(0, 0, 255), prefix=False):
        if prefix:
            msg = main.config.get('service_message_prefix') + msg
        self.serviceMessages.append([msg, color])

    def setPosition(self, x: int, y: int):
        self.rawDataToSend.append('setpos/' + str(x) + '/' + str(y))

    def getNickname(self) -> str:
        return self.player.nickname

    def setNickname(self, nickname: str):
        self.player.nickname = nickname

    def __receiveMessages(self) -> None:
        try:
            dataRaw = self.s.recv(1073741824).decode('utf-8')

            for message in dataRaw.split(';'):
                if message:
                    self.__messagesFromClient.append(message)
        except socket.error:
            pass
        except Exception as e:
            print(self.game.getGameIDString(), "Exception while receiving messages from client:", e)

    def __handleMessages(self) -> None:
        try:
            message: str
            # if self.__messagesFromClient: print(self.__messagesFromClient)
            if self.__messagesFromClient: self.lastAliveMessage = time.time()

            for message in self.__messagesFromClient:
                if message.startswith('/'):
                    print(self.game.getGameIDString(), "Command from", self.getNickname(), ":", message)
                    self.game.commandsFromClients.append([self.clientID, message])

                elif message == 'disconnect':
                    self.game.whenLastPlayerJoined = time.time()
                    self.disconnected = True
                    self.player.active = False
                    self.game.playersLeft.append(self.clientID)
                    self.s.close()
                    print(self.game.getGameIDString(), self.getNickname(), "with address", self.a, "disconnected.")

                elif 'load_chunk' in message:
                    _, x, y = message.split('/')
                    x, y = int(x), int(y)

                    blocks, attributes = self.game.level.getChunk(x, y)
                    self.dataToSend.append('chunk/' + str(blocks) + '/' + str(attributes))

                elif message == 'get_objects':
                    m = ''

                    if time.time() - self.whenBasicDataSent >= 5:
                        m += 'timeofday/' + str(self.game.timeofday) + ';'
                        m += 'yourid/' + str(self.clientID) + ';'
                        self.whenBasicDataSent = time.time()

                    for p in range(len(self.playersLeft)):
                        m += 'p/' + str(self.playersLeft[p]) + '/0/0/mage/False/0;'

                    for p in range(len(self.game.players)):
                        if p != self.clientID and self.game.players[p].player.active:
                            player = self.game.players[p].player
                            m += 'p/' + str(p) + '/' + str(player.x) + '/' + str(player.y) \
                                 + '/' + str(player.texture) + '/' + str(player.active) + '/' \
                                 + str(player.health) + ';'

                    for bullet in range(len(self.game.bullets)):
                        b = self.game.bullets[bullet]
                        m += 'b/' + str(self.game.bullets.index(b)) + '/' + str(b.x) + '/' + str(b.y) \
                             + '/' + str(b.movX) + '/' + str(b.movY) \
                             + '/' + str(b.color) + '/' + str(b.active) + ';'

                    # print(self.changedBlocks)
                    for block in range(len(self.changedBlocks)):
                        x, y = self.changedBlocks[block]
                        m += 'cb/' + str(x) + '/' + str(y) + '/' + str(self.game.level.level[x, y]) + '/' + \
                             str(self.game.level.attributes[x, y]) + ';'
                        # print(m)

                    for b in self.changedObjects:
                        m += 'o/' + str(b[0]) + '/' + str(b[1]) + '/' + str(b[2]) + '/' + str(b[3]) + ';'

                    for b in self.newMessages:
                        if b[0] != self.clientID:
                            m += 'msg/' + str(b[0]) + '/' + str(b[1]) + ';'

                    for b in self.serviceMessages:
                        m += 'service/' + str(b[0]) + '/' + str(b[1]) + ';'

                    for b in self.rawDataToSend:
                        m += b + ';'

                    # if m == '':
                    #     m = 'nothing'

                    self.dataToSend.append(m)
                    self.changedBlocks.clear()
                    self.changedObjects.clear()
                    self.newMessages.clear()
                    self.serviceMessages.clear()
                    self.rawDataToSend.clear()
                    self.playersLeft.clear()
                elif 'set_nick' in message:
                    message = message.replace('set_nick/', '').split('/')

                    self.player.nickname = message[0]
                    print(self.game.getGameIDString(), 'Client #', self.clientID, 'set his nickname to', message[0])
                elif 'set_player' in message:
                    # print(message)

                    message = message.replace('set_player', '').split('/')

                    p = Player(float(message[0]), float(message[1]), message[2], int(message[3]),
                               nickname=self.player.nickname)

                    self.player = p
                elif 'set_block' in message:
                    # print(message)

                    message = message.replace('set_block', '').split('/')

                    x, y, block, attributes = int(message[0]), int(message[1]), message[2], eval(message[3])

                    self.game.level.level[x, y] = block
                    self.game.level.attributes[x, y] = attributes

                    if 'computer' in block:
                        c = Computer(self.game, x, y)
                        self.game.computers.append(c)

                    self.game.changedBlocks.append([int(message[0]), int(message[1])])
                elif 'shoot' in message:
                    message = message.replace('shoot', '').split('/')

                    b = Bullet(int(message[0]), int(message[1]),
                               int(message[2]), int(message[3]), eval(message[4]),
                               self.clientID)
                    b.active = True

                    # Checking if there's aren't any bullets that are in the same position as ours
                    same_pos = False
                    for bullet in self.game.bullets:
                        if bullet.x == b.x and bullet.y == b.y:
                            same_pos = True

                    if not same_pos:
                        self.game.bullets.append(b)
                elif 'create_object' in message:
                    message = message.replace('create_object', '').split('/')

                    self.game.objects[int(message[0]), int(message[1])] = Object(int(message[0]), int(message[1]),
                                                                                 message[2])

                    self.game.changedObjects.append([int(message[0]), int(message[1]), message[2], True])
                elif 'remove_object' in message:
                    message = message.replace('remove_object', '').split('/')

                    self.game.objects[int(message[0]), int(message[1])].active = False

                    self.game.changedObjects.append([int(message[0]), int(message[1]), '', False])
                elif 'attack' in message:
                    message = message.replace('attack', '').split('/')

                    self.game.playersDamaged.append(Damage(int(message[1]), int(message[0]), self.clientID))
                elif 'computer_input' in message:
                    message = message.replace('computer_input', '').split('/')

                    x,y, char = int(message[0]), int(message[1]), message[2]

                    for computer in self.game.computers:
                        if computer.x == x and computer.y == y:
                            computer.interpreter.addInput(char)

                else:
                    if message:
                        print(self.game.getGameIDString(), self.getNickname(), ":", message)
                        self.game.newMessages.append([self.clientID, message])

            self.__messagesFromClient.clear()

        except Exception as e:
            print(self.game.getGameIDString(), "Exception while handling", self.getNickname(), "'s messages:\n", e)
            self.__messagesFromClient.clear()
            print()
            traceback.print_exc()

    def getPlayer(self) -> Player:
        return self.player

    def update(self) -> None:
        if self.disconnected:
            self.player.active = False
        else:
            # Disconnecting client if it is not responding for 10 seconds.
            if time.time() - self.lastAliveMessage >= 10:
                print(self.game.getGameIDString(),
                      self.getNickname(), "has been not responding for 10 seconds! Disconnecting him/her.")

                try:
                    self.disconnect(reason='Timed out.')
                except Exception as e:
                    print(self.game.getGameIDString(), "Error while trying to send disconnect message:", e)

                self.disconnected = True
                self.player.active = False
                self.game.playersLeft.append(self.clientID)
                self.s.close()
                print(self.game.getGameIDString(), "Client #" + str(self.clientID) + " disconnected: ", self.a)

                return

            try:
                self.__receiveMessages()

                self.__handleMessages()
            except Exception as e:
                print(self.game.getGameIDString(), "Exception in Client.update():", e)
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
                        print(self.game.getGameIDString(), "Error while sending data to", self.getNickname(), e)
            except socket.error:
                pass
            except Exception as e:
                print(self.game.getGameIDString(), "Ex", e)

    def disconnect(self, reason=None):
        if reason is None:
            reason = main.config.get('shutdown_message')

        if self.player.active:
            try:
                self.player.active = False
                self.game.playersLeft.append(self.clientID)

                self.s.setblocking(True)

                msg = 'disconnect/' + reason + ';'
                self.s.send(msg.encode('utf-8'))
                self.disconnected = True
            except Exception as e:
                print(self.game.getGameIDString(), "Exception while trying to disconnect", self.getNickname(), e)


class LevelContainer:
    def __init__(self, game: Game, defaultVal, disableChecking=False):
        self.lvl = {}

        self.game = game
        self.defaultVal = defaultVal
        self.disableChecking = disableChecking

    def __getitem__(self, item: (int, int)):
        try:
            if item in self.lvl:
                return self.lvl[item]
            else:
                # print("Index out of bounds error. Tried to access block at", item)
                return self.defaultVal
        except:
            print("Level.__getitem__(item) error. item:", item)
            traceback.print_exc()
            return self.defaultVal

    def __setitem__(self, key: (int, int), value):
        if key in self.lvl and not self.disableChecking:
            if value != self.lvl[key] and key not in self.game.changedBlocks:
                #print(value, self.lvl[key])
                self.game.changedBlocks.append([key[0], key[1]])
        self.lvl[key] = value


class Level:
    def __init__(self, game: Game):
        self.game = game

        self.level = LevelContainer(self.game, 'grass')
        self.attributes = LevelContainer(self.game, {}, disableChecking=True)
        self.generatedChunks = []

        self.__generated = False

    def updateLevel(self):
        # Updating wires
        wiresUpdated = 0
        for x,y in self.game.blocksToUpdate:
            if 'wire' in self.level[x, y]:
                variant = ['f', 'f', 'f', 'f']
                if 'electrical' in self.attributes[x-1, y] and self.attributes[x, y]['electrical']:
                    variant[2] = 't'
                if 'electrical' in self.attributes[x+1, y] and self.attributes[x, y]['electrical']:
                    variant[3] = 't'
                if 'electrical' in self.attributes[x, y-1] and self.attributes[x, y]['electrical']:
                    variant[0] = 't'
                if 'electrical' in self.attributes[x, y+1] and self.attributes[x, y]['electrical']:
                    variant[1] = 't'

                variant = "".join(i for i in variant)

                if variant != self.attributes[x, y]['rotation']:
                    self.attributes[x, y]['rotation'] = variant
                    self.game.changedBlocks.append([x, y])
                    wiresUpdated += 1

        if wiresUpdated > 0:
            pass
            # print("Updated wires:", wiresUpdated)

        positions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        for x,y in self.game.blocksToUpdate:
            if 'switch' in self.level[x, y] and self.attributes[x, y]['on']:

                for pos in positions:
                    x1, y1 = x + pos[0], y + pos[1]
                    if 'wire' in self.level[x1, y1] or 'lamp' in self.level[x1, y1] or 'computer' in self.level[x1, y1]:
                        if not 'energy_source' in self.attributes[x1, y1] \
                           and self.attributes[x1, y1]['energy'] == 0:
                            self.setBlockAttribute(x1, y1, 'energy_source', (x, y))
                            self.setBlockAttribute(x1, y1, 'energy', 1)
                            self.game.changedBlocks.append([x1, y1])

            elif 'wire' in self.level[x, y]:
                if 'energy' in self.attributes[x, y] and 'energy_source' in self.attributes[x, y]:
                    if self.attributes[x, y]['energy'] > 0 and \
                       'energy' in self.attributes[self.attributes[x, y]['energy_source']] and \
                       self.attributes[self.attributes[x, y]['energy_source']]['energy'] > 0:

                        for pos in positions:
                            x1, y1 = x + pos[0], y + pos[1]
                            if 'wire' in self.level[x1, y1] or 'lamp' in self.level[x1, y1] or 'computer' in self.level[x1, y1]:
                                if not 'energy_source' in self.attributes[x1, y1] \
                                   and self.attributes[x1, y1]['energy'] == 0:
                                    self.setBlockAttribute(x1, y1, 'energy_source', (x, y))
                                    self.setBlockAttribute(x1, y1, 'energy', 1)
                                    self.game.changedBlocks.append([x1, y1])
                    elif 'energy_source' in self.attributes[x, y]:
                        self.setBlockAttribute(x, y, 'energy', 0)
                        self.removeBlockAttribute(x, y, 'energy_source')
                        self.game.changedBlocks.append([x, y])
                elif 'energy_source' in self.attributes[x, y]:
                    self.setBlockAttribute(x,y, 'energy', 0)
                    self.removeBlockAttribute(x,y, 'energy_source')
                    self.game.changedBlocks.append([x, y])
            elif 'lamp' in self.level[x, y]:
                if 'energy_source' in self.attributes[x, y] and 'energy' in self.attributes[x, y] and \
                   'energy' in self.attributes[self.attributes[x, y]['energy_source']]:
                    if self.attributes[x, y]['energy'] <= 0 or \
                       self.attributes[self.attributes[x, y]['energy_source']]['energy'] <= 0 and \
                       'energy_source' in self.attributes[x, y]:
                        self.setBlockAttribute(x,y, 'energy', 0)
                        self.removeBlockAttribute(x,y, 'energy_source')
                        self.game.changedBlocks.append([x, y])
                elif 'energy_source' in self.attributes[x, y]:
                    self.setBlockAttribute(x,y, 'energy', 0)
                    self.removeBlockAttribute(x,y, 'energy_source')
                    self.game.changedBlocks.append([x, y])

        computer: Computer
        for computer in self.game.computers:
            if not computer.on and 'energy' in self.attributes[computer.x, computer.y] and \
               self.attributes[computer.x, computer.y]['energy'] > 0:
                computer.startup()

    def setLevel(self, level: dict):
        # Checking if there's any missing blocks.
        for x,y in level:
            self.level[x, y] = level[x, y]

    def setBlock(self, x: int, y: int, block: str):
        self.level[x, y] = block

    def setBlockAttribute(self, x: int, y: int, key: str, val: any):
        self.attributes[x, y][key] = val

    def removeBlockAttribute(self, x: int, y: int, key: str):
        if key in self.attributes[x, y]: del self.attributes[x, y][key]

    def replaceBlockAttributes(self, x: int, y: int, attribute: dict):
        self.attributes[x, y] = attribute

    def generateBlock(self, x, y, addToChangedBlocks=True, force=False):
        r = random.randint(0, 7)
        b = 'grass'
        if x < 0 or y < 0 or x > 1024 or y > 1024:
            b = 'barrier'
        else:
            if r == 0:
                b = 'wall'
            if r == 1:
                b = 'tree'
            # if r == 2 and random.randint(0, 3) == 0:
            #     b = self.createChest(x, y)
            if r == 3 and random.randint(0, 3) == 0:
                b = 'heart'
        if not force:
            if self.level[x, y] == 'grass':
                self.level[x, y] = b
                self.attributes[x, y] = {}
        else:
            self.level[x, y] = b

        if self.__generated and addToChangedBlocks:
            self.game.changedBlocks.append([x, y])

    def generateChunk(self, cx, cy):
        for x in range(cx*8, cx*8+8):
            for y in range(cy*8, cy*8+8):
                self.generateBlock(x, y, addToChangedBlocks=False)
        if (cx, cy) not in self.generatedChunks: self.generatedChunks.append((cx, cy))

    def getChunk(self, cx, cy) -> tuple[dict, dict]:
        if (cx, cy) in self.generatedChunks and (cx*8, cy*8) in self.level.lvl:
            blocks, attributes = {}, {}
            for x1 in range(cx * 8, cx * 8 + 8):
                for y1 in range(cy * 8, cy * 8 + 8):
                    blocks[x1, y1] = self.game.level.level[x1, y1]
                    attributes[x1, y1] = self.game.level.attributes[x1, y1]
            return blocks, attributes
        elif (cx, cy) in self.generatedChunks and (cx*8, cy*8) not in self.level.lvl:
            try:
                f = open(self.game.savePath + str(cx) + '.' + str(cy) + '.region')
                blocks, attributes = f.read().split('\n')
                blocks, attributes = eval(blocks), eval(attributes)
                for x, y in blocks:
                    self.level[x, y] = blocks[x, y]
                    self.attributes[x, y] = attributes[x, y]
                print("Chunk", cx, cy, "loaded from disk")
                return blocks, attributes
            except:
                print("Failed to load chunk from file")
                traceback.print_exc()
                self.game.level.generateChunk(cx, cy)
                blocks, attributes = {}, {}
                for x1 in range(cx * 8, cx * 8 + 8):
                    for y1 in range(cy * 8, cy * 8 + 8):
                        blocks[x1, y1] = self.game.level.level[x1, y1]
                        attributes[x1, y1] = self.game.level.attributes[x1, y1]
                return blocks, attributes

        else:
            self.game.level.generateChunk(cx, cy)
            blocks, attributes = {}, {}
            for x1 in range(cx * 8, cx * 8 + 8):
                for y1 in range(cy * 8, cy * 8 + 8):
                    blocks[x1, y1] = self.game.level.level[x1, y1]
                    attributes[x1, y1] = self.game.level.attributes[x1, y1]
            return blocks, attributes

    def generateLevel(self):
        pass

    def createChest(self, x, y,
                    lootTable=None, maxItems=8) -> str:
        if lootTable is None:
            # First is item itself, second is max possible items that can be generated,
            # third is spawn chance ( from 0 to 100 )
            lootTable = [
                ['pickaxe', 1, 5],
                ['magic_stick', 1, 10],
                ['candle', 1, 25],
                ['sniper_rifle', 1, 100],
                ['knife', 1, 0.5],
                ['wood', 15, 100],
                ['planks', 50, 30],
                ['wall', 15, 100],
                ['tree', 15, 100]
            ]

        m = []
        for item in range(random.randint(1, maxItems // 2) * 2):
            created = False

            while not created:
                i = random.randint(0, len(lootTable) - 1)
                item = lootTable[i]

                if random.randint(0, 100000) / 1000 <= item[2]:
                    itemName = item[0]
                    itemCount = random.randint(1, item[1])

                    m.append([itemName, itemCount])

                    created = True

        # print(m)

        self.level[x, y] = 'chest'
        self.attributes[x, y] = {'items':m}

        print(self.level[x, y], self.attributes[x, y])
        self.game.changedBlocks.append([x, y])

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


class Lobby:
    def __init__(self):
        self.players: [[socket.socket, tuple]]
        self.players = []

    def __handleMessage(self, sock: socket.socket, addr: tuple, message: str):
        # print(message)

        # There can be multiple commands in one message, they are split with ;
        for msg in message:
            try:
                # If player wants to disconnect
                if msg == 'disconnect':
                    print("Player has left from the lobby.")
                    self.players.remove([sock, addr])
                    sock.close()
                # If players wants to see all active games
                elif msg == 'get_games':
                    toSend = ''
                    for game in main.games:
                        toSend += 'g/' + game.name + '/' + str(game.getPlayersOnline()) + '/' + game.gameID + ';'
                    sock.send(toSend.encode('utf-8'))
                    # print("Sended all active games to player", addr[0])
                # If player wants to see all archived games ( unloaded games, saved on the disk )
                elif msg == 'get_archived_games':
                    toSend = ''
                    try:
                        for filename in os.listdir('savedGames/'):
                            name, gameID, _ = filename.split('.')
                            # Checking if this game is not active
                            foundSame = False
                            for game in main.games:
                                if game.gameID == gameID: foundSame = True

                            if not foundSame:
                                toSend += 'g/' + name + '/0/' + gameID + ';'
                        sock.send(toSend.encode('utf-8'))
                    except Exception as e:
                        print("Failed to send archived games to the client:", e)
                # If player wants to join archived game ( unloaded game, saved on the disk )
                elif 'join_archived_game' in msg:
                    print("Player joining the archived game...")

                    gameid = msg.replace('join_archived_game/', '').split('/')[0]
                    for filename in os.listdir('savedGames/'):
                        name, gameID, _ = filename.split('.')

                        if gameID == gameid:
                            f = open('savedGames/' + filename, 'r', encoding='utf-8')
                            g = Game(name, gameID, f.read())
                            f.close()
                            g.addPlayer(sock, addr)
                            main.games.append(g)
                            print("Player", addr[0], "joined the game", g.getGameIDString())
                            self.players.remove([sock, addr])
                            break
                # If player wants to join the game
                elif 'join_game' in msg:
                    print("Player joining the game...")
                    msg = msg.replace('join_game/', '').split('/')
                    # Structure of request: join_game/gameid/nickname;
                    gameid = msg[0]
                    # Finding battle with exact game id
                    for game in main.games:
                        if game.gameID == gameid:
                            game.addPlayer(sock, addr, nickname=msg[1])
                            print("Player", addr[0], "joined the game", game.getGameIDString())
                            self.players.remove([sock, addr])
                # If player wants to create the game
                elif 'create_game' in msg:
                    print("\nCreating new game")

                    msg = msg.split('/')
                    name = ''
                    if len(msg) == 1:
                        name = 'Game ' + str(len(main.games))
                    else:
                        name = str(msg[1])

                    found = False
                    for game in main.games:
                        if game.name == name:
                            g = game
                            found = True
                    if not found: g = Game(name)

                    g.addPlayer(sock, addr)
                    self.players.remove([sock, addr])
                    main.games.append(g)
                    #  print(main.games)

            except Exception as e:
                print("Exception while handling messages from client in the lobby:", e)
                traceback.print_exc()

    def update(self):
        for sock, addr in self.players:
            # Trying to receive data from the client
            try:
                # Receiving data and decoding it
                d = sock.recv(1048576).decode('utf-8')

                if d:
                    # Handling commands
                    self.__handleMessage(sock, addr, d.split(';'))
            except:
                pass


class Main:
    def __init__(self):
        global main
        main = self

        print("\nStarting BattleKiller2D server", GAME_VERSION, "\n")

        self.lobby = Lobby()
        self.games: [Game]
        self.games = []

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

        try: os.mkdir(self.config.get('saves_folder'))
        except: pass

        for filename in os.listdir(self.config.get('saves_folder')):
            name, gameid = filename.split('.')

            g = Game(name, gameid)

            self.games.append(g)

        print("Starting server on:\nip", self.ip, "\nport", self.port)

        # Binding socket
        print("Binding socket")
        self.s.bind((self.ip, self.port))

        # Starting to listen to new clients
        print("Starting to listen to clients\n")
        self.s.listen(16384)

        # Setting socket mode to "non-blocking" which allows us to skip waiting for a new message
        # If there's no messages from client, an error will be thrown
        self.s.setblocking(False)

        # List for all clients
        self.clients = []
        self.clients: [Client]

    def __acceptNewClients(self):
        try:
            sock, addr = self.s.accept()
            sock.setblocking(False)

            print("\nNew player has joined, moving him(her) to the lobby")

            self.lobby.players.append([sock, addr])
            print("Currently there are", len(self.lobby.players), "players in the lobby.\n")

        except socket.error:
            pass

    def __stopInactiveGames(self):
        for game in self.games:
            # Stopping all games which have no players online and no players have joined to them in last 300 seconds.
            if game.playerHasJoined and \
               game.getPlayersOnline() == 0 and \
               time.time() - game.whenLastPlayerJoined >= int(self.config.get('inactiveGameTimeout')):
                print('\n' + game.getGameIDString(), "is inactive. Stopping it.")
                game.stopGame()
                self.games.remove(game)

    def update(self) -> None:
        try:
            # Deleting inactive games
            self.__stopInactiveGames()

            # Accepting clients
            self.__acceptNewClients()

            # Updating lobby
            self.lobby.update()

            # Updating all active games
            for game in self.games:
                game.update()

        except Exception as e:
            print("CRITICAL SERVER ERROR: ", e)
            traceback.print_exc()

    def shutDown(self):
        print("\nShutting down server.")
        for game in self.games:
            game.save()
            game.stopGame()
            time.sleep(0.2)
        time.sleep(1)
        self.s.close()
        self.s.detach()


class GUI:
    def stopServer(self):
        self.alive = False

    def sendClientMessage(self):
        if len(self.main.clients) >= int(self.entry1.get()):
            self.main.clients[int(self.entry1.get())].dataToSend.append('service/' + self.entry2.get())

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
    try:
        __f = open('version.txt', 'r', encoding='utf-8')
        GAME_VERSION = __f.read()
        __f.close()
    except Exception as __e:
        print("Failed to read game version from the file version.txt. Exception", __e)
        GAME_VERSION = 'version UNKNOWN'

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
