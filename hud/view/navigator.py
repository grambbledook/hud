import enum
import sys
from typing import Optional

from hud.configuration.config import Config, BRIGHT, DARK
from hud.view.device.sensor_window import SensorsWindow
from hud.view.primitives.draggable_window import DraggableWindow
from hud.view.device.trainer_window import TrainerWindow
from hud.view.workout.workout_window import WorkoutWindow
from hud.view.workout_statistics.workout_statistics_window import WorkoutStatisticsWindow


class AppState(enum.Enum):
    WAITING_FOR_TRAINER = 1
    WAITING_FOR_SENSORS = 2
    WAITING_FOR_WORKOUT = 3
    IN_WORKOUT = 4
    WORKOUT_FINISHED = 5
    EXITING = 9


class ViewNavigator:
    def __init__(self, app_config: Config, trainer_choice_window: TrainerWindow,
                 additional_sensors_window: SensorsWindow, workout_window: WorkoutWindow,
                 workout_statistics_window: WorkoutStatisticsWindow):
        self.app_config = app_config
        self.trainer_choice_window = trainer_choice_window
        trainer_choice_window.prev.connect(self.progress_to_state)
        trainer_choice_window.next.connect(self.progress_to_state)

        self.additional_sensors_window = additional_sensors_window
        additional_sensors_window.prev.connect(self.progress_to_state)
        additional_sensors_window.next.connect(self.progress_to_state)

        self.workout_window = workout_window
        workout_window.prev.connect(self.progress_to_state)
        workout_window.next.connect(self.progress_to_state)

        self.workout_statistics_window = workout_statistics_window
        workout_statistics_window.prev.connect(self.progress_to_state)
        workout_statistics_window.next.connect(self.progress_to_state)

        self.select_workout_window = None
        self.exit_window = None
        self.active_window: Optional[DraggableWindow] = None
        self.app_state = AppState.WAITING_FOR_TRAINER

    def progress_to_state(self, new_state_int: int):
        new_state = AppState(new_state_int)
        old_state, self.app_state = self.app_state, new_state
        print(f"Transitioning from state [{old_state}] to [{new_state}]")

        self.apply()

    def switch_schema(self):
        layout = self.app_config.hud_layout
        layout.theme = BRIGHT if layout.theme == DARK else DARK

        self.apply()

    def apply(self):
        prev_window = self.active_window

        match self.app_state:
            case AppState.WAITING_FOR_TRAINER:
                new_window = self.active_window = self.trainer_choice_window
            case AppState.WAITING_FOR_SENSORS:
                new_window = self.active_window = self.additional_sensors_window
            case AppState.WAITING_FOR_WORKOUT:
                new_window = self.active_window = self.select_workout_window
                sys.exit(0)
            case AppState.IN_WORKOUT:
                new_window = self.active_window = self.workout_window
                sys.exit(0)
            case AppState.WORKOUT_FINISHED:
                new_window = self.active_window = self.workout_statistics_window
            case AppState.EXITING:
                new_window = self.active_window = self.exit_window
                sys.exit(0)
            case _:
                new_window = self.active_window = self.active_window

        print(f"Switching from window [{prev_window}] to [{new_window}]")

        if new_window:
            new_window.applyUiChanges(self.app_config)

        if prev_window and prev_window != new_window:
            prev_window.hide()

        if new_window and prev_window != new_window:
            new_window.show()

        if not new_window:
            print(f"Expected to have a window for the state [{self.app_state}], bust was None")
