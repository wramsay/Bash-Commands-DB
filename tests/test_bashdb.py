import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
import bashdb


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
