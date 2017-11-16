# Golumn

Golumn is a visual data viewer. `column` with a "g". It behaves similar to the
`column` command, but with a graphic user interface. It bridges the command line
and desktop divide by allowing us to present tabular data outside the confines
of the terminal.

<img src='https://user-images.githubusercontent.com/1975119/32884159-0a16cbae-ca7f-11e7-96a0-e703a7cbcde3.png' alt='screenshot' />

The challenges without this tool is attempting managing a bunch of tabular
output within only a terminal alone. It's difficult to maintain context when
long scrolling text and we're often executing the same statements to bring up
previous results.

A typical workflow without this tool is chain together commands:

```sh
# psql
#   -A :: remove whitespace
#   -c :: run the SQL statement
# column
#   -t :: table-ize
#   -s :: set delimiter
# less
#   -S :: Scroll horizontally (enables left/right arrows)
psql -Ac 'select * from pg_tables' | column -ts '|' | less -S
```

When you're done viewing the data it disappears. Leaving you to remember what
you saw as you're building the next statement. We could (and probably should)
manage our terminal windows better with splits and tabs, but there's limits
which desktop GUI's have solved. Enter `golumn`.

## Usage

```sh
# Open a CSV file:
golumn data.csv &

# Pipe in the data:
cat data.csv | golumn &

# Show Query Results:
psql -Ac 'select * from pg_tables' | golumn &
```

## Installation

This package is available via https://pypi.python.org/pypi.
To install on your system try:
```sh
pip install golumn --upgrade --user
# --upgrade ensures you get the latest version
# --user install only for your user
```
For more info on install pip packages see: https://pip.pypa.io/en/stable/quickstart/

Make sure `pip` binaries are available in your `$PATH`:

```sh
pip show golumn
# => Name: golumn
# => Version: 0.3.0
# => Summary: Graphical CSV viewer. `column` with a "g"
# => Home-page: https://github.com/ddrscott/golumnpy
# => Author: Scott Pierce
# => Author-email: ddrscott@gmail.com
# => License: MIT
# => Location: /Users/scott.pierce/Library/Python/2.7/lib/python/site-packages
# => Requires: wxPython
```

In the above case I need to ensure `~/Library/Python/2.7/bin` was in my `$PATH`


## Contributing

Bug reports and pull requests are welcome on GitHub at https://github.com/ddrscott/golumnpy

## Feature List
- [x] Zoom fonts via CMD++, CMD+-, CMD+0
- [x] Filter by Selection via SHIFT+CMD+S
- [x] Remove Filter via SHIFT+CMD+R
- [x] Sort by Current Column A to Z SHIFT+CMD+A
- [x] Sort by Current Column Z to A SHIFT+CMD+Z
- [x] Single App Instance
- [ ] Search filter across all columns
- [ ] History List
- [ ] `--update` flag to refresh data for last frame
- [ ] `--height num` argument to allow sizing the frame by percentage or pixels
- [ ] `--width num` argument to allow sizing the frame by percentage or pixels
- [ ] `--headers x,a,z` argument to specify headers instead of auto detecting

## License

The gem is available as open source under the terms of the [MIT License](https://opensource.org/licenses/MIT).
