from bluetooth import BLE
from time import sleep_ms, ticks_ms
from ZIP96Pico import *
from KitronikPicoWBluetooth import BLEPeripheral
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

# Setup peripheral
peripheral = BLEPeripheral(BLE())

# Wait for central to connect
while not peripheral.isConnected():
    sleep_ms(100)

screen.fill((100, 100, 0))
screen.show()

# Set write callback, to process a write event
def writeCallback(value):
    global received
    received = bytes(value)

received = None
peripheral.writeCallback = writeCallback
start = 0

# Set read callback, to send start command
def readCallback():
    peripheral.readCallback = None
    return "START"

peripheral.readCallback = readCallback

# Wait for central to read start command
while peripheral.readCallback is not None:
    sleep_ms(50)

screen.fill((0, 100, 0))
screen.show()

# Loop while central still connected
while peripheral.isConnected():
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
        # Notify central of updated position using service charactistic
        peripheral.notify(bytes([playerX, playerY, tone]))
        gamer.Buzzer.playTone_Length(tone * 100, 50)
    
    screen.fill(screen.BLACK)
    screen.setLEDMatrix(playerX, playerY, screen.WHITE)
    screen.show()

    # Process received write value from central to service charactistic
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
            peripheral.notify(bytes([config[2]]))
    
    sleep_ms(125)
