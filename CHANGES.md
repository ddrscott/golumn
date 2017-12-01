# Change Log

## 0.8.1
- Handle headers with illegal characters

## 0.8.0
- Align numeric columns to the right (Issue #5)
- Open frame in active display
- Ensure grid cell is selected after click
- Fixed connection errors between main and background thread
- Fix row index synchronization. (Issue #8)

## 0.7.3
- drop Pandas due to incompatibilities with py2app

## 0.7.0
- dropped support for Python 2.7
  - for use of lru_cache
- import into SQLite3 database to reduce memory use
  - removed regexp search across columns
- use Pandas for CVS parsing and type matching

## 0.6.0
- Add search across columns
