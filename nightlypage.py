#!/usr/bin/env python
# Andrew Sutherland <dr3wsuth3rland@gmail.com>

import os

from sys import argv

from drewis import html,analytics

script, base_path = argv
base_url = 'n'
page_title = 'Evervolv Nightlies'

staging = []
for d in sorted(os.listdir(base_path)):
    if os.path.isdir(os.path.join(base_path,d)):
        z = [ f for f in sorted(os.listdir(os.path.join(base_path,d))) \
                    if f.endswith('.zip') or f.endswith('.html') ]
        staging.append((d,z))

final = []
for i in staging:
    if i[1]:
        final.append((i[0], [ j for j in html.list_to_links_with_analytics(i[1], \
                    '%s/%s' % (base_url, i[0]), 'NightlyClick') ]))

final.reverse() # newest first

n = html.Create()
n.title(page_title)
n.analytics(analytics.Get())
n.header(page_title)
n.body(html.tup_to_ul(final))
n.write('nightlies.html')
