#!/usr/bin/env python
# Andrew Sutherland <dr3wsuth3rland@gmail.com>

from drewis import html,analytics

page_title = 'Evervolv Downloads'

body = [ '<a href="nightlies.html">Nightly Builds</a>', '<a href="releases.html">Release Builds</a>' ]

n = html.Create()
n.title(page_title)
n.analytics(analytics.Get())
n.header(page_title)
n.body(html.list_to_ul(body))
n.write('index.html')
