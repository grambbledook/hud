#pragma once
#include <vector>

#include "Data.h"

namespace Services {
    const auto HRM = Service(
        "Heart Rate Monitor",
        UUID("0000180d-0000-1000-8000-00805f9b34fb"),
        UUID("00002a37-0000-1000-8000-00805f9b34fb")
    );

    const auto CSC = Service(
        "Cadence & Speed Sensor",
        UUID("00001816-0000-1000-8000-00805f9b34fb"),
        UUID("00002a5b-0000-1000-8000-00805f9b34fb")
    );

    const auto PWR = Service(
        "Power Meter",
        UUID("00001818-0000-1000-8000-00805f9b34fb"),
        UUID("00002a63-0000-1000-8000-00805f9b34fb")
    );

    const auto LEGACY_BIKE_TRAINER = Service(
        "Bike Trainer (FE-C over Bluetooth)",
        UUID("6e40fec1-b5a3-f393-e0a9-e50e24dcca9e"),
        UUID("6e40fec2-b5a3-f393-e0a9-e50e24dcca9e")
    );

    const std::vector<Service> SUPPORTED_SERVICES = {HRM, CSC, PWR, LEGACY_BIKE_TRAINER};
}