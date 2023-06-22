# Kitronik Pico W Bluetooth MicroPython
 
This repo contains a Bluetooth MicroPython library file for the [Raspberry Pi Pico W](https://kitronik.co.uk/5345).

To use the library you can save the `KitronikPicoWBluetooth.py` file onto the Pico W so it can be imported.

Also in this repo are some examples of how to use the library in the `Example Code` folder.

# How to use the Bluetooth library for Pico W
Below is a small section explaining how to use each function from the Pico W Bluetooth library.

The Peripheral:
- [Setup the Peripheral](https://github.com/KitronikLtd/Kitronik-Pico-W-Bluetooth-MicroPython#setup-the-peripheral)
- [Wait for Connection on the Peripheral](https://github.com/KitronikLtd/Kitronik-Pico-W-Bluetooth-MicroPython#wait-for-connection-on-the-peripheral)
- [Handle Read Requests on the Peripheral](https://github.com/KitronikLtd/Kitronik-Pico-W-Bluetooth-MicroPython#handle-read-requests-on-the-peripheral)
- [Handle Write Requests on the Peripheral](https://github.com/KitronikLtd/Kitronik-Pico-W-Bluetooth-MicroPython#handle-write-requests-on-the-peripheral)
- [Notify Centrals of Updated Values from the Peripheral](https://github.com/KitronikLtd/Kitronik-Pico-W-Bluetooth-MicroPython#notify-centrals-of-updated-values-from-the-peripheral)
- [Indicate to Centrals of Updated Values from the Peripheral](https://github.com/KitronikLtd/Kitronik-Pico-W-Bluetooth-MicroPython#indicate-to-centrals-of-updated-values-from-the-peripheral)

The Central:
- [Setup the Central](https://github.com/KitronikLtd/Kitronik-Pico-W-Bluetooth-MicroPython#setup-the-central)
- [Scan and Connect to Peripheral on the Central](https://github.com/KitronikLtd/Kitronik-Pico-W-Bluetooth-MicroPython#scan-and-connect-to-peripheral-on-the-central)
- [Read from Peripheral on the Central](https://github.com/KitronikLtd/Kitronik-Pico-W-Bluetooth-MicroPython#read-from-peripheral-on-the-central)
- [Write to Peripheral from the Central](https://github.com/KitronikLtd/Kitronik-Pico-W-Bluetooth-MicroPython#write-to-peripheral-from-the-central)
- [Handle Notify Requests on the Central](https://github.com/KitronikLtd/Kitronik-Pico-W-Bluetooth-MicroPython#handle-notify-requests-on-the-central)
- [Handle Indicate Requests on the Central](https://github.com/KitronikLtd/Kitronik-Pico-W-Bluetooth-MicroPython#handle-indicate-requests-on-the-central)
- [Disconnect from Peripheral on the Central](https://github.com/KitronikLtd/Kitronik-Pico-W-Bluetooth-MicroPython#disconnect-from-peripheral-on-the-central)
<br/>

## The Peripheral
### Setup the Peripheral
To use the Bluetooth library for a Pico W peripheral we first need to import the library and setup our peripheral device. To initialise our peripheral we can use the `BLEPeripheral` class which will take a `BLE` object as its input. Using the BLE object it will setup and advertise the peripheral and its GATT service which other devices can scan for.
``` python
from KitronikPicoWBluetooth import BLEPeripheral
from bluetooth import BLE
# Setup peripheral
peripheral = BLEPeripheral(BLE())
```
<br/>

### Wait for Connection on the Peripheral
To wait for a central to connect to the peripheral we can use the `isConnected` function which returns when a central is connected.
``` python
# Wait for central to connect
while not peripheral.isConnected():
    sleep_ms(100)
```
<br/>

### Handle Read Requests on the Peripheral
To make the service characteristic value more flexible, when the characteristic is read by a central device the Bluetooth library sends it the return value from the `readCallback`. To set the characteristic value we have to set the `readCallback` to our own function which returns the value we want to send the central device. In the example below, when the central device reads from the peripheral it will return the numbers 31, 32 as an array of bytes
``` python
# Read callback function
def twoBytes():
    return bytes([31, 32])

# Set peripheral readCallback to the twoBytes function
peripheral.readCallback = twoBytes
```
<br/>

### Handle Write Requests on the Peripheral
To again make the service characteristic value more flexible, when a central device writes to the characteristic the Bluetooth library passes the write value to the `writeCallback`. To retrieve this write value we have to set the `writeCallback` to our own function which accepts the value written by the central as an input. In the example below, when the central device writes to the peripheral it will print the array of bytes that were sent.
``` python
# Write callback function
def printBytes(writeValue):
    print(bytes(writeValue))

# Set peripheral writeCallback to the printBytes function
peripheral.writeCallback = printBytes
```
<br/>

### Notify Centrals of Updated Values from the Peripheral
To notify the connected centrals of an updated service characteristic value we can use the `notify` function. This function takes one input for the value we want to send to the centrals. The `notify` function is different to the peripheral `read` functionality as the `read` functionality is caused by the central requesting the characteristic's value. The `notify` function is instead telling the centrals of an updated value, rather than waiting for them to request it. In the example below, the peripheral device notifies the connected centrals of the updated value being the numbers 31, 32 as an array of bytes.
``` python
# Notify the centrals of an updated value
peripheral.notify(bytes([31, 32]))
```
<br/>

### Indicate to Centrals of Updated Values from the Peripheral
To indicate to the connected centrals of an updated service characteristic value we can use the `indicate` function. This function takes one input for the value we want to send to the centrals. The `indicate` function is mostly the same as the `notify` function but instead requires the connected centrals to send an acknowledgement when they have received the updated value. In the example below, the peripheral device notifies the connected centrals of the updated value being the numbers 31, 32 as an array of bytes, and the centrals will respond to say they have received the value.
``` python
# Indicate to the centrals of an updated value
peripheral.indicate(bytes([31, 32]))
```
<br/>

## The Central
### Setup the Central
To use the Bluetooth library for a Pico W central we first need to import the library and setup our central device. To initialise our central we can use the `BLECentral` class which will take a `BLE` object as its input. Using the BLE object it will setup the central ready to scan for a peripheral.
``` python
from KitronikPicoWBluetooth import BLECentral
from bluetooth import BLE
# Setup central
central = BLECentral(BLE())
```
<br/>

### Scan and Connect to Peripheral on the Central
To connect to a peripheral device we first need to run a scan to see if there is one available to connect to. To run a scan we use the `scan` function which takes one inputs for the end of scan callback. The scan callback takes three inputs for the address type, address and name of the found peripheral. When the peripheral has not been found then all of these parameters are set to `None`.

In the example below, we have created a global variable called `notFound`. Inside the `onScan` callback function we set `notFound` to `True` when the callback's parameters are `None`. When the callback's parameters are not `None` then we have found the peripheral. Once we know there is a peripheral available to connect to, we can connect to it using the `connect` function.

After we have called the `scan` function we want to loop until the central has connected to the peripheral device. To do this we'll use the `isConnected` function and loop while the central is not connected. Inside the loop we also want to check whether the `notFound` variable is `True`. When `notFound` is `True` then we haven't found the peripheral and so haven't been able to connect to it.
``` python
# End of scan callback function
def onScan(addrType, addr, name):
    global notFound
    if addrType is not None:
        # Found the peripheral, so connect to it
        central.connect()
    else:
        # Not found the peripheral
        notFound = True

# Flag for whether the peripheral has been found
notFound = False
# Scan for peripheral
central.scan(onScan)

# Wait for connection to peripheral
while not central.isConnected():
    sleep_ms(100)
    if notFound:
        # When peripheral has not been found, exit the program
        import sys
        sys.exit()
```
<br/>

### Read from Peripheral on the Central
To read the service characteristic value from the peripheral we first have to set the `readCallback`. To retrieve the read value we have to set the `readCallback` to our own function which accepts the value read from the peripheral as an input. In the example below, when the central device reads from the peripheral it will print the array of bytes that were sent. After setting the `readCallback` we can call the `read` function to perform the read from the peripheral.
``` python
# Read callback function
def printBytes(readValue):
    print(bytes(readValue))

# Set central readCallback to the printBytes function
central.readCallback = printBytes
# Read from the peripheral
central.read()
```
<br/>

### Write to Peripheral from the Central
To write to the peripheral's service characteristic value we can use the `write` function. This function takes one input for the value we want to send to the peripheral. In the example below, the central device writes to the peripheral the updated value being the numbers 31, 32 as an array of bytes.
``` python
# Write to the peripheral an updated value
central.write(bytes([31, 32]))
```
<br/>

### Handle Notify Requests on the Central
To handle a notify request from the peripheral we need to set the `notifyCallback`. When the connected peripheral notifies the central of an updated value we can retrieve that value using the `notifyCallback` which we will set to our own function. In the example below, when the peripheral device notifies the central it will print the array of bytes that were sent.
``` python
# Notify callback function
def printBytes(readValue):
    print(bytes(readValue))

# Set central notifyCallback to the printBytes function
central.notifyCallback = printBytes
```
<br/>

### Handle Indicate Requests on the Central
To handle an indicate request from the peripheral we need to set the `indicateCallback`. When the connected peripheral indicates to the central of an updated value we can retrieve that value using the `indicateCallback` which we will set to our own function. The `indicate` function is mostly the same as the `notify` function but instead requires the central to send an acknowledgement when they have received the updated value from the peripheral. In the example below, when the peripheral device indicates to the central it will print the array of bytes that were sent.
``` python
# Read callback function
def printBytes(readValue):
    print(bytes(readValue))

# Set central indicateCallback to the printBytes function
central.indicateCallback = printBytes
```
<br/>

### Disconnect from Peripheral on the Central
To disconnect from a peripheral we can use the `disconnect` function. The `disconnect` function will tell the peripheral it is disconnecting, and reset the central back to its initial state with all its callbacks and handlers set to `None`.
``` python
# Disconnect from the peripheral
central.disconnect()
```
<br/>
