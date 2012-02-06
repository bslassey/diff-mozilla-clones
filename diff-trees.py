import subprocess
from subprocess import Popen, PIPE
import urllib2
import simplejson
import re
import math
from datetime import datetime
import os

srcdir_1 = "./mozilla-aurora"
srcdir_2 = "./mozilla-beta"
directories_of_interest = "mobile/android widget/src/android widget/android"
aurora_merge_date_str = "2011-12-21"
aurora_merge_date = datetime.strptime(aurora_merge_date_str, "%Y-%m-%d");

landedBugs = {}
unlandedBugs = []

def getBugInfo(bug):
    try:
        spec = "https://api-dev.bugzilla.mozilla.org/latest/bug/" + bug
        print "Getting: " + spec
        req = urllib2.Request(spec, None, {'user-agent':'dougt/rocks', 'Content-Type': 'application/json'})
        opener = urllib2.build_opener()
        f = opener.open(req)
        result = simplejson.load(f)
        not11 = "false"
        if datetime.strptime(result['last_change_time'], '%Y-%m-%dT%H:%M:%SZ') < aurora_merge_date:
            return None
        try:
            if "not-fennec-11" in result['whiteboard']:
                return None
        except KeyError:
            not11 = "false"
        return result['assigned_to']['real_name'], result['summary'], not11
    except urllib2.HTTPError:
        return "Stuart", "I do not have a pony. See bug " + bug, "true"

def getLandedBugs(srcdir, dirs_to_diff):
    cmd = "hg log -d \">" + aurora_merge_date_str + "\" --template '{desc|firstline}\n' " + dirs_to_diff
    p = Popen(cmd, cwd=srcdir, shell=True, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate()
    lines = stdout.splitlines()
    for line in lines:
        try: # if the bugNum isn't a number it'll throw
            bugNum = int(line[4:10], 10)
            print "bug number: " + str(bugNum)
            landedBugs[bugNum] = True
        except ValueError:
            print "not a bug: " + line
            

def getUnlandedBugs(srcdir, dirs_to_diff):
    cmd = "hg log -d \">" + aurora_merge_date_str + "\" --template '{rev}\t{node|short}\t{author}\t{desc|firstline}\n' " + dirs_to_diff
    p = Popen(cmd, cwd=srcdir, shell=True, stdin=PIPE, stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate()
    lines = stdout.splitlines()
    for line in lines:
        tmp = line.partition('\t')
        rev = tmp[0]
        remander = tmp[2].partition('\t')
        changeset = remander[0]
        remander2 = remander[2].partition('\t')
        author = remander2[0]
        summary = remander2[2]
        try: # if the bugNum isn't a number it'll throw
            bugNum = int(summary[4:10], 10)
            print "bug num: " + str(bugNum)
            if not landedBugs.has_key(bugNum):
                tup = rev, bugNum, changeset, author, summary
                unlandedBugs.append(tup)
        except ValueError:
            print "not a bug: " + summary

print "updating source directories:"
subprocess.call(["hg", "pull", "-u"], cwd=srcdir_2)
subprocess.call(["hg", "pull", "-u"], cwd=srcdir_1)

print "collecting data about " + srcdir_2
getLandedBugs(srcdir_2, directories_of_interest)

print "collecting data about " + srcdir_1
getUnlandedBugs(srcdir_1, directories_of_interest)

print str(len(unlandedBugs)) + " havent' landed in " + srcdir_2

html_out =\
\
"<html><head><title>Diff Between" + srcdir_1 + " and " + srcdir_2 + "</title><style>"\
"#container {width: 100%; display: table;}"\
".row { display: table-row;}"\
".bugnum { width: 15%; display: table-cell;}"\
".owner { width: 25%; display: table-cell;}"\
".summary { width: 60%; display: table-cell;}"\
"</style>\n" \
"<script>\n" \
"function openAllBugs() {\n" \
"  var bugs = document.getElementsByTagName(\"a\");\n" \
"  for (a in bugs) {\n" \
"    try {\n" \
"      var decor = bugs[a].parentNode.parentNode.style.textDecoration;\n" \
"      if (decor != \"line-through\")\n" \
"        window.open(bugs[a].getAttribute(\"href\"));\n" \
"    } catch(e) {}\n" \
"  }\n" \
"}\n" \
"</script>\n" \
"</head><body>"\
"<h1>Diff Between" + srcdir_1 + " and " + srcdir_2 + "</h1>"\
"<div id=\"container\">\n" \
"<button onClick=\"openAllBugs()\">Open All Bugs</button>\n"
written_out_bugs = {}
unlandedBugs.sort()
try:
    os.mkdir("patches")
except OSError:
    print "patches dir exists"
series_file = open("./patches/series", "w")
for index in unlandedBugs:
    print index
    bugNum = index[1]
    rev = index[0]
    changeset = index[2]
    author = index[3]
    summary = index[4]
    not11 = False
    if not written_out_bugs.has_key(bugNum):
        written_out_bugs[bugNum] = True
        print "bug number: " + str(bugNum) + " rev: " + rev
        #info = getBugInfo(str(bugNum))
        #if info is None:
        #    continue
        html_out += "<div class=\"row\" "
        if not11:
            html_out += "style=\"text-decoration: line-through;\""
        html_out += ">\n"
        html_out += "\t<span class=\"bugnum\"> <a href=\"https://bugzilla.mozilla.org/show_bug.cgi?id=" + str(bugNum) + "\">" + str(bugNum) + "</a></span>"
        html_out += "<span class=\"owner\">" + author + "</span>"
        html_out += "<span class=\"summary\">" + summary + "</span>\n"
        html_out += "</div>\n"
    print "creating changeset file"
    patch_file = open("patches/" + changeset, "w")
    print "exporting changeset"
    cmd = "hg export " + changeset
    p = Popen(cmd, cwd=srcdir_1, shell=True, stdin=PIPE, stdout=patch_file, stderr=PIPE)
    p.communicate()
    print "closing changeset file"
    patch_file.close()
    print "writing series file"
    series_file.write(changeset + " # rev: " + rev + " bug " + str(bugNum) + " " + author + " " + summary +"\n")


html_out += "</div></body></html>"


fout = open("data.html", "w")
fout.write(html_out.encode('UTF-8'))
fout.close()
series_file.close()
