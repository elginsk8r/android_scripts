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

#menu {
    list-style: none;
    padding: 0;
    margin: 0;
}

.clear {
    clear: both;
}

#listContainer{
  margin-top:15px;
}

#expList ul, li {
    list-style: none;
    margin:0;
    padding:0;
    cursor: pointer;
}
#expList p {
    margin:0;
    display:block;
}
#expList p:hover {
    background-color:#121212;
}
#expList li {
    line-height:140%;
    text-indent:0px;
    background-position: 1px 8px;
    padding-left: 20px;
    background-repeat: no-repeat;
}

/* Collapsed state for list element */
#expList .collapsed {
    background-image: url(img/collapsed.png);
}
/* Expanded state for list element
/* NOTE: This class must be located UNDER the collapsed one */
#expList .expanded {
    background-image: url(img/expanded.png);
}
#expList {
    clear: both;
}

.listControl{
  margin-bottom: 15px;
}
.listControl a {
    border: 1px solid #555555;
    color: #555555;
    cursor: pointer;
    height: 1.5em;
    line-height: 1.5em;
    margin-right: 5px;
    padding: 4px 10px;
}
.listControl a:hover {
    background-color:#555555;
    color:#222222;
    font-weight:normal;
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
r.script('<script type="text/javascript" src="js/jquery-1.4.2.min.js"></script>')
r.script('<script type="text/javascript" src="js/scripts.js"></script>')
r.script(analytics.Get())
r.header(page_title)
r.body(warning_message)
r.body([ '<div id="listContainer">',
         ' <div class="listControl">',
         '  <a id="expandList">Expand all</a>',
         '  <a id="collapseList">Collapse all</a>',
         ' </div>' ])
r.body(html.tup_to_ul(final,True))
r.body([ '</div>' ])
r.write('releases.html')
