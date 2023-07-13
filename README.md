# pyGrasp

This project exploits the kinematic redundancy of the robotic system to enhance its dexterity in task performance, such as grasping single or multiple objects, or multitasking.
It is the Python realization and generalization of [1].

## Project Structure
The project contains the following main functional modules:

### 1. Modeling
- **Robot**: given a robot description file (URDF or xacro), this functional module constructs and stores the full kinematic tree of the robot. For now, three robots are considered:
  - Robotic hand: Allegro hand, human hand
  - Robotic arm: KUKA iiwa, with or w/o the Allegro hand
  - Humanoid robot: iCub
- **Object**: the target object can be represented by (1) a group of geometric primitives (e.g., spheres, cylinders, etc.), and the contact on the object surface can have a closed-form expression; or (2) point cloud data, then a spherical coordinate can be constructed by training a model of the radius $r$, as a function of $theta$ and $phi$.
- **Contact**: for now, *point contact with friction* model is used (torsional friction is optional).

### 2. Analysis of Kinematics
Offline analysis of the robot kinematic model to construct:
- **Reachability map**
- **Opposition space**
- **Self-collision map**

### 3. Grasp Synthesis
Given the robot and the model of the target object, this functional module deals with: 
- **Problem formulation**
- **Solving optimization**: currently, `SciPy` package is used to solve the optimization problem with `scipy.optimize()`.

### 4. Sequential Grasp Optimization
- Generates a sequence of grasps to achieve the grasping of multiple objects;
- Optimize overall kinematic efficiency to maximize the number of objects to grasp, or the number of subtasks to execute.

### 5. Collision-free Path Planning
Generate a collision-free path that drives the robotic system from its current configuration to grasp the target object.
Three types of collision are considered:
- **Self collision**: collision among robot links;
- **Robot-object collision**: collision between the target object and any robotic links;
- **Object-object collision**: collision between the target object and any previously grasped objects.

### 6. Motion Generation and Control
Control the robotic system to move along the planned collision-free path, and grasp with compliance and robustness.

## Expected Features
Here list of the features with low priority.
- The coordination of multiple robots
- Manipulation motion generation
- Coordinated multitasking

## Dependencies
1. [hand_dexterity](https://github.com/kunpengyao/hand_dexterity): the MATLAB version code for a multi-fingered dexterous robotic hand to grasp multiple objects
2. [SynGrasp](http://sirslab.dii.unisi.it/syngrasp/): A MATLAB Toolbox for Grasp Analysis of Human and Robotic Hands
3. [CasADi](https://web.casadi.org/): an open-source tool for nonlinear optimization and algorithmic differentiation
4. [scipy.optimize](https://docs.scipy.org/doc/scipy/reference/optimize.html#module-scipy.optimize): provides functions for minimizing (or maximizing) objective functions, possibly subject to constraints. It includes solvers for nonlinear problems (with support for both local and global optimization algorithms), linear programing, constrained and nonlinear least-squares, root finding, and curve fitting.
5. [scikit-learn](https://scikit-learn.org/stable/index.html): for using machine learning tools.

## References
1. Yao, K., & Billard, A. (2023). [Exploiting Kinematic Redundancy for Robotic Grasping of Multiple Objects](https://ieeexplore.ieee.org/abstract/document/10086636). IEEE Transactions on Robotics.
2. Pozzi M, Achilli GM, Valigi MC and Malvezzi M (2022) Modeling and Simulation of Robotic Grasping in Simulink Through Simscape Multibody. Front. Robot. AI 9:873558. doi: 10.3389/frobt.2022.873558

## Get Started

### 1. Activate or create the virtual environment

```
# [KY]
$ conda activate MyoSuite
```

Otherwise, create the conda virtual environment from the `requirements.txt`:
```
conda create --name <env_name> --file requirements.txt
```

Always register conda environment requirements to `requirements.txt` and `environment.yml`.

### Examples to test modules