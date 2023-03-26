"""
Here we define the database models for the time tracking application.

The database is a SQLite database, we store all time slots in the pensieve table.

It has the following columns:

    pk: primary key, autoincrementing integer
    start: start time of the time slot, in ISO 8601 format
    end: end time of the time slot, in ISO 8601 format
    passive: whether the time slot was passive or not, boolean, default False
    tags: tags associated with the time slot, comma separated string
    description: description of the time slot, string

"""

import sqlite3
from datetime import datetime
from typing import Any, cast

import pendulum
from pendulum.datetime import DateTime
from pendulum.parser import parse
from pendulum.period import Period
from pydantic import BaseModel, validator


class Sentinel:
    ...


sentinel = Sentinel()


class TimeSegment(BaseModel):
    start: DateTime
    end: DateTime | None = None
    passive: bool = False
    tags: list[str] | None = None
    description: str | None = None

    @validator("start")
    def parse_start(cls, value: str | datetime | DateTime) -> DateTime:
        if isinstance(value, DateTime):
            return value
        if isinstance(value, datetime):
            value = str(value)
        new_value = parse(value)
        if isinstance(new_value, DateTime):
            return new_value
        raise ValueError(f"Could not parse {value} as a datetime")

    @validator("end")
    def parse_end(cls, value: str | datetime | DateTime | None) -> DateTime | None:
        if value is None:
            return None
        return cls.parse_start(value)

    @validator("tags")
    def parse_tags(cls, value: str | list[str] | None) -> list[str] | None:
        if value is None:
            return []
        if isinstance(value, str):
            return value.split(",")
        if isinstance(value, list):
            return value
        raise ValueError(f"Could not parse {value} as a list of tags")

    @property
    def duration(self) -> Period:
        if self.end is None:
            duration = cast(Period, pendulum.now() - self.start)
        else:
            duration = cast(Period, self.end - self.start)

        return duration


class PensiveRow(TimeSegment):
    pk: int


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
            f"""
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

    def add_slot(
        self,
        start: DateTime,
        end: DateTime | None = None,
        passive: bool | None = False,
        tags: list[str] | None = None,
        description: str | None = None,
    ) -> PensiveRow:
        """
        Add a time slot to the database.

        Returns the primary key of the newly created time slot.
        """
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
        self.connection.commit()
        if cursor.lastrowid is None:
            raise Exception("Failed to insert time slot into database")
        return cast(PensiveRow, self.get_slot(pk))

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
            self.connection.commit()
            return cursor.lastrowid
        return result[0]

    def get_tags_for_slot(self, pk: int) -> list[str]:
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

    def update_slot(
        self,
        pk: int,
        start: DateTime | Sentinel = sentinel,
        end: DateTime | None | Sentinel = sentinel,
        passive: bool | None | Sentinel = sentinel,
        tags: list[str] | None | Sentinel = sentinel,
        description: str | None | Sentinel = sentinel,
    ) -> None:
        """
        Update a time slot in the database.
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
            stored_tags = set(self.get_tags_for_slot(pk))
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
                    INNER JOIN {self.table_name}_tags ON tags.pk = {self.table_name}_tags.tags_pk
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

    def get_latest_slot(self) -> PensiveRow | None:
        """
        get the latest time slot from the database according to the start time.
        """
        cursor = self.connection.cursor()
        cursor.execute(
            f"""
            SELECT pk, start, end, passive, description FROM {self.table_name}
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
            tags=self.get_tags_for_slot(pk),
            description=description,
        )

    def delete_slot(self, pk: int) -> None:
        cursor = self.connection.cursor()
        cursor.execute(
            f"""
            DELETE FROM {self.table_name} WHERE pk = ?
            """,
            (pk,),
        )
        self.connection.commit()

    def get_slot(self, pk: int) -> PensiveRow | None:
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
            tags=self.get_tags_for_slot(pk),
            description=description,
        )

    def get_slots_between(
        self,
        start: DateTime,
        end: DateTime,
    ) -> list[PensiveRow]:
        """
        Get all time slots between the given start and end times.

        This includes slots that start before the given start time and / or end after
        the given end time.
        """
        cursor = self.connection.cursor()

        cursor.execute(
            f"""
            SELECT pk, start, end, passive, description FROM {self.table_name}
            WHERE start <= ? AND (end >= ? OR end IS NULL)
            ORDER BY start ASC
            """,
            (str(end), str(start)),
        )

        rows = cursor.fetchall()
        return [
            PensiveRow(
                pk=pk,
                start=start,
                end=end,
                passive=passive,
                tags=self.get_tags_for_slot(pk),
                description=description,
            )
            for pk, start, end, passive, description in rows
        ]

    def get_all_slots(self) -> list[PensiveRow]:
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
                tags=self.get_tags_for_slot(pk),
                description=description,
            )
            for pk, start, end, passive, description in rows
        ]
