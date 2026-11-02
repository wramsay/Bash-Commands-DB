import json
import io
from contextlib import redirect_stdout
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import bashdb


class EntryTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.db = Path(self.folder.name) / 'test.sqlite3'
        source = Path(self.folder.name) / 'input.json'
        source.write_text(json.dumps([
            {'command': 'git status', 'category': 'Git', 'description': 'original'},
            {'command': 'abcdefghij', 'category': 'Boundary / Child'},
        ]))
        bashdb.import_file(self.db, source)

    def test_save_categories_duplicates_and_preserve_text(self):
        record = {'command': '  echo "a  b"  ', 'category': 'New / Child',
                  'description': 'example', 'platforms': ['Linux'], 'notes': 'note'}
        ident = bashdb.add_command(self.db, record)
        self.assertIsNone(bashdb.add_command(self.db, dict(record, category='Elsewhere')))
        bashdb.add_command(self.db, {'command': 'pwd', 'category': 'Git'})
        with bashdb.connect(self.db) as conn:
            row = conn.execute('SELECT * FROM commands WHERE id = ?', (ident,)).fetchone()
            self.assertEqual(row['command'], 'echo "a  b"')
            self.assertEqual(row['category'], 'New / Child')
            self.assertEqual(json.loads(row['platforms']), ['Linux'])
            self.assertEqual(row['notes'], 'note')
            self.assertEqual(dict(bashdb.category_counts(conn))['New'], 1)
            self.assertEqual(conn.execute('PRAGMA integrity_check').fetchone()[0], 'ok')

    def test_similarity_threshold_scope_and_confirmation(self):
        record = {'command': 'abcdefgXYZ', 'category': 'Boundary'}
        with self.assertRaises(bashdb.SimilarCommandsError) as caught:
            bashdb.add_command(self.db, record)
        self.assertAlmostEqual(caught.exception.matches[0][0], .70)
        with bashdb.connect(self.db) as conn:
            self.assertEqual(len(bashdb.search(conn)), 2)
            self.assertEqual(bashdb.similar_commands(conn, 'abcdefWXYZ', 'Boundary'), [])
            self.assertEqual(bashdb.similar_commands(conn, record['command'], 'Git'), [])
        approved = [row['id'] for score, row in caught.exception.matches]
        self.assertIsInstance(bashdb.add_command(self.db, record, approved), int)
        # A later matching entry still requires its own approval.
        with self.assertRaises(bashdb.SimilarCommandsError):
            bashdb.add_command(self.db, dict(record, command='abcdefgXYQ'), approved)

    def run_browser(self, inputs):
        output = io.StringIO()
        with bashdb.connect(self.db) as conn, patch('builtins.input', side_effect=inputs), redirect_stdout(output):
            bashdb.browse(conn, self.db)
            with self.assertRaises(sqlite3.OperationalError):
                conn.execute('DELETE FROM commands')
        return output.getvalue()

    def test_browser_new_and_existing_categories_refresh(self):
        output = self.run_browser(['add', 'new', 'Fresh', 'uname -a',
                                   'system info', 'Linux, macOS', '', '', '', '', 'q'])
        self.assertIn('Added command #', output)
        self.assertIn('[Fresh] uname -a', output)
        # Categories are sorted: Boundary, Boundary / Child, Fresh, Git.
        self.run_browser(['add', '4', 'pwd', '', '', '', '', '', '', 'q'])
        with bashdb.connect(self.db) as conn:
            self.assertEqual(len(bashdb.search(conn, category='Git')), 2)

    def test_browser_similarity_decline_accept_and_cancel(self):
        for answer, expected in [('', 1), ('yes', 2)]:
            output = self.run_browser(['add', '3', 'git status -s',
                                      '', '', '', '', '', '', answer, 'q'])
            self.assertIn('70% similar format', output)
            with bashdb.connect(self.db) as conn:
                self.assertEqual(len(bashdb.search(conn, category='Git')), expected)
        self.run_browser(['add', 'new', 'Never saved', 'new command', KeyboardInterrupt(), 'q'])
        with bashdb.connect(self.db) as conn:
            self.assertNotIn('Never saved', dict(bashdb.category_counts(conn)))

    def test_empty_input_and_global_exact_duplicate(self):
        for record in ({'command': ' ', 'category': 'Git'},
                       {'command': 'pwd', 'category': ' '}):
            with self.assertRaises(ValueError):
                bashdb.add_command(self.db, record)
        self.assertIsNone(bashdb.add_command(self.db, {
            'command': ' git status ', 'category': 'Different', 'description': 'replacement'}))
        with bashdb.connect(self.db) as conn:
            self.assertEqual(bashdb.search(conn, 'git status')[0]['description'], 'original')


class ImportTests(unittest.TestCase):
    def test_category_hierarchy(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'input.json'
            db = Path(folder) / 'test.sqlite3'
            source.write_text(json.dumps([
                {'command': str(i), 'category': category}
                for i, category in enumerate([
                    'Neovim', 'Neovim / Android', 'Neovim / Python',
                    'Neovim / Python / Tools', 'Neovim extras', 'Other',
                    'Literal_% / Child'])]))
            bashdb.import_file(db, source)
            with bashdb.connect(db) as conn:
                self.assertEqual(len(bashdb.search(conn, category='Neovim')), 4)
                self.assertEqual(len(bashdb.search(conn, category='Neovim / Python')), 2)
                self.assertEqual(len(bashdb.search(conn, '3', 'Neovim')), 1)
                self.assertEqual(len(bashdb.search(conn, category='Literal_%')), 1)
                self.assertEqual(len(bashdb.search(conn, category='Literal')), 0)
                counts = dict(bashdb.category_counts(conn))
                self.assertEqual(counts['Neovim'], 4)
                self.assertEqual(counts['Neovim / Python'], 2)
                self.assertEqual(counts['Other'], 1)

    def test_duplicates_validation_and_readonly(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / 'input.json'
            db = Path(folder) / 'test.sqlite3'
            source.write_text(json.dumps({'commands': [
                {'command': ' echo "a  b" ', 'description': 'original'},
                {'command': 'echo "a  b"', 'description': 'replacement'},
                {'command': 'echo "a b"', 'caution': 'retained'}]}))
            self.assertEqual(bashdb.import_file(db, source), (2, 1))
            self.assertEqual(bashdb.import_file(db, source), (0, 3))
            with bashdb.connect(db) as conn:
                self.assertEqual(bashdb.search(conn, 'original')[0]['description'], 'original')
                self.assertEqual(len(bashdb.search(conn, 'retained')), 1)
                self.assertEqual(conn.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
                with self.assertRaises(sqlite3.OperationalError):
                    conn.execute('DELETE FROM commands')
            source.write_text(json.dumps([{'command': 'new'}, {'command': 42}]))
            with self.assertRaises(ValueError):
                bashdb.import_file(db, source)
            with bashdb.connect(db) as conn:
                self.assertEqual(len(bashdb.search(conn)), 2)
