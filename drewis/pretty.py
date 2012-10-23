# Andrew Sutherland <dr3wsuth3rland@gmail.com>

def time(t):
    '''takes timedelta object, returns string'''
    h, r = divmod(t.seconds, 3600)
    m, s = divmod(t.seconds, 60)
    return '%sh %sm %ss' % (h, m, s)
