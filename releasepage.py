#!/usr/bin/env python
# Andrew Sutherland <dr3wsuth3rland@gmail.com>

import os

from sys import argv

from drewis import html,analytics

def get_device_name(name):
    if name == 'Acies':
        return 'HTC Evo 4G'
    elif name == 'Artis':
        return 'HTC Evo Shift 4G'
    elif name == 'Bellus':
        return 'HTC Evo 4G LTE'
    elif name == 'Dives':
        return 'HTC Droid Incredible'
    elif name == 'Conor':
        return 'HTC Droid Incredible 2'
    elif name == 'Eligo':
        return 'HTC Droid Eris'
    elif name == 'Gapps':
        return 'Google Apps'
    elif name == 'Iaceo':
        return 'HTC Amaze 4G'
    elif name == 'Mirus':
        return 'Google Nexus 7'
    elif name == 'Neco':
        return 'HTC Evo 3D'
    elif name == 'Perdo':
        return 'Google Nexus One'
    elif name == 'Primo':
        return 'Samsung Galaxy Nexus (VZW)'
    elif name == 'Queo':
        return 'HP Touchpad'
    elif name == 'Turba':
        return 'HTC Desire (GSM)'
    else:
        return 'Other'

def is_device(name):
    if name == 'Acies':
        return True
    elif name == 'Artis':
        return True
    elif name == 'Bellus':
        return True
    elif name == 'Dives':
        return True
    elif name == 'Conor':
        return True
    elif name == 'Eligo':
        return True
    elif name == 'Gapps':
        return True
    elif name == 'Iaceo':
        return True
    elif name == 'Mirus':
        return True
    elif name == 'Neco':
        return True
    elif name == 'Perdo':
        return True
    elif name == 'Primo':
        return True
    elif name == 'Queo':
        return True
    elif name == 'Turba':
        return True
    else:
        return False

script, base_path = argv
base_url = 'http://ev-dl1.deuweri.com'
warning_message = ['<p>This list may be incomplete.</p>', '<p>If you dont see what you want try browsing <a href="http://ev-dl1.deuweri.com/">ev-dl1.deuweri.com</a></p>']
page_title('Evervolv Releases')
#base_url = 'r'

staging = []
for d in sorted(os.listdir(base_path)):
    if os.path.isdir(os.path.join(base_path,d)):
        z = [ f for f in sorted(os.listdir(os.path.join(base_path,d))) \
                    if f.endswith('.zip') ]
        staging.append((d,z))

final = []
for i in staging:
    if i[1] and is_device(i[0]):
        final.append((get_device_name(i[0]), [ j for j in \
                html.list_to_links_with_analytics(i[1], '%s/%s' % (base_url, i[0]), \
                'ReleaseClick') ]))

sorted(final)
r = html.Create()
r.title(page_title)
r.analytics(analytics.Get())
r.header(page_title)
r.body(warning_message)
r.body(html.tup_to_ul(final))
r.write('releases.html')
