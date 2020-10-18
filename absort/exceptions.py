__all__ = ["Unreachable"]


class Unreachable(Exception):
    """ Some branch is theoretically unreachable, but surprisingly jumped in """
