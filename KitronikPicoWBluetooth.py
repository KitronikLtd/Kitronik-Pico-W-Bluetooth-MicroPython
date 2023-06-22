'''
This code was written and modified by Kitronik Ltd.

Large sections of the code is modified code from the MicroPython project examples.

Thank you to the MicroPython project as this library wouldn't have been
possible without them.

https://github.com/micropython/micropython/blob/master/LICENSE
'''

import bluetooth
from micropython import const
from struct import pack, unpack

'''
Bluetooth Low Energy - Peripheral Device
'''

# BLE Peripheral Interrupt Event Numbers
_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)
_IRQ_GATTS_READ_REQUEST = const(4)
_IRQ_GATTS_INDICATE_DONE = const(20)

# Our BLE GATT Service
MES_SERVICE_UUID = bluetooth.UUID(0x93AF)
MES_CHARACTERISTIC_UUID = (bluetooth.UUID(0x5404), bluetooth.FLAG_WRITE | bluetooth.FLAG_WRITE_NO_RESPONSE | bluetooth.FLAG_READ | bluetooth.FLAG_NOTIFY | bluetooth.FLAG_INDICATE,)
MES_CONTROLLER_SERVICE = (MES_SERVICE_UUID, (MES_CHARACTERISTIC_UUID,),)
ADVERTISE_APPEARANCE_GAMEPAD = const(0x03C4)

# Advertising payloads are repeated packets of the following form:
#   1 byte data length (N + 1)
#   1 byte type (see constants below)
#   N bytes type-specific data
_ADV_TYPE_FLAGS = const(0x01)
_ADV_TYPE_NAME = const(0x09)
_ADV_TYPE_UUID16_COMPLETE = const(0x3)
_ADV_TYPE_UUID32_COMPLETE = const(0x5)
_ADV_TYPE_UUID128_COMPLETE = const(0x7)
_ADV_TYPE_APPEARANCE = const(0x19)

# Generate a payload to be passed to gap_advertise(adv_data=...).
def advertising_payload(limited_disc=False, br_edr=False, name=None, services=None, appearance=0):
    payload = bytearray()

    def _append(adv_type, value):
        nonlocal payload
        payload += pack("BB", len(value) + 1, adv_type) + value

    _append(
        _ADV_TYPE_FLAGS,
        pack("B", (0x01 if limited_disc else 0x02) + (0x18 if br_edr else 0x04)),
    )

    if name:
        _append(_ADV_TYPE_NAME, name)

    if services:
        for uuid in services:
            b = bytes(uuid)
            if len(b) == 2:
                _append(_ADV_TYPE_UUID16_COMPLETE, b)
            elif len(b) == 4:
                _append(_ADV_TYPE_UUID32_COMPLETE, b)
            elif len(b) == 16:
                _append(_ADV_TYPE_UUID128_COMPLETE, b)

    # See org.bluetooth.characteristic.gap.appearance.xml
    if appearance:
        _append(_ADV_TYPE_APPEARANCE, pack("<h", appearance))

    return payload

class BLEPeripheral:
    # Initialise BLE and advertise our service
    def __init__(self, ble, name="mpy-peripheral"):
        self._ble = ble
        self._ble.active(True)
        self._ble.irq(self._irq)
        ((self._handle,),) = self._ble.gatts_register_services((MES_CONTROLLER_SERVICE,))
        self._connections = set()
        self._payload = advertising_payload(name=name, services=[MES_SERVICE_UUID], appearance=ADVERTISE_APPEARANCE_GAMEPAD)
        self._advertise()
        
        # Connected device callbacks
        self.readCallback = None
        self.writeCallback = None
    
    # Advertise our service so the central device can scan for it
    def _advertise(self, interval_us=500000):
        self._ble.gap_advertise(interval_us, adv_data=self._payload)
    
    # BLE event interrupt handler
    def _irq(self, event, data):
        if event == _IRQ_CENTRAL_CONNECT:
            # A central has connected to this peripheral
            conn_handle, addr_type, addr = data
            self._connections.add(conn_handle)
            # Increase the buffer size to 64 bytes
            self._ble.gatts_set_buffer(self._handle, 64)
            
        elif event == _IRQ_CENTRAL_DISCONNECT:
            # A central has disconnected from this peripheral
            conn_handle, addr_type, addr = data
            self._connections.remove(conn_handle)
            
            # Start advertising again to allow a new connection
            self._advertise()
            
        elif event == _IRQ_GATTS_WRITE:
            # A client has written to this characteristic or descriptor
            conn_handle, attr_handle = data
            value = self._ble.gatts_read(attr_handle)
            
            if self.writeCallback is not None:
                # Process the value written inside writeCallback
                self.writeCallback(value)
            
        elif event == _IRQ_GATTS_READ_REQUEST:
            # A client has issued a read
            conn_handle, attr_handle = data
            
            if self.readCallback is not None:
                # Write the value returned by readCallback, ready for a central to read
                self._ble.gatts_write(attr_handle, self.readCallback())
            
        elif event == _IRQ_GATTS_INDICATE_DONE:
            # A client has acknowledged the indication
            conn_handle, value_handle, status = data
    
    # Returns true if we've successfully connected a device
    def isConnected(self):
        return len(self._connections) > 0
    
    # Notify centrals of new characteristic value
    def notify(self, value):
        # Write the value, ready for a central to read
        self._ble.gatts_write(self._handle, value)
        
        for conn_handle in self._connections:
            # Notify connected centrals, no acknowledgement from central
            self._ble.gatts_notify(conn_handle, self._handle)
    
    # Indicate to centrals of new characteristic value
    def indicate(self, value):
        # Write the value, ready for a central to read
        self._ble.gatts_write(self._handle, value)
        
        for conn_handle in self._connections:
            # Indicate connected centrals, receive acknowledgement from central
            self._ble.gatts_indicate(conn_handle, self._handle)

'''
Bluetooth Low Energy - Central Device
'''

# BLE Central Interrupt Event Numbers
_IRQ_SCAN_RESULT = const(5)
_IRQ_SCAN_DONE = const(6)
_IRQ_PERIPHERAL_CONNECT = const(7)
_IRQ_PERIPHERAL_DISCONNECT = const(8)
_IRQ_GATTC_SERVICE_RESULT = const(9)
_IRQ_GATTC_SERVICE_DONE = const(10)
_IRQ_GATTC_CHARACTERISTIC_RESULT = const(11)
_IRQ_GATTC_CHARACTERISTIC_DONE = const(12)
_IRQ_GATTC_READ_RESULT = const(15)
_IRQ_GATTC_READ_DONE = const(16)
_IRQ_GATTC_WRITE_DONE = const(17)
_IRQ_GATTC_NOTIFY = const(18)
_IRQ_GATTC_INDICATE = const(19)

# Advertise Types
_ADV_IND = const(0x00)
_ADV_DIRECT_IND = const(0x01)

# Decode Peripheral Name from Advertise Payload
def decode_name(payload):
    n = decode_field(payload, _ADV_TYPE_NAME)
    return str(n[0], "utf-8") if n else ""

# Decode Peripheral Service Characteristics from Advertise Payload
def decode_field(payload, adv_type):
    i = 0
    result = []
    while i + 1 < len(payload):
        if payload[i + 1] == adv_type:
            result.append(payload[i + 2 : i + payload[i] + 1])
        i += 1 + payload[i]
    return result

# Decode Peripheral Service from Advertise Payload
def decode_services(payload):
    services = []
    for u in decode_field(payload, _ADV_TYPE_UUID16_COMPLETE):
        services.append(bluetooth.UUID(unpack("<h", u)[0]))
    for u in decode_field(payload, _ADV_TYPE_UUID32_COMPLETE):
        services.append(bluetooth.UUID(unpack("<d", u)[0]))
    for u in decode_field(payload, _ADV_TYPE_UUID128_COMPLETE):
        services.append(bluetooth.UUID(u))
    return services

class BLECentral:
    # Initialise BLE
    def __init__(self, ble):
        self._ble = ble
        self._ble.active(True)
        self._ble.irq(self._irq)
        self._reset()

    # Reset BLE connection, handlers and callbacks
    def _reset(self):
        # Cached name and address from a successful scan
        self._name = None
        self._addr_type = None
        self._addr = None

        # Connected device handles
        self._conn_handle = None
        self._start_handle = None
        self._end_handle = None
        self._value_handle = None

        # Callbacks for completion of various operations
        self._scan_callback = None
        self._conn_callback = None
        self.readCallback = None
        self.notifyCallback = None
        self.indicateCallback = None

    # BLE event interrupt handler
    def _irq(self, event, data):
        if event == _IRQ_SCAN_RESULT:
            # A single scan result
            addr_type, addr, adv_type, rssi, adv_data = data
            
            if adv_type in (_ADV_IND, _ADV_DIRECT_IND) and MES_SERVICE_UUID in decode_services(adv_data):
                # Found a potential device, remember it and stop scanning.
                self._addr_type = addr_type
                self._addr = bytes(addr)
                self._name = decode_name(adv_data) or "?"
                self._ble.gap_scan(None)

        elif event == _IRQ_SCAN_DONE:
            # Scan duration finished or manually stopped
            if self._scan_callback:
                if self._addr:
                    # Found a device during the scan (and the scan was explicitly stopped).
                    self._scan_callback(self._addr_type, self._addr, self._name)
                    self._scan_callback = None
                else:
                    # Scan timed out.
                    self._scan_callback(None, None, None)

        elif event == _IRQ_PERIPHERAL_CONNECT:
            # A successful gap_connect()
            conn_handle, addr_type, addr = data
            
            if addr_type == self._addr_type and addr == self._addr:
                self._conn_handle = conn_handle
                self._ble.gattc_discover_services(self._conn_handle)

        elif event == _IRQ_PERIPHERAL_DISCONNECT:
            # Connected peripheral has disconnected
            conn_handle, addr_type, addr = data
            
            if conn_handle == self._conn_handle:
                # If it was initiated by us, it'll already be reset.
                self._reset()

        elif event == _IRQ_GATTC_SERVICE_RESULT:
            # Called for each service found by gattc_discover_services()
            conn_handle, start_handle, end_handle, uuid = data
            
            if conn_handle == self._conn_handle and uuid == MES_SERVICE_UUID:
                self._start_handle, self._end_handle = start_handle, end_handle

        elif event == _IRQ_GATTC_SERVICE_DONE:
            # Called once service discovery is complete
            conn_handle, status = data
            
            if self._start_handle and self._end_handle:
                self._ble.gattc_discover_characteristics(self._conn_handle, self._start_handle, self._end_handle)
            else:
                raise Exception("Failed to find Peripheral Device.")

        elif event == _IRQ_GATTC_CHARACTERISTIC_RESULT:
            # Called for each characteristic found by gattc_discover_services()
            conn_handle, end_handle, value_handle, properties, uuid = data
            
            if conn_handle == self._conn_handle and uuid == MES_CHARACTERISTIC_UUID[0]:
                self._value_handle = value_handle

        elif event == _IRQ_GATTC_CHARACTERISTIC_DONE:
            # Called once service characteristic discovery is complete
            conn_handle, status = data
            
            if self._value_handle:
                # We've finished connecting and discovering device, fire the connect callback.
                if self._conn_callback:
                    self._conn_callback()
            else:
                raise Exception("Failed to find Peripheral Characteristic.")

        elif event == _IRQ_GATTC_READ_RESULT:
            # A gattc_read() has completed
            conn_handle, value_handle, char_data = data
            
            if conn_handle == self._conn_handle and value_handle == self._value_handle:
                if self.readCallback:
                    # Process the value read inside readCallback
                    self.readCallback(char_data)

        elif event == _IRQ_GATTC_READ_DONE:
            # A gattc_read() has completed
            conn_handle, value_handle, status = data
        
        elif event == _IRQ_GATTC_WRITE_DONE:
            # A gattc_write() has completed
            conn_handle, value_handle, status = data

        elif event == _IRQ_GATTC_NOTIFY:
            # A server has sent a notify request
            conn_handle, value_handle, notify_data = data
            
            if conn_handle == self._conn_handle and value_handle == self._value_handle:
                if self.notifyCallback:
                    # Process the value read inside notifyCallback
                    self.notifyCallback(notify_data)
        
        elif event == _IRQ_GATTC_INDICATE:
            # A server has sent an indicate request
            conn_handle, value_handle, notify_data = data
            
            if conn_handle == self._conn_handle and value_handle == self._value_handle:
                if self.indicateCallback:
                    # Process the value read inside indicateCallback
                    self.indicateCallback(notify_data)

    # Find a device advertising the environmental sensor service
    def scan(self, callback):
        self._addr_type = None
        self._addr = None
        self._scan_callback = callback
        self._ble.gap_scan(2000, 30000, 30000)
    
    # Connect to the specified device (otherwise use cached address from a scan)
    def connect(self, addr_type=None, addr=None, callback=None):
        self._addr_type = addr_type or self._addr_type
        self._addr = addr or self._addr
        self._conn_callback = callback
        
        if self._addr_type is None or self._addr is None:
            return False
        
        self._ble.gap_connect(self._addr_type, self._addr)
        return True
    
    # Disconnect from current device
    def disconnect(self):
        if self._conn_handle is None:
            return
        
        self._ble.gap_disconnect(self._conn_handle)
        self._reset()
    
    # Returns true if we've successfully connected and discovered characteristics
    def isConnected(self):
        return self._conn_handle is not None and self._value_handle is not None

    # Issues an (asynchronous) read, will invoke callback with data
    def read(self):
        if not self.isConnected():
            return
        
        self._ble.gattc_read(self._conn_handle, self._value_handle)
    
    # Issues an (asynchronous) write, optionally receive acknowledgement from peripheral
    def write(self, data, response=False):
        if not self.isConnected():
            return
        
        self._ble.gattc_write(self._conn_handle, self._value_handle, data, 1 if response else 0)
