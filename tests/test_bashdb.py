import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
import bashdb


class ImportTests(unittest.TestCase):
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
