import heapq

def build_order(graph):
    nodes = set(graph)
    for dependencies in graph.values():
        nodes.update(dependencies)

    indegree = {node: 0 for node in nodes}
    dependents = {node: set() for node in nodes}

    for task, dependencies in graph.items():
        unique_dependencies = set(dependencies)
        indegree[task] = len(unique_dependencies)
        for dependency in unique_dependencies:
            dependents[dependency].add(task)

    ready = [node for node, degree in indegree.items() if degree == 0]
    heapq.heapify(ready)

    order = []
    while ready:
        node = heapq.heappop(ready)
        order.append(node)
        for dependent in dependents[node]:
            indegree[dependent] -= 1
            if indegree[dependent] == 0:
                heapq.heappush(ready, dependent)

    if len(order) != len(nodes):
        raise ValueError("cycle detected")

    return order
