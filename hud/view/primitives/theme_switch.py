import inspect
from functools import cache

from hud.configuration.config import Config


def with_switchable_theme(cls):
    def applyUiChanges(self, app_config: Config):
        for k, v in self.__dict__.items():
            if k == 'parent':
                continue

            if hasattr(v, 'setStyleSheet'):
                v.setStyleSheet(app_config.hud_layout.theme.colour_scheme)

            if hasattr(v, 'applyTheme'):
                v.applyTheme(app_config.hud_layout.theme)

            if hasattr(v, 'adjustSize'):
                v.adjustSize()

            if hasattr(v, 'applyUiChanges'):
                v.applyUiChanges(app_config)

            if hasattr(v, 'adjustSize'):
                v.adjustSize()

            if hasattr(v, 'updateGeometries'):
                v.updateGeometries()

            if hasattr(v, 'updateEditorData'):
                v.updateEditorData()

            if hasattr(v, 'update'):
                try:
                    v.update()
                except:
                    pass

        if hasattr(self, 'adjustSize'):
            self.adjustSize()

        if hasattr(self, 'update'):
            self.update()

    cls.applyUiChanges = applyUiChanges
    return cls


@cache
def get_number_of_parameters(func):
    if hasattr(func, '__text_signature__'):
        signature = func.__text_signature__

        if signature:
            # Remove the first character '(' and the last two characters ')/'
            signature = signature[1:-2]
            # Split the signature on ', ' to get a list of parameters
            parameters = signature.split(', ')
            # Filter out any empty strings resulting from leading commas
            parameters = [param for param in parameters if param]
            return len(parameters)

    return 0
