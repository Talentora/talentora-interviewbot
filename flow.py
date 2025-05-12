from enum import Enum, auto
import json
from typing import List, Dict, Optional, Any, Union

class NodeType(Enum):
    """Enum representing different types of nodes in the interview flow."""
    QUESTION = "question"
    BRANCH = "branching"
    START = "start"
    END = "conclusion"

class Node:
    """
    Represents a node in the interview flow.
    """
    def __init__(self, node_id: str, content: str, node_type: str, criteria: Optional[str] = None, follow_up_toggle: Optional[bool] = False):
        self.id = node_id
        self.content = content
        self.criteria = criteria
        self.follow_up_toggle = follow_up_toggle
        # Convert string node_type to enum
        try:
            self.type = next((t for t in NodeType if t.value == node_type), NodeType.END)
        except Exception:
            # Fallback to END in case of any error
            self.type = NodeType.END


    def __repr__(self):
        return f"Node(id={self.id!r}, content={self.content!r})"


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
                content=data.get("content", ""),
                criteria=data.get("criteria"),
                node_type=n.get("type", ""),
                follow_up_toggle=data.get("follow_up_toggle", False)
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

    def get_next_node_ids(self, node_id: str) -> Optional[Union[List[str], str]]:
        """
        Return the next node(s) after the current node.
        - For branch nodes: returns a list of node IDs
        - For question/section nodes: returns a single node ID
        - For end nodes: raises an error
        """
        node = self.get_node(node_id)
        if node is None:
            return None
        
        if node.type == NodeType.END:
            raise ValueError(f"Cannot get next node for end node {node_id}")
        
        outgoing_edges = self._by_source.get(node_id, [])
        if not outgoing_edges:
            raise ValueError(f"Node {node_id} has no outgoing edges")
            
        if node.type == NodeType.BRANCH:
            return [edge.target for edge in outgoing_edges]
        else:
            # For question/section nodes, return just the first target as a string
            return outgoing_edges[0].target

    def get_previous_node_ids(self, node_id: str) -> List[str]:
        """
        Return a list of source node IDs that lead into the given node.
        """
        return [edge.source for edge in self._by_target.get(node_id, [])]


    def get_initial_node(self) -> Optional[Node]:
        """
        Return the START node in the flow, or None if none exists.
        """
        for node_id, node in self.nodes.items():
            if node.type == NodeType.START:
                return node
        return None

    def is_question_node(self, node_id: str) -> bool:
        """
        Check whether the node is of type 'question'.
        """
        node = self.get_node(node_id)
        return node is not None and node.type == NodeType.QUESTION
    
    
    def is_branching_node(self, node_id: str) -> bool:
        """
        Check whether the node is of type 'branching'.
        """
        node = self.get_node(node_id)
        return node is not None and node.type == NodeType.BRANCH

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
        return [nid for nid, n in self.nodes.items() if n.type == NodeType.QUESTION]

    def __repr__(self):
        return f"FlowGraph(nodes={len(self.nodes)}, edges={len(self.edges)})"
