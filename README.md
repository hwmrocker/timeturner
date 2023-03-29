Time Turner
===========

## A Minimalistic Time Tracker.

This is a minimalistic time tracker that allows you to record when you start working, even if it is in the past, stop running activities now, and add activities from the past. It also ensures legal rest periods are included if you forgot to track them.

In the Harry Potter series, the Time-Turner is a magical device that allows the user to travel back in time. Time Turner is a time tracker that lets you "turn back time" and record activities from the past.

**Warning, this is still an alpha release, the API is not stable yet.**

## Usage

### Starting an Activity

To start tracking an activity, run the following command:


![`timeturner add`](img/add.svg)

This will record the current time as the start of your activity.

If you forgot to start tracking an activity yesterday, you can provide the start time with an additional parameter, `-10m` would mean 10 minutest ago. The full list of possible time values can be [seen further down](#examples-for-times)

### Stopping an Activity

To stop tracking the current activity, run the following command:


![`timeturner end`](img/end.svg)


This will record the current time as the end of your activity and calculate the total duration.

### Adding a Past Activity

If you forgot to track an activity in the past, you can add it with `timeturner add <start_time> - <end_time>`

![`timeturner add -- -1d@9:00 - +8h45m`](img/add_past.svg)

## Configuration

| Environment Variable       | Default Value                    | Description                                  |
| -------------------------- | -------------------------------- | -------------------------------------------- |
| TIMETURNER_CONFIG_HOME     | ~/$XDG_CONFIG_HOME/timeturner    | The directory for configuration files.       |
| TIMETURNER_CONFIG_FILE     | timeturner.toml                  | The configuration file to use.               |
| TIMETURNER_DATABASE__HOME  | value of $TIMETURNER_CONFIG_HOME | The directory to store the database file in. |
| TIMETURNER_DATABASE__FILE  | timeturner.db                    | The database file to use.                    |
| TIMETURNER_DATABASE__TABLE | pensive                          | The table to use in the database.            |

## Examples

### Examples for times

<start_time> or <end_time> could be one of the following Examples:

| Example         | Description                               |
| --------------- | ----------------------------------------- |
|                 | now                                       |
| 9:00            | 9:00 today                                |
| -1m             | 1 minute ago                              |
| -1h             | 1 hour ago                                |
| -1d             | 1 day ago, you will be asked for the time |
| -1d@9:00        | 1 day ago 9:00                            |
| +1m             | 1 minute from now                         |
| +1h             | 1 hour from now                           |
| 12 7:00         | 7:00 on the 12th of the current month     |
| 02-28 9:00      | 9:00 on February 28 of the current year   |
| 2022-02-28 9:00 | 9:00 on February 28, 2022                 |



### Automatic Rest Periods

If you forget to track a rest period, the time tracker will reduce the required rest period before showing it. For periods greater than 4h 15 are reducted, for periods greater than 6:15 additional 30m are reducted.



TODOs:
- [ ] Add Changelog
- [ ] Add Configuration
  - [ ] ignore seconds
  - [ ] freeze time, to generate useful images
  - [ ] automatic rest periods
- [ ] show and generate tui output
- [ ] Add section about contributions
- [ ] Add precommit hook to ensure code is formatted
- [ ] Add version and git hash to build, so it can be shown in the tui
- [ ] Generate docstrings for DB methods
- [ ] Remove import command (it contains assumptions that will not be true for everyone)
  - [ ] Document how to import data from other time trackers
  - [ ] Add mode to convert hamster output to jsonl file.
  - [ ] Add mode to import jsonl file
- [ ] Add logging
  - [ ] allow different log levels for database and application
- [ ] add a change log
- [ ] README
  - [ ] auto generate config options
- [ ] db
  - [ ] add table for tags


TODOS by command:

- [ ] add
  - [ ] allow passive activities
  - [ ] allow sick days
- [ ] end
  - [ ] add tests

- [ ] configure
  - [ ] modify and write configfile
  - [ ] allow to add aliases for commands
    - [ ] e.g. new new add alias with setting passive to true
- [ ] list
  - [ ] split up multiday activities
  - [ ] add option to show only open activities
  - [ ] group by year, month, week, day
  - [ ] add tests

- [ ] undo (revert the last change)
### Design Goals

- minimalistic, little to type
- enforce as little as possible
- be clear
- be extensible
  - TODO: support plugins (maybe a later version)
  - be able to use it programmatically
  - be able to use it as a library


### Open Questions

- [ ] should the get_latest_segment return segments from the future (start_time in the future)?

### Nice to have:
- [ ] Build a minimal Docker image (maybe)
- [ ] https://github.com/ines/termynal
