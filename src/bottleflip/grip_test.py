#!/usr/bin/python2

from copy import copy
import math
import rospy
import baxter_interface
import actionlib
import sys
from baxter_interface import CHECK_VERSION
from baxter_interface import Gripper, Limb

from geometry_msgs.msg import PoseStamped, Pose, Point, Quaternion

from sensor_msgs.msg import JointState

from std_msgs.msg import Header, Empty

from control_msgs.msg import FollowJointTrajectoryAction, FollowJointTrajectoryGoal

from trajectory_msgs.msg import JointTrajectoryPoint

from baxter_core_msgs.srv import SolvePositionIK, SolvePositionIKRequest

from tf.transformations import quaternion_from_euler

class Trajectory(object):
    def __init__(self, limb):
        ns = 'robot/limb/' + limb + '/'
        self._client = actionlib.SimpleActionClient(
            ns + "follow_joint_trajectory",
            FollowJointTrajectoryAction,
        )
        self._goal = FollowJointTrajectoryGoal()
        self._goal_time_tolerance = rospy.Time(0.1)
        self._goal.goal_time_tolerance = self._goal_time_tolerance
        server_up = self._client.wait_for_server(timeout=rospy.Duration(10.0))
        if not server_up:
            rospy.logerr("Timed out waiting for Joint Trajectory"
                         " Action Server to connect. Start the action server"
                         " before running example.")
            rospy.signal_shutdown("Timed out waiting for Action Server")
            sys.exit(1)
        self.clear(limb)

    def add_point(self, positions, time):
        point = JointTrajectoryPoint()
        point.positions = copy(positions)
        point.time_from_start = rospy.Duration(time)
        self._goal.trajectory.points.append(point)

    def start(self):
        self._goal.trajectory.header.stamp = rospy.Time.now()
        self._client.send_goal(self._goal)

    def stop(self):
        self._client.cancel_goal()

    def wait(self, timeout=15.0):
        self._client.wait_for_result(timeout=rospy.Duration(timeout))

    def result(self):
        return self._client.get_result()

    def clear(self, limb):
        self._goal = FollowJointTrajectoryGoal()
        self._goal.goal_time_tolerance = self._goal_time_tolerance
        self._goal.trajectory.joint_names = [limb + '_' + joint for joint in \
            ['s0', 's1', 'e0', 'e1', 'w0', 'w1', 'w2']]


global right_gripper
global right_limb

if __name__ == '__main__':
	rospy.init_node('griptest')

	ns = "ExternalTools/right/PositionKinematicsNode/IKService"
	
	rospy.wait_for_message("/robot/sim/started", Empty)
		
	iksvc = rospy.ServiceProxy(ns, SolvePositionIK)	
	global right_gripper

	#rospy.sleep(rospy.Duration(5,0))

	rs = baxter_interface.RobotEnable(CHECK_VERSION)
	rs.enable()

	right_gripper = Gripper('right');
	right_limb = Limb('right');

	right_gripper.calibrate()
	hdr = Header(stamp=rospy.Time.now(), frame_id='base')
	
	print "opening gripper"
	right_gripper.open()

	current_angles = [right_limb.joint_angle(joint) for joint in right_limb.joint_names()]

	orient_quaternion_components = quaternion_from_euler(math.pi, 0,math.pi/2)
	orient_down = Quaternion()
	orient_down.x = orient_quaternion_components[0]
	orient_down.y = orient_quaternion_components[1]
	orient_down.z = orient_quaternion_components[2]
	orient_down.w = orient_quaternion_components[3]
	
	highPose = PoseStamped(header=hdr, pose=Pose(position=Point(0, -0.428, -0.57), orientation=orient_down))
	gripPose = PoseStamped(header=hdr, pose=Pose(position=Point(0, -0.428, -0.71), orientation=orient_down))
	liftPose = PoseStamped(header=hdr, pose=Pose(position=Point(0, -0.428, -0.5), orientation=orient_down))
	
	ikreq = SolvePositionIKRequest()
	ikreq.pose_stamp.append(highPose)
	ikreq.pose_stamp.append(gripPose)
	ikreq.pose_stamp.append(liftPose)
	seedstate = JointState()
	seedstate.name=('right_e0', 'right_e1', 'right_s0', 'right_s1', 'right_w0', 'right_w1', 'right_w2')
	seedstate.position=current_angles
#	ikreq.seed_angles.append(seedstate)
#	ikreq.seed_angles.append(seedstate)


	try:
	  rospy.wait_for_service(ns, 5.0)
	  resp = iksvc(ikreq)
	except (rospy.ServiceException, rospy.ROSException), e:
	  rospy.logerr("Service call failed to IK service: %s" % (e))
	  print "Service call failed"

	print resp

	traj = Trajectory('right')

        
        traj.add_point(current_angles, 0.0)
	

	traj.add_point(resp.joints[0].position, 3.0)
	traj.add_point(resp.joints[1].position, 6.0)

	traj.start()
	traj.wait(12.0)
	right_gripper.close()

	current_angles = [right_limb.joint_angle(joint) for joint in right_limb.joint_names()]
	traj.clear('right')
	traj.add_point(current_angles, 0)
	traj.add_point(resp.joints[2].position, 2.5)
	traj.start()
	traj.wait(2.5)



        #rospy.spin()

