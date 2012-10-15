#!/bin/bash

html_start () {
    local html_file=$1
    cat <<EOF > $html_file
<!DOCTYPE html>
<html><body>
EOF
}

html_header () {
    local html_file=$1
    local header=$2
    cat <<EOF >> $html_file
<h3>$header</h3>
EOF
}

html_body () {
    local html_file=$1
    local readfile=$2
    cat <<EOF >> $html_file
<p>$(cat $readfile | sed ':a;N;$!ba;s/\n/\<br\>/g')</p>
EOF
}

html_end () {
    local html_file=$1
    cat <<EOF >> $html_file
</body></html>
EOF
}

html_start $EV_HTML_CHANGELOG
html_header $EV_HTML_CHANGELOG $(basename $EV_CHANGELOG)
html_body $EV_HTML_CHANGELOG $EV_CHANGELOG
html_end $EV_HTML_CHANGELOG

html_start $EV_HTML_BUILDLOG
html_header $EV_HTML_BUILDLOG $(basename $EV_BUILDLOG)
html_body $EV_HTML_BUILDLOG $EV_CHANGELOG
html_end $EV_HTML_BUILDLOG
