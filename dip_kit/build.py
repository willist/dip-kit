import copy
from threading import Lock

from .application import Application
from .express import delegate_methods


# TODO: Add injector registration APIs to Plan.

class Plan(object):
    def __init__(self, config=None):
        self._prefix = None
        self.config = {}
        if config is not None:
            self.config.update(config)
        self.routes = {}
        self._got_first_request = False
        self.before_request_fns = []
        self.before_first_request_fns = []
        self.before_first_request_lock = Lock()
        self.after_request_fns = []
        self.errorhandlers = {}

    def update(self, plan):
        self.config.update(plan.config)
        self.routes.update(plan.routes)
        self.before_request_fns = \
            plan.before_request_fns + self.before_request_fns
        self.before_first_request_fns = \
            plan.before_first_request_fns + self.before_first_request_fns
        self.after_request_fns.extend(plan.after_request_fns)
        self.errorhandlers.update(plan.errorhandlers)

    def copy(self):
        # One-level deep shallow copy of registration data.
        plan = self.__class__()
        plan._prefix = copy.copy(self._prefix)
        plan.config = copy.copy(self.config)
        plan.routes = copy.copy(self.routes)
        plan.before_request_fns = copy.copy(self.before_request_fns)
        plan.before_first_request_fns = \
            copy.copy(self.before_first_request_fns)
        plan.after_request_fns = copy.copy(self.after_request_fns)
        plan.errorhandlers = copy.copy(self.errorhandlers)
        return plan

    def has_prefix(self):
        return self._prefix is not None

    def get_prefix(self):
        return self._prefix

    def set_prefix(self, prefix):
        self._prefix = None
        if prefix and prefix != '/':
            self._prefix = prefix

    def determine_methods(self, methods=None, method=None):
        if method is not None:
            return [method]
        return ['GET']

    def add_url_rule(self, rule, fn, methods=None, method=None):
        # fn is required until build_only rules are supported.
        methods = self.determine_methods(methods=methods, method=method)
        self.routes[(rule, tuple(methods))] = fn

    def route(self, rule, methods=None, method=None):
        def decorator(fn, methods=methods, method=method):
            self.add_url_rule(rule, fn=fn, methods=methods, method=method)
            return fn
        return decorator

    def iter_routes(self):
        for key in self.routes:
            rule, methods = key
            fn = self.routes[key]
            yield rule, methods, fn

    def errorhandler(self, exception):
        def decorator(fn):
            self.errorhandlers[exception] = fn
            return fn
        return decorator

    def iter_errorhandlers(self):
        for error_type, handler in self.errorhandlers.items():
            yield error_type, handler

    def before_request(self, fn):
        self.before_request_fns.append(fn)

    def before_first_request(self, fn):
        self.before_first_request_fns.append(fn)

    def iter_before_request_handlers(self):
        if not self._got_first_request:
            with self.before_first_request_lock:
                if not self._got_first_request:
                    self._got_first_request = True
                    for fn in self.before_first_request_fns:
                        yield fn
        for fn in self.before_request_fns:
            yield fn

    def after_request(self, fn):
        self.after_request_fns.append(fn)

    def iter_after_request_handlers(self):
        for fn in self.after_request_fns:
            yield fn


@delegate_methods
class Builder(object):
    plan_class = Plan
    default_application_class = Application

    delegated_methods = {
        'plan': [
            'add_url_rule',
            'route',
            'errorhandler',
            'before_request',
            'before_first_request',
            'after_request',
        ],
    }

    def __init__(self, config=None, application_class=None):
        self.set_application_class(application_class)
        self.plan = self.plan_class(config=config)

    def iter_plans(self):
        yield self.plan.copy()

    def copy(self):
        builder = self.__class__(application_class=self.application_class)
        builder.plan = self.plan.copy()
        return builder

    def build_application(self, application_class=None):
        if application_class is None:
            application_class = self.application_class
        return application_class(plans=list(self.iter_plans()))

    def set_application_class(self, application_class):
        if application_class is None:
            self.application_class = self.default_application_class
        else:
            self.application_class = application_class


class Crew(Builder):
    def __init__(self, *builder_items, config=None, application_class=None):
        self.set_application_class(application_class)
        # TODO: Cascade config.
        self.plan = self.plan_class(config=config)
        self.builder_items = builder_items

    def copy(self):
        crew = self.__class__(application_class=self.application_class)
        crew.plan = self.plan.copy()
        crew.builders = copy.copy(self.builders)
        return crew

    def iter_plans(self):
        crew_plan = self.plan.copy()
        for prefix, builder in self.builder_items:
            for plan_copy in builder.iter_plans():
                plan_copy.set_prefix(prefix)
                plan_copy.update(crew_plan)
                yield plan_copy
        yield crew_plan
