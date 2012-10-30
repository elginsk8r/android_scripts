#!/usr/bin/env python
# Andrew Sutherland <dr3wsuth3rland@gmail.com>

import os

from sys import argv

from drewis import html,analytics

from ev import devices

script, base_path = argv
base_url = 'http://ev-dl1.deuweri.com'
warning_message = ['<p>This list may be incomplete.</p>', '<p>If you dont see what you want try browsing <a href="http://ev-dl1.deuweri.com/">ev-dl1.deuweri.com</a></p>']
page_title = 'Evervolv Releases'
mirror_base_url = 'r'
css = '''
body {
    font-family:"Lucida Console", Monaco, monospace;
}
'''

staging = []
for d in sorted(os.listdir(base_path)):
    if os.path.isdir(os.path.join(base_path,d)):
        z = [ f for f in sorted(os.listdir(os.path.join(base_path,d)))
                    if f.endswith('.zip') ]
        staging.append((d,z))

final = []
for i in staging:
    if i[1] and devices.is_device(i[0]):
        final.append(('%s %s:' % (i[0],devices.get_device_name(i[0])), [ j for j in
                html.make_analytic_links_with_mirror(i[1], '%s/%s' % (base_url, i[0]),
                '%s/%s' % (mirror_base_url, i[0]),
                'ReleaseClick') ]))

r = html.Create()
r.title(page_title)
r.css(css)
r.analytics(analytics.Get())
r.header(page_title)
r.body(warning_message)
r.body(html.tup_to_ul(final))
r.write('releases.html')
