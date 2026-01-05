import networkx as nx
from collections import defaultdict, deque

class AMLGraphDetector:
    """
    Simple in-memory AML graph detector.
    Tracks money flow and flags mule-like behavior.
    """

    def __init__(
        self,
        window_size=500,
        fan_threshold=10,
        degree_threshold=15
    ):
        self.G = nx.DiGraph()
        self.recent_edges = deque(maxlen=window_size)

        self.fan_threshold = fan_threshold
        self.degree_threshold = degree_threshold

        self.in_counts = defaultdict(int)
        self.out_counts = defaultdict(int)

    def add_transaction(self, from_acct: int, to_acct: int):
        # add edge
        self.G.add_edge(from_acct, to_acct)
        self.recent_edges.append((from_acct, to_acct))

        self.out_counts[from_acct] += 1
        self.in_counts[to_acct] += 1

    def detect_mule(self):
        """
        Mule heuristics:
        - High fan-in AND fan-out
        - High total degree in short window
        """
        alerts = []

        nodes = set(list(self.in_counts.keys()) + list(self.out_counts.keys()))
        for node in nodes:
            fan_in = self.in_counts[node]
            fan_out = self.out_counts[node]
            total_degree = fan_in + fan_out

            if (
                fan_in >= self.fan_threshold
                and fan_out >= self.fan_threshold
                and total_degree >= self.degree_threshold
            ):
                alerts.append({
                    "node": node,
                    "fan_in": fan_in,
                    "fan_out": fan_out,
                    "total_degree": total_degree
                })

        return alerts

    def reset_window(self):
        """Reset sliding window counts"""
        self.in_counts.clear()
        self.out_counts.clear()
