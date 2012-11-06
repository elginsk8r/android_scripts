# Andrew Sutherland <dr3wsuth3rland@gmail.com>

class Create(object):
    '''Creates a basic html file'''

    def __init__(self):
        self.text = ['<!DOCTYPE html>',
                    '<html lang="en">',
                    '<head>',
                    '<meta charset=utf-8" />',
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
