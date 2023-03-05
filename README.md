Time Turner
===========

## A Minimalistic Time Tracker.

This is a minimalistic time tracker that allows you to record when you start working, even if it is in the past, stop running activities now, and add activities from the past. It also ensures legal rest periods are included if you forgot to track them.

In the Harry Potter series, the Time-Turner is a magical device that allows the user to travel back in time. Time Turner is a time tracker that lets you "turn back time" and record activities from the past.

## Usage

### Starting an Activity

To start tracking an activity, run the following command:


```
tt start
```

This will record the current time as the start of your activity.



### Starting an Activity in the Past

If you forgot to start tracking an activity, you can add it with the following command:

```
tt start <start_time>
```

### Stopping an Activity

To stop tracking the current activity, run the following command:

```
tt stop
```

This will record the current time as the end of your activity and calculate the total duration.

### Adding a Past Activity

If you forgot to track an activity, you can add it with the following command:

```
tt add <start_time> <end_time>
```

Replace <start_time> and <end_time> with the start and end times of your activity in the format YYYY-MM-DD HH:MM:SS. For example:

```
tt add 2022-02-28 09:00 2022-02-28 12:00
```

This will add the activity with the specified start and end times to your records.

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


### Tracking Legal Rest Periods

If you start an activity at 9:00 and work for 7 hours without taking a legal rest period, the time tracker will automatically add a 30-minute rest period when you stop the activity. To record this activity, run the following commands:

```
tt start
# Work for 7 hours without stopping
tt stop
```

This will record the activity with a duration of 7 hours and 30 minutes.

### Legal Rest Periods (TODO: should be part of reporting)

If you forget to track a legal rest period, the time tracker will automatically add it when you stop an activity. The legal rest periods are inserted without changing the total duration. For now only the following check is implemented:

- Make sure you took at least 45 min of rest a day.
- Warn if you worked more than 10 hours a day.


TODOs:
- [ ] Add Changelog
- [ ] Add Configuration
- [ ] show and generate tui output
- [ ] Add section about contributions
- [ ] Add license
- [ ] Add precommit hook to ensure code is formatted
- [ ] Add version and git hash to build, so it can be shown in the tui
- [ ] Generate docstrings for DB methods
- [ ] Build a minimal Docker image (maybe)

TODOS by command:

- [ ] add
  - [ ] auto close activities that are still open
  - [ ] break up activities when a activity is inserted in the middle
  - [ ] add tests
- [ ] stop (maybe rename to end)
  - [ ] add tests

- [ ] configure
  - [ ] modify and write configfile
- [ ] list
  - [ ] add option to show only open activities
  - [ ] add shortcut / alias `l`
  - [ ] add tests
### Design Goals

- minimalistic, little to type
- enforce as little as possible
- be clear
- be extensible
  - TODO: support plugins (maybe a later version)
  - be able to use it programmatically
  - be able to use it as a library


### Open Questions

- [ ] should the get_latest_slot return slots from the future (start_time in the future)?
