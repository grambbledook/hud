import enum


class AppState(enum.Enum):
    WAITING_FOR_TRAINER = 1
    WAITING_FOR_SENSORS = 2
    WAITING_FOR_WORKOUT = 3
    IN_WORKOUT = 4
    WORKOUT_FINISHED = 5
    EXITING = 9
