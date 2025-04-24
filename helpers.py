import numpy as np


def facet_to_tuple(facet):
    return tuple(map(tuple, facet))


def point_to_tuple(point):
    return tuple(point)


def get_adj_map(facets):
    # Given a list of facets, return a map that given a facet returns all adjacent facets
    point_map = dict()

    for facet in facets:
        for point in facet:
            point = point_to_tuple(point)

            if point in point_map:
                point_map[point].add(facet_to_tuple(facet))
            else:
                point_map[point] = {facet_to_tuple(facet)}

    adj_map = dict()

    for facet in facets:
        v1, v2, v3 = facet

        v1_facets = point_map[point_to_tuple(v1)]
        v2_facets = point_map[point_to_tuple(v2)]
        v3_facets = point_map[point_to_tuple(v3)]

        # For a facet to be adjacent it must share two points
        v1v2_adj = v1_facets.intersection(v2_facets)
        v1v3_adj = v1_facets.intersection(v3_facets)
        v2v3_adj = v2_facets.intersection(v3_facets)

        adj_facets = v1v2_adj.union(v1v3_adj).union(v2v3_adj)

        # Remove self from adjacent list
        if facet_to_tuple(facet) in adj_facets:
            adj_facets.remove(facet_to_tuple(facet))

        adj_map[facet_to_tuple(facet)] = list(adj_facets)

    return adj_map

# Recursive variant of decompose
# path: working decomposition set
# adj_map: adjaceny map of all facets
# removed_set: set containing all points in path so far
# depth: Length of path to end recursion at. If set to None, length of adj_map will be use instead


def _decompose(path, adj_map, removed_set, depth):
    if depth and len(path) == depth:
        return path
    if len(path) == len(adj_map):
        # Fully decomposed stl
        return path

    # Look at facets adjacent to the last removed, from closet to furthest.
    mean_of_last = np.array(path[-1]).mean(axis=0)
    adjacent_facets = [(np.linalg.norm(
        mean_of_last - np.array(adj).mean(axis=0)), adj) for adj in adj_map[path[-1]]]
    adjacent_facets = sorted(adjacent_facets, key=lambda x: x[0])
    adjacent_facets = [adjacent[1] for adjacent in adjacent_facets]

    for adjacent_facet in adjacent_facets:
        # This facet is already in the path, skip
        if adjacent_facet in removed_set:
            continue

        removed_set.add(adjacent_facet)
        rec = _decompose(path + [adjacent_facet], adj_map, removed_set, depth)

        # On the golden path, return
        if rec:
            return rec
        removed_set.remove(adjacent_facet)

    # Dead end
    return None

# Remove facet by facet such that a facet removed is always adjacent with the prior facet removed.
# facets: list of facets to decompose.
# depth: Length of path to end recursion at. If set to None, length of adj_map will be use instead


def decompose(facets, depth=None):
    adj_map = get_adj_map(facets)

    for facet in facets:
        facet = facet_to_tuple(facet)

        path = [facet]

        path = _decompose(path, adj_map, set(path), depth)

        if path:
            return path

    raise Exception('Unable to find decomposition')
