from bluetooth import BLE
from time import sleep_ms, ticks_ms
from ZIP96Pico import *
from KitronikPicoWBluetooth import BLECentral
from random import randint

# Setup the gamer and screen variables
gamer = KitronikZIP96()
screen = gamer.Screen
screenWidth = 12
screenHeight = 8

# Set brightness and clear screen
screen.setBrightness(10)
screen.fill((100, 0, 0))
screen.show()

# Setup game variables
playerX = 0
playerY = 0

# Setup central
central = BLECentral(BLE())
notFound = False

# Scan for peripheral
def onScan(addrType, addr, name):
    global notFound
    if addrType is not None:
        print("Found sensor:", addrType, addr, name)
        central.connect()
    else:
        notFound = True
        print("No sensor found.")

central.scan(callback=onScan)

# Wait for connection to peripheral
while not central.isConnected():
    sleep_ms(100)
    if notFound:
        screen.fill((255, 0, 0))
        screen.show()

screen.fill((100, 100, 0))
screen.show()

# Set notify callback, to process a notify event
def notifyCallback(value):
    global received
    received = bytes(value)

received = None
central.notifyCallback = notifyCallback
start = 0

# Set read callback, to process start command
def readCallback(value):
    val = bytes(value).decode("utf-8")
    if val == "START":
        central.readCallback = None

central.readCallback = readCallback
central.read()

# Wait for start command from peripheral
while central.readCallback is not None:
    sleep_ms(50)

screen.fill((0, 100, 0))
screen.show()

# Loop while still connected to peripheral
while central.isConnected():
    if gamer.Up.pressed():
        if playerY > 0:
            change = True
            playerY -= 1
    if gamer.Down.pressed():
        if playerY < screenHeight - 1:
            change = True
            playerY += 1
    if gamer.Left.pressed():
        if playerX > 0:
            change = True
            playerX -= 1
    if gamer.Right.pressed():
        if playerX < screenWidth - 1:
            change = True
            playerX += 1
    if gamer.A.pressed():
        start = ticks_ms()
        tone = randint(3, 30)
        # Write position to peripheral service charactistic
        central.write(bytes([playerX, playerY, tone]))
        gamer.Buzzer.playTone_Length(tone * 100, 50)
    
    screen.fill(screen.BLACK)
    screen.setLEDMatrix(playerX, playerY, screen.WHITE)
    screen.show()

    # Process received value from peripheral service charactistic
    if received is not None:
        config = received
        received = None
        
        if len(config) == 1:
            end = ticks_ms()
            print("Full time (ms):", end - start)
            print("Half time (ms):", (end - start) / 2)
        else:
            screen.setLEDMatrix(config[0], config[1], screen.CYAN)
            screen.show()
            gamer.Buzzer.playTone_Length(config[2] * 100, 50)
            central.write(bytes([config[2]]))
    
    sleep_ms(125)
