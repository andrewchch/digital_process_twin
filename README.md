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

A code-as-process-model framework for defining, validating, executing, and generating representations of sociotechnical business processes — processes that involve both automated (system) actors and human actors.

---

## Overview

`process_model.py` is the core of this project. Its primary purpose is to let you **define a business process entirely in Python code** and then:

- **Validate** the process structure to automatically surface gaps, missing logic, and open questions as trackable work items.
- **Generate process diagrams** (Mermaid flowcharts) directly from the class structure — no manual diagram maintenance required.
- **Simulate / execute** the process end-to-end with a real or mock context, exercising both human and system actors.
- **Collaborate** on the process design: gaps and assumptions discovered during validation become a structured backlog that human and AI agents can work through together.

The design philosophy is that **the code is the canonical process definition**. The diagram and validation report are derived from it automatically, so they are always in sync.

---

## Key Concepts

### Process

The `Process` abstract base class is the orchestrator. A concrete process subclass declares:

- `actors()` — the roles (human or system) that participate.
- `steps()` — the ordered sequence of steps that make up the process.
- `name` / `description` — human-readable metadata.

Key methods:

| Method | Purpose |
|---|---|
| `validate()` | Reflect on the process structure and surface gaps as `WorkItem` objects. |
| `report()` | Print a formatted gap/work-item report to stdout. |
| `generate_mermaid()` | Return a Mermaid flowchart string derived from the step definitions. |
| `print_mermaid()` | Print the Mermaid diagram to stdout. |
| `run(context)` | Execute the process with a shared context dict, stepping through each `Step`. |
| `raise_gap(...)` | Explicitly register a gap, question, assumption, or improvement as a `WorkItem`. |

### Actor

An `Actor` represents a **role** in the process, not a specific person. Roles can be human (e.g. `AuthorActor`, `ApproverActor`) or automated (e.g. `SystemActor`). Each actor implements:

- `perform(action, context)` — carry out a named action and return the updated context.
- `notify(message, context)` — receive a notification (e.g. email, Slack, in-app alert).

Unimplemented actions raise `NotImplementedError`, which `validate()` automatically detects and registers as a gap.

### Step

A `Step` is a discrete unit of work carried out by one `Actor`. Each step class declares:

- `actor` — the responsible `Actor` subclass.
- `inputs` / `outputs` — `DataObject` subclasses consumed and produced.
- `preconditions` / `postconditions` — plain-English invariants.
- `description` — what the step does.
- `handle(context)` — the core step logic (raise `NotImplementedError` to mark as a gap).
- `on_error(context, error)` — compensation / escalation logic on failure.

### DataObject

A `DataObject` is any piece of data that flows through a process. It carries a **state machine**: a defined set of states and valid transitions, enforced at runtime. Attempts to make an invalid transition raise a `ValueError`.

### WorkItem

A `WorkItem` represents a gap, question, assumption, or improvement discovered in the process. Work items are raised automatically by `validate()` or explicitly via `raise_gap()`. Each item has a type, status, owner, and resolution field, forming a **collaboration backlog**.

| Type | Meaning |
|---|---|
| `GAP` | Missing logic or undefined execution path. |
| `QUESTION` | Ambiguity requiring a decision. |
| `ASSUMPTION` | Something assumed that needs confirmation. |
| `IMPROVEMENT` | Optional enhancement. |

---

## Built-in Example: Document Approval Process

The file ships with a fully worked example — `DocumentApprovalProcess` — which models an intranet document workflow:

```
CreateDraft → EditAndFinaliseDraft → SubmitForApproval
  → ReviewDocument → [approved] SetAccessPolicy → PublishDocument
                   → [rejected] EditAndFinaliseDraft (loop)
```

**Actors:** `AuthorActor`, `ApproverActor`, `AdminActor`, `SystemActor`  
**Data objects:** `Document` (with a 7-state machine), `AccessPolicy`, `Notification`

Deliberate gaps are present (e.g. approver assignment logic, notification delivery, access policy ownership) to demonstrate how the validation and work-item system works in practice.

---

## Usage

```python
from process_model import DocumentApprovalProcess

process = DocumentApprovalProcess()

# Surface structural gaps as work items
process.validate()
process.report()

# Generate a Mermaid flowchart
process.print_mermaid()

# Execute the process with a mock context
process.run({
    "user_id":           "alice@example.com",
    "title":             "Q3 Engineering Update",
    "content":           "This quarter we shipped...",
    "approval_decision": "approve",
    "approver_id":       "bob@example.com",
})
```

Or run it directly:

```bash
python process_model.py
```

---

## Defining Your Own Process

1. **Define data objects** — subclass `DataObject`, declare `states`, `initial_state`, and `valid_transitions`.
2. **Define actors** — subclass `Actor`, implement `perform()` and `notify()`.
3. **Define steps** — subclass `Step`, set `actor`, `inputs`, `outputs`, `preconditions`, `postconditions`, and implement `handle()`.
4. **Define the process** — subclass `Process`, implement `actors()` and `steps()`.
5. **Validate and iterate** — call `process.validate()` and `process.report()` to surface gaps, then resolve them one by one.

---

## Potential Applications

- **Process documentation** — keep diagrams and specifications automatically in sync with the code.
- **Gap analysis** — systematically identify and track missing logic, open decisions, and assumptions.
- **Scenario simulation** — run the process with different mock contexts to test happy paths, rejection loops, and edge cases.
- **AI-assisted process design** — use the work-item backlog as structured input for an AI agent to propose resolutions.
