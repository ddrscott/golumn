Golumn
======

Golumn is a desktop CSV viewer to replace the ``column``. Think ``column`` with
a "g". It behaves similar to the ``column`` command, but with a graphic user
interface. It bridges the command line and desktop divide by allowing us to
present tabular data outside the confines of the terminal.

.. class:: no-web

    .. image:: https://raw.githubusercontent.com/ddrscott/golumn/dev/docs/screenshot.png
        :alt: screenshot
        :width: 100%
        :align: center

It is challenging without this tool to manage a bunch of
tabular output within only a terminal window. It's difficult to maintain
context when long scrolling text and we're often executing the same
statements to bring up previous results.

A typical workflow without this tool is chain together commands:

.. code:: sh

    # psql
    #   -X :: ignore ~/.psqlrc 
    #   -A :: remove whitespace
    #   -c :: run the SQL statement
    # column
    #   -t :: table-ize
    #   -s :: set delimiter
    # less
    #   -S :: Scroll horizontally (enables left/right arrows)
    psql -X -A --pset footer -c 'select * from actors_list' dvdrental | column -ts '|' | less -S

When you're done viewing the data it disappears. Leaving you to remember
what you saw as you're building the next statement. We could (and
probably should) manage our terminal windows better with splits and
tabs, but there's limits which desktop GUI's have solved. Enter
``golumn``.

Usage
-----

.. code:: sh

    # Open a CSV file:
    golumn data.csv &

    # Pipe in the data:
    cat data.csv | golumn &

    # Show Query Results:
    psql -X -A --pset footer -c 'select * from actors_list' dvdrental | golumn &

Installation
------------

Requires Python3. Please makes sure it's installed property on target OS with
Pip package manager.

This package is available via https://pypi.python.org/pypi. To install
on the target system try:

.. code:: sh

    pip3 install golumn --upgrade --user
    # --upgrade ensures you get the latest version
    # --user install only for your user

For more info on install pip packages see:
https://pip.pypa.io/en/stable/quickstart/

Make sure ``pip3`` binaries are available in your ``$PATH``:

Contributing
------------

Bug reports and pull requests are welcome on GitHub at
https://github.com/ddrscott/golumn

Feature List
------------

-  [x] Zoom fonts via CMD++, CMD+-, CMD+0
-  [x] Filter by Selection via SHIFT+CMD+S
-  [x] Remove Filter via SHIFT+CMD+R
-  [x] Sort by Current Column A to Z SHIFT+CMD+A
-  [x] Sort by Current Column Z to A SHIFT+CMD+Z
-  [x] Single App Instance
-  [x] Search filter across all columns
-  [ ] History List
-  [ ] ``--update`` flag to refresh data for last frame
-  [ ] ``--height num`` argument to allow sizing the frame by percentage
   or pixels
-  [ ] ``--width num`` argument to allow sizing the frame by percentage
   or pixels
-  [ ] ``--headers x,a,z`` argument to specify headers instead of auto
   detecting

License
-------

The gem is available as open source under the terms of the `MIT License <https://opensource.org/licenses/MIT>`__.
