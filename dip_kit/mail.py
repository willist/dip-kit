__all__ = ['MailerMixin']


class MailerMixin(object):
    def get_mailer(self):
        raise NotImplementedError('mailer')
