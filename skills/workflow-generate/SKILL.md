---
name: workflow-generate
description: 使用 flowlet 库和 uv 工具自动生成 Python 工作流项目。当用户需要：1) 将需求描述转换为 flowlet 工作流代码，2) 创建完整的工作流项目（包含 uv 初始化、依赖管理、运行脚本），3) 实现特定的工作流模式（顺序、并行、条件分支、扇入扇出等），4) 理解 flowlet API 和最佳实践时使用此 skill。
---

# Flowlet 工作流生成器

## 快速开始

这个 skill 帮助用户使用 [flowlet](https://github.com/your-repo/flowlet) 库创建 Python 工作流，并使用 [uv](https://github.com/astral-sh/uv) 管理项目环境和依赖。

**基本工作流：**

```python
from flowlet import Input, node, workflow_compile, workflow_run

class Inputs:
    data = Input(str, desc="输入数据")

@node(inputs={"x": Inputs.data}, outputs={"result": "结果"})
def process(x):
    return x.upper()

compiled = workflow_compile(Inputs)
ctx, output = workflow_run(compiled)
```

**使用 uv 运行：**
```bash
uv run python workflow.py
```

## 项目生成工作流

当用户描述工作流需求时，按以下步骤生成完整项目：

### 1. 创建项目结构

使用 uv 初始化新项目：

```bash
# 创建项目目录
mkdir my-workflow && cd my-workflow

# 使用 uv 初始化
uv init --lib

# 安装 flowlet
uv pip install flowlet
```

**生成项目模板包含：**
- `pyproject.toml` - 项目配置和依赖声明
- `workflow.py` - 工作流定义文件
- `README.md` - 项目说明文档

### 2. 定义输入参数

从用户需求中提取输入参数，定义 `Inputs` 类：

```python
class Inputs:
    user_id = Input(int, desc="用户ID")
    action = Input(str, desc="操作类型")
    options = Input(dict, desc="选项配置")
```

### 3. 分解任务节点

将需求分解为独立的处理步骤，每个步骤作为一个节点：

- **顺序任务**：前一步的输出作为后一步的输入
- **并行任务**：多个任务共享相同的输入，无相互依赖
- **条件分支**：根据中间结果决定执行路径
- **数据转换**：清洗、验证、格式化数据

### 4. 建立依赖关系

通过 `inputs` 参数建立节点间的依赖：

```python
@node(inputs={"data": Inputs.raw}, outputs={"result": "清洗后数据"})
def clean(data):
    return data.strip()

@node(inputs={"data": clean.result}, outputs={"result": "验证结果"})
def validate(data):
    return len(data) > 0
```

### 5. 处理条件逻辑

使用 `when` 参数实现条件分支，使用 `optional()` 合并分支：

```python
@node(inputs={"x": validate.result}, outputs={"route": "路由"})
def router(x):
    return "A" if x > 0 else "B"

@node(
    inputs={"x": clean.result},
    outputs={"result": "A分支结果"},
    when=lambda route, **_: route == "A"
)
def branch_a(route, x):
    return x * 2

from flowlet import optional

@node(
    inputs={
        "a": optional(branch_a.result),
        "b": optional(branch_b.result)
    },
    outputs={"result": "最终结果"}
)
def merge(a=None, b=None):
    return a if a is not None else b
```

### 6. 配置运行环境

确保项目包含正确的 `pyproject.toml`：

```toml
[project]
name = "my-workflow"
version = "0.1.0"
description = "Flowlet 工作流项目"
requires-python = ">=3.8"
dependencies = [
    "flowlet",
]
```

### 7. 提供运行命令

告诉用户如何使用 uv 运行工作流：

```bash
# 设置参数并运行
export WORKFLOW_PARAM='{"user_id": 123, "action": "process"}'
uv run python workflow.py

# 或一行命令
WORKFLOW_PARAM='{"user_id": 123}' uv run python workflow.py
```

## 常见工作流模式

### 顺序处理

数据经过一系列处理步骤：

```python
@node(inputs={"data": Inputs.raw}, outputs={"result": "验证后"})
def validate(data):
    return data

@node(inputs={"data": validate.result}, outputs={"result": "转换后"})
def transform(data):
    return data

@node(inputs={"data": transform.result}, outputs={"result": "保存后"})
def save(data):
    return data
```

### 并行处理

多个独立任务同时执行：

```python
@node(inputs={"data": Inputs.data}, outputs={"result": "任务1"})
def task1(data):
    return data + "_1"

@node(inputs={"data": Inputs.data}, outputs={"result": "任务2"})
def task2(data):
    return data + "_2"

@node(
    inputs={"t1": task1.result, "t2": task2.result},
    outputs={"result": "合并结果"}
)
def merge(t1, t2):
    return [t1, t2]
```

### 数据处理管道

ETL 或数据流处理：

```python
@node(inputs={"items": Inputs.items}, outputs={"result": "过滤后"})
def filter_items(items):
    return [x for x in items if x > 0]

@node(inputs={"items": filter_items.result}, outputs={"result": "映射后"})
def map_items(items):
    return [x * 2 for x in items]

@node(inputs={"items": map_items.result}, outputs={"result": "聚合结果"})
def reduce_items(items):
    return sum(items)
```

### 多路分支

根据条件执行不同处理：

```python
@node(inputs={"data": Inputs.data}, outputs={"type": "类型"})
def classify(data):
    if isinstance(data, str):
        return "string"
    elif isinstance(data, (int, float)):
        return "number"
    else:
        return "other"

@node(
    inputs={"data": Inputs.data},
    outputs={"result": "字符串处理"},
    when=lambda type, **_: type == "string"
)
def handle_string(type, data):
    return data.upper()
```

## UV 使用指南

### 安装 uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# 或使用 pip
pip install uv
```

### 项目初始化

```bash
# 创建新项目
uv init --lib my-workflow
cd my-workflow

# 安装 flowlet
uv pip install flowlet

# 安装其他依赖
uv pip install requests aiohttp
```

### 运行工作流

```bash
# 基本运行
uv run python workflow.py

# 带参数运行
export WORKFLOW_PARAM='{"data": "test"}'
uv run python workflow.py

# 一行命令
WORKFLOW_PARAM='{"data": "test"}' uv run python workflow.py
```

### 依赖管理

```bash
# 添加依赖
uv pip install package-name

# 更新依赖
uv pip install --upgrade package-name

# 查看已安装的包
uv pip list

# 导出依赖
uv pip freeze > requirements.txt
```

### 开发工具

```bash
# 运行测试（如果配置了）
uv run pytest

# 代码检查
uv run ruff check .

# 格式化代码
uv run ruff format .
```

## 项目模板

### pyproject.toml

```toml
[project]
name = "my-workflow"
version = "0.1.0"
description = "Flowlet 工作流项目"
readme = "README.md"
requires-python = ">=3.8"
dependencies = [
    "flowlet",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### workflow.py 基本结构

```python
import asyncio
import logging
from flowlet import Input, node, workflow_compile, workflow_run

logging.basicConfig(level=logging.INFO)

class Inputs:
    data = Input(str, desc="输入数据")

@node(inputs={"x": Inputs.data}, outputs={"result": "结果"})
def process(x):
    return x

def main():
    compiled = workflow_compile(Inputs)
    ctx, output = workflow_run(compiled)
    print(f"输出: {output}")

if __name__ == "__main__":
    main()
```

## 节点定义规范

### 单输出节点

```python
@node(inputs={"x": Inputs.data}, outputs={"result": "结果"})
def single_output(x):
    return x * 2
```

### 多输出节点

```python
@node(
    inputs={"x": Inputs.data},
    outputs={"sum": "和", "product": "积"}
)
def multi_output(x):
    return {"sum": x + x, "product": x * x}
```

### 异步节点

```python
import asyncio

@node(inputs={"url": Inputs.url}, outputs={"result": "响应"})
async def fetch_data(url):
    await asyncio.sleep(1)
    return "data"
```

## 错误处理

### 参数验证

```python
@node(inputs={"data": Inputs.data}, outputs={"result": "结果"})
def validate_and_process(data):
    if not data:
        raise ValueError("数据不能为空")
    return process(data)
```

### 安全执行

```python
@node(inputs={"data": Inputs.data}, outputs={"result": "结果"})
def safe_process(data):
    try:
        return risky_operation(data)
    except SpecificError as e:
        logging.error(f"操作失败: {e}")
        return default_value
```

## 高级特性

### 多输出引用

```python
@node(
    inputs={"x": Inputs.data},
    outputs={"sum": "和", "count": "计数"}
)
def compute(x):
    return {"sum": sum(x), "count": len(x)}

@node(
    inputs={"total": compute.sum, "num": compute.count},
    outputs={"result": "平均值"}
)
def average(total, num):
    return total / num
```

### 复杂条件

```python
def should_process(route, data, threshold, ctx=None):
    """复杂条件判断"""
    if route != "target":
        return False
    if data is None:
        return False
    return True

@node(
    inputs={"route": router.route, "data": process_data.result},
    outputs={"result": "处理结果"},
    when=should_process
)
def conditional_node(route, data):
    return process(data)
```

### 循环处理（在节点内）

flowlet 不支持动态节点，循环需要在节点内实现：

```python
@node(inputs={"items": Inputs.items}, outputs={"result": "处理结果"})
async def process_loop(items):
    results = []
    for item in items:
        result = await async_process(item)
        results.append(result)
    return results
```

## 调试和监控

### 查看执行信息

```python
compiled = workflow_compile(Inputs)
ctx, output = workflow_run(compiled)

# 执行时间
for node_name, timing in ctx.timings.items():
    print(f"{node_name}: {timing:.3f}秒")

# 跳过的节点
for node_name, reason in ctx.skipped.items():
    print(f"{node_name}: {reason}")

# 各节点输出
for node_name, outputs in ctx.outputs.items():
    print(f"{node_name}: {outputs}")
```

### 导出工作流图

```python
from flowlet import workflow_compile_graph
import json

graph = workflow_compile_graph(Inputs)
print(json.dumps(graph, indent=2, ensure_ascii=False))
```

## 参考资源

### 项目模板

使用 [assets/project_template/](assets/project_template/) 目录作为起点：
- `pyproject.toml` - 项目配置模板
- `workflow.py` - 完整工作流示例
- `README.md` - 项目文档模板

### 详细的 API 文档

查看 [references/api_reference.md](references/api_reference.md) 获取完整的 API 参考，包括：
- 所有函数和类的详细说明
- 参数和返回值
- 错误处理
- 执行语义

### 工作流模式库

查看 [references/patterns.md](references/patterns.md) 获取更多工作流模式：
- 14 种常见模式的完整示例
- 使用场景说明
- 实现细节和注意事项

## 最佳实践

1. **项目结构**
   - 使用 uv 初始化项目结构
   - 在 `pyproject.toml` 中声明所有依赖
   - 保持项目简洁，一个项目一个工作流

2. **命名规范**
   - Inputs 类统一命名为 `Inputs`
   - 节点函数使用动词（`process_data`, `validate_input`）
   - 输出键使用描述性名称（`result`, `processed_data`）

3. **依赖管理**
   - 使用 uv 统一管理依赖
   - 在 `pyproject.toml` 中明确声明依赖版本
   - 使用虚拟环境隔离项目依赖

4. **文档字符串**
   - 为每个节点添加文档字符串
   - 说明输入、输出和处理逻辑

5. **错误处理**
   - 在节点内部处理预期内的异常
   - 对于无法恢复的错误，抛出异常终止工作流

6. **日志记录**
   - 使用 logging 模块记录关键操作
   - 日志会自动收集到 `ctx.logs` 中

7. **性能优化**
   - 识别可以并行执行的独立任务
   - 使用异步节点处理 I/O 密集型操作

## 限制和注意事项

1. **不支持动态节点**：所有节点必须在代码中静态定义
2. **循环在节点内实现**：需要循环时，在单个异步节点内使用 Python 循环
3. **节点应无状态**：避免在节点间共享状态，使用输出传递数据
4. **依赖必须是 DAG**：不能有循环依赖，编译时会检测并报错
5. **参数通过环境变量**：运行时参数必须通过 `WORKFLOW_PARAM` 环境变量提供
6. **uv 版本要求**：确保使用最新版本的 uv 以获得最佳性能
