
from . import nvb_def


def ascii_identifier(s):
    """Convert to lower case. Convert 'null' to empty string."""
    if (not s or s.lower() == nvb_def.null):
        return ""
    return s


def ascii_texture(s):
    """Convert 'null' to empty string."""
    if (not s or s.lower() == nvb_def.null):
        return ""
    return s


def ascii_float(s):
    """Custom string to float conversion. Treat every error as 0.0."""
    try:
        f = float(s)
    except ValueError:
        f = 0.0
    return f


def ascii_int(s):
    """Custom string to int conversion. Convert to float first, then int."""
    return int(float(s))


def ascii_bool(s):
    """Custom string to bool conversion. Only numbers >= 1 are True."""
    try:
        b = (ascii_int(s) >= 1)
    except ValueError:
        b = False
    return b


def ascii_color(l):
    """Convert list of strings to color."""
    color = [ascii_float(v) for v in l[:4]]
    color.extend([1.0] * (4-len(color)))
    return color