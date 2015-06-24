#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright (c) 2013,2014 Jérémie DECOCK (http://www.jdhp.org)

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

# see: https://docs.python.org/3.3/library/subprocess.html#module-subprocess

import argparse
import datetime
import sys
import os
import subprocess

CONFIG_DIR="/etc/piclockradio"
DEFAULT_RADIO="mpr"

# If you launch a sub-process (even with shell=False), then the
# subprocess.Popen.kill() function will only kill that sub-process (so if there
# are any "grandchild" processes, they won't be terminated.).
# See: http://stackoverflow.com/questions/3908063/python-subprocess-with-shell-true-redirections-and-platform-independent-subproc
#
# The solution is to use preexec_fn to cause the subprocess to acquire it's own
# session group (then a signal is sent to all processes in that session group).
# See: http://stackoverflow.com/questions/3876886/timeout-a-subprocess

###############################################################################

def get_web_radio_dict():
    """Parse web radios"""

    filename = os.path.join(CONFIG_DIR, "radio", "web_radios.txt")

    if not os.path.isfile(filename):
        print "ERROR: can't find data {0}".format(filename)
        sys.exit(1)

    if os.path.splitext(filename)[1] == ".gz":
        # FILENAME IS COMPRESSED
        fd = gzip.open(filename, "rU")
    else:
        # FILENAME ISN'T COMPRESSED
        fd = open(filename, "rU")

    ## PRETTY NAME
    #pretty_name = fd.readline().strip()
    #if pretty_name == "":
    #    pretty_name = filename

    # LOGO
    # TODO

    # WEBRADIOS
    web_radio_dict = {}
    for line in fd.readlines():
        item = line.split()
        if len(item) == 2:
            web_radio_dict[item[0]] = item[1].strip()
    fd.close()

    return web_radio_dict

###############################################################################


def play_radio(radio_id, timeout=None):
    """Attention: Appel bloquant"""

    web_radio_dict = get_web_radio_dict()
    url = web_radio_dict[radio_id]

    try:
        output = subprocess.check_output(['omxplayer', url], stderr=subprocess.STDOUT, universal_newlines=True, timeout=timeout)
        #output = subprocess.check_output(args, stderr=subprocess.STDOUT, universal_newlines=True, timeout=timeout, preexec_fn=os.setsid)
        #print(output)
    except OSError as e:
        print("Execution failed:", e, file=sys.stderr)
    except subprocess.CalledProcessError as e:
        print("Execution failed:", e, file=sys.stderr)
        #print("  Return code:", e.returncode, file=sys.stderr)
        #print("  Output message:", e.output, file=sys.stderr)
    except subprocess.TimeoutExpired as e:
        print("Timeout", file=sys.stderr)
        #print("  Output message:", e.output, file=sys.stderr)
        #print("  Timeout:", e.timeout, file=sys.stderr)


###############################################################################

def main():

    if not os.path.isdir(CONFIG_DIR):
        print "ERROR: can't find {0}".format(CONFIG_DIR)
        sys.exit(1)

    # PARSE ARGUMENTS #########################################################

    parser = argparse.ArgumentParser(description='A smart alarm for Raspberry Pi.')

    parser.add_argument("--radio", "-r",  help="the name of the radio to play", metavar="STRING", default=DEFAULT_RADIO)
    parser.add_argument("--duration", "-d",  help="the number of seconds before the alarm stop", metavar="INTEGER", type=int)

    args = parser.parse_args()

    # LAUNCH OMXPLAYER ########################################################

    try:
        play_radio(args.radio, args.duration)
    except:
        print "ERROR: radio failed."

    # KILL ALL ################################################################

    #os.kill(0, 15)

if __name__ == '__main__':
    main()

