#!/usr/bin/env python

import pyratemp
import Queue
import BaseHTTPServer, os, subprocess, re, sys, threading, webbrowser
from SimpleHTTPServer import SimpleHTTPRequestHandler

DELAY = 0.5
DEFAULT_PORT = 14141
PROTOCOL = "HTTP/1.0"

SCRIPT_DIR = os.path.realpath(os.path.dirname(sys.argv[0]))

CHANGE_RE = "^\d+(?:,\d+)?[acd]\d+(?:,\d+)?$"

ipq = Queue.Queue()
class CleanExit:
    pass

def main(argv):
    
    if len(argv) != 3:
        print "usage: diff-vis file1 file2"
        sys.exit(1)

    #check if files exist. make sure we are using the same relative path as from the shell
    file1 = argv[1]
    file2 = argv[2]
    for f in (file1, file2):
        if not os.path.exists(f):
            print "ERROR: file",f,"does not exist"
            sys.exit(1)

    #run diff on the two input files
    p = subprocess.Popen(["diff", file1, file2], stdout=subprocess.PIPE)
    diff, err = p.communicate()
    
    #parse the diff result
    data = diff.split('\n')
    diffs = []
    for line in data:
        if re.match(CHANGE_RE,line):
            diff = {"position":line, "new":[], "old":[]}
            diffs.append(diff)
            continue
        
        if line.startswith("> "):
            diff["new"].append(line[2:])
        elif line.startswith("< "):
            diff["old"].append(line[2:])
        
    data = diffs

    #spawn the webserver
    spawn(data)

class DiffPageHandler(BaseHTTPServer.BaseHTTPRequestHandler):
        
    def do_GET(self):
        
        params = {"diffs": self.data}
        
        t = pyratemp.Template(filename=SCRIPT_DIR + "/index.html")
        result = t(**pyratemp.dictkeyclean(params))
        
        self.wfile.write(result)
        
    def do_POST(self):
        
        self.wfile.write("")
        ipq.put(CleanExit)

def spawn(data):

    RequestHandler = DiffPageHandler
    RequestHandler.data = data
    RequestHandler.protocol = PROTOCOL

    httpd = BaseHTTPServer.HTTPServer(("localhost",DEFAULT_PORT),RequestHandler)
    tr = fork_httpd(httpd)

    RequestHandler.thread = tr

    webbrowser.open("http://localhost:%d/" % DEFAULT_PORT)

    try:
        while True:
            tr.join(DELAY)
            try:
                if ipq.get(False) == CleanExit:
                    sys.exit(0)
            except Queue.Empty:
                pass
    except KeyboardInterrupt:
        sys.exit(0)
        

def fork_httpd(httpd):
    tr = threading.Thread(target=httpd.serve_forever)
    tr.setDaemon(True)
    tr.daemon = True
    tr.start()
    return tr


if __name__ == "__main__":
    main(sys.argv)
