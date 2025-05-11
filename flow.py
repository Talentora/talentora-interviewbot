import json
from typing import List, Dict, Optional, Any


class Node:
    """
    Represents a node in the interview flow.
    """
    def __init__(self, node_id: str, label: str, content: str, criteria: Optional[str] = None, node_type: str = ""):
        self.id = node_id
        self.label = label
        self.content = content
        self.criteria = criteria
        self.type = node_type

    def __repr__(self):
        return f"Node(id={self.id!r}, label={self.label!r})"


class Edge:
    """
    Represents a directed edge in the interview flow.
    """
    def __init__(self, edge_id: str, source: str, target: str, edge_type: str = "", source_handle: str = "", target_handle: str = ""):
        self.id = edge_id
        self.source = source
        self.target = target
        self.type = edge_type
        self.source_handle = source_handle
        self.target_handle = target_handle

    def __repr__(self):
        return f"Edge(id={self.id!r}, {self.source!r} -> {self.target!r})"


class FlowGraph:
    """
    Encapsulates the nodes and edges of the interview flow and provides utility methods.
    """
    def __init__(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]):
        # Parse nodes
        self.nodes: Dict[str, Node] = {}
        for n in nodes:
            data = n.get("data", {})
            node = Node(
                node_id=n.get("id", ""),
                label=data.get("label", ""),
                content=data.get("content", ""),
                criteria=data.get("criteria"),
                node_type=n.get("type", "")
            )
            self.nodes[node.id] = node

        # Parse edges
        self.edges: List[Edge] = []
        self._by_source: Dict[str, List[Edge]] = {}
        self._by_target: Dict[str, List[Edge]] = {}
        for e in edges:
            edge = Edge(
                edge_id=e.get("id", ""),
                source=e.get("source", ""),
                target=e.get("target", ""),
                edge_type=e.get("type", ""),
                source_handle=e.get("sourceHandle", ""),
                target_handle=e.get("targetHandle", "")
            )
            self.edges.append(edge)
            self._by_source.setdefault(edge.source, []).append(edge)
            self._by_target.setdefault(edge.target, []).append(edge)

    @classmethod
    def from_json_file(cls, path: str) -> "FlowGraph":
        """
        Load a flow graph from a JSON file with 'nodes' and 'edges' keys.
        """
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls(nodes=data.get('nodes', []), edges=data.get('edges', []))

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FlowGraph":
        """
        Load a flow graph from a dict with 'nodes' and 'edges'.
        """
        return cls(nodes=data.get('nodes', []), edges=data.get('edges', []))

    def get_node(self, node_id: str) -> Optional[Node]:
        """
        Return the Node object for the given ID, or None if not found.
        """
        return self.nodes.get(node_id)

    def get_next_node_ids(self, node_id: str) -> List[str]:
        """
        Return a list of target node IDs directly reachable from the given node.
        """
        return [edge.target for edge in self._by_source.get(node_id, [])]

    def get_previous_node_ids(self, node_id: str) -> List[str]:
        """
        Return a list of source node IDs that lead into the given node.
        """
        return [edge.source for edge in self._by_target.get(node_id, [])]

    def get_initial_node_ids(self) -> List[str]:
        """
        Return a list of node IDs with no incoming edges (starting points of the flow).
        """
        return [nid for nid in self.nodes if not self.get_previous_node_ids(nid)]

    def get_initial_node(self) -> Optional[Node]:
        """
        Return the first initial Node (no incoming edges), or None if none exist.
        """
        initial_ids = self.get_initial_node_ids()
        if not initial_ids:
            return None
        return self.get_node(initial_ids[0])

    def is_question_node(self, node_id: str) -> bool:
        """
        Check whether the node is of type 'question'.
        """
        node = self.get_node(node_id)
        return node is not None and node.type == 'question'

    def get_node_content(self, node_id: str) -> str:
        """
        Return the content (prompt text) for the given node.
        """
        node = self.get_node(node_id)
        return node.content if node else ''

    def get_node_criteria(self, node_id: str) -> Optional[str]:
        """
        Return the evaluation criteria for a question node.
        """
        node = self.get_node(node_id)
        return node.criteria if node else None

    def all_question_ids(self) -> List[str]:
        """
        Return IDs of all nodes of type 'question'.
        """
        return [nid for nid, n in self.nodes.items() if n.type == 'question']

    def __repr__(self):
        return f"FlowGraph(nodes={len(self.nodes)}, edges={len(self.edges)})"
