#!/usr/bin/env python
# Andrew Sutherland <dr3wsuth3rland@gmail.com>

from drewis import html,analytics

page_title = 'Evervolv Downloads'

body = [ '<a href="nightlies.html">Nightly Builds</a>',\
         '<a href="releases.html">Release Builds</a>' ]
css = '''
body {
    background-color:#0099CC;
    font-family:"Lucida Console", Monaco, monospace;
    color:#FFFFFF;
}
a:link {color:#FFFFFF;}
a:visited {color:#FFFFFF;}
'''

m = html.Create()
m.title(page_title)
m.css(css)
m.analytics(analytics.Get())
m.header(page_title)
m.body(html.list_to_ul(body))
m.write('index.html')
