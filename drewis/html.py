#/usr/bin/env python

class Create(object):
    '''Creates a basic html file'''

    def __init__(self):
        self.text = ['<!DOCTYPE html>','<html>','<head>','<title>','</title>','<script>','</script>','</head>','<body>','<h3>','</h3>','</body>','</html>']

    def addtitle(self, title):
        '''takes string'''
        i = self.text.index('</title>')
        self.text.insert(i, title)

    def addheader(self, header):
        '''takes string'''
        i = self.text.index('</h3>')
        self.text.insert(i, header)

    def addbody(self, body):
        '''takes list'''
        body.reverse()
        i = self.text.index('</body>')
        for line in body:
            self.text.insert(i,line + '<br>')

    def write(self, html_file):
        '''takes name of file to write'''
        fd = open(html_file, 'w')
        for line in self.text:
            fd.write(line + '\n')
        fd.close()

def parseFile(input_file):
    '''takes name of file to read, returns list'''
    f = open(input_file, 'r')
    t = f.read().split('\n')
    f.close()
    return t



