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
n.script('<script type="text/javascript" src="js/jquery-1.4.2.min.js"></script>')
n.script('<script type="text/javascript" src="js/scripts.js"></script>')
n.script(analytics.Get())
n.header(page_title)
n.body( [ '<div id="listContainer">',
          ' <div class="listControl">',
          '  <a id="expandList">Expand all</a>',
          '  <a id="collapseList">Collapse all</a>',
          ' </div>' ] +
        html.tup_to_ul(final,True) +
        [ '</div>' ])
n.write('nightlies.html')
