#!/usr/bin/env python

import argparse
import datetime
import pickle
import socket
import sys
import os
from os.path import normpath, join, expanduser, isdir

import golumn
from golumn.App import GolumnApp, HOST, PORT


def create_parser():
    parser = argparse.ArgumentParser(
        prog='golumn',
        description='View data based on OPTIONS. Use "-" as FILE to read from stdin.',
        usage='%(prog)s  [OPTIONS] FILE',
    )

    parser.add_argument(
        '-t', '--title',
        dest='title',
        metavar='TITLE',
        help='Window TITLE of result set')

    parser.add_argument(
        '--version',
        action='version',
        version=golumn.__version__)

    parser.add_argument('filename', nargs='?')

    return parser


def golumn_home():
    home = expanduser("~")
    return normpath(join(home, '.golumn'))


def history_dir():
    return normpath(join(golumn_home(), 'history'))


def setup():
    if not isdir(golumn_home()):
        os.mkdir(golumn_home())

    if not isdir(history_dir()):
        os.mkdir(history_dir())


def new_hist_file():
    return normpath(join(history_dir(),
        datetime.datetime.now().strftime('%Y-%m-%dT%H:%M:%S.csv')))


def send_server(args):
    """
    Try to send args to an existing application.
    @return false if it can't cannect to one.
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((HOST, PORT))

        package = {'args': args, 'data': None}
        if not args.filename:
            package['data'] = sys.stdin.read()
        s.sendall(pickle.dumps(package))
        s.close()
        return True
    except socket.error:
        return False


def main(args=None):
    parser = create_parser()
    args = parser.parse_args(args)

    setup()

    # when no file is passed in. Assume use is piping in the data.
    if args.filename is None:
        args.filename = new_hist_file()
        with open(args.filename, 'w+b') as dst:
            dst.write(sys.stdin.read())

    if send_server(args):
        sys.exit(0)

    # we must be the first instance, start it up
    app = GolumnApp(useBestVisual=True)
    title = args.title or os.path.basename(args.filename or '-')
    app.LoadPath(title, args.filename)
    app.MainLoop()
    return 0
