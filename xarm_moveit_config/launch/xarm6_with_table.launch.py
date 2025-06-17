#!/usr/bin/env python3
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import (
    LaunchConfiguration,
    PathJoinSubstitution,
    Command,
)
from launch_ros.substitutions import FindPackageShare
from launch_ros.actions import Node


def generate_launch_description():
    # ------------------------------- xArm 6 ----------------------------------
    hw_ns = LaunchConfiguration("hw_ns", default="xarm")

    xarm_moveit_fake_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution(
                [FindPackageShare("xarm_moveit_config"), "launch", "_robot_moveit_fake.launch.py"]
            )
        ),
        launch_arguments={
            "dof": "6",
            "robot_type": "xarm",
            "hw_ns": hw_ns,
            "no_gui_ctrl": "false",
        }.items(),
    )

    # --------------------------- Rotary table --------------------------------
    # 1. Robot description (processed xacro)
    rotary_description = Command(
        [
            "xacro ",
            PathJoinSubstitution(
                [FindPackageShare("xarm_description"), "urdf", "rotary_table.urdf.xacro"]
            ),
        ]
    )

    rotary_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="rotary_table_state_publisher",
        namespace="rotary_table",
        parameters=[{"robot_description": rotary_description}],
        output="screen",
    )

    # 2. ros2_control node (fake hardware) for the rotary joint
    rotary_ros2_control = Node(
        package="controller_manager",
        executable="ros2_control_node",
        name="controller_manager",
        namespace="rotary_table",
        parameters=[
            {"robot_description": rotary_description},
            "/home/dellubuntu/xarm_ws_humble/src/xarm_ros2_fork/xarm_moveit_config/config/rotary_table_controller.yaml",
        ],
        output="screen",
    )

    # 3. Broadcaster and trajectory controller spawners
    rotary_js_broadcaster = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "joint_state_broadcaster",
            "--controller-manager",
            "/rotary_table/controller_manager",
        ],
        output="screen",
    )

    rotary_traj_controller = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "rotary_table_controller",
            "--controller-manager",
            "/rotary_table/controller_manager",
        ],
        output="screen",
    )
    
    

    # -------------------------------------------------------------------------
    return LaunchDescription(
        [
            xarm_moveit_fake_launch,
            rotary_state_publisher,
            rotary_ros2_control,
            rotary_js_broadcaster,
            rotary_traj_controller,
        ]
    )
