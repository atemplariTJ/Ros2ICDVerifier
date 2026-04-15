import rclpy
from rclpy.node import Node
import time
import random

# Import standard messages
from sensor_msgs.msg import Image, BatteryState, LaserScan
from geometry_msgs.msg import Twist
from std_msgs.msg import String

# Import custom message
try:
    from icd_custom_msgs.msg import CustomData, CommunicationHeader
except ImportError:
    print("Warning: icd_custom_msgs not found. Run 'source icd_ws/install/setup.bash' first.")
    CustomData = None

class DummyRosNode(Node):
    def __init__(self):
        super().__init__('dummy_icd_publisher')
        self.get_logger().info("Dummy ROS2 Node started - Publishing test topics...")

        # 1. /camera/image_raw (30Hz) - Normal
        self.pub_camera = self.create_publisher(Image, '/camera/image_raw', 10)
        self.timer_camera = self.create_timer(1.0/30.0, self.cb_camera)

        # 2. /cmd_vel (20Hz) - Normal
        self.pub_cmd_vel = self.create_publisher(Twist, '/cmd_vel', 10)
        self.timer_cmd_vel = self.create_timer(1.0/20.0, self.cb_cmd_vel)

        # 3. /vla_model/action (10Hz) - NOT published (Simulated by not creating timer/pub)
        # To test 'NOT_RECEIVED' status

        # 4. /battery_state (1Hz) - QoS Mismatch (Publisher is BestEffort, ICD expects Reliable)
        from rclpy.qos import QoSProfile, QoSReliabilityPolicy
        qos_best_effort = QoSProfile(reliability=QoSReliabilityPolicy.BEST_EFFORT, depth=10)
        self.pub_battery = self.create_publisher(BatteryState, '/battery_state', qos_best_effort)
        self.timer_battery = self.create_timer(1.0, self.cb_battery)

        # 5. /lidar/scan (15Hz) - Hz Mismatch (Publishing at 5Hz instead of 15Hz)
        self.pub_lidar = self.create_publisher(LaserScan, '/lidar/scan', 10)
        self.timer_lidar = self.create_timer(1.0/5.0, self.cb_lidar)

        # 6. /custom/data_test (10Hz) - Custom Msg with Header Validation
        if CustomData:
            self.pub_custom = self.create_publisher(CustomData, '/custom/data_test', 10)
            self.timer_custom = self.create_timer(1.0/10.0, self.cb_custom)

    def cb_camera(self):
        msg = Image()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "camera_link"
        msg.height = 480
        msg.width = 640
        self.pub_camera.publish(msg)

    def cb_cmd_vel(self):
        msg = Twist()
        msg.linear.x = 1.0
        msg.angular.z = 0.5
        self.pub_cmd_vel.publish(msg)

    def cb_battery(self):
        msg = BatteryState()
        msg.percentage = 85.0
        self.pub_battery.publish(msg)

    def cb_lidar(self):
        msg = LaserScan()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.ranges = [random.uniform(1.0, 5.0) for _ in range(10)]
        self.pub_lidar.publish(msg)

    def cb_custom(self):
        msg = CustomData()
        # Set dummy ID values: Src=1, Dst=[2, 3]
        # In actual communication_header logic, these are uint8
        msg.header.src = 1
        # Test: Simulate missing Dst '3' by only including '2' randomly
        if random.random() > 0.5:
            msg.header.dst = [2, 3] # Success
        else:
            msg.header.dst = [2]    # Missing 3
            
        msg.x = random.uniform(0.0, 100.0)
        self.pub_custom.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    node = DummyRosNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()