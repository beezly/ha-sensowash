"""Constants for the Duravit SensoWash integration."""

DOMAIN = "sensowash"
MANUFACTURER = "Duravit"

# Config / options entry keys
CONF_PAIRING_KEY = "pairing_key"  # hex string, for serial-protocol devices

# Coordinator update interval (seconds) — state is primarily push via BLE notify,
# but we poll periodically as a fallback.
UPDATE_INTERVAL = 30

# hass.data key for storing coordinator capabilities between restarts
CONF_CAPABILITIES = "capabilities"
