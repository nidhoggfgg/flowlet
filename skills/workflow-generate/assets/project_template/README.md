# Flowlet 工作流项目

这是一个使用 [flowlet](https://github.com/your-repo/flowlet) 构建的工作流项目。

## 环境要求

- Python >= 3.8
- [uv](https://github.com/astral-sh/uv) (推荐的 Python 包管理器)

## 安装 uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# 或使用 pip
pip install uv
```

## 项目初始化

如果这是一个新项目，使用以下命令初始化：

```bash
# 使用 uv 初始化项目
uv init --lib

# 安装 flowlet 依赖
uv pip install flowlet
```

## 运行工作流

### 1. 基本运行

```bash
uv run python workflow.py
```

### 2. 设置参数并运行

通过环境变量 `WORKFLOW_PARAM` 传递 JSON 格式的参数：

```bash
export WORKFLOW_PARAM='{"input_data": "hello", "config": {}, "threshold": 10}'
uv run python workflow.py
```

### 3. 一行命令运行

```bash
WORKFLOW_PARAM='{"input_data": "hello"}' uv run python workflow.py
```

## 项目结构

```
.
├── pyproject.toml    # 项目配置和依赖
├── workflow.py       # 工作流定义
└── README.md         # 本文件
```

## 开发工作流

1. **定义输入参数**：在 `Inputs` 类中添加输入参数
2. **创建节点**：使用 `@node` 装饰器定义处理步骤
3. **建立依赖**：通过 `inputs` 参数连接节点
4. **编译和运行**：使用 `workflow_compile` 和 `workflow_run`

## 常见命令

```bash
# 添加新依赖
uv pip install <package-name>

# 更新依赖
uv pip install --upgrade <package-name>

# 查看已安装的包
uv pip list

# 运行测试（如果有）
uv run pytest

# 运行 linting（如果有）
uv run ruff check .
```

## 调试技巧

启用详细日志：

```python
# 在 workflow.py 中修改日志级别
logging.basicConfig(level=logging.DEBUG)
```

查看工作流图结构：

```python
from flowlet import workflow_compile_graph
import json

graph = workflow_compile_graph(Inputs)
print(json.dumps(graph, indent=2, ensure_ascii=False))
```

## 更多信息

- [Flowlet API 文档](https://docs.flowlet.dev)
- [工作流模式参考](https://docs.flowlet.dev/patterns)
- [uv 文档](https://github.com/astral-sh/uv)
