import asyncio
import contextvars
import inspect
import json
import logging
import os
import sys
import textwrap
import time
import uuid


class Input:
    def __init__(self, typ, desc=""):
        self.type = typ
        self.desc = desc
        self.name = None

    def __repr__(self):
        return f"Input(name={self.name!r}, type={self.type}, desc={self.desc!r})"


class _OutputRef:
    def __init__(self, node, key):
        self.node = node
        self.key = key

    def __repr__(self):
        return f"OutputRef(node={self.node.name!r}, key={self.key!r})"


class _OptionalRef:
    def __init__(self, src):
        self.src = src

    def __repr__(self):
        return f"OptionalRef(src={self.src!r})"


def optional(src):
    return _OptionalRef(src)


class _SkipValue:
    def __repr__(self):
        return "SKIP"


SKIP = _SkipValue()


class _Node:
    def __init__(self, func, inputs, outputs, when=None):
        self.func = func
        self.inputs = inputs or {}
        self.outputs = outputs or {}
        self.when = when
        self.name = func.__name__
        self.output_keys = list(self.outputs.keys())
        self.__name__ = func.__name__
        self.__doc__ = func.__doc__

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    def __getattr__(self, item):
        if item in self.outputs:
            return _OutputRef(self, item)
        raise AttributeError(f"{self.name} has no output {item!r}")

    def __repr__(self):
        return f"Node(name={self.name!r})"


def node(inputs=None, outputs=None, when=None):
    def decorator(func):
        return _Node(func, inputs, outputs, when=when)
    return decorator


def _collect_inputs(inputs_cls):
    inputs = {}
    for name, value in inputs_cls.__dict__.items():
        if isinstance(value, Input):
            value.name = name
            inputs[name] = value
    return inputs


def _collect_nodes(namespace):
    return [value for value in namespace.values() if isinstance(value, _Node)]


class _WorkflowContext:
    def __init__(self, logger=None, trace_id=None, run_id=None):
        self.logger = logger or logging.getLogger("workflow")
        self.trace_id = trace_id or uuid.uuid4().hex
        self.run_id = run_id or uuid.uuid4().hex
        self.timings = {}
        self.skipped = {}
        self.results = {}
        self.outputs = {}
        self.logs = {}
        self.start_time = None
        self.end_time = None


_current_node = contextvars.ContextVar("workflow_current_node", default=None)


class _ContextLogHandler(logging.Handler):
    def __init__(self, ctx):
        super().__init__()
        self.ctx = ctx

    def emit(self, record):
        node_name = _current_node.get()
        if not node_name:
            return
        entry = {
            "time": record.created,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.pathname:
            entry["pathname"] = record.pathname
        if record.lineno:
            entry["lineno"] = record.lineno
        if record.exc_info:
            entry["exc_info"] = self.formatException(record.exc_info)
        self.ctx.logs.setdefault(node_name, []).append(entry)


def _attach_log_handler(ctx, level=logging.INFO):
    handler = _ContextLogHandler(ctx)
    handler.setLevel(logging.NOTSET)
    root = logging.getLogger()
    old_level = root.level
    if old_level > level:
        root.setLevel(level)
    root.addHandler(handler)
    return handler, root, old_level


def _detach_log_handler(handler, root, old_level=None):
    if handler and root:
        root.removeHandler(handler)
        if old_level is not None:
            root.setLevel(old_level)


def _build_graph(nodes):
    deps = {node: set() for node in nodes}
    adj = {node: set() for node in nodes}
    for node in nodes:
        for src in node.inputs.values():
            if isinstance(src, _OptionalRef):
                src = src.src
            if isinstance(src, _OutputRef):
                if src.node not in deps:
                    raise ValueError(f"Unknown node dependency: {src.node}")
                deps[node].add(src.node)
                adj[src.node].add(node)
    return deps, adj


def _toposort_levels(nodes, deps, adj):
    indeg = {node: len(deps[node]) for node in nodes}
    queue = [node for node in nodes if indeg[node] == 0]
    levels = []
    order = []
    while queue:
        level = list(queue)
        levels.append(level)
        queue = []
        for node in level:
            order.append(node)
            for nxt in adj[node]:
                indeg[nxt] -= 1
                if indeg[nxt] == 0:
                    queue.append(nxt)
    if len(order) != len(nodes):
        raise ValueError("Circular dependency detected.")
    return levels, order


def _validate_signatures(nodes):
    for node in nodes:
        sig = inspect.signature(node.func)
        params = sig.parameters
        param_names = set(params.keys())
        has_var_kw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values())

        invalid_inputs = [name for name in node.inputs.keys() if name not in param_names]
        if invalid_inputs and not has_var_kw:
            raise ValueError(
                f"{node.name} has inputs {invalid_inputs} not present in "
                f"function signature {list(param_names)}"
            )

        missing_required = []
        for name, p in params.items():
            if p.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                continue
            if p.kind == inspect.Parameter.POSITIONAL_ONLY:
                if p.default is inspect._empty:
                    missing_required.append(name)
                continue
            if p.default is inspect._empty and name not in node.inputs:
                missing_required.append(name)

        if missing_required:
            raise ValueError(
                f"{node.name} is missing required inputs: {missing_required} "
                f"(signature: {sig})"
            )

        for name, p in params.items():
            if p.kind == inspect.Parameter.POSITIONAL_ONLY and name in node.inputs:
                raise ValueError(
                    f"{node.name} uses positional-only parameter {name}; "
                    "workflow injection only supports keyword arguments"
                )


def workflow_compile(inputs_cls, namespace=None):
    if namespace is None:
        module = sys.modules.get(inputs_cls.__module__)
        namespace = module.__dict__ if module else globals()
    inputs = _collect_inputs(inputs_cls)
    nodes = _collect_nodes(namespace)
    _validate_signatures(nodes)
    deps, adj = _build_graph(nodes)
    levels, order = _toposort_levels(nodes, deps, adj)
    return {"inputs": inputs, "nodes": nodes, "order": levels, "flat_order": order}


def workflow_compile_graph(inputs_cls, namespace=None):
    compiled = workflow_compile(inputs_cls, namespace)
    ordered_nodes = compiled["flat_order"]
    inputs_payload = []
    for name, inp in compiled["inputs"].items():
        inputs_payload.append({
            "name": name,
            "type": inp.type.__name__ if inp.type else None,
            "description": inp.desc,
        })

    def _strip_decorators(source_text):
        if not source_text:
            return source_text
        lines = source_text.splitlines()
        start = 0
        for idx, line in enumerate(lines):
            stripped = line.lstrip()
            if stripped.startswith("def ") or stripped.startswith("async def "):
                start = idx
                break
        return "\n".join(lines[start:]).strip()

    nodes_payload = []
    for node in ordered_nodes:
        doc = node.__doc__ or ""
        description = textwrap.dedent(doc).strip()
        try:
            source = textwrap.dedent(inspect.getsource(node.func)).strip()
            source = _strip_decorators(source)
        except (OSError, TypeError):
            source = ""
        nodes_payload.append({
            "name": node.name,
            "inputs": list(node.inputs.keys()),
            "outputs": dict(node.outputs),
            "description": description,
            "source": source,
        })

    edges_payload = []
    for node in compiled["nodes"]:
        for input_name, src in node.inputs.items():
            optional_input = False
            if isinstance(src, _OptionalRef):
                optional_input = True
                src = src.src
            if isinstance(src, _OutputRef):
                edges_payload.append({
                    "source": src.node.name,
                    "target": node.name,
                    "source_output": src.key,
                    "target_input": input_name,
                    "optional": optional_input,
                })

    levels_payload = [
        [node.name for node in level]
        for level in compiled["order"]
    ]
    return {
        "inputs": inputs_payload,
        "nodes": nodes_payload,
        "edges": edges_payload,
        "levels": levels_payload,
    }


def _load_params(inputs):
    raw = os.environ.get("WORKFLOW_PARAM", "{}")
    try:
        data = json.loads(raw) if raw else {}
    except json.JSONDecodeError as exc:
        raise ValueError(f"WORKFLOW_PARAM is not valid JSON: {raw}") from exc
    params = {}
    for name, inp in inputs.items():
        if name not in data:
            raise ValueError(f"Missing input parameter: {name}")
        value = data[name]
        if inp.type is None:
            params[name] = value
            continue
        try:
            params[name] = inp.type(value)
        except Exception as exc:
            raise ValueError(
                f"Parameter {name} cannot be converted to {inp.type}: {value}"
            ) from exc
    return params


def _normalize_outputs(node, result):
    if not node.output_keys:
        return {}
    if len(node.output_keys) == 1:
        return {node.output_keys[0]: result}
    if isinstance(result, dict):
        missing = [key for key in node.output_keys if key not in result]
        if missing:
            raise ValueError(f"{node.name} is missing outputs: {missing}")
        return {key: result[key] for key in node.output_keys}
    if isinstance(result, (list, tuple)) and len(result) == len(node.output_keys):
        return dict(zip(node.output_keys, result))
    raise ValueError(f"{node.name} output does not match declared outputs")


def _resolve_kwargs(node, params, results):
    kwargs = {}
    missing_required = []
    for name, src in node.inputs.items():
        optional_input = False
        if isinstance(src, _OptionalRef):
            optional_input = True
            src = src.src
        if isinstance(src, Input):
            kwargs[name] = params[src.name]
        elif isinstance(src, _OutputRef):
            if src.node not in results:
                if optional_input:
                    kwargs[name] = None
                else:
                    missing_required.append(name)
                continue
            value = results[src.node].get(src.key, SKIP)
            if value is SKIP:
                if optional_input:
                    kwargs[name] = None
                else:
                    missing_required.append(name)
                continue
            kwargs[name] = value
        else:
            kwargs[name] = src
    return kwargs, missing_required


def _skip_outputs(node):
    if not node.output_keys:
        return {}
    return {key: SKIP for key in node.output_keys}


def _call_when(node, kwargs, ctx):
    if node.when is None:
        return True
    try:
        sig = inspect.signature(node.when)
    except (TypeError, ValueError):
        return bool(node.when(**kwargs))
    params = sig.parameters
    has_var_kw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values())
    if has_var_kw:
        call_kwargs = dict(kwargs)
    else:
        call_kwargs = {k: v for k, v in kwargs.items() if k in params}
    if "ctx" in params:
        call_kwargs["ctx"] = ctx
    return bool(node.when(**call_kwargs))


def _final_output(compiled, results):
    last_node = None
    flat_order = compiled.get("flat_order") or []
    if flat_order:
        last_node = flat_order[-1]
    return results.get(last_node) if last_node else None


async def _workflow_run_async(compiled):
    ctx = _WorkflowContext()
    params = _load_params(compiled["inputs"])
    results = {}
    levels = compiled.get("order") or []
    max_concurrency = max((len(level) for level in levels), default=0)
    sem = asyncio.Semaphore(max_concurrency) if max_concurrency else None
    ctx.start_time = time.perf_counter()
    log_handler, log_root, log_old_level = _attach_log_handler(ctx)
    ctx.logger.info(
        "workflow start trace_id=%s run_id=%s", ctx.trace_id, ctx.run_id
    )

    async def _run_node(node):
        token = _current_node.set(node.name)
        try:
            kwargs, missing_required = _resolve_kwargs(node, params, results)
            if missing_required:
                ctx.skipped[node.name] = f"missing inputs: {missing_required}"
                ctx.timings[node.name] = 0.0
                output = _skip_outputs(node)
                ctx.outputs[node.name] = output
                return node, output
            if not _call_when(node, kwargs, ctx):
                ctx.skipped[node.name] = "condition false"
                ctx.timings[node.name] = 0.0
                output = _skip_outputs(node)
                ctx.outputs[node.name] = output
                return node, output
            node_start = time.perf_counter()
            async def _call():
                result = await _execute_node(node, kwargs)
                return node, _normalize_outputs(node, result)
            if sem:
                async with sem:
                    node, output = await _call()
            else:
                node, output = await _call()
            ctx.timings[node.name] = time.perf_counter() - node_start
            ctx.outputs[node.name] = output
            ctx.logger.debug("node done name=%s elapsed=%.6fs", node.name, ctx.timings[node.name])
            return node, output
        finally:
            _current_node.reset(token)

    async def _execute_node(node, kwargs):
        if inspect.iscoroutinefunction(node.func):
            result = await node.func(**kwargs)
        else:
            result = node.func(**kwargs)
        if inspect.isawaitable(result):
            result = await result
        return result

    try:
        for level in levels:
            tasks = [asyncio.create_task(_run_node(node)) for node in level]
            for node, output in await asyncio.gather(*tasks):
                results[node] = output
    finally:
        ctx.end_time = time.perf_counter()
        ctx.logger.info(
            "workflow end trace_id=%s run_id=%s elapsed=%.6fs",
            ctx.trace_id,
            ctx.run_id,
            ctx.end_time - ctx.start_time,
        )
        _detach_log_handler(log_handler, log_root, log_old_level)
    ctx.results = results
    return ctx, _final_output(compiled, results)


def workflow_run(compiled):
    return asyncio.run(
        _workflow_run_async(compiled)
    )

__all__ = ['workflow_run', 'node', 'Input', 'workflow_compile', 'workflow', 'optional', 'SKIP', 'workflow_compile_graph']
