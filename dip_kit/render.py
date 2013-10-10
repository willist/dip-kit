import os


def relative_folder(path, folder='templates'):
    if os.path.isdir(path):
        return os.path.abspath(os.path.join(path, folder))
    else:
        return os.path.abspath(os.path.join(path, '..', folder))


class RenderMixin(object):
    def get_render(self):
        raise NotImplementedError('render')
