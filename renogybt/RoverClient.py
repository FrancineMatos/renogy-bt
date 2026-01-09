import logging
from .BaseClient import BaseClient
from .Utils import bytes_to_int, parse_temperature

# Read and parse BT-1/BT-2 type bluetooth modules connected to Renogy Rover/Wanderer/Adventurer
FUNCTION = {
    3: "READ",
    6: "WRITE"
}

CHARGING_STATE = {
    0: 'deactivated',
    1: 'activated',
    2: 'mppt',
    3: 'equalizing',
    4: 'boost',
    5: 'floating',
    6: 'current limiting'
}

LOAD_STATE = {
  0: 'off',
  1: 'on'
}

BATTERY_TYPE = {
    1: 'open',
    2: 'sealed',
    3: 'gel',
    4: 'lithium',
    5: 'custom'
}

def add_field(target, name, value, device_class="", unit="", icon=""):
    target[name] = {
        "value": value,
        "device_class": device_class,
        "unit_of_measurement": unit,
        "icon": icon
    }
    

class RoverClient(BaseClient):
    def __init__(self, config, on_data_callback=None, on_error_callback=None):
        super().__init__(config)
        self.execution_count = 0   # 👈 contador real
        self.on_data_callback = on_data_callback
        self.on_error_callback = on_error_callback
        self.data = {}
        self.sections = [
            {'register': 12, 'words': 8, 'parser': self.parse_device_info},
            {'register': 26, 'words': 1, 'parser': self.parse_device_address},
            {'register': 256, 'words': 34, 'parser': self.parse_chargin_info},
            {'register': 57348, 'words': 1, 'parser': self.parse_battery_type}
        ]
        self.set_load_params = {'function': 6, 'register': 266}

    async def on_data_received(self, response):
        operation = bytes_to_int(response, 1, 1)
        if operation == 6: # write operation
            self.parse_set_load_response(response)
            self.on_write_operation_complete()
            self.data = {}
        else:
            # read is handled in base class
            await super().on_data_received(response)

    def on_write_operation_complete(self):
        logging.info("on_write_operation_complete")
        if self.on_data_callback is not None:
            self.on_data_callback(self, self.data)

    def set_load(self, value = 0):
        logging.info("setting load {}".format(value))
        request = self.create_generic_read_request(self.device_id, self.set_load_params["function"], self.set_load_params["register"], value)
        self.ble_manager.characteristic_write_value(request)

    def parse_device_info(self, bs):
        data = {}
        data['function'] = FUNCTION.get(bytes_to_int(bs, 1, 1))
        data['model'] = (bs[3:19]).decode('utf-8').strip()
        self.data.update(data)

    def parse_device_address(self, bs):
        data = {}
        data['device_id'] = bytes_to_int(bs, 4, 1)
        self.data.update(data)

    def parse_chargin_info(self, bs):
        self.execution_count += 1
        temp_unit = self.config['data']['temperature_unit']
        device_info = {}
    
        add = lambda *args, **kw: add_field(device_info, *args, **kw)
    
        add(
            "function",
            FUNCTION.get(bytes_to_int(bs, 1, 1)),
            icon="mdi:desktop-classic"
        )
    
        add(
            "battery_percentage",
            bytes_to_int(bs, 3, 2),
            "battery", "%", "mdi:battery-charging"
        )
    
        add(
            "battery_voltage",
            bytes_to_int(bs, 5, 2, scale=0.1),
            "voltage", "V", "mdi:sine-wave"
        )
    
        add(
            "battery_current",
            bytes_to_int(bs, 7, 2, scale=0.01),
            "current", "A", "mdi:current-ac"
        )
    
        add(
            "battery_temperature",
            parse_temperature(bytes_to_int(bs, 10, 1), temp_unit),
            "temperature", temp_unit, "mdi:temperature-celsius"
        )
    
        add(
            "controller_temperature",
            parse_temperature(bytes_to_int(bs, 9, 1), temp_unit),
            "temperature", temp_unit, "mdi:temperature-celsius"
        )
    
        add(
            "load_status",
            LOAD_STATE.get(bytes_to_int(bs, 67, 1) >> 7),
            icon="mdi:power-plug-battery-outline"
        )
    
        add(
            "load_voltage",
            bytes_to_int(bs, 11, 2, scale=0.1),
            "voltage", "V", "mdi:sine-wave"
        )
    
        add(
            "load_current",
            bytes_to_int(bs, 13, 2, scale=0.01),
            "current", "A", "mdi:current-ac"
        )
    
        add(
            "load_power",
            bytes_to_int(bs, 15, 2),
            "power", "W", "mdi:flash"
        )
    
        add(
            "pv_voltage",
            bytes_to_int(bs, 17, 2, scale=0.1),
            "voltage", "V", "mdi:sine-wave"
        )
    
        add(
            "pv_current",
            bytes_to_int(bs, 19, 2, scale=0.01),
            "current", "A", "mdi:current-ac"
        )
    
        add(
            "pv_power",
            bytes_to_int(bs, 21, 2),
            "power", "W", "mdi:flash"
        )
    
        add(
            "max_charging_power_today",
            bytes_to_int(bs, 33, 2),
            "power", "W", "mdi:flash"
        )
    
        add(
            "max_discharging_power_today",
            bytes_to_int(bs, 35, 2),
            "power", "W", "mdi:flash"
        )
    
        add(
            "charging_amp_hours_today",
            bytes_to_int(bs, 37, 2),
            "current", "A", "mdi:current-ac"
        )
    
        add(
            "discharging_amp_hours_today",
            bytes_to_int(bs, 39, 2),
            "current", "A", "mdi:current-ac"
        )
    
        add(
            "power_generation_today",
            bytes_to_int(bs, 41, 2),
            "power", "W", "mdi:flash"
        )
    
        add(
            "power_consumption_today",
            bytes_to_int(bs, 43, 2),
            "power", "W", "mdi:flash"
        )
    
        add(
            "power_generation_total",
            bytes_to_int(bs, 59, 4),
            "power", "W", "mdi:flash"
        )
    
        add(
            "charging_status",
            CHARGING_STATE.get(bytes_to_int(bs, 68, 1)),
            icon="mdi:connection"
        )
        
        add(
            "amostrage",
            self.execution_count,
            icon="mdi:counter"
        )        
        
        self.data.update({"device_info": device_info})

    def parse_battery_type(self, bs):
        data = {}
        data['function'] = FUNCTION.get(bytes_to_int(bs, 1, 1))
        data['battery_type'] = BATTERY_TYPE.get(bytes_to_int(bs, 3, 2))
        self.data.update(data)

    def parse_set_load_response(self, bs):
        data = {}
        data['function'] = FUNCTION.get(bytes_to_int(bs, 1, 1))
        data['load_status'] = bytes_to_int(bs, 5, 1)
        self.data.update(data)
