#!/usr/bin/env python
# Andrew Sutherland <dr3wsuth3rland@gmail.com>

import os

from sys import argv

from drewis import html,analytics

script, base_path = argv
base_url = 'n'
page_title = 'Evervolv Nightlies'
css = '''
body {
    font-family:"Lucida Console", Monaco, monospace;
}
'''

staging = []
for d in sorted(os.listdir(base_path)):
    if os.path.isdir(os.path.join(base_path,d)):
        z = [ f for f in sorted(os.listdir(os.path.join(base_path,d)))
                    if f.endswith('.zip') or f.endswith('.html') ]
        staging.append((d,z))

final = []
for i in staging:
    if i[1]:
        # We only want to track clicks for zip files
        # so slit into two lists and concat them for final tuple
        temp_zips = []
        temp_other = []
        for f in i[1]:
            if f.endswith('.zip'):
                temp_zips.append(f)
            else:
                temp_other.append(f)
        final.append((i[0],
            html.make_analytic_links(temp_zips,
                '%s/%s' % (base_url, i[0]), 'NightlyClick') +
            html.make_links(temp_other, '%s/%s' % (base_url, i[0]))))

final.reverse() # newest first

n = html.Create()
n.title(page_title)
n.css(css)
n.analytics(analytics.Get())
n.header(page_title)
n.body(html.tup_to_ul(final))
n.write('nightlies.html')
