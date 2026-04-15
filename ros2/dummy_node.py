import rclpy
from rclpy.node import Node
import time
import random

# Import standard messages
from sensor_msgs.msg import Image, BatteryState, LaserScan, Imu, NavSatFix
from geometry_msgs.msg import Twist
from std_msgs.msg import String, Int32
from rclpy.qos import QoSProfile, QoSReliabilityPolicy

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

        # 1. /camera/image_raw (30Hz) - Normal (BestEffort)
        qos_best_effort = QoSProfile(reliability=QoSReliabilityPolicy.BEST_EFFORT, depth=10)
        self.pub_camera = self.create_publisher(Image, '/camera/image_raw', qos_best_effort)
        self.timer_camera = self.create_timer(1.0/30.0, self.cb_camera)

        # 2. /cmd_vel (20Hz) - Normal (Reliable)
        self.pub_cmd_vel = self.create_publisher(Twist, '/cmd_vel', 10)
        self.timer_cmd_vel = self.create_timer(1.0/20.0, self.cb_cmd_vel)

        # 3. /imu/data (100Hz) - Normal (BestEffort)
        self.pub_imu = self.create_publisher(Imu, '/imu/data', qos_best_effort)
        self.timer_imu = self.create_timer(1.0/100.0, self.cb_imu)

        # 4. /gps/fix (5Hz) - Normal (Reliable)
        self.pub_gps = self.create_publisher(NavSatFix, '/gps/fix', 10)
        self.timer_gps = self.create_timer(1.0/5.0, self.cb_gps)

        # 5. /status/system (1Hz) - Normal (Reliable)
        self.pub_status = self.create_publisher(String, '/status/system', 10)
        self.timer_status = self.create_timer(1.0, self.cb_status)

        # 6. /vla_model/action - NOT_RECEIVED (Simulated by NOT publishing)

        # 7. /battery_state (1Hz) - FAIL: QoS Mismatch (Expected Reliable, Pub=BestEffort)
        self.pub_battery = self.create_publisher(BatteryState, '/battery_state', qos_best_effort)
        self.timer_battery = self.create_timer(1.0, self.cb_battery)

        # 8. /lidar/scan (15Hz) - FAIL: Hz Mismatch (Pub=5Hz, Expected 15Hz)
        self.pub_lidar = self.create_publisher(LaserScan, '/lidar/scan', 10)
        self.timer_lidar = self.create_timer(1.0/5.0, self.cb_lidar)

        # 9. /custom/data_test (10Hz) - FAIL: Dst Mismatch (Simulate randomly)
        if CustomData:
            self.pub_custom = self.create_publisher(CustomData, '/custom/data_test', 10)
            self.timer_custom = self.create_timer(1.0/10.0, self.cb_custom)

        # 10. /diagnostic/error (2Hz) - FAIL: Type Mismatch (Pub=Int32, Expected String)
        self.pub_diag_error = self.create_publisher(Int32, '/diagnostic/error', 10)
        self.timer_diag_error = self.create_timer(1.0/2.0, self.cb_diag_error)

    def cb_camera(self):
        msg = Image()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.height = 480
        msg.width = 640
        self.pub_camera.publish(msg)

    def cb_cmd_vel(self):
        msg = Twist()
        msg.linear.x = 1.0
        self.pub_cmd_vel.publish(msg)

    def cb_imu(self):
        msg = Imu()
        msg.header.stamp = self.get_clock().now().to_msg()
        self.pub_imu.publish(msg)

    def cb_gps(self):
        msg = NavSatFix()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.latitude = 37.5665
        msg.longitude = 126.9780
        self.pub_gps.publish(msg)

    def cb_status(self):
        msg = String()
        msg.data = "SYSTEM_OK"
        self.pub_status.publish(msg)

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
        msg.header.src = 1
        # Randomly fail: Missing Dst ID '3'
        if random.random() > 0.5:
            msg.header.dst = [2, 3] # PASS
        else:
            msg.header.dst = [2]    # FAIL (Missing 3)
        msg.x = random.uniform(0.0, 100.0)
        self.pub_custom.publish(msg)

    def cb_diag_error(self):
        msg = Int32()
        msg.data = 404 # Sending integer instead of string
        self.pub_diag_error.publish(msg)

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