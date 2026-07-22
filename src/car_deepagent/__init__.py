"""car_deepagent package."""

__all__ = ["graph"]


def __getattr__(name: str):
    if name == "graph":
        from car_deepagent.graph import get_graph

        return get_graph()
    raise AttributeError(name)
