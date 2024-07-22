#include <algorithm>
#include <iostream>

#include "Events.h"
#include "Model.h"

constexpr auto MM_TO_KM = 1.0 / 1000000;
constexpr auto MS_TO_MIN = 1.0 / (60 * 1024);
constexpr auto MS_TO_HOUR = 1.0 / (60 * 60 * 1024);
constexpr auto DEFAULT_TIRE_CIRCUMFERENCE_MM = 2168;

void Model::setHeartRateMonitor(const std::shared_ptr<Device> &device) {
    std::cout << "Model::setHeartRateMonitor: " << device->deviceId() <<std::endl;
    hrmState.device = device;
}

void Model::setCadenceSensor(const std::shared_ptr<Device> &device) {
    std::cout << "Model::setCadenceSensor: " << device->deviceId() <<std::endl;
    cadenceState.device = device;
}

void Model::setSpeedSensor(const std::shared_ptr<Device> &device) {
    std::cout << "Model::setSpeedSensor: " << device->deviceId() <<std::endl;
    speedState.device = device;
}

void Model::setPowerMeter(const std::shared_ptr<Device> &device) {
    std::cout << "Model::setPowerMeter: " << device->deviceId() <<std::endl;
    powerState.device = device;
}

void Model::recordHeartData(const MeasurementEvent<HrmMeasurement> &event) {
    if (*hrmState.device != *event.device) {
        std::cout << "Device mismatch." << std::endl;
        std::cout << "  Should be: " << hrmState.device->deviceId() << " but was: " << event.device->deviceId() << std::endl;
        return;
    }

    hrmState.recordMetric(event.measurement.hrm);
    hrmState.aggregateMetric(event.measurement.hrm);
    std::cout << "HRM: " << hrmState.stats.latest << " AVG: " << hrmState.stats.average << std::endl;
}

void Model::recordCadenceData(const MeasurementEvent<CadenceMeasurement> &event) {
    std::cout << "Model::recordCadenceData" << std::endl;
    if (*cadenceState.device != *event.device) {
        return;
    }

    cadenceState.recordMetric(std::pair{event.measurement.ccr, event.measurement.lcet});

    auto [events, dataPresent ] = cadenceState.getLastN(2);
    auto [prevCcr, prevLcet, ccr, lcet] = std::tuple_cat(events[0], events[1]);
    std::cout << "  Prev[" << prevCcr << ", " << prevLcet << "], Cur[" << ccr << ", " << lcet << "]" << std::endl;

    if (lcet == prevLcet and dataPresent) {
        std::cout << "  Same timestamp. Skipping..." << std::endl;
        cadenceState.unrecordMetric();
        return;
    }

    const auto lcetResetCorrection = lcet > prevLcet ? 0 : 0x10000;

    const auto totalRevolutions = ccr - prevCcr;
    const auto timeDelta = lcet - prevLcet + lcetResetCorrection;

    const auto cadence = totalRevolutions / (timeDelta * MS_TO_MIN);

    cadenceState.aggregateMetric(std::round(cadence));
    std::cout << "CADENCE: " << cadenceState.stats.latest << " AVG: " << cadenceState.stats.average << std::endl;
}

void Model::recordSpeedData(const MeasurementEvent<SpeedMeasurement> &event) {
    std::cout << "Model::recordSpeedData" << std::endl;
    if (*speedState.device != *event.device) {
        std::cout << "  Device mismatch." << std::endl;
        std::cout << "  Should be: " << speedState.device->deviceId() << " but was: " << event.device->deviceId() << std::endl;
        return;
    }

    speedState.recordMetric(std::pair{event.measurement.cwr, event.measurement.lwet});

    auto [events, dataPresent] = speedState.getLastN(2);
    auto [prevCwr, prevLwet, cwr, lwet] = std::tuple_cat(events[0], events[1]);

    std::cout << "  Prev[" << prevCwr << ", " << prevLwet << "], Cur[" << cwr << ", " << lwet << "]" << std::endl;
    if (lwet == prevLwet and dataPresent) {
        speedState.unrecordMetric();
        return;
    }

    const auto lwetResetCorrection = lwet > prevLwet ? 0 : 0x10000;

    const auto totalRevolutions = cwr - prevCwr;
    const auto timeDelta = lwet - prevLwet + lwetResetCorrection;

    const auto totalKmh = totalRevolutions * DEFAULT_TIRE_CIRCUMFERENCE_MM * MM_TO_KM;
    const auto speed = totalKmh / timeDelta * MS_TO_HOUR;

    speedState.aggregateMetric(std::round(speed));
    std::cout << "SPEED: " << speedState.stats.latest << " AVG: " << speedState.stats.average << std::endl;
}

void Model::recordPowerData(const MeasurementEvent<PowerMeasurement> &event) {
    if (*powerState.device != *event.device) {
        return;
    }

    powerState.recordMetric(event.measurement.power);
    powerState.aggregateMetric(event.measurement.power);
    std::cout << "POWER: " << powerState.stats.latest << " AVG: " << powerState.stats.average << std::endl;
}