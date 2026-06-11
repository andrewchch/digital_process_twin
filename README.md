# digital_process_twin
A simulation of a process with human actor behaviours defined in code

## Web App

A minimal [Flask](https://flask.palletsprojects.com/) UI lets you enter a process description and view the generated diagram.

### Quick start

```bash
pip install -r requirements.txt
python app.py
```

Then open <http://127.0.0.1:5000> in your browser.

### Diagram generation

The `generate_diagram(process_description: str) -> str` function in `process_diagram.py` is a stub that returns a placeholder SVG.  Replace its body with the real implementation when ready.

**Sanitization contract:** `generate_diagram` must return a fully sanitized SVG string.  All user-supplied text must be HTML-escaped before inclusion so the result is safe to embed directly in the page.

### Configuration

| Environment variable | Default | Description |
|---|---|---|
| `FLASK_DEBUG` | `false` | Set to `true` only in development – **never in production**, as debug mode allows arbitrary code execution. |
