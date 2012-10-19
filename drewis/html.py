#/usr/bin/env python
# Andrew Sutherland <dr3wsuth3rland@gmail.com>

class Create(object):
    '''Creates a basic html file'''

    def __init__(self):
        self.text = ['<!DOCTYPE html>','<html>','<head>','<title>','</title>','</head>','<body>','<h3>','</h3>','</body>','</html>']

    def title(self, title):
        '''takes string'''
        i = self.text.index('</title>')
        self.text.insert(i, title)

    def analytics(self, script):
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

def tup_to_ul(i):
    '''takes tuple as [(d, [z, z, ...]), ...] and creates a nested ul, returns list'''
    l = []
    for j in i:
        k,q = j
        l.append(' <li>%s</li>' % k)
        l.append('  <ul>')
        for r in q:
            l.append('   <li>%s</li>' % r)
        l.append('  </ul>')
    l.insert(0,'<ul>')
    l.append('</ul>')
    return l

def list_to_links_with_analytics(i, p, action='Click'):
    '''takes list, link prefix and optional action to report to analytics'''
    l = []
    for item in i:
        l.append('<a href="%s/%s" onClick="_gaq.push([\'_trackEvent\', \'%s\', \'%s\']);">%s</a>' % (p,item,action,item,item))
    return l
