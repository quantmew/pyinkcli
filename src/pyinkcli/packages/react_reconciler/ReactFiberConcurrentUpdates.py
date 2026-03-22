def markUpdateLaneFromFiberToRoot(source, _update, lane):
    node = source
    root = None
    while node is not None:
        node.child_lanes = getattr(node, "child_lanes", 0) | lane
        alternate = getattr(node, "alternate", None)
        if alternate is not None:
            alternate.child_lanes = getattr(alternate, "child_lanes", 0) | lane
        parent = getattr(node, "return_fiber", None)
        if parent is None and getattr(node, "tag", None) == 3:
            root = node
            node.pending_lanes = getattr(node, "pending_lanes", 0) | lane
            break
        node = parent
    return root

