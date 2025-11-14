# Timetable Viewer

Internal Flask web application that parses EduPage / ASC Timetable exports
(`data/Classes.html` and `data/Teachers.html`) and renders responsive class and
teacher schedules for students and faculty of the Internal Affairs University.

## Prerequisites

- Python 3.10 or newer (the app uses only the standard library, Flask and
  BeautifulSoup).
- EduPage export files placed in the `data/` directory with the exact names:
  - `data/Classes.html`
  - `data/Teachers.html`

## Installation

```bash
python -m venv .venv
. .venv/bin/activate  # On Windows use: .venv\Scripts\activate
pip install Flask beautifulsoup4
```

If you prefer pinning dependencies, create a `requirements.txt` file with the
packages above and install with `pip install -r requirements.txt`.

## Running the application

1. Ensure the virtual environment is activated and the dependencies are
   installed.
2. From the repository root run one of the following commands:

   ```bash
   flask --app app run --host 0.0.0.0 --port 5000
   # or for quick local testing
   flask --app app run
   ```

   The `--host 0.0.0.0` option exposes the server on your local network so
   students and teachers can reach it. Replace `5000` with another free port if
   required.

3. Open a browser and navigate to `http://<server-ip>:5000/` (for example,
   `http://127.0.0.1:5000/` when running locally). Users can then select their
   school and class or their teacher name to view the corresponding odd and even
   week timetables.

## Updating timetable data

To refresh the schedules, replace `data/Classes.html` and `data/Teachers.html`
with the latest EduPage exports. No server restart is required because the app
parses the files on start-up; simply restart the Flask process to reload the new
data.

## Development tips

- Run `python -m compileall .` to perform a quick syntax check.
- When editing templates or CSS, the development server's auto-reload feature
  (enabled by default when using `flask run`) picks up changes automatically.
