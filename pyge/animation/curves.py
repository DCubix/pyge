import math

def linear(t): return t

def ease_in_quad(t):
    return t ** 2

def ease_in_cubic(t):
    return t ** 3

def ease_in_back(t):
    c1 = 1.70158
    c3 = c1 + 1.0
    return c3 * ease_in_cubic(t) - c1 * ease_in_quad(t)

def ease_in_elastic(t):
    c4 = (2.0 * math.pi) / 3.0
    if t <= 1e-5: return 0.0
    if t >= 1.0: return 1.0
    return -math.pow(2.0, 10.0 * t - 10.0) * math.sin((t * 10.0 - 10.75) * c4)

def ease_out_quad(t):
    return 1.0 - ease_in_quad(1.0 - t)

def ease_out_cubic(t):
    return 1.0 - ease_in_cubic(1.0 - t)

def ease_out_back(t):
    c1 = 1.70158
    c3 = c1 + 1.0
    return 1.0 + c3 * ease_in_cubic(t - 1.0) + c1 * ease_in_quad(t - 1.0)

def ease_out_elastic(t):
    c4 = (2.0 * math.pi) / 3.0
    if t <= 1e-5: return 0.0
    if t >= 1.0: return 1.0
    return math.pow(2.0, -10.0 * t) * math.sin((t * 10.0 - 0.75) * c4) + 1.0

def ease_in_out_quad(t):
    return 2.0 * ease_in_quad(t) if t < 0.5 else -1.0 + (4.0 - 2.0 * t) * t

def ease_in_out_cubic(t):
    k = 2.0 * t - 2.0;
    return 4.0 * t * t * t if t < 0.5 else (t - 1.0) * k * k + 1.0
