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
from typing import Any

from pendulum.datetime import DateTime
from pydantic import BaseModel


class Sentinel:
    ...


sentinel = Sentinel()


class TimeSlot(BaseModel):
    start: DateTime
    end: DateTime | None = None
    passive: bool = False
    tags: str | None = None
    description: str | None = None


class PensiveRow(TimeSlot):
    pk: int


def str_if_not_none(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


class DatabaseConnection:
    table_name = "pensieve"

    def __init__(self, database_file: str = "timeturner.db"):
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
                tags TEXT,
                description TEXT
            )
            """
        )
        self.connection.commit()

    def add_slot(
        self,
        start: DateTime,
        end: DateTime | None = None,
        passive: bool | None = False,
        tags: str | None = None,
        description: str | None = None,
    ) -> int:
        """
        Add a time slot to the database.

        Returns the primary key of the newly created time slot.
        """
        # fix passive if it is None
        if passive is None:
            passive = False

        query = f"""
            INSERT INTO {self.table_name} (start, end, passive, tags, description)
            VALUES (?, ?, ?, ?, ?)
            """
        values = (
            str_if_not_none(start),
            str_if_not_none(end),
            passive,
            tags,
            description,
        )
        cursor = self.connection.cursor()
        cursor.execute(
            query,
            values,
        )
        self.connection.commit()
        if cursor.lastrowid is None:
            raise Exception("Failed to insert time slot into database")
        return cursor.lastrowid

    def update_slot(
        self,
        pk: int,
        start: DateTime | Sentinel = sentinel,
        end: DateTime | None | Sentinel = sentinel,
        passive: bool | None | Sentinel = sentinel,
        tags: str | None | Sentinel = sentinel,
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
        if tags is not sentinel:
            elements_to_update.append("tags = ?")
            values_to_update.append(tags)
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
        self.connection.commit()

    def get_latest_slot(self) -> PensiveRow | None:
        """
        get the latest time slot from the database according to the start time.
        """
        cursor = self.connection.cursor()
        cursor.execute(
            f"""
            SELECT pk, start, end, passive, tags, description FROM {self.table_name}
            ORDER BY start DESC LIMIT 1
            """
        )

        row = cursor.fetchone()
        if row is None:
            return None
        pk, start, end, passive, tags, description = row
        if passive is None:
            passive = False
        return PensiveRow(
            pk=pk,
            start=start,
            end=end,
            passive=passive,
            tags=tags,
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
            SELECT pk, start, end, passive, tags, description FROM {self.table_name}
            WHERE pk = ?
            """,
            (pk,),
        )

        row = cursor.fetchone()
        if row is None:
            return None
        pk, start, end, passive, tags, description = row
        if passive is None:
            passive = False
        return PensiveRow(
            pk=pk,
            start=start,
            end=end,
            passive=passive,
            tags=tags,
            description=description,
        )

    def get_slots_between(
        self,
        start: DateTime,
        end: DateTime,
    ) -> list[PensiveRow]:
        """
        Get all time slots between the given start and end times.

        This includes slots that start before the given start time and / or end after the given end time.
        """
        cursor = self.connection.cursor()

        cursor.execute(
            f"""
            SELECT pk, start, end, passive, tags, description FROM {self.table_name}
            WHERE start <= ? AND (end >= ? OR end IS NULL)
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
                tags=tags,
                description=description,
            )
            for pk, start, end, passive, tags, description in rows
        ]

    def get_all_slots(self) -> list[PensiveRow]:
        cursor = self.connection.cursor()

        cursor.execute(
            f"""
            SELECT pk, start, end, passive, tags, description FROM {self.table_name}
            """
        )

        rows = cursor.fetchall()
        return [
            PensiveRow(
                pk=pk,
                start=start,
                end=end,
                passive=passive,
                tags=tags,
                description=description,
            )
            for pk, start, end, passive, tags, description in rows
        ]
