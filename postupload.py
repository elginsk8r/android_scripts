#!/usr/bin/env python

from sys import argv
import os

script, directory = argv

dirlist = sorted(os.listdir(directory))

analytics = """
<script type="text/javascript">
 var _gaq = _gaq || [];
 _gaq.push(['_setAccount', 'UA-18083075-6']);
 _gaq.push(['_trackPageview']);
(function() {
    var ga = document.createElement('script'); ga.type = 'text/javascript'; ga.async = true;
    ga.src = ('https:' == document.location.protocol ? 'https://ssl' : 'http://www') + '.google-analytics.com/ga.js';
    var s = document.getElementsByTagName('script')[0]; s.parentNode.insertBefore(ga, s);
  })();
</script>
"""

hheader  = '<!DOCTYPE html>\n<html>\n<head>\n'
hheader += '<title>Evervolv Nightlies</title>'
hheader += analytics
hheader += '</head>\n<body>\n'

hbody  = '<h3>Evervolv Nightly Builds</h3>\n<ul>\n'
hbody += '    <li><a href="..">Go Back</a></br></li>\n'

for dirname in dirlist:
    if os.path.isdir(os.path.join(directory, dirname)):
        hbody += '    <li><a href="%s" onClick="_gaq.push([\'_trackEvent\', \'NightlyClick\', \'%s\']);">%s</a><br></li>\n' % (dirname, dirname, dirname)

hbody += '</ul>\n'

hfooter = '</body>\n</html>'

f = open(os.path.join(directory, "index.html"), "w")
f.write(hheader + hbody + hfooter)
f.close()
