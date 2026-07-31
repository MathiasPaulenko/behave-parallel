"""Environment hooks for simple test fixtures."""


def before_all(context):
    context.config.setup_logging()


def after_all(context):
    pass


def before_feature(context, feature):
    pass


def after_feature(context, feature):
    pass


def before_scenario(context, scenario):
    pass


def after_scenario(context, scenario):
    pass
