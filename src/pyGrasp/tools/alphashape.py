"""
Tools for working with alpha shapes.
"""
import time
import itertools
import logging
from shapely.ops import unary_union, polygonize
from shapely.geometry import MultiPoint, MultiLineString
from scipy.spatial import Delaunay, ConvexHull
import numpy as np
from typing import Union, Tuple, List
import trimesh
import timeit
from tqdm import tqdm
import matplotlib.pyplot as plt


OPTIMAL_VERT_NUMBER = np.inf   # This might help in certain cases but there is no guarantee


def circumcenter(points: Union[List[Tuple[float]], np.ndarray]) -> np.ndarray:
    """
    Calculate the circumcenter of a set of points in barycentric coordinates.

    Args:
      points: An `N`x`K` array of points which define an (`N`-1) simplex in K
        dimensional space.  `N` and `K` must satisfy 1 <= `N` <= `K` and
        `K` >= 1.

    Returns:
      The circumcenter of a set of points in barycentric coordinates.
    """
    points = np.asarray(points)
    num_rows, _ = points.shape
    A = np.bmat([[2 * points @ points.T,
                  np.ones((num_rows, 1))],
                 [np.ones((1, num_rows)), np.zeros((1, 1))]])
    b = np.hstack((np.sum(points * points, axis=1),
                   np.ones((1))))
    return np.linalg.solve(A, b)[:-1]


def circumradius(points: Union[List[Tuple[float]], np.ndarray]) -> float:
    """
    Calculte the circumradius of a given set of points.

    Args:
      points: An `N`x`K` array of points which define an (`N`-1) simplex in K
        dimensional space.  `N` and `K` must satisfy 1 <= `N` <= `K` and
        `K` >= 1.

    Returns:
      The circumradius of a given set of points.
    """
    points = np.asarray(points)
    crc = circumcenter(points)
    dot_prod = crc @ points
    full_res = np.linalg.norm(points[0, :] - dot_prod)
    return full_res
    #return np.linalg.norm(points[0, :] - np.dot(circumcenter(points), points))


def circumradius_vec(simplices: np.ndarray, vertices: np.ndarray) -> np.ndarray:
    """
    Calculte the circumradius of a given set of points.

    Args:
      points: An `N`x`K` array of points which define an (`N`-1) simplex in K
        dimensional space.  `N` and `K` must satisfy 1 <= `N` <= `K` and
        `K` >= 1.

    Returns:
      The circumradius of a given set of points.
    """
    NUMERICAL_PRECISION = 1e-9
    simplices_coords = np.asarray(vertices[simplices])

    a = np.linalg.norm(simplices_coords[:, 0, :] - simplices_coords[:, 1, :], axis=1)
    A = np.linalg.norm(simplices_coords[:, 2, :] - simplices_coords[:, 3, :], axis=1)

    b = np.linalg.norm(simplices_coords[:, 0, :] - simplices_coords[:, 2, :], axis=1)
    B = np.linalg.norm(simplices_coords[:, 1, :] - simplices_coords[:, 3, :], axis=1)

    c = np.linalg.norm(simplices_coords[:, 0, :] - simplices_coords[:, 3, :], axis=1)
    C = np.linalg.norm(simplices_coords[:, 1, :] - simplices_coords[:, 2, :], axis=1)

    aA = a*A
    bB = b*B
    cC = c*C

    V = np.abs(np.sum((simplices_coords[:, 0, :] - simplices_coords[:, 3, :]) *
               np.cross((simplices_coords[:, 1, :] - simplices_coords[:, 3, :]),
                        (simplices_coords[:, 2, :] - simplices_coords[:, 3, :]), axis=1), axis=-1)) / 6
    numerator = (aA + bB + cC) * (aA - bB + cC) * (aA + bB - cC) * (- aA + bB + cC)
    numerator[numerator < 0] = 0   # Have to patch for numerical precision
    numerator = np.sqrt(numerator)

    V[V < NUMERICAL_PRECISION] = NUMERICAL_PRECISION  # Avoid division by zero, we're gonna get rid of those values later anyway
    circum_radii = numerator / (24*V)

    # Ignore faces with volume close to zero yielding bad precision
    # NOTE: This should ultimately impair the precision for high alphas...
    # especially when tetrahedrons have bad form factors...
    # But iit is a lot quicker
    circum_radii[V <= 1e-9] = 0

    return circum_radii


# TODO: Vectorize this shit for faster execution
def alphasimplices(points: Union[List[Tuple[float]], np.ndarray]) -> \
        Union[List[Tuple[float]], np.ndarray]:
    """
    Returns an iterator of simplices and their circumradii of the given set of
    points.

    Args:
      points: An `N`x`M` array of points.

    Yields:
      A simplex, and its circumradius as a tuple.
    """

    coords = np.asarray(points)
    tri = Delaunay(coords, incremental=True)

    for simplex in tri.simplices:
        simplex_points = coords[simplex]
        try:
            cr = circumradius(simplex_points)
            yield simplex, cr
        except np.linalg.LinAlgError:
            logging.debug('Singular matrix. Likely caused by all points lying in an N-1 space.')


def alphasimplices_vec(points: Union[List[Tuple[float]], np.ndarray, trimesh.Trimesh]) -> Tuple[np.ndarray, np.ndarray]:

    if type(points) == trimesh.Trimesh:
        raise ValueError("Alphasimplices for trimeshes is not implemented yet")
    coords = np.asarray(points)
    tri = Delaunay(coords)
    cr = circumradius_vec(tri.simplices, coords)

    return tri.simplices, cr


def alphashape(points: Union[List[Tuple[float]], np.ndarray],
               alpha: float = 0):
    """
    Compute the alpha shape (concave hull) of a set of points.  If the number
    of points in the input is three or less, the convex hull is returned to the
    user.  For two points, the convex hull collapses to a `LineString`; for one
    point, a `Point`.

    Args:

      points (list or ``shapely.geometry.MultiPoint`` or \
          ``geopandas.GeoDataFrame``): an iterable container of points
      alpha (float): alpha value

    Returns:

      ``shapely.geometry.Polygon`` or ``shapely.geometry.LineString`` or
      ``shapely.geometry.Point`` or ``geopandas.GeoDataFrame``: \
          the resulting geometry
    """

    # If given a triangle for input, or an alpha value of zero or less,
    # return the convex hull.

    if len(points) < 4 or (alpha is not None and not callable(
            alpha) and alpha < 0):
        if not isinstance(points, MultiPoint):
            points = MultiPoint(list(points))
        return points.convex_hull

    # Convert the points to a numpy array
    coords = np.asarray(points)

    # Create a set to hold unique edges of simplices that pass the radius
    # filtering
    edges = set()

    # Create a set to hold unique edges of perimeter simplices.
    # Whenever a simplex is found that passes the radius filter, its edges
    # will be inspected to see if they already exist in the `edges` set.  If an
    # edge does not already exist there, it will be added to both the `edges`
    # set and the `permimeter_edges` set.  If it does already exist there, it
    # will be removed from the `perimeter_edges` set if found there.  This is
    # taking advantage of the property of perimeter edges that each edge can
    # only exist once.
    perimeter_edges = set()

    simplices, cr = alphasimplices_vec(coords)
    for point_indices, circumradius in zip(simplices, cr):
        if callable(alpha):
            resolved_alpha = alpha(point_indices, circumradius)
        else:
            resolved_alpha = alpha
        # Radius filter
        if circumradius < 1.0 / resolved_alpha:
            for edge in itertools.combinations(point_indices, r=coords.shape[-1]):
                if all([e not in edges for e in itertools.combinations(edge, r=len(edge))]):
                    edges.add(edge)
                    perimeter_edges.add(edge)
                else:
                    perimeter_edges -= set(itertools.combinations(edge, r=len(edge)))

    if coords.shape[-1] > 3:
        return perimeter_edges
    elif coords.shape[-1] == 3:
        result = trimesh.Trimesh(vertices=coords, faces=list(perimeter_edges))
        trimesh.repair.fix_normals(result)
        result.process(validate=True)
        return result

    # Create the resulting polygon from the edge points
    m = MultiLineString([coords[np.array(edge)] for edge in perimeter_edges])
    triangles = list(polygonize(m))
    result = unary_union(triangles)

    return result


def check_circumradius(simplices, vertices) -> bool:
    """
    Check that both circumradius methods yield the same result
    """

    # Vectorized circumradius
    t0_vec = time.time()
    vec_cr = circumradius_vec(simplices, vertices)
    t1_vec = time.time()

    # Iterative circumradius (this implementation is a fast as it gets for non-vectorized)
    iter_cr = np.zeros((simplices.shape[0]))
    t0_iter = time.time()
    for i, simplex in enumerate(simplices):
        simplex_points = vertices[simplex]
        try:
            iter_cr[i] = circumradius(simplex_points)
        except np.linalg.LinAlgError:
            logging.debug('Singular matrix. Likely caused by all points lying in an N-1 space.')
    t1_iter = time.time()

    comp = np.logical_or(np.abs((vec_cr - iter_cr)/iter_cr) < 1e-3, vec_cr == 0)

    t_vec = t1_vec - t0_vec
    t_iter = t1_iter - t0_iter
    print(f"Vectorized: {t_vec}")
    print(f"Iterative: {t_iter}")
    if t_vec < t_iter:
        print(f"Verctorized is {t_iter/t_vec} times faster than iterative")
    else:
        print(f"Iterative is {t_vec/t_iter} times faster than vectorized")

    return comp.all()


def check_alpha_comp_time(nb_folds: int, nb_pt_max: int, increment: int) -> None:

    np.random.seed(0)

    nb_pts_ls = np.arange(increment, nb_pt_max, increment)
    exec_times = np.zeros_like(nb_pts_ls)

    for i, nb_pts in tqdm(enumerate(nb_pts_ls)):
        point_set = 10 * np.random.rand(nb_pts, 3)
        exec_times[i] = timeit.timeit(lambda: alphashape(point_set, 2), number=nb_folds)

    plt.scatter(nb_pts_ls, exec_times)
    plt.show()