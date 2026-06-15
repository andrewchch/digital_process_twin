# Copilot Instructions for digital_process_twin

## Project Purpose

`digital_process_twin` is a **code-as-process-model** framework for defining, validating, executing, and generating representations of sociotechnical business processes — processes that involve both automated (system) actors and human actors. The canonical process definition lives in Python code; diagrams and validation reports are derived from it automatically.

A minimal Flask web UI (`app.py`) lets users enter a process description and view a generated diagram.

---

## Repository Layout

| Path | Purpose |
|---|---|
| `app.py` | Flask application entry point. Serves the web UI and calls `generate_diagram`. |
| `process_model.py` | Core framework: `Process`, `Actor`, `Step`, `DataObject`, `WorkItem` abstractions plus the built-in `DocumentApprovalProcess` example. |
| `process_diagram.py` | `generate_diagram(process_description: str) -> str` stub — returns a sanitized SVG string. |
| `templates/index.html` | Jinja2 template for the Flask web UI. |
| `static/style.css` | Stylesheet for the web UI. |
| `requirements.txt` | Python dependencies. |

---

## Key Abstractions

### `Process`
Abstract base class. Subclasses must implement:
- `actors()` — list of `Actor` subclasses participating in the process.
- `steps()` — ordered list of `Step` subclasses.
- `name` / `description` — human-readable metadata.

Key methods: `validate()`, `report()`, `generate_mermaid()`, `print_mermaid()`, `run(context)`, `raise_gap(...)`.

### `Actor`
Represents a **role** (not a specific person). May be human (e.g. `AuthorActor`) or automated (e.g. `SystemActor`). Must implement `perform(action, context)` and `notify(message, context)`. Unimplemented actions raise `NotImplementedError`, which `validate()` detects automatically.

### `Step`
A discrete unit of work carried out by one `Actor`. Declares:
- `actor` — responsible `Actor` subclass.
- `inputs` / `outputs` — `DataObject` subclasses.
- `preconditions` / `postconditions` — plain-English invariants.
- `handle(context)` — core step logic; raise `NotImplementedError` to mark as a gap.
- `on_error(context, error)` — compensation / escalation logic.

### `DataObject`
A piece of data flowing through the process. Carries a **state machine** with defined states and valid transitions enforced at runtime; invalid transitions raise `ValueError`.

### `WorkItem`
A gap, question, assumption, or improvement. Raised automatically by `validate()` or explicitly via `raise_gap()`. Types: `GAP`, `QUESTION`, `ASSUMPTION`, `IMPROVEMENT`.

---

## Coding Conventions

- **Python 3** throughout; use type hints on all new functions and methods.
- **Abstract base classes** via `abc.ABC` / `@abc.abstractmethod` for `Process`, `Actor`, `Step`, and `DataObject`.
- **No external diagram library required** — `generate_mermaid()` builds Mermaid flowchart strings directly.
- **Sanitization contract:** `generate_diagram` in `process_diagram.py` **must** return a fully sanitized SVG string. All user-supplied text must be HTML-escaped before inclusion so the result is safe to embed directly in the page.
- **Flask configuration:** never enable `FLASK_DEBUG=true` in production — debug mode allows arbitrary code execution.
- Follow existing patterns when adding new `Step`, `Actor`, or `DataObject` subclasses (see `DocumentApprovalProcess` in `process_model.py` as the reference example).

---

## Running Locally

```bash
pip install -r requirements.txt
python app.py
# Open http://127.0.0.1:5000
```

To exercise the process model directly:

```bash
python process_model.py
```

---

## Extending the Framework

1. **New data objects** — subclass `DataObject`; declare `states`, `initial_state`, and `valid_transitions`.
2. **New actors** — subclass `Actor`; implement `perform()` and `notify()`.
3. **New steps** — subclass `Step`; set `actor`, `inputs`, `outputs`, conditions, and implement `handle()`.
4. **New processes** — subclass `Process`; implement `actors()` and `steps()`.
5. **Validate and iterate** — call `process.validate()` and `process.report()` to surface gaps, then resolve them.

---

## Common Pitfalls

- Leaving `handle()` unimplemented (`NotImplementedError`) is intentional to mark gaps — do not suppress these errors; `validate()` relies on them.
- State-machine transitions in `DataObject` are enforced at runtime; ensure `valid_transitions` is complete before adding new states.
- The web app embeds SVG directly in the HTML response — never skip HTML-escaping user input inside `generate_diagram`.
