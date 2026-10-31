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

## Database schema and reference format

`commands.sqlite3` contains one table, `commands`, with no foreign keys or separate metadata tables:

| Column | SQLite definition | Content |
| --- | --- | --- |
| `id` | `INTEGER PRIMARY KEY` | Stable, database-generated entry ID |
| `command` | `TEXT NOT NULL UNIQUE` | Case-sensitive command text, or a reference-entry title |
| `description` | `TEXT NOT NULL` | Purpose |
| `category` | `TEXT NOT NULL` | Browsing category, such as Git, GitHub, or Filesystem |
| `platforms` | `TEXT NOT NULL` | JSON-encoded list of platform strings; `[]` when unspecified |
| `notes` | `TEXT NOT NULL` | Usage notes; enriched entries include `Syntax:` and `Example:` lines |
| `risk` | `TEXT NOT NULL` | Informational label such as `normal` or `review`; empty when unspecified |
| `used_for` | `TEXT NOT NULL` | Practical purpose or workflow context |
| `caution` | `TEXT NOT NULL` | Relevant limitations and cautions |

The unique constraint creates SQLite's automatic index on `command` using the default case-sensitive BINARY collation. The importer trims outer whitespace before matching; internal whitespace, quoting, and case remain significant. There are no column defaults: the importer supplies empty strings for omitted text metadata and `[]` for omitted platforms. Syntax and examples use existing fields so the Python application needs no schema migration. Reference entries are explicitly marked as prose, not executable commands.

The Git, GitHub CLI, and file-management update adds 8 entries and enriches 18 existing entries, bringing the catalog to 115. Existing IDs, command strings, and unrelated records are preserved. Importing still skips existing commands; metadata enrichment is a separate, explicitly requested database edit.

## Parallel terminals and SSH collaboration

Multiple terminals or SSH sessions on the same computer can use the same repository folder. Saved file changes are immediately shared; reconnecting or pulling is unnecessary for edits in that folder. Unsaved editor buffers are not shared. Changes pushed from another computer require pulling to update the checkout. Separate clones, even on one computer, need synchronization.

Different-file edits can coexist, but the working tree and staging area are shared. `git add .` may stage everyone's changes. Stage specific paths, review `git diff --cached`, and coordinate commits, pulls, and branch switches. The database includes a searchable “Parallel terminals and SSH collaboration” reference entry.

Troubleshooting:

- A regular folder needs `git init` or a proper `git clone` before remote commands work.
- A commit is local until pushed; `git log -1` alone does not prove it reached GitHub.
- Do not copy nested `.git` directories into a parent repository. The catalog's `rsync` command excludes `.git` at every depth. Its trailing source slash copies contents; matching files can be overwritten, while destination-only files remain. See the [rsync manual](https://download.samba.org/pub/rsync/rsync.1).
- `~` does not expand inside quotes; use `"$HOME/path"` for quoted home-directory paths.
- Replace placeholder URLs with actual URLs, omitting literal `<` and `>` characters.
- Repository creation with `gh repo create NAME --private --source=. --remote=origin --push` needs an initialized local repository and commits to push. Review existing remotes first. See the [GitHub CLI manual](https://cli.github.com/manual/gh_repo_create).

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
