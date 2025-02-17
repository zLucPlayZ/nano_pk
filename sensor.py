"""Platform for sensor integration."""
import logging
from homeassistant.helpers.entity import Entity
from . import DOMAIN, CONF_HOST, CONF_FORMAT, CONF_NAME, CONF_PARAMS, CONF_PARAMS_STANDARD, CONF_PARAMS_FULL, CONF_LANG, \
    CONF_LANG_EN, CONF_LANG_DE
from datetime import timedelta
from .hargassner import HargassnerBridge

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=5)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the sensor platform."""
    host = hass.data[DOMAIN][CONF_HOST]
    format = hass.data[DOMAIN][CONF_FORMAT]
    name = hass.data[DOMAIN][CONF_NAME]
    paramSet = hass.data[DOMAIN][CONF_PARAMS]
    lang = hass.data[DOMAIN][CONF_LANG]
    bridge = HargassnerBridge(host, msg_format=format)
    if paramSet == CONF_PARAMS_FULL:
        entities = []
        for p in bridge.data().values():
            if p.key() == "Störung":
                entities.append(HargassnerErrorSensor(bridge, name))
            elif p.key() == "ZK":
                entities.append(HargassnerStateSensor(bridge, name, lang))
            else:
                entities.append(HargassnerSensor(bridge, name + " " + p.description(), p.key()))
        async_add_entities(entities)
    else:
        async_add_entities([
            HargassnerErrorSensor(bridge, name),
            HargassnerStateSensor(bridge, name, lang),
            HargassnerSensor(bridge, name + " boiler temperature", "TK"),
            HargassnerSensor(bridge, name + " smoke gas temperature", "TRG"),
            HargassnerSensor(bridge, name + " output", "Leistung", "mdi:fire"),
            HargassnerSensor(bridge, name + " outside temperature", "Taus"),
            HargassnerSensor(bridge, name + " buffer temperature 0", "TB1", "mdi:coolant-temperature"),
            HargassnerSensor(bridge, name + " buffer temperature 1", "TPo", "mdi:coolant-temperature"),
            HargassnerSensor(bridge, name + " buffer temperature 2", "TPm", "mdi:coolant-temperature"),
            HargassnerSensor(bridge, name + " buffer temperature 3", "TPu", "mdi:coolant-temperature"),
            HargassnerSensor(bridge, name + " return temperature", "TRL"),
            HargassnerSensor(bridge, name + " buffer level", "Puff Füllgrad", "mdi:gauge"),
            HargassnerSensor(bridge, name + " pellet stock", "Lagerstand", "mdi:silo"),
            HargassnerSensor(bridge, name + " pellet consumption", "Verbrauchszähler", "mdi:basket-unfill"),
            HargassnerSensor(bridge, name + " flow temperature", "TVL_1")
        ])


class HargassnerSensor(Entity):
    """Representation of a Sensor."""

    def __init__(self, bridge, description, param_name, icon=None):
        """Initialize the sensor."""
        self._state = None
        self._bridge = bridge
        self._description = description
        self._paramName = param_name
        self._icon = icon
        self._unit = bridge.get_unit(param_name)

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._description

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit

    @property
    def icon(self):
        """Return an icon for the sensor in the GUI."""
        return self._icon

    async def async_update(self):
        """Fetch new state data for the sensor.
        This is the only method that should fetch new data for Home Assistant.
        """
        self._state = self._bridge.get_value(self._paramName)


class HargassnerErrorSensor(HargassnerSensor):
    ERRORS = {
        "5": "Aschelade entleeren",
        "6": "Aschelade zu voll",
        "29": "Verbrennungsstörung",
        "30": "Batterie leer",
        "31": "Blockade Einschubmotor",
        "32": "Füllzeit überschritten",
        "70": "Pelletslagerstand niedrig",
        "89": "Schieberost schwergängig",
        "93": "Aschelade offen",
        "227": "Lagerraumschalter aus",
        "228": "Pelletsbehälter fast leer",
        "229": "Füllstandsmelder kontrollieren",
        "371": "Brennraum prüfen"
    }

    def __init__(self, bridge, device_name):
        super().__init__(bridge, device_name + " operation", "Störung", "mdi:alert")

    async def async_update(self):
        raw_state = self._bridge.get_value(self._paramName)
        if raw_state is None:
            self._state = "Unknown"
        elif raw_state == "False":
            self._state = "OK"
            self._icon = "mdi:check"
        else:
            error_id = self._bridge.get_value("Störungs Nr")
            error_descr = self.ERRORS.get(error_id)
            if error_descr is None:
                self._state = "error " + error_id
            else:
                self._state = error_descr
            self._icon = "mdi:alert"


class HargassnerStateSensor(HargassnerSensor):
    UNKNOWN_STATE = "?"
    STATES = {
        "1": {CONF_LANG_DE: "Aus", CONF_LANG_EN: "Off"},
        "2": {CONF_LANG_DE: "Startvorbereitung", CONF_LANG_EN: "Preparing start"},
        "3": {CONF_LANG_DE: "Kessel Start", CONF_LANG_EN: "Boiler start"},
        "4": {CONF_LANG_DE: "Zündüberwachung", CONF_LANG_EN: "Monitoring ignition"},
        "5": {CONF_LANG_DE: "Zündung", CONF_LANG_EN: "Ignition"},
        "6": {CONF_LANG_DE: "Übergang LB", CONF_LANG_EN: "Transition to FF"},
        "7": {CONF_LANG_DE: "Leistungsbrand", CONF_LANG_EN: "Full firing"},
        "9": {CONF_LANG_DE: "Warten auf EA", CONF_LANG_EN: "Waiting for AR"},
        "10": {CONF_LANG_DE: "Entaschung", CONF_LANG_EN: "Ash removal"},
        "12": {CONF_LANG_DE: "Putzen", CONF_LANG_EN: "Cleaning"},
        "UNKNOWN_STATE": {CONF_LANG_DE: "Unbekannt", CONF_LANG_EN: "Unknown"}
    }

    def __init__(self, bridge, device_name, lang):
        super().__init__(bridge, device_name + " boiler state", "ZK")
        self._lang = lang

    async def async_update(self):
        raw_state = self._bridge.get_value(self._paramName)
        if raw_state in self.STATES:
            self._state = self.STATES[raw_state][self._lang]
        else:
            self._state = self.STATES["UNKNOWN_STATE"][self._lang] + " (" + str(raw_state) + ")"
        if raw_state == "6" or raw_state == "7":
            self._icon = "mdi:fireplace"
        else:
            self._icon = "mdi:fireplace-off"
