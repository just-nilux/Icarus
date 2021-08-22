

class IkarusException(Exception):

    def __init__(self, message):
        self.message = message

    def __str__(self):
        return 'IkarusException: %s' % (self.message)


class SysStatDownException(IkarusException):

    def __init__(self):
        super().__init__('Broker is down!')


class NotImplementedException(IkarusException):
    def __init__(self, value):
        message = f'Not implemented: {value}'
        super().__init__(message)