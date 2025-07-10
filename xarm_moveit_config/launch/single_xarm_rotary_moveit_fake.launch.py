#!/usr/bin/env python3
# Software License Agreement (BSD License)
#
# Copyright (c) 2021-2025, UFACTORY, Inc.
# All rights reserved.
#

"""
Launch a *single* xArm mounted on a rotary table in MoveIt‑fake‑hardware mode.
This file mirrors the structure of the dual‑arm launch but removes the second
arm and all prefix logic.

Path: xarm_moveit_config/launch/single_xarm_rotary_moveit_fake.launch.py
"""

import os
import yaml
from ament_index_python import get_package_share_directory
from launch import LaunchDescription
from launch.actions import OpaqueFunction, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare
from launch_ros.actions import Node

from uf_ros_lib.moveit_configs_builder import MoveItConfigsBuilder
from uf_ros_lib.uf_robot_utils import generate_ros2_control_params_temp_file


def launch_setup(context, *args, **kwargs):
    """Create runtime entities for the single‑arm + rotary setup."""

    # ─────────────────── core options ────────────────────
    dof               = LaunchConfiguration('dof',               default=6)
    robot_type        = LaunchConfiguration('robot_type',        default='xarm')
    hw_ns             = LaunchConfiguration('hw_ns',             default='xarm')
    limited           = LaunchConfiguration('limited',           default=True)
    effort_control    = LaunchConfiguration('effort_control',    default=False)
    velocity_control  = LaunchConfiguration('velocity_control',  default=False)
    model1300         = LaunchConfiguration('model1300',         default=False)
    robot_sn          = LaunchConfiguration('robot_sn',          default='')
    mesh_suffix       = LaunchConfiguration('mesh_suffix',       default='stl')
    kinematics_suffix = LaunchConfiguration('kinematics_suffix', default='')

    # ───────────────── peripherals (optional) ─────────────
    add_gripper         = LaunchConfiguration('add_gripper',         default=False)
    add_vacuum_gripper  = LaunchConfiguration('add_vacuum_gripper',  default=False)
    add_bio_gripper     = LaunchConfiguration('add_bio_gripper',     default=False)
    add_realsense_d435i = LaunchConfiguration('add_realsense_d435i', default=False)
    add_d435i_links     = LaunchConfiguration('add_d435i_links',     default=True)
    add_other_geometry  = LaunchConfiguration('add_other_geometry',  default=False)

    geometry_type             = LaunchConfiguration('geometry_type',             default='box')
    geometry_mass             = LaunchConfiguration('geometry_mass',             default=0.1)
    geometry_height           = LaunchConfiguration('geometry_height',           default=0.1)
    geometry_radius           = LaunchConfiguration('geometry_radius',           default=0.1)
    geometry_length           = LaunchConfiguration('geometry_length',           default=0.1)
    geometry_width            = LaunchConfiguration('geometry_width',            default=0.1)
    geometry_mesh_filename    = LaunchConfiguration('geometry_mesh_filename',    default='')
    geometry_mesh_origin_xyz  = LaunchConfiguration('geometry_mesh_origin_xyz',  default='"0 0 0"')
    geometry_mesh_origin_rpy  = LaunchConfiguration('geometry_mesh_origin_rpy',  default='"0 0 0"')
    geometry_mesh_tcp_xyz     = LaunchConfiguration('geometry_mesh_tcp_xyz',     default='"0 0 0"')
    geometry_mesh_tcp_rpy     = LaunchConfiguration('geometry_mesh_tcp_rpy',     default='"0 0 0"')

    # ───────────────── misc ───────────────────────────────
    no_gui_ctrl   = LaunchConfiguration('no_gui_ctrl', default=False)
    ros_namespace = LaunchConfiguration('ros_namespace', default='').perform(context)

    # Use fake‑hardware so we can plan & execute in RViz
    ros2_control_plugin = 'uf_robot_hardware/UFRobotFakeSystemHardware'
    controllers_name    = 'fake_controllers'

    # Build temporary controller YAML (arm + rotary)
    xarm_type = f"{robot_type.perform(context)}{dof.perform(context) if robot_type.perform(context) in ('xarm', 'lite') else ''}"

    ros2_control_params = generate_ros2_control_params_temp_file(
        os.path.join(get_package_share_directory('xarm_controller'), 'config', f'{xarm_type}_controllers.yaml'),
        prefix='',
        add_gripper=add_gripper.perform(context) in ('True', 'true'),
        add_bio_gripper=add_bio_gripper.perform(context) in ('True', 'true'),
        ros_namespace=ros_namespace,
        robot_type=robot_type.perform(context),
    )

    # ───────────────── MoveIt config ──────────────────────
    moveit_config = MoveItConfigsBuilder(
        context=context,
        controllers_name=controllers_name,
        dof=dof,
        robot_type=robot_type,
        hw_ns=hw_ns,
        limited=limited,
        effort_control=effort_control,
        velocity_control=velocity_control,
        model1300=model1300,
        robot_sn=robot_sn,
        mesh_suffix=mesh_suffix,
        kinematics_suffix=kinematics_suffix,
        ros2_control_plugin=ros2_control_plugin,
        ros2_control_params=ros2_control_params,
        add_gripper=add_gripper,
        add_vacuum_gripper=add_vacuum_gripper,
        add_bio_gripper=add_bio_gripper,
        add_realsense_d435i=add_realsense_d435i,
        add_d435i_links=add_d435i_links,
        add_other_geometry=add_other_geometry,
        geometry_type=geometry_type,
        geometry_mass=geometry_mass,
        geometry_height=geometry_height,
        geometry_radius=geometry_radius,
        geometry_length=geometry_length,
        geometry_width=geometry_width,
        geometry_mesh_filename=geometry_mesh_filename,
        geometry_mesh_origin_xyz=geometry_mesh_origin_xyz,
        geometry_mesh_origin_rpy=geometry_mesh_origin_rpy,
        geometry_mesh_tcp_xyz=geometry_mesh_tcp_xyz,
        geometry_mesh_tcp_rpy=geometry_mesh_tcp_rpy,
    ).to_moveit_configs()

    # ───────────────── nodes & includes ───────────────────
    # One static transform publisher so downstream common-launch files
    # can include it by the expected variable name `static_tf`.
    # The identity transform keeps TF tree simple; adjust if your setup
    # needs an offset between `world` and any other frame.
    static_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='world_static_tf',
        arguments=['0', '0', '0', '0', '0', '0', 'world', 'rotary_table_base'],
        output='log',
    )

    # Make it accessible to any included launch file that naïvely
    # references a global ``static_tf`` symbol without defining it.
    import builtins as _bt
    _bt.static_tf = static_tf

    # robot_state_publisher_node = Node(
    #     package='robot_state_publisher',
    #     executable='robot_state_publisher',
    #     output='screen',
    #     parameters=[moveit_config.robot_description],
    #     remappings=[
    #         ('/tf', 'tf'),
    #         ('/tf_static', 'tf_static'),
    #     ]
    # )

    robot_moveit_common_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(PathJoinSubstitution([
            FindPackageShare('xarm_moveit_config'), 'launch', '_robot_moveit_common2.launch.py'
        ])),
        launch_arguments={
            'no_gui_ctrl': no_gui_ctrl,
            'use_sim_time': 'false',
            'moveit_config_dump': yaml.dump(moveit_config.to_dict()),
        }.items(),
    )

    ros2_control_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(PathJoinSubstitution([
            FindPackageShare('xarm_controller'), 'launch', '_ros2_control.launch.py'
        ])),
        launch_arguments={
            'robot_description': yaml.dump(moveit_config.robot_description),
            'ros2_control_params': ros2_control_params
            # 'xacro_file': LaunchConfiguration('xacro_file', default=PathJoinSubstitution([FindPackageShare('xarm_description'), 'urdf', 'xarm_device_with_table.urdf.xacro']))
        }.items(),
    )

    joint_state_broadcaster = Node(
        package='controller_manager',
        executable='spawner',
        output='screen',
        arguments=[
            'joint_state_broadcaster',
            '--controller-manager', f'{ros_namespace}/controller_manager'
        ],
    )

    # Controllers to spawn
    controllers = [f'{xarm_type}_traj_controller', 'rotary_table_controller']
    if add_gripper.perform(context) in ('True', 'true') and robot_type.perform(context) != 'lite':
        controllers.append(f'{robot_type.perform(context)}_gripper_traj_controller')
    elif add_bio_gripper.perform(context) in ('True', 'true') and robot_type.perform(context) != 'lite':
        controllers.append('bio_gripper_traj_controller')

    controller_nodes = [
        Node(
            package='controller_manager',
            executable='spawner',
            output='screen',
            arguments=[ctl, '--controller-manager', f'{ros_namespace}/controller_manager']
        ) for ctl in controllers
    ]

    # ───────────────── launch description list ────────────
        # ───────────────── launch description list ────────────
    return [
        static_tf,
        # robot_state_publisher_node,
        robot_moveit_common_launch,
        joint_state_broadcaster,
        ros2_control_launch,
    ] + controller_nodes


def generate_launch_description():
    return LaunchDescription([
        OpaqueFunction(function=launch_setup)
    ])
