import heapq

def build_order(graph):
    indegree = {}
    dependents = {}

    for task in graph:
        indegree[task] = 0
        dependents.setdefault(task, [])

    for task, deps in graph.items():
        unique_deps = set(deps)
        indegree[task] = len(unique_deps)
        for dep in unique_deps:
            indegree.setdefault(dep, 0)
            dependents.setdefault(dep, [])
            dependents[dep].append(task)

    ready = [name for name, count in indegree.items() if count == 0]
    heapq.heapify(ready)
    order = []

    while ready:
        name = heapq.heappop(ready)
        order.append(name)
        for dependent in dependents[name]:
            indegree[dependent] -= 1
            if indegree[dependent] == 0:
                heapq.heappush(ready, dependent)

    if len(order) != len(indegree):
        raise ValueError("cycle detected")

    return order
