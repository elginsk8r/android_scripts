# Andrew Sutherland <dr3wsuth3rland@gmail.com>

class Create(object):
    '''Creates a basic html file'''

    def __init__(self):
        self.text = ['<!DOCTYPE html>',
                    '<html>',
                    '<head>',
                    '<meta http-equiv="Content-Type" content="text/html; charset=utf-8" />',
                    '<title>','</title>',
                    '<style type="text/css">','</style>',
                    '</head>',
                    '<body>',
                    '<h3>','</h3>',
                    '</body>',
                    '</html>']

    def title(self, title):
        '''takes string'''
        i = self.text.index('</title>')
        self.text.insert(i, title)

    def css(self, css):
        '''takes string'''
        i = self.text.index('</style>')
        self.text.insert(i, css)

    def script(self, script):
        '''takes string'''
        i = self.text.index('</head>')
        self.text.insert(i, script)

    def header(self, header):
        '''takes string'''
        i = self.text.index('</h3>')
        self.text.insert(i, header)

    def body(self, body):
        '''takes list'''
        body.reverse()
        i = self.text.index('</body>')
        for line in body:
            self.text.insert(i,line)

    def write(self, html_file):
        '''takes name of file to write'''
        with open(html_file, 'w') as f:
            for line in self.text:
                f.write(line + '\n')


# helpers
def parse_file(input_file):
    '''takes name of file to read, returns list'''
    with open(input_file, 'r') as f:
        t = f.read().split('\n')
    return t

def add_line_breaks(i):
    return [ j + '<br>' for j in i ]

def list_to_ul(i):
    '''takes list, returns list'''
    l = [ ' <li>%s</li>' % j for j in i ]
    l.insert(0,'<ul>')
    l.append('</ul>')
    return l

def tup_to_ul(i, expandable=False):
    '''takes tuple as [(d, [z, z, ...]), ...] and creates a nested ul, returns list'''
    l = []
    for j in i:
        k,q = j
        l.append(' <li>%s' % k)
        l.append('  <ul>')
        for r in q:
            l.append('   <li>%s</li>' % r)
        l.append('  </ul>')
        l.append(' </li>')
    if expandable:
        l.insert(0, '<ul id="expList">')
    else:
        l.insert(0,'<ul>')
    l.append('</ul>')
    return l

def make_links(i, p):
    '''takes list, link prefix and optional action to report to analytics'''
    return [ '<a href="%s/%s">%s</a>' % (p,j,j) for j in i ]

def make_analytic_links(i, p, action='Click'):
    '''takes list, link prefix and optional action to report to analytics'''
    return [ '<a href="%s/%s" onClick="_gaq.push([\'_trackEvent\', \'%s\', \
        \'%s\']);">%s</a>' % (p,j,action,j,j) for j in i ]

def make_links_with_mirror(i, p, m):
    '''takes list, link prefix, mirror prefix, and optional action for analytics'''
    return [ '<a href="%s/%s">%s</a> <a href="%s/%s">(mirror)</a>' %
        (p,j,j,m,j) for j in i ]

def make_analytic_links_with_mirror(i, p, m, action='Click'):
    '''takes list, link prefix, mirror prefix, and optional action for analytics'''
    return [ '<a href="%s/%s" onClick="_gaq.push([\'_trackEvent\', \'%s\', \
        \'%s\']);">%s</a> <a href="%s/%s" onClick="_gaq.push([\'_trackEvent\', \
        \'%s\', \'%s\']);">(mirror)</a>' %
        (p,j,action,j,j,m,j,action,j) for j in i ]
