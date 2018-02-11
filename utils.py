def format_speed(s):
    if s >= 1e18:
        return '%6.2f EH/s' % (s/1e18)
    elif s >= 1e15:
        return '%6.2f PH/s' % (s/1e15)
    elif s >= 1e12:
        return '%6.2f TH/s' % (s/1e12)
    elif s >= 1e9:
        return '%6.2f GH/s' % (s/1e9)
    elif s >= 1e6:
        return '%6.2f MH/s' % (s/1e6)
    elif s >= 1e3:
        return '%6.2f kH/s' % (s/1e3)
    else:
        return '%6.2f  H/s' % s

def format_speeds(speeds):
    return ', '.join([format_speed(s) for s in speeds])

def format_time(seconds):
    m = seconds // 60
    s = seconds % 60
    if m == 1 and s == 0:
        return '60 s'
    elif m == 0:
        return '%2d s' % s
    else:
        return '%1d:%02d' % (m, s)

