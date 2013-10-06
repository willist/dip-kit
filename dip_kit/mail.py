from flask_mail import Mail, Message


__all__ = ['MailerMixin', 'Message']


class MailerMixin(object):
    def get_mailer(self):
        if hasattr(self, 'mailer'):
            return self.mailer
        self.mailer = Mail(self.get_app())
        return self.mailer
