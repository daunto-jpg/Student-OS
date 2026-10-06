import os
import sqlite3
import tempfile
import unittest

from student_os import db, profile

EXPECTED_TABLES = {"student", "courses", "timetable", "assignments",
                   "attendance", "notes", "settings"}


class A1Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "test.db")
        db.init_db(self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def add_course(self, conn, code="CSC301"):
        cur = conn.execute(
            "INSERT INTO courses (code, name, credit_unit) VALUES (?, 'Test', 3)", (code,))
        return cur.lastrowid


class TestInit(A1Base):
    def test_creates_all_tables(self):
        with db.db_session(self.path) as conn:
            names = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue(EXPECTED_TABLES <= names)

    def test_creates_file_in_missing_folder(self):
        nested = os.path.join(self.tmp.name, "a", "b", "app.db")
        db.init_db(nested)
        self.assertTrue(os.path.exists(nested))

    def test_init_is_idempotent_and_keeps_data(self):
        with db.db_session(self.path) as conn:
            self.add_course(conn)
        version = db.init_db(self.path)  # second run
        self.assertEqual(version, db.LATEST_VERSION)
        with db.db_session(self.path) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM courses").fetchone()[0], 1)

    def test_default_threshold_seeded(self):
        with db.db_session(self.path) as conn:
            v = conn.execute(
                "SELECT value FROM settings WHERE key='attendance_threshold'").fetchone()[0]
        self.assertEqual(v, "75")

    def test_failed_migration_rolls_back(self):
        path = os.path.join(self.tmp.name, "bad.db")
        original = db.MIGRATIONS
        db.MIGRATIONS = [(1, ["CREATE TABLE ok (id INTEGER)", "NOT VALID SQL"])]
        try:
            with self.assertRaises(sqlite3.Error):
                db.init_db(path)
        finally:
            db.MIGRATIONS = original
        conn = db.get_connection(path)
        tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        self.assertEqual(db.get_schema_version(conn), 0)
        conn.close()
        self.assertEqual(tables, [])


class TestForeignKeys(A1Base):
    def test_foreign_keys_on(self):
        conn = db.get_connection(self.path)
        self.assertEqual(conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)
        conn.close()

    def test_orphan_rows_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            with db.db_session(self.path) as conn:
                conn.execute("INSERT INTO attendance (course_id, date, status) "
                             "VALUES (999, '2026-10-01', 'Present')")

    def test_deleting_course_cascades(self):
        with db.db_session(self.path) as conn:
            cid = self.add_course(conn)
            conn.execute("INSERT INTO attendance (course_id, date, status) "
                         "VALUES (?, '2026-10-01', 'Present')", (cid,))
            conn.execute("INSERT INTO notes (course_id, title) VALUES (?, 'n')", (cid,))
        with db.db_session(self.path) as conn:
            conn.execute("DELETE FROM courses WHERE id = ?", (cid,))
        with db.db_session(self.path) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM attendance").fetchone()[0], 0)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM notes").fetchone()[0], 0)


class TestConstraints(A1Base):
    def test_duplicate_course_code_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            with db.db_session(self.path) as conn:
                self.add_course(conn, "CSC301")
                self.add_course(conn, "CSC301")

    def test_bad_attendance_status_rejected(self):
        with self.assertRaises(sqlite3.IntegrityError):
            with db.db_session(self.path) as conn:
                cid = self.add_course(conn)
                conn.execute("INSERT INTO attendance (course_id, date, status) "
                             "VALUES (?, '2026-10-01', 'Maybe')", (cid,))

    def test_one_attendance_record_per_course_per_day(self):
        with self.assertRaises(sqlite3.IntegrityError):
            with db.db_session(self.path) as conn:
                cid = self.add_course(conn)
                for _ in range(2):
                    conn.execute("INSERT INTO attendance (course_id, date, status) "
                                 "VALUES (?, '2026-10-01', 'Present')", (cid,))

    def test_session_rolls_back_on_error(self):
        try:
            with db.db_session(self.path) as conn:
                self.add_course(conn)
                raise RuntimeError("boom")
        except RuntimeError:
            pass
        with db.db_session(self.path) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM courses").fetchone()[0], 0)


class TestProfile(A1Base):
    def test_empty_before_setup(self):
        self.assertIsNone(profile.get_profile(self.path))

    def test_save_and_read(self):
        profile.save_profile("Ada", "2026/2027", "First", self.path)
        self.assertEqual(profile.get_profile(self.path),
                         {"name": "Ada", "academic_session": "2026/2027", "semester": "First"})

    def test_update_keeps_single_row(self):
        profile.save_profile("Ada", "2026/2027", "First", self.path)
        profile.save_profile("Ada B", "2026/2027", "Second", self.path)
        with db.db_session(self.path) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM student").fetchone()[0], 1)
        self.assertEqual(profile.get_profile(self.path)["semester"], "Second")

    def test_blank_name_rejected(self):
        with self.assertRaises(ValueError):
            profile.save_profile("   ", db_path=self.path)

    def test_second_row_impossible(self):
        profile.save_profile("Ada", db_path=self.path)
        with self.assertRaises(sqlite3.IntegrityError):
            with db.db_session(self.path) as conn:
                conn.execute("INSERT INTO student (id, name) VALUES (2, 'Other')")


if __name__ == "__main__":
    unittest.main()
