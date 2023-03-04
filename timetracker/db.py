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


class TimeSlot(BaseModel):
    start: DateTime
    end: DateTime | None
    passive: bool
    tags: str | None
    description: str | None


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
        passive: bool = False,
        tags: str | None = None,
        description: str | None = None,
    ) -> int:
        """
        Add a time slot to the database.

        Returns the primary key of the newly created time slot.
        """
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
        start: DateTime | None = None,
        end: DateTime | None = None,
        passive: bool | None = None,
        tags: str | None = None,
        description: str | None = None,
    ) -> None:
        """
        Update a time slot in the database.
        """
        query = f"""
            UPDATE {self.table_name}
            SET start = ?, end = ?, passive = ?, tags = ?, description = ?
            WHERE pk = ?
            """
        values = (
            str_if_not_none(start),
            str_if_not_none(end),
            passive,
            tags,
            description,
            pk,
        )
        cursor = self.connection.cursor()
        cursor.execute(
            query,
            values,
        )
        self.connection.commit()

    def get_latest_slot(self) -> PensiveRow | None:
        cursor = self.connection.cursor()
        cursor.execute(
            f"""
            SELECT pk, start, end, passive, tags, description FROM {self.table_name} ORDER BY pk DESC LIMIT 1
            """
        )

        row = cursor.fetchone()
        if row is None:
            return None
        pk, start, end, passive, tags, description = row
        return PensiveRow(
            pk=pk,
            start=start,
            end=end,
            passive=passive,
            tags=tags,
            description=description,
        )
