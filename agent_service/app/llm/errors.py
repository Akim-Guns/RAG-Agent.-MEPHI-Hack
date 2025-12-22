from gigachat.exceptions import GigaChatException


class BlackListException(GigaChatException):
    def __init__(self, *args):
        super().__init__(*args)

class ParserException(GigaChatException):
    def __init__(self, *args):
        super().__init__(*args)