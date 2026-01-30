"""
Flowlet 工作流项目

使用 uv 管理项目依赖和运行：

1. 初始化项目（如果还没初始化）：
   uv init --lib
   uv pip install flowlet

2. 运行工作流：
   uv run python workflow.py

3. 设置参数并运行：
   export WORKFLOW_PARAM='{"param1": "value1"}'
   uv run python workflow.py
"""

import asyncio
import logging
from flowlet import Input, node, optional, workflow_compile, workflow_run

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


# ==================== 步骤 1: 定义输入参数 ====================
class Inputs:
    """定义工作流的所有输入参数"""

    # 示例参数，根据实际需求修改
    input_data = Input(str, desc="输入数据")
    config = Input(dict, desc="配置参数")
    threshold = Input(int, desc="阈值")


# ==================== 步骤 2: 定义工作流节点 ====================

@node(
    inputs={"data": Inputs.input_data},
    outputs={"result": "验证后的数据"}
)
def validate_input(data):
    """
    验证输入数据

    Args:
        data: 原始输入数据

    Returns:
        验证后的数据，如果无效则抛出异常
    """
    logging.info(f"验证输入数据: {data}")
    if not data:
        raise ValueError("输入数据不能为空")

    # 在这里添加验证逻辑
    return data


@node(
    inputs={
        "data": validate_input.result,
        "config": Inputs.config
    },
    outputs={"result": "处理后的数据"}
)
async def process_data(data, config):
    """
    处理数据（异步示例）

    Args:
        data: 验证后的数据
        config: 配置参数

    Returns:
        处理后的数据
    """
    logging.info(f"处理数据: {data}, 配置: {config}")
    await asyncio.sleep(0.1)  # 模拟异步操作

    # 在这里添加处理逻辑
    processed = f"{data}_processed"
    return processed


@node(
    inputs={
        "data": process_data.result,
        "threshold": Inputs.threshold
    },
    outputs={"route": "路由结果"}
)
def route_decision(data, threshold):
    """
    路由决策节点

    Args:
        data: 处理后的数据
        threshold: 阈值

    Returns:
        路由标识 ("high" 或 "low")
    """
    value = len(data)
    logging.info(f"路由决策: value={value}, threshold={threshold}")

    if value > threshold:
        return "high"
    return "low"


@node(
    inputs={"data": process_data.result},
    outputs={"result": "高值处理结果"},
    when=lambda route, **_: route == "high"
)
def handle_high(route, data):
    """
    处理高值分支

    Args:
        route: 路由标识
        data: 处理后的数据

    Returns:
        高值处理结果
    """
    logging.info(f"执行高值处理: {data}")
    return f"{data}_high"


@node(
    inputs={"data": process_data.result},
    outputs={"result": "低值处理结果"},
    when=lambda route, **_: route == "low"
)
def handle_low(route, data):
    """
    处理低值分支

    Args:
        route: 路由标识
        data: 处理后的数据

    Returns:
        低值处理结果
    """
    logging.info(f"执行低值处理: {data}")
    return f"{data}_low"


@node(
    inputs={
        "high": optional(handle_high.result),
        "low": optional(handle_low.result)
    },
    outputs={"result": "最终结果"}
)
def merge_results(high=None, low=None):
    """
    合并分支结果

    Args:
        high: 高值分支结果（可选）
        low: 低值分支结果（可选）

    Returns:
        最终结果
    """
    result = high if high is not None else low
    logging.info(f"合并结果: {result}")
    return result


# ==================== 步骤 3: 执行工作流 ====================
def main():
    """主函数"""
    try:
        # 编译工作流
        compiled = workflow_compile(Inputs)

        # 可选：导出工作流图（用于可视化或文档）
        # graph = workflow_compile_graph(Inputs)
        # import json
        # print(json.dumps(graph, indent=2, ensure_ascii=False))

        # 执行工作流
        ctx, output = workflow_run(compiled)

        # 输出结果
        print("\n" + "="*50)
        print("工作流执行完成")
        print("="*50)
        print(f"Trace ID: {ctx.trace_id}")
        print(f"Run ID: {ctx.run_id}")
        print(f"总耗时: {ctx.end_time - ctx.start_time:.3f}秒")
        print(f"\n各节点耗时:")
        for node_name, timing in ctx.timings.items():
            print(f"  - {node_name}: {timing:.3f}秒")

        if ctx.skipped:
            print(f"\n跳过的节点:")
            for node_name, reason in ctx.skipped.items():
                print(f"  - {node_name}: {reason}")

        print(f"\n最终输出: {output}")
        print("="*50)

        return output

    except Exception as e:
        logging.error(f"工作流执行失败: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
