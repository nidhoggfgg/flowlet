# Flowlet API 参考

完整的 flowlet 库 API 文档。

## 核心组件

### Input

定义工作流的输入参数。

```python
class Input:
    def __init__(self, typ, desc=""):
        """
        参数:
            typ: 参数类型（int, str, float, list, dict 等），类型转换会在运行时进行
            desc: 参数描述（用于文档和调试）
        """
```

**使用示例：**

```python
class Inputs:
    name = Input(str, desc="用户名称")
    age = Input(int, desc="用户年龄")
    data = Input(dict, desc="附加数据")
```

**重要：** 运行时需要通过环境变量 `WORKFLOW_PARAM` 提供 JSON 格式的参数值：

```bash
export WORKFLOW_PARAM='{"name": "Alice", "age": 30, "data": {}}'
python workflow.py
```

---

### @node

装饰器，将函数转换为工作流节点。

```python
def node(inputs=None, outputs=None, when=None):
    """
    参数:
        inputs (dict): 输入映射，格式为 {"参数名": 来源}
            - 来源可以是 Input 实例
            - 可以是其他节点的输出引用（other_node.result）
            - 可以是常量值
        outputs (dict): 输出定义，格式为 {"输出名": "描述"}
        when (callable): 条件函数，返回 True 时执行该节点
            - 接收所有 inputs 参数作为关键字参数
            - 可以接收 ctx 参数（当前执行上下文）
    """
```

**inputs 详解：**

- **来自 Inputs**：`Inputs.param_name`
- **来自节点输出**：`other_node.result` 或 `other_node.output_key`（多输出时）
- **常量值**：直接提供字面量或变量
- **可选依赖**：`optional(other_node.result)`

**outputs 详解：**

- 单输出：返回值直接作为输出
- 多输出：返回 dict、list 或 tuple，顺序必须与 outputs 定义一致

**when 条件：**

```python
# 简单条件
when=lambda x, **_: x > 0

# 复杂条件
when=lambda route, data, **_: route == "A" and data is not None

# 使用上下文
when=lambda ctx, **_: ctx.get("allow_execution", True)
```

---

### optional

标记可选依赖，当上游节点未执行时注入 `None`。

```python
def optional(src):
    """
    参数:
        src: 节点输出引用（如 node.result）
    """
```

**使用场景：**

- 条件分支的合并点
- 可能被跳过的上游节点
- 多个可选输入的节点

**示例：**

```python
@node(
    inputs={
        "a": optional(branch_a.result),
        "b": optional(branch_b.result)
    },
    outputs={"result": "合并结果"}
)
def merge(a=None, b=None):
    return a if a is not None else b
```

---

### SKIP

特殊标记值，表示节点被跳过时的输出。

```python
SKIP  # _SkipValue 实例
```

**使用场景：**

通常不需要直接使用，但在检查节点输出时可能会遇到。

---

### workflow_compile

编译工作流，构建 DAG 结构。

```python
def workflow_compile(inputs_cls, namespace=None):
    """
    参数:
        inputs_cls: Inputs 类，包含所有 Input 定义
        namespace: 命名空间（默认为 inputs_cls 所在模块）

    返回:
        dict: 编译后的工作流，包含:
            - inputs: Input 定义
            - nodes: 所有节点对象列表
            - order: 拓扑排序的层级（每层的节点可并行执行）
            - flat_order: 扁平化的节点执行顺序
    """
```

**返回值结构：**

```python
{
    "inputs": {"param_name": Input对象},
    "nodes": [_Node对象列表],
    "order": [[node1, node2], [node3]],  # 每个子列表是一层
    "flat_order": [node1, node2, node3]  # 扁平顺序
}
```

---

### workflow_run

执行编译后的工作流。

```python
def workflow_run(compiled):
    """
    参数:
        compiled: workflow_compile 返回的编译对象

    返回:
        tuple: (ctx, output)
            - ctx: _WorkflowContext 对象，包含执行信息
            - output: 最后一个节点的输出
    """
```

**_WorkflowContext 属性：**

```python
class _WorkflowContext:
    trace_id: str      # 追踪 ID
    run_id: str        # 运行 ID
    timings: dict      # 每个节点的执行时间 {node_name: seconds}
    skipped: dict      # 被跳过的节点 {node_name: reason}
    outputs: dict      # 每个节点的输出 {node_name: {output_key: value}}
    logs: dict         # 每个节点的日志 {node_name: [log_entries]}
    start_time: float  # 开始时间（perf_counter）
    end_time: float    # 结束时间（perf_counter）
```

**示例：**

```python
compiled = workflow_compile(Inputs)
ctx, output = workflow_run(compiled)

print(f"Trace ID: {ctx.trace_id}")
print(f"Total time: {ctx.end_time - ctx.start_time:.3f}s")
print(f"Node timings: {ctx.timings}")
print(f"Final output: {output}")
```

---

### workflow_compile_graph

导出工作流图为可序列化格式。

```python
def workflow_compile_graph(inputs_cls, namespace=None):
    """
    参数:
        inputs_cls: Inputs 类
        namespace: 命名空间

    返回:
        dict: 可序列化的图结构，包含:
            - inputs: 输入定义列表
            - nodes: 节点元数据列表
            - edges: 依赖边列表
            - levels: 并行层级
    """
```

**返回值结构：**

```python
{
    "inputs": [
        {
            "name": "param_name",
            "type": "str",
            "description": "参数描述"
        }
    ],
    "nodes": [
        {
            "name": "node_name",
            "inputs": ["param1", "param2"],
            "outputs": {"result": "输出描述"},
            "description": "节点文档字符串",
            "source": "def node_func(...): ..."
        }
    ],
    "edges": [
        {
            "source": "source_node_name",
            "target": "target_node_name",
            "source_output": "result",
            "target_input": "param1",
            "optional": false
        }
    ],
    "levels": [
        ["node1", "node2"],  # 第1层可并行执行
        ["node3"]            # 第2层
    ]
}
```

**用途：**

- 可视化工作流
- 文档生成
- 工作流分析和验证
- 导出给前端展示

---

## 节点定义规则

### 函数签名

节点函数的参数必须与 `inputs` 定义匹配：

```python
# 正确：参数名与 inputs 的键一致
@node(inputs={"x": Inputs.data, "y": 1}, outputs={"result": "结果"})
def my_node(x, y):
    return x + y

# 错误：参数名不匹配
@node(inputs={"x": Inputs.data}, outputs={"result": "结果"})
def my_node(wrong_name):  # 错误！应该是 x
    return wrong_name
```

### 返回值

```python
# 单输出
@node(inputs={"x": Inputs.data}, outputs={"result": "结果"})
def single_output(x):
    return x * 2  # 直接返回

# 多输出（dict）
@node(
    inputs={"x": Inputs.data},
    outputs={"sum": "和", "product": "积"}
)
def multi_output_dict(x):
    return {"sum": x + x, "product": x * x}

# 多输出（tuple/list）
@node(
    inputs={"x": Inputs.data},
    outputs={"sum": "和", "product": "积"}
)
def multi_output_tuple(x):
    return (x + x, x * x)  # 按顺序对应 outputs 的键
```

### async/await

节点可以是异步函数：

```python
import asyncio

@node(inputs={"url": Inputs.url}, outputs={"result": "响应"})
async def fetch_data(url):
    await asyncio.sleep(1)
    return "data"
```

---

## 错误处理

### 参数验证错误

```python
# 缺少必需参数
ValueError: Missing input parameter: name

# 类型转换失败
ValueError: Parameter age cannot be converted to int: "abc"
```

### 循环依赖检测

```python
# 工作流存在循环依赖
ValueError: Circular dependency detected.
```

### 签名不匹配

```python
# 节点函数参数与 inputs 不匹配
ValueError: node_name has inputs ['missing'] not present in function signature ['x', 'y']

# 缺少必需参数
ValueError: node_name is missing required inputs: ['z'] (signature: (x, y, z))
```

---

## 执行语义

### 并行执行

同一层的所有节点会并行执行（使用 asyncio）：

```python
# 这两个节点会并行执行
@node(inputs={"x": Inputs.a}, outputs={"result": "A"})
def task_a(x):
    pass

@node(inputs={"x": Inputs.b}, outputs={"result": "B"})
def task_b(x):
    pass

# 这个节点等待上面两个完成
@node(inputs={"a": task_a.result, "b": task_b.result}, ...)
def merge(a, b):
    pass
```

### 条件执行

使用 `when` 控制节点是否执行：

- `when` 返回 `True`：正常执行
- `when` 返回 `False`：节点被跳过，输出标记为 `SKIP`
- 条件函数在节点执行前被调用，接收所有输入参数

### 可选依赖

使用 `optional()` 标记可能缺失的依赖：

- 如果上游节点被跳过（输出 `SKIP`），`optional()` 会将其转换为 `None`
- 如果上游节点正常执行，`optional()` 会传递实际输出值

### 日志收集

工作流会自动收集每个节点的日志：

```python
import logging

@node(inputs={"x": Inputs.data}, outputs={"result": "结果"})
def my_node(x):
    logging.info("Processing data")  # 会记录到 ctx.logs[my_node]
    return x
```

---

## 最佳实践

### 1. 命名规范

- Inputs 类：使用 `Inputs`
- 节点函数：使用动词或动词+名词（如 `process_data`, `validate`）
- 输出键：使用描述性名称（如 `result`, `processed_data`, `is_valid`）

### 2. 文档字符串

为节点添加文档字符串：

```python
@node(inputs={"x": Inputs.data}, outputs={"result": "处理结果"})
def process_data(x):
    """
    处理输入数据，执行清洗和转换。

    Args:
        x: 原始数据字符串

    Returns:
        处理后的数据
    """
    return x.strip().lower()
```

### 3. 错误处理

在节点内部处理异常：

```python
@node(inputs={"x": Inputs.data}, outputs={"result": "结果"})
def safe_process(x):
    try:
        return risky_operation(x)
    except Exception as e:
        logging.error(f"Error: {e}")
        return None  # 或返回默认值
```

### 4. 类型转换

利用 Input 的类型转换：

```python
class Inputs:
    count = Input(int, desc="数量")  # 自动从字符串转为整数
    enabled = Input(bool, desc="是否启用")  # 转换为布尔值
```

### 5. 复杂条件

使用辅助函数定义复杂条件：

```python
def should_process_branch(route, data, ctx=None):
    """判断是否应该执行该分支"""
    if route != "A":
        return False
    if data is None:
        return False
    return True

@node(
    inputs={"route": router.route, "data": Inputs.data},
    outputs={"result": "结果"},
    when=should_process_branch
)
def branch_a(route, data):
    pass
```

---

## 限制和注意事项

1. **不支持动态节点**：所有节点必须在编译时定义，不能在运行时动态创建
2. **循环在节点内实现**：如需循环逻辑，在单个异步节点内使用 Python 循环
3. **状态管理**：节点应是无状态的，如需状态管理使用外部存储
4. **并发限制**：同一层的节点并发数等于该层节点数，无法自定义并发限制
5. **取消机制**：不支持运行时取消工作流执行
