import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from difflib import get_close_matches
from zoneinfo import ZoneInfo

import yaml

from fw_core import to_utc_iso

DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]


class ScheduleError(Exception):
    pass


@dataclass
class Rule:
    name: str
    lab: str
    profile: str
    start: datetime
    end: datetime


def _parse_time(value, where):
    try:
        return datetime.strptime(str(value), "%H:%M").time()
    except ValueError:
        raise ScheduleError(f"{where}: bad time {value!r}, expected HH:MM")


def short_lab(lab):
    """'Лабораторија 200в  - ТМФ' -> '200в'; falls back to the full name if it has no number."""
    match = re.search(r"\d+\w*", lab)
    return match.group(0) if match else lab


def parse_schedule(text):
    data = yaml.safe_load(text) or {}
    if not isinstance(data, dict) or not data.get("subjects"):
        raise ScheduleError("schedule needs a non-empty `subjects` list")
    data.setdefault("timezone", "Europe/Skopje")
    try:
        ZoneInfo(data["timezone"])
    except Exception:
        raise ScheduleError(f"unknown timezone {data['timezone']!r}")
    return data


def load_schedule(path):
    with open(path) as f:
        return parse_schedule(f.read())


def next_monday(today=None):
    today = today or date.today()
    return today + timedelta(days=7 - today.weekday())


def expand_week(schedule, week_start):
    """Expand weekly slots into concrete rules for the week starting at `week_start` (a Monday)."""
    tz = ZoneInfo(schedule["timezone"])
    rules = []
    for subject in schedule["subjects"]:
        subject_name = subject.get("name")
        if not subject_name:
            raise ScheduleError("every subject needs a `name`")
        for slot in subject.get("slots") or []:
            where = f"{subject_name} slot {slot}"
            day = str(slot.get("day", "")).lower()[:3]
            if day not in DAYS:
                raise ScheduleError(f"{where}: bad day, use one of {DAYS}")
            profile = slot.get("profile") or subject.get("profile") or schedule.get("profile")
            if not profile:
                raise ScheduleError(f"{where}: no profile (set it on slot, subject or top level)")
            labs = slot.get("lab")
            labs = [labs] if isinstance(labs, str) else labs
            if not labs:
                raise ScheduleError(f"{where}: missing `lab`")
            slot_date = week_start + timedelta(days=DAYS.index(day))
            start = datetime.combine(slot_date, _parse_time(slot.get("from"), where), tzinfo=tz)
            end = datetime.combine(slot_date, _parse_time(slot.get("to"), where), tzinfo=tz)
            if end <= start:
                raise ScheduleError(f"{where}: `to` must be after `from`")
            for lab in labs:
                name = f"{subject_name}-{short_lab(lab)}-{day}-{start:%d.%m}-{start:%H%M}"
                rules.append(Rule(name, lab, profile, start, end))
    return rules


def validate_names(rules, lab_data, profile_data):
    """Return list of error strings for lab/profile names unknown to the REST API."""
    errors = []
    for kind, wanted, known in (
        ("lab", {r.lab for r in rules}, lab_data),
        ("profile", {r.profile for r in rules}, profile_data),
    ):
        for name in sorted(wanted - known.keys()):
            hint = get_close_matches(name, known.keys(), n=1)
            suffix = f" (did you mean {hint[0]!r}?)" if hint else ""
            errors.append(f"unknown {kind} {name!r}{suffix}")
    return errors


def rule_times_utc(rule):
    return to_utc_iso(rule.start), to_utc_iso(rule.end)
