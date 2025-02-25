"""An example on how to use grasp synthesis in this package
"""
import random
import trimesh

import pyGrasp.utils as pgu
from pyGrasp.robot_model import RobotModel
from pyGrasp.grasp_synthesiser import GraspSynthesizer


# Choose your example robot here
SELECTED_ROBOT = pgu.CH_LONG_URDF_PATH  # Find all possible robot in the utils.py file


def main() -> None:
    """Gets the model of a robot and.
    """

    random.seed(0)  # For repeatability

    # Load urdfgut
    if SELECTED_ROBOT.folder.is_dir() and SELECTED_ROBOT.file_path.is_file():
        robot_model = RobotModel(SELECTED_ROBOT.folder, SELECTED_ROBOT.file_path)
        print("Loaded robot model:")
        print(robot_model)
    else:
        raise FileNotFoundError(f"URDF provided is not a valid file path: {SELECTED_ROBOT}")

    # Create reachable space
    gs = GraspSynthesizer(robot_model)

    # Create an object to grasp
    obj_to_grasp_prim = trimesh.primitives.Sphere(radius=0.1)
    obj_to_grasp = trimesh.Trimesh(faces=obj_to_grasp_prim.faces, vertices=obj_to_grasp_prim.vertices)

    # Synthesize grasp
    best_links = gs._os.get_best_os(point_cloud=obj_to_grasp.vertices, excluded_links=['iiwa_link_0'])
    if best_links is not None:
        print(f"Grasp synthesis between {best_links[0]} and {best_links[1]}")
        gs.synthtize_in_os(best_links[0], best_links[1], obj_to_grasp)
    else:
        print("Couldn't find an OS fitting the object")


if __name__ == "__main__":
    main()
