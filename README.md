# Bash Command DB

A terminal reference for shell commands, backed by the included `commands.sqlite3` database. Python 3.8+ is required; there are no third-party dependencies. Source JSON files stay local and are not needed to browse the database.

## Start

From this directory:

```sh
python3 bashdb.py
```

Use `n`/`p` for pages, `s` to search, `c` to select a category, `a` for all commands, a command ID to read details, or `q` to quit. Commands are displayed as reference text; the application never executes them. Descriptions and cautions come from the supplied archives and are not independently verified.

You can also query directly:

```sh
python3 bashdb.py search git
python3 bashdb.py search --category 'Package repair'
python3 bashdb.py categories
python3 bashdb.py show 1
```

Search matches literal text in commands and metadata, case-insensitively for ASCII. Browsing opens SQLite read-only. The default database is located beside `bashdb.py`, even when launched from another directory. Use `--db PATH` before a subcommand to select another database.

## Import a selected JSON file

```sh
python3 bashdb.py import path/to/commands.json
```

Accepts a JSON list of command objects or an object with a `commands` list. Each record must have a nonempty string `command`. Optional string fields are `description`, `category`, `notes`, `risk`, `used_for`, and `caution`; `platforms` is a list of strings. All records are validated before insertion, and each import uses a transaction.

Commands are unique by case-sensitive text with outer whitespace removed. Duplicates are skipped without overwriting existing metadata. Internal whitespace and quoting remain significant. Repeating an import adds no duplicates. Generated database IDs replace source IDs; other source fields and dataset-level metadata are omitted.

The initial database is populated from `developer_command_archive.json` and `linux_troubleshooting_bash_commands.json`. Future agent imports follow [AGENTS.md](AGENTS.md) and process only the source explicitly named by the user.

## Version control

Commit `bashdb.py`, `commands.sqlite3`, `README.md`, `AGENTS.md`, `.gitignore`, and `tests/`. JSON sources are ignored at every directory level. Clones receive the populated database and can use the program immediately. The database contents are shared with anyone who receives the repository.

This folder was not a Git repository when the prototype was created. To initialize it and stage the deliverables:

```sh
git init
git add .gitignore README.md AGENTS.md bashdb.py commands.sqlite3 tests/
git commit -m "Add terminal command database prototype"
```

Ignore rules do not remove files already tracked by Git or erase prior history. SQLite is a binary file: coordinate database updates to avoid conflicting changes across branches.

## Validation

```sh
python3 -m unittest discover -s tests
```

Tests cover duplicate handling, preservation of existing metadata and shell whitespace, input validation, search, database integrity, and read-only browsing.
