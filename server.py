import random
import socket
import time
import traceback
import os
from tkinter import *

MAP_W = 16
MAP_H = 8


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

    def __init__(self, name: str, gameId=None,
                 level=None  # If level will be not none, it will be used as level
                 ):
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
        print("Initializing level for game", self.getGameIDString())
        self.level = Level(self)
        if level is not None:
            try:
                lvl = level
                if type(lvl) == str:
                    lvl = eval(lvl)

                self.level.setLevel(lvl)
            except Exception as e:
                print(self.getGameIDString(), "Failed to inialize level from variable:", e)
                self.level.generateLevel()
        else:
            print("Generating level for game", self.getGameIDString())
            self.level.generateLevel()

        self.computers: [Computer]
        self.computers = []
        self.computerUpdatesPerSecond = main.config.get('computerClockSpeed')
        self.__lastComputersUpdate = time.time()

        # Spawnpoint where joined players will appear
        print("Creating spawnpoint ", end='')
        generated = False
        while not generated:
            x, y = random.randint(0, MAP_W - 1), random.randint(0, MAP_H - 1)
            if self.level.level[x, y] == 'grass':
                self.spawn = Spawnpoint(x, y)
                print("at", self.spawn.x, self.spawn.y, "for game", self.getGameIDString())
                break

        self.lastBulletUpdate = time.time()
        self.lastBoostSpawn = time.time()
        self.lastWireUpdate = time.time()

        self.bullets = []
        self.bullets: [Bullet]

        self.objects = {}
        self.objects: {(int, int): Object}

        self.changedBlocks = []
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

    def addPlayer(self, sock: socket.socket, addr: tuple):
        player = Player(0, 0, 'grass', 100, str(self.i))

        client = Client(sock, addr, player, self.i, self)
        client.setPosition(self.spawn.x, self.spawn.y)
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
            cmd = command.split(' ')
            if cmd[0] == 'kick':
                client: Client
                for client in self.players:
                    if client.clientID == int(cmd[1]):
                        client.disconnect(reason=''.join([s + ' ' for s in cmd[2::]]))
                        return 'Successfully kicked player #' + str(cmd[1])
                return 'No player found with id #' + str(cmd[1])
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
            for client in self.players:
                if client.clientID == command[0]:
                    print(client.clientID)
                    client.serviceMessages.append(response)
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

    def update(self) -> None:
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

                # self.__deleteDisconnectedPlayers()

                # Spawning chests ( only if there is at least one player online )
                if time.time() - self.lastBoostSpawn >= 60 and self.getPlayersOnline() > 0:
                    print(self.getGameIDString(), "Spawning new ", end='')
                    spawned = False
                    while not spawned:
                        x, y = random.randint(0, MAP_W - 1), random.randint(0, MAP_H - 1)
                        if self.level.level[x, y] == 'grass':
                            if random.randint(0, 4) == 0:
                                print("health boost")
                                self.level.setBlock(x, y, 'heart')
                            else:
                                print("chest")
                                self.level.createChest(x, y)
                            spawned = True

                    self.lastBoostSpawn = time.time()

                self.timeofday += 1/2400
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
            # if self.__messagesFromClient: print(self.__messagesFromClient)
            for message in self.__messagesFromClient:
                if message == 'alive':
                    self.lastAliveMessage = time.time()

                elif '/command' in message:
                    print(self.game.getGameIDString(), "Command from ", self.getNickname(), message)
                    cmd = message.replace('/command ', '')
                    self.game.commandsFromClients.append([self.clientID, cmd])

                elif message == 'disconnect':
                    self.game.whenLastPlayerJoined = time.time()
                    self.disconnected = True
                    self.player.active = False
                    self.game.playersLeft.append(self.clientID)
                    self.s.close()
                    print(self.game.getGameIDString(), self.getNickname(), "with address", self.a, "disconnected.")

                elif message == 'unity_get_level':
                    print(self.game.getGameIDString(), self.getNickname(), " (unity client) loaded the map.")
                    m = ''
                    for x in range(MAP_W):
                        for y in range(MAP_H):
                            m += self.game.level.level[x, y]
                            if y < MAP_H-1: m += '^'
                            elif x < MAP_W-1: m += '~'
                            

                    s = 'map' + m
                    print(self.game.level.level)
                    print(s)
                    self.dataToSend.append(s)
                elif message == 'get_level':
                    print(self.game.getGameIDString(), self.getNickname(), "loaded the map.")
                    self.dataToSend.append('map' + str(self.game.level.level))
                    self.dataToSend.append('attributes' + str(self.game.level.attributes))

                elif message == 'get_objects':
                    m = ''

                    m += 'timeofday/' + str(self.game.timeofday) + ';'

                    m += 'yourid/' + str(self.clientID) + ';'

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
                        m += 'cb/' + str(x) + '/' + str(y) + '/' + self.game.level.level[x, y] + '/' + \
                             str(self.game.level.attributes[x, y]) + ';'

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

                    x, y, block = int(message[0]), int(message[1]), message[2]

                    self.game.level.level[x, y] = block
                    if len(message) > 3:
                        self.game.level.attributes[x, y] = eval(message[3])

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


class Level:
    def __init__(self, game: Game):
        self.game = game

        self.level: {(int, int): str}
        self.level = {}

        self.attributes: {(int, int): dict}
        self.attributes = {}

        self.__prevFrameAttributes: {(int, int): dict}
        self.__prevFrameAttributes = {}

        self.__prevFrameBlocks: {(int, int): str}
        self.__prevFrameBlocks = {}

        for x in range(MAP_W):
            for y in range(MAP_H):
                self.level[x, y] = 'grass'
                self.attributes[x, y] = {}

        self.__updateMapBuffer()

        self.__generated = False

    def __updateMapBuffer(self):
        for x in range(MAP_W):
            for y in range(MAP_H):
                try:
                    self.__prevFrameAttributes[x, y] = self.attributes[x, y].copy()
                    self.__prevFrameBlocks[x, y] = self.level[x, y]
                except:
                    self.__prevFrameAttributes[x, y] = {}
                    self.__prevFrameBlocks[x, y] = 'grass'

    def acceptAllUpdates(self):
        for x in range(MAP_W):
            for y in range(MAP_H):
                if self.__prevFrameBlocks[x, y] != self.level[x, y] or \
                   self.__prevFrameAttributes[x, y] != self.attributes[x, y]:
                    # print("Changed block at", x, y, "old:", self.__prevFrameBlocks[x, y], "new:", self.level[x, y],
                    #       '\nold attributes:', self.__prevFrameAttributes[x, y], 'new:', self.attributes[x, y], '\n')
                    self.game.changedBlocks.append([x, y])
        self.__updateMapBuffer()

    def declineAllUpdates(self):
        pass

    def updateLevel(self):
        # Updating wires
        wiresUpdated = 0
        for x in range(MAP_W):
            for y in range(MAP_H):
                if 'wire' in self.level[x, y]:
                    variant = ['f', 'f', 'f', 'f']
                    if x > 0 and 'electrical' in self.attributes[x-1, y] and self.attributes[x, y]['electrical']:
                        variant[2] = 't'
                    if x < MAP_W - 1 and 'electrical' in self.attributes[x+1, y] and self.attributes[x, y]['electrical']:
                        variant[3] = 't'
                    if y > 0 and 'electrical' in self.attributes[x, y-1] and self.attributes[x, y]['electrical']:
                        variant[0] = 't'
                    if y < MAP_H - 1 and 'electrical' in self.attributes[x, y+1] and self.attributes[x, y]['electrical']:
                        variant[1] = 't'

                    variant = "".join(i for i in variant)

                    if variant != self.attributes[x, y]['rotation']:
                        a = self.attributes[x, y]
                        a['rotation'] = variant
                        self.replaceBlockAttributes(x, y, a)
                        wiresUpdated += 1

        # if wiresUpdated > 0:
        #     print("Updated wires:", wiresUpdated)

        positions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        for x in range(MAP_W):
            for y in range(MAP_H):
                if 'switch' in self.level[x, y] and self.attributes[x, y]['on']:

                    for pos in positions:
                        x1, y1 = x + pos[0], y + pos[1]
                        if 0 <= x1 <= MAP_W - 1 and 0 <= y1 <= MAP_H - 1:
                            if 'wire' in self.level[x1, y1] or 'lamp' in self.level[x1, y1] or 'computer' in self.level[x1, y1]:
                                if not 'energy_source' in self.attributes[x1, y1] \
                                   and self.attributes[x1, y1]['energy'] == 0:
                                    self.setBlockAttribute(x1, y1, 'energy_source', (x, y))
                                    self.setBlockAttribute(x1, y1, 'energy', 1)

                elif 'wire' in self.level[x, y]:
                    if 'energy' in self.attributes[x, y] and 'energy_source' in self.attributes[x, y]:
                        if self.attributes[x, y]['energy'] > 0 and \
                           'energy' in self.attributes[self.attributes[x, y]['energy_source']] and \
                           self.attributes[self.attributes[x, y]['energy_source']]['energy'] > 0:

                            for pos in positions:
                                x1, y1 = x + pos[0], y + pos[1]
                                if 0 <= x1 <= MAP_W - 1 and 0 <= y1 <= MAP_H - 1:
                                    if 'wire' in self.level[x1, y1] or 'lamp' in self.level[x1, y1] or 'computer' in self.level[x1, y1]:
                                        if not 'energy_source' in self.attributes[x1, y1] \
                                           and self.attributes[x1, y1]['energy'] == 0:
                                            self.setBlockAttribute(x1, y1, 'energy_source', (x, y))
                                            self.setBlockAttribute(x1, y1, 'energy', 1)
                        else:
                            self.setBlockAttribute(x, y, 'energy', 0)
                            self.removeBlockAttribute(x, y, 'energy_source')
                    else:
                        self.setBlockAttribute(x,y, 'energy', 0)
                        self.removeBlockAttribute(x,y, 'energy_source')
                elif 'lamp' in self.level[x, y]:
                    if 'energy_source' in self.attributes[x, y] and 'energy' in self.attributes[x, y] and \
                       'energy' in self.attributes[self.attributes[x, y]['energy_source']]:
                        if self.attributes[x, y]['energy'] <= 0 or \
                           self.attributes[self.attributes[x, y]['energy_source']]['energy'] <= 0:
                            self.setBlockAttribute(x,y, 'energy', 0)
                            self.removeBlockAttribute(x,y, 'energy_source')
                    else:
                        self.setBlockAttribute(x, y, 'energy', 0)
                        self.removeBlockAttribute(x, y, 'energy_source')

        computer: Computer
        for computer in self.game.computers:
            if not computer.on and 'energy' in self.attributes[computer.x, computer.y] and \
               self.attributes[computer.x, computer.y]['energy'] > 0:
                computer.startup()

        self.acceptAllUpdates()

    def setLevel(self, level: dict):
        # Checking if there's any missing blocks.
        lvl = {}
        for x in range(MAP_W):
            for y in range(MAP_H):
                if not (x, y) in level:
                    lvl[x, y] = 'grass'
                else:
                    lvl[x, y] = level[x, y]
        self.level = lvl

    def setBlock(self, x: int, y: int, block: str):
        self.level[x, y] = block

    def setBlockAttribute(self, x: int, y: int, key: str, val: any):
        self.attributes[x, y][key] = val

    def removeBlockAttribute(self, x: int, y: int, key: str):
        if key in self.attributes[x, y]: del self.attributes[x, y][key]

    def replaceBlockAttributes(self, x: int, y: int, attribute: dict):
        self.attributes[x, y] = attribute

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
        self.attributes[x, y] = {}

        if self.__generated:
            self.game.changedBlocks.append([x, y])

    def generateLevel(self):
        gen_start = time.time()

        for x in range(MAP_W):
            for y in range(MAP_H):
                self.generateBlock(x, y)
        self.level[0, 0] = 'grass'

        gen_end = time.time()

        self.__generated = True

        # print(self.level)

        print("Level has been successfully generated in", gen_end - gen_start, "seconds")

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
                ['planks', 50, 30],
                ['wall', 15, 100],
                ['tree', 15, 100]
            ]

        m = 'chest'
        for item in range(random.randint(1, maxItems // 2) * 2):
            created = False

            while not created:
                i = random.randint(0, len(lootTable) - 1)
                item = lootTable[i]

                if random.randint(0, 100000) / 1000 <= item[2]:
                    itemName = item[0]
                    itemCount = random.randint(1, item[1])

                    m += ',' + itemName + '=' + str(itemCount)

                    created = True

        # print(m)

        self.level[x, y] = m
        if self.__generated:
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
        print(message)
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
                    # Structure of request: join_game/gameid;
                    gameid = msg[0]
                    # Finding battle with exact game id
                    for game in main.games:
                        if game.gameID == gameid:
                            game.addPlayer(sock, addr)
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

        if self.config.get('loadGames'):
            for filename in os.listdir('savedGames/'):
                gameid = 'Undefined'
                try:
                    f = open('savedGames/' + filename, 'r', encoding='utf-8')
                    c = f.read()
                    f.close()

                    name, gameid, _ = filename.split('.')

                    g = Game(name, gameid, level=c)

                    self.games.append(g)
                except Exception as e:
                    print("Failed to load saved level for game", gameid, ": ", e)

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
