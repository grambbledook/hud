#pragma once
#include <mutex>

#include "Channel.h"
#include "Events.h"

template<typename T, typename = std::enable_if_t<std::is_same_v<T, int> || std::is_same_v<T, double>> >
struct Statistics {
    T latest;
    T min;
    T max;
    double average;
    int count;

    void aggregate(T value) {
        latest = value;
        min = std::min(min, value);
        max = std::max(max, value);
        average = (average * count + value) / (count + 1);
        count++;
    }
};


template<typename A, typename B, typename = std::enable_if_t<std::is_same_v<B, int> || std::is_same_v<B, double>> >
struct State {
    std::shared_ptr<Device> device;
    std::vector<A> data;
    Statistics<B> stats;


    std::pair<std::vector<A>, bool> getLastN(int n) {
        if (n > data.size()) {
            return {std::vector<A>(n), false};
        }

        return {std::vector<A>(data.end() - n, data.end()), true};
    }

    void recordMetric(A value) {
        if (data.size() == 2) {
            data.erase(data.begin());
        }
        data.push_back(value);
    }

    void unrecordMetric() {
        if (data.empty()) {
            return;
        }
        data.erase(data.end() - 1);
    };

    void aggregateMetric(B value) {
        stats.aggregate(value);
    }
};


class Model {
public:
    void addDevice(const std::shared_ptr<Device> &device);
    std::vector<std::shared_ptr<Device>> getDevices(GattService service);

    void setHeartRateMonitor(const std::shared_ptr<Device> &device);
    void setCadenceSensor(const std::shared_ptr<Device> &device);
    void setSpeedSensor(const std::shared_ptr<Device> &device);
    void setPowerMeter(const std::shared_ptr<Device> &device);
    void setBikeTrainer(const std::shared_ptr<Device> &device);

    void recordHeartData(const MeasurementEvent<HrmMeasurement> &event);
    void recordCadenceData(const MeasurementEvent<CadenceMeasurement> &event);
    void recordSpeedData(const MeasurementEvent<SpeedMeasurement> &event);
    void recordPowerData(const MeasurementEvent<PowerMeasurement> &event);
    void recordTrainerData(const MeasurementEvent<GeneralData> &event);
    void recordTrainerData(const MeasurementEvent<GeneralSettings> &event);
    void recordTrainerData(const MeasurementEvent<SpecificTrainerData> &event);

public:
    Notifications<Statistics<int>> hrmNotifications;
    Notifications<Statistics<double>> speedNotifications;
    Notifications<Statistics<int>> cadenceNotifications;
    Notifications<Statistics<int>> powerNotifications;
    Notifications<std::string> trainerNotifications;

    std::unordered_map<std::string, std::shared_ptr<Device>> devices;
private:
    std::mutex mutex;

    State<int, int> hrmState = {
        __nullptr,
        std::vector<int>{},
        {0, 0, 0, 0.0, 0}
    };

    State<std::pair<int, int>, int> cadenceState = {
        __nullptr,
        std::vector<std::pair<int, int> >{},
        {0, 0, 0, 0.0, 0}
    };

    State<std::pair<int, int>, double> speedState = {
        __nullptr,
        std::vector<std::pair<int, int> >{},
        {0.0, 0.0, 0.0, 0.0, 0}
    };

    State<int, int> powerState = {
        __nullptr,
        std::vector<int>{},
        {0, 0, 0, 0.0, 0}
    };
};
