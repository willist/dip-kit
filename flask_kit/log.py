import logging


class LoggerMixin(object):
    def get_logger(self):
        if hasattr(self, 'logger'):
            return self.logger
        logger = logging.getLogger(self.config.get('LOGGER_NAME', __name__))
        logger.setLevel(self.config.get('LOGGER_LEVEL', logging.INFO))
        handler = self.config.get('LOGGER_HANDLER', None)
        if handler is None:
            handler = logging.StreamHandler()
        logger.addHandler(handler)
        self.logger = logger
        return self.logger
