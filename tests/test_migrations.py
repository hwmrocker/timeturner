import sqlite3

from timeturner.db import DatabaseConnection
from timeturner.settings import ReportSettings


def create_table_v1(cursor, table_name):
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            pk INTEGER PRIMARY KEY AUTOINCREMENT,
            start DATETIME,
            end DATETIME,
            passive BOOLEAN DEFAULT FALSE,
            description TEXT
        )
        """
    )
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS tags (
            pk INTEGER PRIMARY KEY AUTOINCREMENT,
            tag TEXT
        )
        """
    )
    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {table_name}_tags (
            {table_name}_pk INTEGER,
            tags_pk INTEGER,
            FOREIGN KEY({table_name}_pk) REFERENCES {table_name}(pk),
            FOREIGN KEY(tags_pk) REFERENCES tags(pk)
        )
        """
    )

    # insert some tags
    cursor.execute("INSERT INTO tags (tag) VALUES ('sick')")
    cursor.execute("INSERT INTO tags (tag) VALUES ('foo')")


def test_migrate_from_v1(tmp_path):
    # Create a new SQLite database in the temporary path
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    create_table_v1(cursor, "my_table")
    conn.commit()

    ## insert test data
    # a segment smaller than 1 day
    cursor.execute(
        "INSERT INTO my_table (start, end) VALUES ('2020-01-01 09:00', '2020-01-02 12:00')"
    )
    # a segment that spans excatly 1 day but has not a full_day tag, starting from midnight
    cursor.execute(
        "INSERT INTO my_table (start, end) VALUES ('2020-01-02 00:00', '2020-01-03 00:00')"
    )
    # a 24h segment starting at midnight and have the sick tag
    cursor.execute(
        "INSERT INTO my_table (start, end) VALUES ('2020-01-03 00:00', '2020-01-04 00:00')"
    )
    cursor.execute("INSERT INTO my_table_tags (my_table_pk, tags_pk) VALUES (3, 1)")
    conn.commit()
    conn.close()

    report_settings = ReportSettings()
    db = DatabaseConnection(str(db_path), "my_table")
    db.migrate(up_to_version=db.DB_VERSION, report_settings=report_settings)

    assert db.version() == 2

    segments = db.get_all_segments()

    assert len(segments) == 3
    assert len(list(s for s in segments if s.full_days)) == 1
    # Close the database connection
