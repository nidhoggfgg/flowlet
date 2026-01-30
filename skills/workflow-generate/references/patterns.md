# Flowlet 常见工作流模式

本文档描述使用 flowlet 实现的常见工作流模式。

## 1. 顺序执行模式

最简单的工作流，节点按顺序执行。

```python
from flowlet import Input, node, workflow_compile, workflow_run

class Inputs:
    data = Input(str, desc="输入数据")

@node(inputs={"x": Inputs.data}, outputs={"result": "处理后的数据"})
def step1(x):
    return x.upper()

@node(inputs={"x": step1.result}, outputs={"result": "最终结果"})
def step2(x):
    return x + "_PROCESSED"

compiled = workflow_compile(Inputs)
ctx, output = workflow_run(compiled)
```

## 2. 并行执行模式

多个节点在同一层级并行执行（没有依赖关系）。

```python
@node(inputs={"x": Inputs.data}, outputs={"result": "结果A"})
def task_a(x):
    # 与 task_b 并行执行
    return x + "_A"

@node(inputs={"x": Inputs.data}, outputs={"result": "结果B"})
def task_b(x):
    # 与 task_a 并行执行
    return x + "_B"

@node(
    inputs={
        "a": task_a.result,
        "b": task_b.result
    },
    outputs={"result": "合并结果"}
)
def merge(a, b):
    return f"{a} | {b}"
```

## 3. 条件分支模式

根据条件执行不同的分支。

```python
@node(inputs={"x": Inputs.data}, outputs={"route": "路由"})
def router(x):
    return "positive" if x > 0 else "negative"

@node(
    inputs={"x": Inputs.data},
    outputs={"result": "正数处理"},
    when=lambda route, **_: route == "positive"
)
def handle_positive(route, x):
    return x * 2

@node(
    inputs={"x": Inputs.data},
    outputs={"result": "负数处理"},
    when=lambda route, **_: route == "negative"
)
def handle_negative(route, x):
    return x * 3

# 使用 optional 合并分支结果
from flowlet import optional

@node(
    inputs={
        "pos": optional(handle_positive.result),
        "neg": optional(handle_negative.result)
    },
    outputs={"result": "最终结果"}
)
def merge_branches(pos=None, neg=None):
    return pos if pos is not None else neg
```

## 4. 多路分支模式

基于多个条件进行路由。

```python
@node(inputs={"x": Inputs.data}, outputs={"category": "分类"})
def categorize(x):
    if x < 10:
        return "small"
    elif x < 100:
        return "medium"
    else:
        return "large"

@node(
    inputs={"x": Inputs.data},
    outputs={"result": "小值处理"},
    when=lambda category, **_: category == "small"
)
def handle_small(category, x):
    return x * 10

@node(
    inputs={"x": Inputs.data},
    outputs={"result": "中值处理"},
    when=lambda category, **_: category == "medium"
)
def handle_medium(category, x):
    return x * 100

@node(
    inputs={"x": Inputs.data},
    outputs={"result": "大值处理"},
    when=lambda category, **_: category == "large"
)
def handle_large(category, x):
    return x * 1000
```

## 5. 数据处理管道模式

典型的 ETL 或数据处理流水线。

```python
class Inputs:
    raw_data = Input(list, desc="原始数据列表")

@node(inputs={"data": Inputs.raw_data}, outputs={"result": "过滤后数据"})
def filter_data(data):
    return [x for x in data if x > 0]

@node(inputs={"data": filter_data.result}, outputs={"result": "转换后数据"})
def transform_data(data):
    return [x * 2 for x in data]

@node(inputs={"data": transform_data.result}, outputs={"result": "聚合结果"})
def aggregate_data(data):
    return sum(data)
```

## 6. 错误处理和重试模式

在工作流中处理可能的错误。

```python
@node(inputs={"x": Inputs.data}, outputs={"result": "处理结果", "error": "错误信息"})
def process_with_fallback(x):
    try:
        result = risky_operation(x)
        return {"result": result, "error": None}
    except Exception as e:
        return {"result": None, "error": str(e)}

@node(
    inputs={
        "result": process_with_fallback.result,
        "error": process_with_fallback.error
    },
    outputs={"result": "最终结果"}
)
def handle_result(result, error):
    if error:
        return f"Error occurred: {error}, using fallback"
    return f"Success: {result}"
```

## 7. 批处理模式

处理批量数据，每个批次独立处理。

```python
class Inputs:
    items = Input(list, desc="待处理项目列表")
    batch_size = Input(int, desc="批次大小")

@node(
    inputs={"items": Inputs.items, "size": Inputs.batch_size},
    outputs={"batches": "批次列表"}
)
def create_batches(items, size):
    return [items[i:i + size] for i in range(0, len(items), size)]

# 注意：flowlet 目前不直接支持动态节点，需要在编译时确定节点结构
# 批处理通常需要在单个节点内处理
```

## 8. 超时和取消模式

使用 asyncio 实现超时控制。

```python
import asyncio

@node(inputs={"x": Inputs.data}, outputs={"result": "结果"})
async def process_with_timeout(x):
    try:
        result = await asyncio.wait_for(
            slow_operation(x),
            timeout=5.0
        )
        return result
    except asyncio.TimeoutError:
        return "TIMEOUT"
```

## 9. 状态机模式

通过条件分支实现状态转换。

```python
@node(inputs={"x": Inputs.data}, outputs={"state": "当前状态"})
def initialize(x):
    return "initialized"

@node(
    inputs={"x": Inputs.data},
    outputs={"state": "处理状态"},
    when=lambda state, **_: state == "initialized"
)
def process(state, x):
    # 处理逻辑
    return "processed"

@node(
    inputs={"x": Inputs.data},
    outputs={"state": "完成状态"},
    when=lambda state, **_: state == "processed"
)
def finalize(state, x):
    # 完成逻辑
    return "completed"
```

## 10. 扇入扇出模式

一个任务分发到多个并行任务，然后汇总结果。

```python
@node(inputs={"x": Inputs.data}, outputs={"result": "原始数据"})
def split(x):
    return x

@node(inputs={"x": split.result}, outputs={"result": "任务1结果"})
def task1(x):
    return x + "_task1"

@node(inputs={"x": split.result}, outputs={"result": "任务2结果"})
def task2(x):
    return x + "_task2"

@node(inputs={"x": split.result}, outputs={"result": "任务3结果"})
def task3(x):
    return x + "_task3"

@node(
    inputs={
        "t1": task1.result,
        "t2": task2.result,
        "t3": task3.result
    },
    outputs={"result": "汇总结果"}
)
def aggregate(t1, t2, t3):
    return [t1, t2, t3]
```

## 11. 循环模式（有限次数）

flowlet 不支持动态循环，但可以用固定节点模拟。

```python
@node(inputs={"x": Inputs.data}, outputs={"result": "第1次迭代"})
def iteration1(x):
    return process(x, 1)

@node(inputs={"x": iteration1.result}, outputs={"result": "第2次迭代"})
def iteration2(x):
    return process(x, 2)

@node(inputs={"x": iteration2.result}, outputs={"result": "第3次迭代"})
def iteration3(x):
    return process(x, 3)

# 对于复杂循环，建议在单个异步节点内实现
@node(inputs={"x": Inputs.data}, outputs={"result": "循环结果"})
async def loop_in_node(x):
    result = x
    for i in range(10):
        result = await process_step(result, i)
    return result
```

## 12. 外系统集成模式

与外部服务交互的工作流。

```python
import asyncio

@node(inputs={"url": Inputs.data}, outputs={"result": "响应数据"})
async def fetch_data(url):
    # 使用 aiohttp 或 httpx
    import aiohttp
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()

@node(inputs={"data": fetch_data.result}, outputs={"result": "处理结果"})
def process_response(data):
    # 处理 API 响应
    return data.get("results", [])
```

## 13. 缓存模式

避免重复计算。

```python
# 在节点级别实现缓存
_cache = {}

@node(inputs={"x": Inputs.data}, outputs={"result": "缓存结果"})
def with_cache(x):
    if x not in _cache:
        _cache[x] = expensive_computation(x)
    return _cache[x]
```

## 14. 链式验证模式

多步骤验证流程。

```python
@node(inputs={"x": Inputs.data}, outputs={"result": "格式验证"})
def validate_format(x):
    if not isinstance(x, str):
        raise ValueError("Invalid format")
    return x

@node(inputs={"x": validate_format.result}, outputs={"result": "内容验证"})
def validate_content(x):
    if len(x) == 0:
        raise ValueError("Empty content")
    return x

@node(inputs={"x": validate_content.result}, outputs={"result": "业务验证"})
def validate_business(x):
    if "forbidden" in x:
        raise ValueError("Forbidden content")
    return x
```

## 注意事项

1. **节点定义必须使用装饰器**：所有工作流节点必须使用 `@node` 装饰器
2. **依赖关系通过 inputs 声明**：通过引用其他节点的 `.result` 建立依赖
3. **条件分支使用 when**：when 函数接收所有输入参数作为关键字参数
4. **optional 用于可选依赖**：当上游节点可能不执行时使用 `optional()`
5. **动态节点不支持**：flowlet 在编译时构建 DAG，不支持运行时动态创建节点
6. **循环在节点内实现**：如需循环，在单个异步节点内使用 Python 循环
