#/usr/bin/env python
# Andrew Sutherland <dr3wsuth3rland@gmail.com>

class Create(object):
    '''Creates a basic html file'''

    def __init__(self):
        self.text = ['<!DOCTYPE html>','<html>','<head>','<title>','</title>','<script>','</script>','</head>','<body>','<h3>','</h3>','</body>','</html>']

    def title(self, title):
        '''takes string'''
        i = self.text.index('</title>')
        self.text.insert(i, title)

    def analytics(self, script):
        '''takes string'''
        i = self.text.index('</script>')
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
            self.text.insert(i,line + '<br>')

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



