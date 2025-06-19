"""
Here we define the database models for the time tracking application.

The database is a SQLite database, we store all time segments in the pensieve table.

It has the following columns:

    pk: primary key, autoincrementing integer
    start: start time of the time segment, in ISO 8601 format
    end: end time of the time segment, in ISO 8601 format
    passive: whether the time segment was passive or not, boolean, default False
    tags: tags associated with the time segment, comma separated string
    description: description of the time segment, string

"""

import sqlite3
from datetime import date, datetime
from typing import TYPE_CHECKING, Any, Optional, cast

from timeturner.helper import end_of_day, start_of
from timeturner.models import PensiveRow

if TYPE_CHECKING:
    from timeturner.settings import ReportSettings


class Sentinel: ...


sentinel = Sentinel()


def str_if_not_none(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


class DatabaseConnection:
    DB_VERSION = 2

    def __init__(
        self,
        database_file: str = "timeturner.db",
        table_name: str = "pensieve",
        *,
        report_settings: "ReportSettings | None" = None,
    ):
        """
        Initialize the DatabaseConnection.

        Args:
            database_file (str): Path to the SQLite database file.
            table_name (str): Name of the table to use for storing segments.
            report_settings (ReportSettings | None): Optional report settings for migrations.

        This will create the table if it does not exist.
        """
        self.table_name = table_name
        self.database_file = database_file
        self.connection = sqlite3.connect(self.database_file)
        self.report_settings = report_settings
        self.create_table()
        # self.migrate(up_to_version=2)

    def migrate(self, up_to_version: int, report_settings: "ReportSettings") -> None:
        """
        Migrate the database schema to the specified version.

        Args:
            up_to_version (int): The version to migrate the database to.
            report_settings (ReportSettings): Settings used during migration.

        Raises:
            ValueError: If the current version is greater than the target version.
        """
        current_version = self.version()
        if current_version == up_to_version:
            return
        if current_version > up_to_version:
            raise ValueError(
                f"Current database version is {current_version}, "
                f"cannot migrate to version {up_to_version}"
            )
        for version in range(current_version + 1, up_to_version + 1):
            getattr(self, f"_migrate_to_{version}")(report_settings)
            cursor = self.connection.cursor()
            cursor.execute(
                """
                INSERT INTO applied_migrations (version_number) VALUES (?)
                """,
                (str(version),),
            )
            self.connection.commit()

    def _migrate_to_2(self, report_settings) -> None:
        """
        Perform migration to database version 2.

        Args:
            report_settings: Settings used to determine full day tags.
        """
        print("Migrating database to version 2 ...")
        cursor = self.connection.cursor()
        cursor.execute(
            f"""
            ALTER TABLE {self.table_name} RENAME TO old_{self.table_name}
            """
        )
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                pk INTEGER PRIMARY KEY AUTOINCREMENT,
                start DATETIME,
                end DATETIME,
                passive BOOLEAN DEFAULT FALSE,
                full_days BOOLEAN DEFAULT FALSE,
                description TEXT
            )
            """
        )
        cursor.execute(
            f"""
            INSERT INTO {self.table_name} (start, end, passive, description)
            SELECT start, end, passive, description FROM old_{self.table_name}
            """
        )
        cursor.execute(
            f"""
            DROP TABLE old_{self.table_name}
            """
        )
        for segment in self.get_all_segments():
            print(f"Updating segment {segment.pk} {segment}", end=" ")
            if report_settings.has_full_day_tags(segment.tags):
                self.update_segment(segment.pk, full_days=True)
                print("full_days=True")
            print()

        self.connection.commit()
        print("Migration to version 2 complete")

    def create_table(self):
        """
        Create the main, tags, and migration tables if they do not exist.
        """
        cursor = self.connection.cursor()
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                pk INTEGER PRIMARY KEY AUTOINCREMENT,
                start DATETIME,
                end DATETIME,
                passive BOOLEAN DEFAULT FALSE,
                full_days BOOLEAN DEFAULT FALSE,
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
            CREATE TABLE IF NOT EXISTS {self.table_name}_tags (
                {self.table_name}_pk INTEGER,
                tags_pk INTEGER,
                FOREIGN KEY({self.table_name}_pk) REFERENCES {self.table_name}(pk),
                FOREIGN KEY(tags_pk) REFERENCES tags(pk)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS applied_migrations (
                version_id INTEGER PRIMARY KEY,
                version_number TEXT
            )
            """
        )

        self.connection.commit()

    def version(self):
        """
        Get the current database schema version.

        Returns:
            int: The current version number.
        """
        cursor = self.connection.cursor()
        cursor.execute(
            """
            SELECT version_number FROM applied_migrations ORDER BY version_id DESC LIMIT 1
            """
        )
        row = cursor.fetchone()
        if row is None:
            return 1
        return int(row[0])

    def add_segment(
        self,
        start: datetime,
        end: datetime | None = None,
        passive: bool | None = False,
        full_days: bool | None = False,
        tags: list[str] | None = None,
        description: str | None = None,
    ) -> PensiveRow:
        """
        Add a new segment to the database.

        Args:
            start (datetime): Start time of the segment.
            end (datetime | None): End time of the segment.
            passive (bool | None): Whether the segment is passive.
            full_days (bool | None): Whether the segment spans full days.
            tags (list[str] | None): Tags associated with the segment.
            description (str | None): Description of the segment.

        Returns:
            PensiveRow: The inserted segment row.
        """
        # fix passive if it is None
        if passive is None:
            passive = False
        if full_days is None:
            full_days = False
        if tags is None:
            tags = []
        query = f"""
            INSERT INTO {self.table_name} (start, end, passive, full_days, description)
            VALUES (?, ?, ?, ?, ?)
            """
        values = (
            str_if_not_none(start),
            str_if_not_none(end),
            passive,
            full_days,
            description,
        )
        cursor = self.connection.cursor()
        cursor.execute(
            query,
            values,
        )
        if cursor.lastrowid is None:
            raise Exception("Failed to insert segment into database")
        pk = cursor.lastrowid
        for tag in tags:
            tag_pk = self.insert_or_get_tag_pk(tag)
            cursor.execute(
                f"""
                INSERT INTO {self.table_name}_tags ({self.table_name}_pk, tags_pk)
                VALUES (?, ?)
                """,
                (pk, tag_pk),
            )
            if cursor.lastrowid is None:
                raise Exception("Failed to insert tag into database")
        self.connection.commit()
        return cast(PensiveRow, self.get_segment(pk))

    def insert_or_get_tag_pk(self, tag: str) -> int:
        """
        Insert a tag into the tags table if it does not exist, or get its primary key.

        Args:
            tag (str): The tag to insert or look up.

        Returns:
            int: The primary key of the tag.
        """
        cursor = self.connection.cursor()
        cursor.execute(
            """
            SELECT pk FROM tags WHERE tag = ?
            """,
            (tag,),
        )
        result = cursor.fetchone()
        if result is None:
            cursor.execute(
                """
                INSERT INTO tags (tag) VALUES (?)
                """,
                (tag,),
            )
            if cursor.lastrowid is None:
                raise Exception("Failed to insert tag into database")
            self.connection.commit()
            return cursor.lastrowid
        return result[0]

    def get_tags_for_segment(self, pk: int) -> list[str]:
        """
        Get all tags associated with a segment.

        Args:
            pk (int): Primary key of the segment.

        Returns:
            list[str]: List of tag strings.
        """
        cursor = self.connection.cursor()
        cursor.execute(
            f"""
            SELECT tags.tag FROM {self.table_name}_tags
            INNER JOIN tags ON tags.pk = {self.table_name}_tags.tags_pk
            WHERE {self.table_name}_tags.{self.table_name}_pk = ?
            """,
            (pk,),
        )
        return [tag for (tag,) in cursor.fetchall()]

    def update_segment(
        self,
        pk: int,
        start: datetime | Sentinel = sentinel,
        end: datetime | None | Sentinel = sentinel,
        passive: bool | None | Sentinel = sentinel,
        full_days: bool | None | Sentinel = sentinel,
        tags: list[str] | None | Sentinel = sentinel,
        description: str | None | Sentinel = sentinel,
    ) -> None:
        """
        Update an existing segment in the database.

        Args:
            pk (int): Primary key of the segment to update.
            start (datetime | Sentinel): New start time, or sentinel to leave unchanged.
            end (datetime | None | Sentinel): New end time, or sentinel to leave unchanged.
            passive (bool | None | Sentinel): New passive value, or sentinel to leave unchanged.
            full_days (bool | None | Sentinel): New full_days value, or sentinel to leave unchanged.
            tags (list[str] | None | Sentinel): New tags, or sentinel to leave unchanged.
            description (str | None | Sentinel): New description, or sentinel to leave unchanged.

        Raises:
            ValueError: If tags is not a list, None, or not set.
        """
        elements_to_update = []
        values_to_update = []
        if start is not sentinel:
            elements_to_update.append("start = ?")
            values_to_update.append(str(start))
        if end is not sentinel:
            elements_to_update.append("end = ?")
            values_to_update.append(str_if_not_none(end))
        if passive is not sentinel:
            elements_to_update.append("passive = ?")
            if passive is None:
                passive = False
            values_to_update.append(passive)
        if full_days is not sentinel:
            elements_to_update.append("full_days = ?")
            if full_days is None:
                full_days = False
            values_to_update.append(full_days)
        if description is not sentinel:
            elements_to_update.append("description = ?")
            values_to_update.append(description)

        query = f"""
            UPDATE {self.table_name}
            SET {', '.join(elements_to_update)}
            WHERE pk = ?
            """
        values = (
            *values_to_update,
            pk,
        )
        cursor = self.connection.cursor()
        cursor.execute(
            query,
            values,
        )

        # insert all tags that are not already in the database
        if tags is not sentinel:
            if tags is None:
                tags = []
            else:
                if not isinstance(tags, list):
                    raise ValueError("tags must be a list, None, or not set")
            stored_tags = set(self.get_tags_for_segment(pk))
            tags_to_insert = set(tags) - stored_tags
            for tag in tags_to_insert:
                tag_pk = self.insert_or_get_tag_pk(tag)
                cursor.execute(
                    f"""
                    INSERT INTO {self.table_name}_tags ({self.table_name}_pk, tags_pk)
                    VALUES (?, ?)
                    """,
                    (pk, tag_pk),
                )
            tags_to_remove = stored_tags - set(tags)
            for tag in tags_to_remove:
                cursor.execute(
                    f"""
                    DELETE FROM {self.table_name}_tags
                    WHERE {self.table_name}_pk = ? AND tags_pk = ?
                    """,
                    (pk, self.insert_or_get_tag_pk(tag)),
                )

                # if tag is not used anywhere else, delete it from the tags table
                cursor.execute(
                    f"""
                    SELECT COUNT(*) FROM tags
                    INNER JOIN {self.table_name}_tags
                        ON tags.pk = {self.table_name}_tags.tags_pk
                    WHERE tags.tag = ?
                    """,
                    (tag,),
                )
                count = cursor.fetchone()
                if count is None:
                    raise Exception("Failed to get count of tags")
                if count[0] == 0:
                    cursor.execute(
                        """
                        DELETE FROM tags WHERE tag = ?
                        """,
                        (tag,),
                    )

        self.connection.commit()

    def get_latest_segment(self, filter_closed_segments=False) -> PensiveRow | None:
        """
        Get the most recently started segment.

        Args:
            filter_closed_segments (bool): If True, only consider segments that are not closed (end is NULL).

        Returns:
            PensiveRow | None: The latest segment, or None if no segments exist.
        """
        cursor = self.connection.cursor()
        where_clause = ""
        if filter_closed_segments:
            where_clause = "WHERE end IS NULL"
        cursor.execute(
            f"""
            SELECT pk, start, end, passive, full_days, description FROM {self.table_name}
            {where_clause}
            ORDER BY start DESC LIMIT 1
            """
        )

        row = cursor.fetchone()
        if row is None:
            return None
        pk, start, end, passive, full_days, description = row
        if passive is None:
            passive = False
        return PensiveRow(
            pk=pk,
            start=start,
            end=end,
            passive=passive,
            full_days=full_days,
            tags=self.get_tags_for_segment(pk),
            description=description,
        )

    def delete_segment(self, pk: int) -> None:
        """
        Delete a segment from the database.

        Args:
            pk (int): Primary key of the segment to delete.
        """
        cursor = self.connection.cursor()
        cursor.execute(
            f"""
            DELETE FROM {self.table_name} WHERE pk = ?
            """,
            (pk,),
        )
        self.connection.commit()

    def get_segment(self, pk: int) -> PensiveRow | None:
        """
        Retrieve a segment by its primary key.

        Args:
            pk (int): Primary key of the segment.

        Returns:
            PensiveRow | None: The segment row, or None if not found.
        """
        cursor = self.connection.cursor()
        cursor.execute(
            f"""
            SELECT pk, start, end, passive, full_days, description FROM {self.table_name}
            WHERE pk = ?
            """,
            (pk,),
        )

        row = cursor.fetchone()
        if row is None:
            return None
        pk, start, end, passive, full_days, description = row
        if passive is None:
            passive = False
        if full_days is None:
            full_days = False
        return PensiveRow(
            pk=pk,
            start=start,
            end=end,
            passive=passive,
            full_days=full_days,
            tags=self.get_tags_for_segment(pk),
            description=description,
        )

    def get_full_day_segment_by_date(
        self,
        date: datetime | date,
    ) -> PensiveRow | None:
        """
        Get a holiday segment by its date.

        Args:
            date (datetime): The date to search for.

        Returns:
            PensiveRow | None: The holiday segment row, or None if not found.
        """
        cursor = self.connection.cursor()
        print(str(start_of(date, "day")), str(end_of_day(date)))
        cursor.execute(
            f"""
            SELECT pk, start, end, passive, full_days, description FROM {self.table_name}
            WHERE full_days = TRUE AND start <= ? AND (end IS NULL OR end = ?)
            """,
            (str(start_of(date, "day")), str(end_of_day(date))),
        )

        row = cursor.fetchone()
        if row is None:
            return None
        pk, start, end, passive, full_days, description = row
        if passive is None:
            passive = False
        return PensiveRow(
            pk=pk,
            start=start,
            end=end,
            passive=passive,
            full_days=full_days,
            tags=self.get_tags_for_segment(pk),
            description=description,
        )

    def get_segments_between(
        self,
        start: datetime,
        end: Optional[datetime] = None,
        exclude_full_days: bool = False,
    ) -> list[PensiveRow]:
        """
        Get all segments between the given start and end times.

        This includes segments that start before the given start time and/or end after
        the given end time.

        Args:
            start (datetime): Start of the interval.
            end (Optional[datetime]): End of the interval (exclusive). If None, only segments starting after 'start' are included.
            exclude_full_days (bool): If True, exclude segments marked as full_days.

        Returns:
            list[PensiveRow]: List of matching segment rows.
        """
        cursor = self.connection.cursor()
        end_is_none = end is None
        if end is None:
            end = start
        exclude_sql = ""
        if exclude_full_days:
            exclude_sql = "AND full_days == FALSE"
        cursor.execute(
            f"""
            SELECT pk, start, end, passive, full_days, description FROM {self.table_name}
            WHERE start <= ? AND (end > ? OR end IS NULL) {exclude_sql}
            ORDER BY start ASC
            """,
            (str(end), str(start)),
        )

        rows = cursor.fetchall()
        collected_rows = [
            PensiveRow(
                pk=pk,
                start=start,
                end=end,
                passive=passive,
                full_days=full_days,
                tags=self.get_tags_for_segment(pk),
                description=description,
            )
            for pk, start, end, passive, full_days, description in rows
        ]

        if end_is_none:
            # if end was not given, we want to include the first segment that starts
            # after the given start time
            cursor.execute(
                f"""
                SELECT pk, start, end, passive, full_days, description FROM {self.table_name}
                WHERE start > ?
                ORDER BY start ASC LIMIT 1
                """,
                (str(start),),
            )
            row = cursor.fetchone()
            if row is not None:
                pk, start, end, passive, full_days, description = row
                collected_rows.append(
                    PensiveRow(
                        pk=pk,
                        start=start,
                        end=end,
                        passive=passive,
                        full_days=full_days,
                        tags=self.get_tags_for_segment(pk),
                        description=description,
                    )
                )
        return collected_rows

    def get_all_segments(self) -> list[PensiveRow]:
        """
        Retrieve all segments from the database.

        Returns:
            list[PensiveRow]: List of all segment rows.
        """
        cursor = self.connection.cursor()

        cursor.execute(
            f"""
            SELECT pk, start, end, passive, full_days, description FROM {self.table_name}
            """
        )

        rows = cursor.fetchall()
        return [
            PensiveRow(
                pk=pk,
                start=start,
                end=end,
                passive=passive,
                full_days=full_days,
                tags=self.get_tags_for_segment(pk),
                description=description,
            )
            for pk, start, end, passive, full_days, description in rows
        ]
