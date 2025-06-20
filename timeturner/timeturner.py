from datetime import date, datetime, timedelta
from itertools import groupby
from pathlib import Path
from typing import Iterator, cast

import holidays

from timeturner import loader
from timeturner.db import DatabaseConnection
from timeturner.helper import dt_add, end_of_day, iter_over_days, now_with_tz, start_of
from timeturner.models import (
    DailySummary,
    DayType,
    NewSegmentParams,
    PensiveRow,
    SegmentsByDay,
)
from timeturner.parser import parse_add_args, parse_list_args, single_time_parse
from timeturner.settings import ReportSettings, TagSettings
from timeturner.tools.boltons_iterutils import pairwise_iter


def add_holidays(
    year: int,
    country: str | None,
    subdivision: str | None,
    *,
    report_settings: ReportSettings,
    db: DatabaseConnection,
) -> list:
    """
    Add all holidays for the given year as segments with the holiday tag.

    Args:
        year (int): The year for which to import holidays.
        country (str | None): Country code (overrides report_settings if provided).
        subdivision (str | None): Subdivision code (overrides report_settings if provided).
        now (datetime): Current time for reference.
    Returns:
        list: List of added segment rows.
    """
    now = now_with_tz()

    if not country:
        raise ValueError("No country provided for holiday import.")

    # Warn if country is set but no subdivision
    if country and not subdivision:
        import warnings

        warnings.warn(
            f"Country '{country}' provided but no subdivision. Only nationwide holidays will be imported."
        )

    # Load holidays
    kwargs = {"years": year, "country": country}
    if subdivision:
        kwargs["subdiv"] = subdivision

    try:
        holiday_obj = holidays.country_holidays(**kwargs)
    except Exception as e:
        raise ValueError(
            f"Failed to load holidays for {country} {subdivision or ''}: {e}"
        )

    added_segments = []
    for date, name in holiday_obj.items():
        # If no subdivision, only add holidays that are valid nationwide

        start = start_of(date, "day").astimezone()
        existing_holiday = db.get_full_day_segment_by_date(date)
        print(f"Checking holiday {name} on {date} ({start}) {existing_holiday=}")
        if existing_holiday and report_settings.holiday_tag in existing_holiday.tags:
            if existing_holiday.description == name:
                # Holiday already exists, skip adding it again
                continue
            elif not existing_holiday.description:
                # If the existing holiday has no description, update it
                updated = db.update_segment(existing_holiday.pk, description=name)
                added_segments.append(updated)
                continue

        # Add segment for this holiday, we need to check for conflicts with vacation
        added = _add(
            NewSegmentParams(
                start=start,
                end=end_of_day(date),  # No end time for holidays
                tags=[report_settings.holiday_tag],
                description=name,
                full_days=True,  # Full day holiday
            ),
            now=now,
            db=db,
            report_settings=report_settings,
        )

        added_segments.extend(added)
    return added_segments


def get_daily_summary(
    day: date,
    segments: list[PensiveRow],
    *,
    report_settings: ReportSettings,
) -> DailySummary:
    """
    Expecting segments to be sorted by start time.
    All segments should be on the same day.
    No segments should overlap.

    get daily work time
    get daily break time
    get daily overtime

    vacation and holiday are not considered work time and produce no overtime
    """
    work_time = timedelta()
    passive_work_time = timedelta()
    break_time = timedelta()
    start = None
    end = None
    by_tag = {}
    segment = None
    track_work_time = True
    tags = set(tag for segment in segments for tag in segment.tags)

    track_work_time = True
    track_break_time = False
    track_over_time = True
    if tags:
        highest_priority_tag = report_settings.get_highest_priority_tag(
            tags,
            filter_full_day=True,
        )
        if highest_priority_tag.full_day:
            track_work_time = highest_priority_tag.track_work_time
            track_break_time = highest_priority_tag.track_break_time
            track_over_time = highest_priority_tag.track_over_time

    for segment in segments:
        worktime_is_passive = False
        for tag in segment.tags:
            tag_setting = report_settings.get_tag(tag)
            if tag_setting.track_work_time_passive:
                worktime_is_passive = True
                break

        if segment.start.date() != day:
            raise ValueError(
                f"Segment is not on the given day. {day} != {segment.start.date()}"
            )
        if report_settings.holiday_tag in segment.tags:
            return DailySummary(
                day=day,
                day_type=DayType.HOLIDAY,
                work_time=timedelta(),
                break_time=timedelta(),
                over_time=timedelta(),
                start=None,
                end=None,
                description="Holiday",
                by_tag={},
            )
        if start is None:
            start = segment.start.time()
        if track_work_time:
            if worktime_is_passive:
                passive_work_time += segment.duration
            else:
                work_time += segment.duration
        elif track_break_time:
            break_time += segment.duration
        for tag in segment.tags:
            if tag not in by_tag:
                by_tag[tag] = timedelta()
            by_tag[tag] += segment.duration

    if segment and segment.end is not None:
        end = segment.end.time()
    for segment, next_segment in pairwise_iter(segments):
        if segment.end is None:
            raise ValueError(
                "Segment has no end time but is followed by another segment."
            )
        new_break = cast(timedelta, next_segment.start - segment.end)
        if new_break > timedelta(minutes=1):
            break_time += new_break
        else:
            # Short breaks are not counted as breaks.
            work_time += new_break

    if work_time > timedelta(hours=6, minutes=15):
        if break_time < timedelta(minutes=45):
            missing_break_time = timedelta(minutes=45) - break_time
            work_time -= missing_break_time
            break_time += missing_break_time
    elif work_time > timedelta(hours=4):
        if break_time < timedelta(minutes=15):
            missing_break_time = timedelta(minutes=15) - break_time
            work_time -= missing_break_time
            break_time += missing_break_time

    # only add passive work time until both add upto 10 hours
    # everything above is ignored
    if work_time > timedelta(hours=10):
        # we ignore passive work time
        pass
    elif work_time + passive_work_time > timedelta(hours=10):
        work_time = timedelta(hours=10)
    else:
        work_time = work_time + passive_work_time

    required_work_duration = report_settings.worktime_per_weekday[
        day.weekday()
    ].duration
    print(f"{required_work_duration=}")
    day_type = DayType.WORK if required_work_duration else DayType.WEEKEND
    if not track_over_time:
        required_work_duration = timedelta()

    # Special handling: if there is a full-day sick segment and at least one work segment,
    # set work_time to 8:00 and overtime to 0:00
    sick_tag = "sick"
    has_full_day_sick = sick_tag in tags

    over_time = work_time - required_work_duration
    if has_full_day_sick and over_time < timedelta():
        # when you are sick, you cannot have negative overtime
        over_time = timedelta()

    return DailySummary(
        day=day,
        day_type=day_type,
        work_time=work_time,
        break_time=break_time,
        over_time=over_time,
        start=start,
        end=end,
        by_tag=by_tag,
    )


def group_by_day(rows: list[PensiveRow]) -> dict[date, list[PensiveRow]]:
    return {k: list(v) for k, v in groupby(rows, lambda r: r.start.date())}


def split_segments_at_midnight(rows: list[PensiveRow]) -> Iterator[PensiveRow]:
    for row in rows:
        if row.end and row.end.date() == row.start.date():
            yield row
        elif not row.end:
            yield row
        else:
            yield PensiveRow(
                pk=row.pk,
                start=row.start,
                end=end_of_day(row.start),
                tags=row.tags,
                description=row.description,
                passive=row.passive,
            )
            for day in iter_over_days(end_of_day(row.start), row.end):
                if day == row.end.date():
                    end = row.end
                else:
                    _end = dt_add(day, days=1)
                    end = datetime(
                        _end.year, _end.month, _end.day, tzinfo=row.start.tzinfo
                    )
                yield PensiveRow(
                    pk=row.pk,
                    start=datetime(
                        day.year, day.month, day.day, tzinfo=row.start.tzinfo
                    ),
                    end=end,
                    tags=row.tags,
                    description=row.description,
                    passive=row.passive,
                )


def list_(
    time: list[str] | None,
    *,
    report_settings: ReportSettings,
    db: DatabaseConnection,
) -> list[SegmentsByDay]:
    if time is None:
        time = []
    segments_per_day = {}
    start, end = parse_list_args(time)
    for day in iter_over_days(start, end):
        segments_per_day[str(day)] = []
    rows = db.get_segments_between(start, end)
    midnight_devided_segments = list(split_segments_at_midnight(rows))
    for day, segments in groupby(midnight_devided_segments, lambda r: r.start.date()):
        segments_per_day[str(day)] = list(segments)
    daily_segments = []
    for day in iter_over_days(start, end):
        # request_period.range("days"):
        day = cast(datetime, day)
        segments = segments_per_day[str(day)]
        daily_segments.append(
            SegmentsByDay(
                day=day,
                weekday=day.weekday(),
                segments=segments,
                summary=get_daily_summary(
                    day,
                    segments,
                    report_settings=report_settings,
                ),
                tags=sorted(
                    set(
                        tag
                        for segment in segments
                        for tag in segment.tags
                        # if tag not in report_settings.ignore_tags
                    )
                ),
            )
        )
    return daily_segments


def add(
    time: list[str] | None,
    *,
    holiday: bool = False,  # is this still needed? TODO: check
    report_settings: ReportSettings,
    db: DatabaseConnection,
) -> list[PensiveRow]:
    now = now_with_tz()

    if time is None:
        time = []
    new_segment_params = parse_add_args(
        time,
        holiday=holiday,
        report_settings=report_settings,
    )
    return _add(new_segment_params, now, report_settings=report_settings, db=db)


def get_tag_prio(tags: list[str], tag_settings: dict[str, TagSettings]) -> int:
    # TODO: add tests
    # highest prio should win, not first
    max_prio = 0
    for tag in tags:
        if tag in tag_settings:
            max_prio = max(tag_settings[tag].priority, max_prio)
    return max_prio


def split_segment_params(
    new_segment_params: NewSegmentParams,
    conflicting_segment: PensiveRow,
) -> tuple[NewSegmentParams | None, NewSegmentParams | None, NewSegmentParams | None]:
    before = None
    middle = None
    after = None
    if new_segment_params.start < conflicting_segment.start:
        before = NewSegmentParams(
            start=new_segment_params.start,
            end=conflicting_segment.start,
            tags=new_segment_params.tags,
            description=new_segment_params.description,
            passive=new_segment_params.passive,
        )
    if (
        conflicting_segment.start <= new_segment_params.start
        and conflicting_segment.end
        and new_segment_params.end
        and new_segment_params.end <= conflicting_segment.end
    ):
        middle = NewSegmentParams(
            start=conflicting_segment.start,
            end=conflicting_segment.end,
            tags=new_segment_params.tags,
            description=new_segment_params.description,
            passive=new_segment_params.passive,
        )
    if conflicting_segment.end and (
        (new_segment_params.end and new_segment_params.end > conflicting_segment.end)
        or (new_segment_params.end is None)
    ):
        after = NewSegmentParams(
            start=conflicting_segment.end,
            end=new_segment_params.end,
            tags=new_segment_params.tags,
            description=new_segment_params.description,
            passive=new_segment_params.passive,
        )
    return before, middle, after


def split_segment_params_per_weekday(
    new_segment_params: NewSegmentParams,
    *,
    report_settings: ReportSettings,
) -> list[NewSegmentParams]:
    ret = []
    assert new_segment_params.end is not None
    start, end = new_segment_params.start, new_segment_params.end
    if report_settings.is_work_day(start):
        condition = "work"
    else:
        condition = "weekend"
    for day in iter_over_days(start, end):
        if condition == "work":
            if not report_settings.is_work_day(day):
                condition = "weekend"
                ret.append(
                    NewSegmentParams(
                        start=start,
                        end=datetime(day.year, day.month, day.day, tzinfo=start.tzinfo),
                        tags=new_segment_params.tags,
                        description=new_segment_params.description,
                        passive=new_segment_params.passive,
                        full_days=new_segment_params.full_days,
                    )
                )

        else:
            if report_settings.is_work_day(day):
                start = datetime(day.year, day.month, day.day, tzinfo=start.tzinfo)
                condition = "work"
    if condition == "work":
        ret.append(
            NewSegmentParams(
                start=start,
                end=end,
                tags=new_segment_params.tags,
                description=new_segment_params.description,
                passive=new_segment_params.passive,
                full_days=new_segment_params.full_days,
            )
        )

    return ret


def _add(
    new_segment_params: NewSegmentParams,
    now: datetime,
    *,
    report_settings: ReportSettings,
    db: DatabaseConnection,
) -> list[PensiveRow]:
    start, end = new_segment_params.start, new_segment_params.end

    current_tag_prio = get_tag_prio(
        new_segment_params.tags, report_settings.tag_settings
    )
    conflicting_segments = None

    for tag in new_segment_params.tags:
        tag_settings = report_settings.tag_settings.get(tag)
        if tag_settings is None:
            continue
        if tag_settings.only_cover_work_days:
            new_segment_params_per_weekday = split_segment_params_per_weekday(
                new_segment_params,
                report_settings=report_settings,
            )
            if len(new_segment_params_per_weekday) == 0:
                return []
            if len(new_segment_params_per_weekday) > 1:
                segments = []
                for new_segment_params in new_segment_params_per_weekday:
                    segments.extend(
                        _add(
                            new_segment_params,
                            now,
                            db=db,
                            report_settings=report_settings,
                        )
                    )
                return segments

            # we have just one segment, so we can continue
            new_segment_params = new_segment_params_per_weekday[0]
        if tag_settings.full_day:
            # If a tag existst that can coexist with multiple other events, do not look for conflicts
            conflicting_segments = [
                segment
                for segment in db.get_segments_between(start, end)
                if segment.full_days
            ]

    if conflicting_segments is None:
        conflicting_segments = db.get_segments_between(
            start, end, exclude_full_days=True
        )

    for conflicting_segment in conflicting_segments:
        print(conflicting_segment.start)
        print(now)
        conflicting_tag_prio = get_tag_prio(
            conflicting_segment.tags, report_settings.tag_settings
        )
        # TODO: return a warning that other segments were changed
        if start <= conflicting_segment.start:
            if end and end > conflicting_segment.start:
                if (
                    conflicting_segment.end and end < conflicting_segment.end
                ) or conflicting_segment.end is None:
                    # the conflicting segment is covering the end partially

                    if conflicting_tag_prio <= current_tag_prio:
                        db.update_segment(conflicting_segment.pk, start=end)
                    else:
                        new_segment_params.end = end = conflicting_segment.start

                else:
                    # conflicting_segment.end and end >= conflicting_segment.end:
                    # the conflicting segment is fully covered by the new segment
                    if conflicting_tag_prio <= current_tag_prio:
                        # delete the conflicting segment, because it is less important
                        # or equal
                        db.delete_segment(conflicting_segment.pk)
                    else:
                        before, _, after = split_segment_params(
                            new_segment_params, conflicting_segment
                        )
                        ret = []
                        if before:
                            ret.extend(
                                _add(
                                    before,
                                    now,
                                    db=db,
                                    report_settings=report_settings,
                                )
                            )
                        # the conflicting middle segment has a higher prio
                        # we don't need to add it
                        if after:
                            ret.extend(
                                _add(
                                    after,
                                    now,
                                    db=db,
                                    report_settings=report_settings,
                                )
                            )
                        return ret

            elif end is None and conflicting_segment.start < now:
                # this cannot have a higher prio
                # all high prio segments need to have defined end
                new_segment_params.end = conflicting_segment.start
        elif conflicting_segment.end is None:
            # current segment starts after an open ended segment
            # we don't need to check the prio, because the conflicting segment
            # needs to be closed any way.
            db.update_segment(conflicting_segment.pk, end=start)
        elif (
            end and start > conflicting_segment.start and end < conflicting_segment.end
        ):
            # new segment is in the middle of the conflicting segment
            if conflicting_tag_prio <= current_tag_prio:
                ret = []
                db.update_segment(conflicting_segment.pk, end=start)
                ret.append(db.add_segment(**new_segment_params.model_dump()))
                ret.append(
                    db.add_segment(
                        end,
                        conflicting_segment.end,
                        tags=conflicting_segment.tags,
                        description=conflicting_segment.description,
                        passive=conflicting_segment.passive,
                    )
                )
                return ret
            else:
                return []
        elif start < conflicting_segment.end and start > conflicting_segment.start:
            # new segment starts in the middle of the conflicting segment
            # the conficting segment has a specific end
            if conflicting_tag_prio <= current_tag_prio:
                db.update_segment(conflicting_segment.pk, end=start)
            else:
                new_segment_params.start = start = conflicting_segment.end

    return [db.add_segment(**new_segment_params.model_dump())]


def end(
    time: list[str] | None,
    *,
    report_settings: ReportSettings,
    db: DatabaseConnection,
) -> PensiveRow | None:
    if time is None:
        time = []
    end = single_time_parse(time)
    last_entry = db.get_latest_segment(filter_closed_segments=True)

    if last_entry is None:
        raise ValueError("No entries to stop")
    if last_entry.end is not None:
        raise ValueError(f"Last entry already ended {last_entry.end!r}")
    pk = last_entry.pk
    db.update_segment(pk, end=end)
    entry = db.get_segment(pk)
    return entry


def import_text(
    path: Path,
    *,
    db: DatabaseConnection,
) -> Iterator[PensiveRow]:
    return loader.import_text(db, path)


def import_json(
    path: Path,
    *,
    report_settings: ReportSettings,
    db: DatabaseConnection,
) -> Iterator[PensiveRow]:
    del report_settings
    return loader.import_json(db, path)
