import argparse
import os
import sys
from datetime import timedelta

import requests

import cron_manager
import fw_core
from get_tokens import AuthError, authenticate
from schedule import ScheduleError, expand_week, load_schedule, next_monday, rule_times_utc, validate_names

DEFAULT_FILE = os.environ.get("FW_SCHEDULE_FILE", "schedule.yaml")


def cmd_list_labs(args):
    print("\n".join(fw_core.fetch_labs()))


def cmd_list_profiles(args):
    print("\n".join(fw_core.fetch_profiles()))


def cmd_run(args):
    schedule = load_schedule(args.file)
    week_start = next_monday()
    rules = []
    for i in range(args.weeks_ahead):
        rules += expand_week(schedule, week_start + timedelta(weeks=i))

    labs, profiles = fw_core.fetch_labs(), fw_core.fetch_profiles()
    errors = validate_names(rules, labs, profiles)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 2

    payloads = []
    for rule in rules:
        time_from, time_to = rule_times_utc(rule)
        payloads.append((rule, fw_core.build_payload(
            rule.name, labs[rule.lab], profiles[rule.profile], time_from, time_to)))

    if args.dry_run:
        for rule, payload in payloads:
            print(f"{rule.name}: {rule.lab} / {rule.profile} {payload['timeFrom']} -> {payload['timeTo']}")
        print(f"{len(payloads)} rule(s), dry run, nothing sent")
        return 0

    username, password = os.environ.get("FW_USERNAME"), os.environ.get("FW_PASSWORD")
    if not username or not password:
        print("set FW_USERNAME and FW_PASSWORD", file=sys.stderr)
        return 2
    try:
        token, cookie = authenticate(username, password)
    except AuthError as e:
        print(f"auth failed: {e}", file=sys.stderr)
        return 1

    failed = 0
    for rule, payload in payloads:
        try:
            fw_core.create_reservation(token, cookie, payload)
            print(f"OK   {rule.name}")
        except requests.RequestException as e:
            failed += 1
            print(f"FAIL {rule.name}: {e}", file=sys.stderr)
    print(f"{len(payloads) - failed}/{len(payloads)} created")
    return 1 if failed else 0


def cmd_install_cron(args):
    cron_manager.install_cron(args.file, args.cron)
    print(cron_manager.show_cron())


def cmd_uninstall_cron(args):
    cron_manager.uninstall_cron()


def cmd_show_cron(args):
    print(cron_manager.show_cron() or "no finki-fw cron installed")


def main():
    parser = argparse.ArgumentParser(description="FINKI firewall rule scheduler")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list-labs", help="print valid lab names").set_defaults(func=cmd_list_labs)
    sub.add_parser("list-profiles", help="print valid profile names").set_defaults(func=cmd_list_profiles)

    run = sub.add_parser("run", help="create next week's rules from the schedule file")
    run.add_argument("--file", default=DEFAULT_FILE)
    run.add_argument("--weeks-ahead", type=int, default=1)
    run.add_argument("--dry-run", action="store_true")
    run.set_defaults(func=cmd_run)

    install = sub.add_parser("install-cron", help="add weekly cron entry")
    install.add_argument("--file", default=DEFAULT_FILE)
    install.add_argument("--cron", default=cron_manager.DEFAULT_CRON)
    install.set_defaults(func=cmd_install_cron)

    sub.add_parser("uninstall-cron").set_defaults(func=cmd_uninstall_cron)
    sub.add_parser("show-cron").set_defaults(func=cmd_show_cron)

    args = parser.parse_args()
    try:
        sys.exit(args.func(args))
    except ScheduleError as e:
        print(f"schedule error: {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
