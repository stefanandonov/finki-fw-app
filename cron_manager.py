import shlex
import subprocess
import sys
from pathlib import Path

BEGIN = "# BEGIN finki-fw"
END = "# END finki-fw"
DEFAULT_CRON = "0 18 * * 0"  # Sunday 18:00
HERE = Path(__file__).resolve().parent


def _read_crontab():
    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    return result.stdout if result.returncode == 0 else ""


def _write_crontab(text):
    subprocess.run(["crontab", "-"], input=text, text=True, check=True)


def _strip_block(text):
    lines, skipping = [], False
    for line in text.splitlines():
        if line.strip() == BEGIN:
            skipping = True
        elif line.strip() == END:
            skipping = False
        elif not skipping:
            lines.append(line)
    return lines


def show_cron():
    text = _read_crontab()
    if BEGIN not in text:
        return ""
    return text[text.index(BEGIN):text.index(END) + len(END)]


def install_cron(schedule_file, cron_expr=DEFAULT_CRON, log_file=None):
    schedule_file = Path(schedule_file).resolve()
    log_file = Path(log_file) if log_file else schedule_file.parent / "fw-cron.log"
    command = (
        f"cd {shlex.quote(str(HERE))} && "
        f"{shlex.quote(sys.executable)} cli.py run --file {shlex.quote(str(schedule_file))} "
        f">> {shlex.quote(str(log_file))} 2>&1"
    )
    lines = _strip_block(_read_crontab())
    lines += [BEGIN, f"{cron_expr} {command}", END]
    _write_crontab("\n".join(lines) + "\n")


def uninstall_cron():
    lines = _strip_block(_read_crontab())
    _write_crontab("\n".join(lines) + "\n" if lines else "")
