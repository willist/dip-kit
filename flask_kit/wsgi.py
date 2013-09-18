class WsgiMixin(object):
    def get_wsgi(self):
        if hasattr(self, 'wsgi'):
            return self.wsgi
        # This is a great place to apply WSGI middleware.
        self.wsgi = self.get_app().wsgi_app
        return self.wsgi
