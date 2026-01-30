import asyncio
import logging

from flowlet import Input, node, optional, workflow_compile, workflow_run, workflow_compile_graph


class Inputs():
    a = Input(int, desc="参数1")
    b = Input(int, desc="参数2")


# 实际的一个工作流示例
@node(inputs={
    "input1": Inputs.a
}, outputs={
    "result": "描述"
})
async def step1(input1):
    """
    步骤1
    """
    logging.info("sleep 1")
    await asyncio.sleep(1)
    return input1


@node(inputs={
    "input1": Inputs.b,
}, outputs={
    "result": "描述"
})
async def step2(input1):
    """
    步骤2
    """
    logging.info("sleep 1")
    await asyncio.sleep(1)
    return input1


@node(inputs={
    "input1": step1.result,
    "input2": step2.result
}, outputs={
    "route": "分支路由"
})
def route(input1, input2):
    """
    分支判断
    """
    return "A" if input1 + input2 >= 0 else "B"


@node(inputs={
    "route": route.route,
    "input1": step1.result
}, outputs={
    "result": "A分支结果"
}, when=lambda route, **_: route == "A")
def step_a(route, input1):
    """
    A 分支
    """
    return input1 * 10


@node(inputs={
    "route": route.route,
    "input2": step2.result
}, outputs={
    "result": "B分支结果"
}, when=lambda route, **_: route == "B")
def step_b(route, input2):
    """
    B 分支
    """
    return input2 * -10


@node(inputs={
    "a": optional(step_a.result),
    "b": optional(step_b.result)
}, outputs={
    "result": "合并结果"
})
def merge(a=None, b=None):
    """
    分支合并
    """
    return a if a is not None else b


def main():
    import json
    graph = workflow_compile_graph(Inputs)
    #print(json.dumps(graph))
    compiled = workflow_compile(Inputs)
    #print(compiled)
    ctx, output = workflow_run(compiled)
    print(ctx.trace_id, ctx.run_id)
    print(ctx.timings)
    print(ctx.logs)
    print(ctx.outputs)
    # print(ctx)
    # print(output)


if __name__ == "__main__":
    main()
