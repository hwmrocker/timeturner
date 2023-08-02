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
from typing import Any, Optional, cast

from pendulum.datetime import DateTime

from timeturner.models import PensiveRow


class Sentinel:
    ...


sentinel = Sentinel()


def str_if_not_none(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


class DatabaseConnection:
    def __init__(
        self,
        database_file: str = "timeturner.db",
        table_name: str = "pensieve",
    ):
        self.table_name = table_name
        self.database_file = database_file
        self.connection = sqlite3.connect(self.database_file)
        self.create_table()

    def create_table(self):
        cursor = self.connection.cursor()
        cursor.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {self.table_name} (
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
            CREATE TABLE IF NOT EXISTS {self.table_name}_tags (
                {self.table_name}_pk INTEGER,
                tags_pk INTEGER,
                FOREIGN KEY({self.table_name}_pk) REFERENCES {self.table_name}(pk),
                FOREIGN KEY(tags_pk) REFERENCES tags(pk)
            )
            """
        )
        self.connection.commit()

    def add_segment(
        self,
        start: DateTime,
        end: DateTime | None = None,
        passive: bool | None = False,
        tags: list[str] | None = None,
        description: str | None = None,
    ) -> PensiveRow:
        # fix passive if it is None
        if passive is None:
            passive = False
        if tags is None:
            tags = []
        query = f"""
            INSERT INTO {self.table_name} (start, end, passive, description)
            VALUES (?, ?, ?, ?)
            """
        values = (
            str_if_not_none(start),
            str_if_not_none(end),
            passive,
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
        cursor = self.connection.cursor()
        cursor.execute(
            f"""
            SELECT tags.tag FROM {self.table_name}_tags
            INNER JOIN tags ON tags.pk = {self.table_name}_tags.tags_pk
            WHERE {self.table_name}_tags.{self.table_name}_pk = ?
            """,
            (pk,),
        )
        return [tag for tag, in cursor.fetchall()]

    def update_segment(
        self,
        pk: int,
        start: DateTime | Sentinel = sentinel,
        end: DateTime | None | Sentinel = sentinel,
        passive: bool | None | Sentinel = sentinel,
        tags: list[str] | None | Sentinel = sentinel,
        description: str | None | Sentinel = sentinel,
    ) -> None:
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
        cursor = self.connection.cursor()
        where_clause = ""
        if filter_closed_segments:
            where_clause = "WHERE end IS NULL"
        cursor.execute(
            f"""
            SELECT pk, start, end, passive, description FROM {self.table_name}
            {where_clause}
            ORDER BY start DESC LIMIT 1
            """
        )

        row = cursor.fetchone()
        if row is None:
            return None
        pk, start, end, passive, description = row
        if passive is None:
            passive = False
        return PensiveRow(
            pk=pk,
            start=start,
            end=end,
            passive=passive,
            tags=self.get_tags_for_segment(pk),
            description=description,
        )

    def delete_segment(self, pk: int) -> None:
        cursor = self.connection.cursor()
        cursor.execute(
            f"""
            DELETE FROM {self.table_name} WHERE pk = ?
            """,
            (pk,),
        )
        self.connection.commit()

    def get_segment(self, pk: int) -> PensiveRow | None:
        cursor = self.connection.cursor()
        cursor.execute(
            f"""
            SELECT pk, start, end, passive, description FROM {self.table_name}
            WHERE pk = ?
            """,
            (pk,),
        )

        row = cursor.fetchone()
        if row is None:
            return None
        pk, start, end, passive, description = row
        if passive is None:
            passive = False
        return PensiveRow(
            pk=pk,
            start=start,
            end=end,
            passive=passive,
            tags=self.get_tags_for_segment(pk),
            description=description,
        )

    def get_segments_between(
        self,
        start: DateTime,
        end: Optional[DateTime] = None,
    ) -> list[PensiveRow]:
        """
        Get all segments between the given start and end times.

        This includes segments that start before the given start time and / or end after
        the given end time.

        end is exclusive, i.e. segments that end at the given end time are not included.
        """
        cursor = self.connection.cursor()
        end_is_none = end is None
        if end is None:
            end = start
        cursor.execute(
            f"""
            SELECT pk, start, end, passive, description FROM {self.table_name}
            WHERE start <= ? AND (end > ? OR end IS NULL)
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
                tags=self.get_tags_for_segment(pk),
                description=description,
            )
            for pk, start, end, passive, description in rows
        ]

        if end_is_none:
            # if end was not given, we want to include the first segment that starts
            # after the given start time
            cursor.execute(
                f"""
                SELECT pk, start, end, passive, description FROM {self.table_name}
                WHERE start > ?
                ORDER BY start ASC LIMIT 1
                """,
                (str(start),),
            )
            row = cursor.fetchone()
            if row is not None:
                pk, start, end, passive, description = row
                collected_rows.append(
                    PensiveRow(
                        pk=pk,
                        start=start,
                        end=end,
                        passive=passive,
                        tags=self.get_tags_for_segment(pk),
                        description=description,
                    )
                )
        return collected_rows

    def get_all_segments(self) -> list[PensiveRow]:
        cursor = self.connection.cursor()

        cursor.execute(
            f"""
            SELECT pk, start, end, passive, description FROM {self.table_name}
            """
        )

        rows = cursor.fetchall()
        return [
            PensiveRow(
                pk=pk,
                start=start,
                end=end,
                passive=passive,
                tags=self.get_tags_for_segment(pk),
                description=description,
            )
            for pk, start, end, passive, description in rows
        ]
