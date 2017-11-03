#!/usr/bin/env python

import argparse
import sys
import os
import csv
import tempfile

import golumn
from golumn.App import GolumnApp


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


def _error(msg):
    """Print msg and optionally exit with return code exit_."""
    sys.stderr.write(u'[ERROR] {0}\n'.format(msg))
    return 1


def main(args=None):
    parser = create_parser()
    args = parser.parse_args(args)

    app = GolumnApp(useBestVisual=True)
    input_file = None
    try:
        if args.filename is None:  # read from stdin
            input_file = tempfile.SpooledTemporaryFile()
            input_file.write(sys.stdin.read())
            input_file.seek(0)
        else:
            input_file = open(args.filename, 'rb')

        title = args.title or os.path.basename(args.filename or '-')
        app.LoadFile(title, input_file)
        app.MainLoop()
    finally:
        input_file.close()
    return 0
