#!/usr/bin/env python3
"""Browse and import a SQLite command reference using only Python's standard library."""
import argparse
import json
from pathlib import Path
import sqlite3
import sys

DEFAULT_DB = Path(__file__).resolve().parent / 'commands.sqlite3'
FIELDS = ('description', 'category', 'platforms', 'notes', 'risk', 'used_for', 'caution')


def import_file(db, filename):
    data = json.loads(Path(filename).read_text(encoding='utf-8'))
    records = data.get('commands') if isinstance(data, dict) else data
    if not isinstance(records, list):
        raise ValueError('Expected a list or an object containing a commands list.')
    # Validate the entire input before changing the database.
    for i, record in enumerate(records, 1):
        if not isinstance(record, dict) or not isinstance(record.get('command'), str) or not record['command'].strip():
            raise ValueError(f'Record {i}: command must be a nonempty string.')
        for field in FIELDS:
            value = record.get(field, [] if field == 'platforms' else '')
            if field == 'platforms':
                if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
                    raise ValueError(f'Record {i}: platforms must be a list of strings.')
            elif not isinstance(value, str):
                raise ValueError(f'Record {i}: {field} must be a string.')
    with sqlite3.connect(db) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS commands (
            id INTEGER PRIMARY KEY, command TEXT NOT NULL UNIQUE,
            description TEXT NOT NULL, category TEXT NOT NULL,
            platforms TEXT NOT NULL, notes TEXT NOT NULL, risk TEXT NOT NULL,
            used_for TEXT NOT NULL, caution TEXT NOT NULL)''')
        before = conn.total_changes
        for record in records:
            values = [json.dumps(record.get(f, [])) if f == 'platforms' else record.get(f, '') for f in FIELDS]
            conn.execute('INSERT INTO commands (command, description, category, platforms, notes, risk, used_for, caution) VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(command) DO NOTHING', [record['command'].strip(), *values])
        added = conn.total_changes - before
    return added, len(records) - added


def connect(db):
    conn = sqlite3.connect(Path(db).resolve().as_uri() + '?mode=ro', uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def search(conn, query='', category=''):
    return conn.execute('''SELECT * FROM commands WHERE
        (? = '' OR instr(lower(command || ' ' || description || ' ' || category || ' ' || notes || ' ' || used_for || ' ' || caution || ' ' || platforms), lower(?)) > 0)
        AND (? = '' OR category = ?) ORDER BY category, command''', (query, query, category, category)).fetchall()


def listing(rows):
    for row in rows:
        print(f"{row['id']:>4}  [{row['category']}] {row['command']}")
    print(f'{len(rows)} command(s)')


def detail(conn, ident):
    row = conn.execute('SELECT * FROM commands WHERE id = ?', (ident,)).fetchone()
    if row is None:
        print('Command not found.')
        return
    print(f"\n#{row['id']}  {row['command']}")
    for field in FIELDS:
        value = ', '.join(json.loads(row[field])) if field == 'platforms' else row[field]
        if value:
            print(f'{field.replace("_", " ").capitalize()}: {value}')


def browse(conn):
    rows, page = search(conn), 0
    while True:
        print(f'\nPage {page + 1}/{max(1, (len(rows) + 14) // 15)}')
        listing(rows[page * 15:(page + 1) * 15])
        print('n next | p previous | s search | c category | a all | ID details | q quit')
        try:
            choice = input('> ').strip()
            if choice == 'q':
                return
            if choice == 'n':
                page = min(page + 1, max(0, (len(rows) - 1) // 15))
            elif choice == 'p':
                page = max(0, page - 1)
            elif choice == 's':
                rows, page = search(conn, input('Search: ')), 0
            elif choice == 'c':
                categories = [r[0] for r in conn.execute('SELECT DISTINCT category FROM commands ORDER BY category')]
                for i, category in enumerate(categories, 1):
                    print(f'{i}. {category}')
                selected = input('Category number: ')
                if selected.isdigit() and 1 <= int(selected) <= len(categories):
                    rows, page = search(conn, category=categories[int(selected) - 1]), 0
                else:
                    print('Invalid category.')
            elif choice == 'a':
                rows, page = search(conn), 0
            elif choice.isdigit():
                detail(conn, int(choice))
                input('\nEnter to return: ')
            else:
                print('Choose a listed action or command ID.')
        except EOFError:
            return


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', type=Path, default=DEFAULT_DB)
    sub = parser.add_subparsers(dest='action')
    sub.add_parser('browse')
    p = sub.add_parser('search')
    p.add_argument('query', nargs='?', default='')
    p.add_argument('--category', default='')
    p = sub.add_parser('show')
    p.add_argument('id', type=int)
    sub.add_parser('categories')
    p = sub.add_parser('import')
    p.add_argument('file', help='Exactly one explicitly selected JSON file')
    args = parser.parse_args()
    try:
        if args.action == 'import':
            added, skipped = import_file(args.db, args.file)
            print(f'Imported {added}; skipped {skipped} duplicate(s).')
            return 0
        with connect(args.db) as conn:
            if args.action == 'search':
                listing(search(conn, args.query, args.category))
            elif args.action == 'show':
                detail(conn, args.id)
            elif args.action == 'categories':
                for row in conn.execute('SELECT category, count(*) FROM commands GROUP BY category ORDER BY category'):
                    print(f'{row[0]} ({row[1]})')
            else:
                browse(conn)
        return 0
    except (OSError, ValueError, sqlite3.Error) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print()
        return 130


if __name__ == '__main__':
    sys.exit(main())
