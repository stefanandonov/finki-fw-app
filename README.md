# Usage

```shell
git clone https://github.com/stefanandonov/finki-fw-app
cd finki-fw-app
docker build -t streamlit-app .
docker run -p 8501:8501 streamlit-app
```

Open localhost:8501 after that to use the app.

# Weekly schedule

Rules for next week (Mon-Sun) are created from a YAML file. Copy `schedule.example.yaml` to `schedule.yaml`:

```yaml
timezone: Europe/Skopje
profile: Default Profile          # optional global default
subjects:
  - name: WP
    profile: Some Profile         # optional subject-level override
    slots:
      - {lab: Lab 1, day: mon, from: "10:00", to: "12:00"}
      - {lab: [Lab 1, Lab 3], day: wed, from: "14:00", to: "16:00", profile: Other Profile}
```

Profile resolves slot > subject > top level. A slot with several labs creates one rule per lab.
Lab and profile names must match the site exactly.

## CLI

Credentials come from the environment: `FW_USERNAME`, `FW_PASSWORD`.

```shell
pip install -r requirements.txt
python cli.py list-labs                               # valid lab names
python cli.py list-profiles                           # valid profile names
python cli.py run --file schedule.yaml --dry-run      # print what would be created
FW_USERNAME=... FW_PASSWORD=... python cli.py run --file schedule.yaml
python cli.py install-cron --file schedule.yaml       # default: Sundays 18:00
python cli.py install-cron --file schedule.yaml --cron "0 20 * * 5"
python cli.py show-cron
python cli.py uninstall-cron
```

`run` has no duplicate detection: running it twice creates the rules twice.
Cron is skipped if the machine is off at that time, so run it on an always-on server.

Cron does not inherit your shell environment: put `FW_USERNAME` and `FW_PASSWORD` in the crontab
(`crontab -e`, lines above the `# BEGIN finki-fw` block) or edit the installed line to export them.
The cron log is `fw-cron.log`, next to the schedule file.

The "Weekly schedule" tab in the Streamlit app does the same as `install-cron`, on the machine running Streamlit.
