"""Constants for the Duravit SensoWash integration."""

DOMAIN = "sensowash"
MANUFACTURER = "Duravit"

# Config entry keys
CONF_ADDRESS = "address"
CONF_NAME = "name"

# Coordinator update interval (seconds) — state is primarily push via BLE notify,
# but we poll periodically as a fallback.
UPDATE_INTERVAL = 30

# Entry data keys
ENTRY_COORDINATOR = "coordinator"
ENTRY_CLIENT = "client"
