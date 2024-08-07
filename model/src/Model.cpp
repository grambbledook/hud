#include <algorithm>
#include <iostream>
#include <memory>

#include "BleDeviceServices.h"
#include "Formula.h"
#include "Model.h"


void Model::addDevice(const std::shared_ptr<Device> &device) {
    std::lock_guard guard(mutex);

    const auto oldDevice = devices[device->deviceId()];
    if (oldDevice and *oldDevice == *device) {
        return;
    }

    const auto newDevice = oldDevice ? std::make_shared<Device>(*oldDevice | *device) : device;

    if (oldDevice and *newDevice == *oldDevice) {
        return;
    }
    devices[device->deviceId()] = newDevice;
    notifications.deviceDiscovered.publish(DeviceDiscovered{newDevice});
}

std::vector<std::shared_ptr<Device> > Model::getDevices(const GattService *service = nullptr) {
    if (service == nullptr) {
        return devices
               | std::views::transform([](const auto &pair) { return pair.second; })
               | std::ranges::to<std::vector<std::shared_ptr<Device> > >();
    }

    return devices
           | std::views::filter([service](const auto &pair) { return pair.second->services.contains(*service); })
           | std::views::transform([](const auto &pair) { return pair.second; })
           | std::ranges::to<std::vector<std::shared_ptr<Device> > >();
}

void Model::setDevice(const std::shared_ptr<Device> &device) {
    if (device->services.contains(BLE::Services::HRM)) {
        setHeartRateMonitor(device);
    }
    if (device->services.contains(BLE::Services::CSC)) {
        setCadenceSensor(device);
        setSpeedSensor(device);
    }
    if (device->services.contains(BLE::Services::PWR)) {
        setPowerMeter(device);
    }
    if (device->services.contains(BLE::Services::FEC_BIKE_TRAINER)) {
        setBikeTrainer(device);
    }
}

void Model::setHeartRateMonitor(const std::shared_ptr<Device> &device) {
    if (hrmState.device and hrmState.device->deviceId() == device->deviceId()) {
        return;
    }
    hrmState.device = device;
    notifications.deviceSelected.publish(DeviceSelected{Service::HEART_RATE, hrmState.device});
}

void Model::setCadenceSensor(const std::shared_ptr<Device> &device) {
    if (cadenceState.device and cadenceState.device->deviceId() == device->deviceId()) {
        return;
    }
    cadenceState.device = device;
    notifications.deviceSelected.publish(DeviceSelected{Service::CADENCE, cadenceState.device});
}

void Model::setSpeedSensor(const std::shared_ptr<Device> &device) {
    if (speedState.device and speedState.device->deviceId() == device->deviceId()) {
        return;
    }
    speedState.device = device;
    notifications.deviceSelected.publish(DeviceSelected{Service::SPEED, speedState.device});
}

void Model::setPowerMeter(const std::shared_ptr<Device> &device) {
    if (powerState.device and powerState.device->deviceId() == device->deviceId()) {
        return;
    }
    powerState.device = device;
    notifications.deviceSelected.publish(DeviceSelected{Service::POWER, powerState.device});
}

void Model::setBikeTrainer(const std::shared_ptr<Device> &device) {
    std::cout << "Model::setBikeTrainer: " << device->deviceId() << std::endl;
}

void Model::recordHeartData(const MeasurementEvent<HrmMeasurement> &event) {
    if (*hrmState.device != *event.device) {
        return;
    }

    hrmState.recordMetric(event.measurement.hrm);
    hrmState.aggregateMetric(event.measurement.hrm);

    publishUpdate();
}

void Model::recordCadenceData(const MeasurementEvent<CadenceMeasurement> &event) {
    if (*cadenceState.device != *event.device) {
        return;
    }

    cadenceState.recordMetric(std::pair{event.measurement.ccr, event.measurement.lcet});

    auto [events, dataPresent] = cadenceState.getLastN(2);
    auto [prevCcr, prevLcet, ccr, lcet] = std::tuple_cat(events[0], events[1]);

    if (lcet == prevLcet and dataPresent) {
        cadenceState.unrecordMetric();
        return;
    }

    const auto lcetResetCorrection = lcet > prevLcet ? 0 : 0x10000;

    const auto totalRevolutions = ccr - prevCcr;
    const auto timeDelta = lcet - prevLcet + lcetResetCorrection;

    const auto cadence = totalRevolutions * BLE::Math::MS_IN_MIN / timeDelta;

    cadenceState.aggregateMetric(cadence);

    publishUpdate();
}

void Model::recordSpeedData(const MeasurementEvent<SpeedMeasurement> &event) {
    if (*speedState.device != *event.device) {
        return;
    }

    speedState.recordMetric(std::pair{event.measurement.cwr, event.measurement.lwet});

    auto [events, dataPresent] = speedState.getLastN(2);
    auto [prevCwr, prevLwet, cwr, lwet] = std::tuple_cat(events[0], events[1]);

    if (lwet == prevLwet and dataPresent) {
        speedState.unrecordMetric();
        return;
    }

    const auto lwetResetCorrection = lwet > prevLwet ? 0 : 0x10000;

    const auto totalRevolutions = cwr - prevCwr;
    const auto timeDelta = lwet - prevLwet + lwetResetCorrection;

    const auto distanceTraveled = totalRevolutions * BLE::Wheels::DEFAULT_TIRE_CIRCUMFERENCE_MM;
    const auto speedMms = distanceTraveled * BLE::Math::MS_IN_SECOND / timeDelta;;

    speedState.aggregateMetric(speedMms);
    publishUpdate();
}

void Model::recordPowerData(const MeasurementEvent<PowerMeasurement> &event) {
    if (*powerState.device != *event.device) {
        return;
    }

    powerState.recordMetric(event.measurement.power);
    powerState.aggregateMetric(event.measurement.power);
    publishUpdate();
}

void Model::recordTrainerData(const MeasurementEvent<GeneralData> &event) {
}

void Model::recordTrainerData(const MeasurementEvent<GeneralSettings> &event) {
}

void Model::recordTrainerData(const MeasurementEvent<SpecificTrainerData> &event) {
    publishUpdate();
}

void Model::publishUpdate() {
    const auto aggregate = WorkoutData{
        Aggregate{hrmState.stats.latest, hrmState.stats.average},
        Aggregate{cadenceState.stats.latest, cadenceState.stats.average},
        Aggregate{speedState.stats.latest, speedState.stats.average},
        Aggregate{powerState.stats.latest, powerState.stats.average},
    };

    notifications.measurements.publish(aggregate);
}
