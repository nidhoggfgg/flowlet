# flowlet

A lightweight Python workflow engine with DAG nodes, async execution, conditional branches, and optional dependencies.

## Features

- Function-based node definition with dependency resolution
- Concurrent execution within each DAG level (asyncio)
- Conditional branches via `when`
- Optional dependencies via `optional(...)`
- Runtime inputs injected from `WORKFLOW_PARAM` (JSON)
- Execution context: trace_id, run_id, timings, logs, outputs
- Exportable workflow graph via `workflow_compile_graph`

## Installation

```bash
pip install flowlet
```

## Quickstart

```python
import asyncio
from flowlet import Input, node, optional, workflow_compile, workflow_run

class Inputs:
    a = Input(int, desc="param a")
    b = Input(int, desc="param b")

@node(inputs={"x": Inputs.a}, outputs={"result": "x"})
async def step1(x):
    await asyncio.sleep(0.1)
    return x + 1

@node(inputs={"y": Inputs.b}, outputs={"result": "y"})
def step2(y):
    return y * 2

@node(inputs={"x": step1.result, "y": step2.result}, outputs={"route": "branch"})
def route(x, y):
    return "A" if x + y >= 0 else "B"

@node(
    inputs={"route": route.route, "x": step1.result},
    outputs={"result": "A"},
    when=lambda route, **_: route == "A",
)
def step_a(route, x):
    return x * 10

@node(
    inputs={"route": route.route, "y": step2.result},
    outputs={"result": "B"},
    when=lambda route, **_: route == "B",
)
def step_b(route, y):
    return y * -10

@node(
    inputs={"a": optional(step_a.result), "b": optional(step_b.result)},
    outputs={"result": "merge"},
)
def merge(a=None, b=None):
    return a if a is not None else b

compiled = workflow_compile(Inputs)
ctx, output = workflow_run(compiled)
print(output)
```

Provide runtime inputs via environment variable:

```bash
export WORKFLOW_PARAM='{"a": 1, "b": 2}'
python your_app.py
```

## Concepts

### Inputs

Declare inputs with `Input(type, desc)` and provide values through `WORKFLOW_PARAM`. Types are cast at runtime.

### Node

Use `@node(inputs=..., outputs=..., when=...)` to wrap a function:

- `inputs`: mapping of parameter name to `Input` or upstream output
- `outputs`: output names and descriptions
- `when`: callable that returns True/False to control execution

### Optional dependencies

Use `optional(step.result)` for dependencies that may be missing; they are injected as `None`.

### Execution

`workflow_compile(Inputs)` builds a compiled graph. `workflow_run(compiled)` runs the workflow and returns:

- `ctx` with trace_id, run_id, timings, logs, outputs, skipped
- `output` is the last node's output

### Graph export

`workflow_compile_graph(Inputs)` returns a serializable DAG:

- `inputs`: input definitions
- `nodes`: node metadata including docstring and source
- `edges`: dependency edges
- `levels`: parallel execution levels

## Notes

- `WORKFLOW_PARAM` must be valid JSON.
- For a single output, return a scalar. For multiple outputs, return a dict or tuple/list.

## License

MIT
