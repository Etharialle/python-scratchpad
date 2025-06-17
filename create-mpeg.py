import argparse
import cv2
import numpy as np
from cv_bridge import CvBridge
from mcap_ros2.reader import read_ros2_messages

# Attempt to import message types. This works best if your ROS 2 environment is sourced
# or if you've pip installed the specific message packages.
try:
    from sensor_msgs.msg import Image, CompressedImage
except ImportError:
    print("Error: Could not import sensor_msgs.msg.Image or CompressedImage.")
    print("Please ensure your ROS 2 environment is sourced or you have 'sensor-msgs-py' installed.")
    print("Example: 'pip install sensor-msgs-py'")
    exit(1)

def mcap_to_mp4(mcap_file, topic_name, output_file, fps=30.0, encoding="bgr8"):
    """
    Converts an image topic from an MCAP file to an MP4 video.

    Args:
        mcap_file (str): Path to the input MCAP file.
        topic_name (str): The image topic to extract (e.g., "/camera/image_raw").
        output_file (str): Path to the output MP4 file.
        fps (float): Frames per second for the output video.
        encoding (str): Desired OpenCV encoding (e.g., "bgr8", "mono8").
    """
    bridge = CvBridge()
    video_writer = None
    image_count = 0
    first_msg_time_ns = None
    last_msg_time_ns = None

    print(f"Reading MCAP file: {mcap_file}")
    print(f"Looking for topic: {topic_name}")

    try:
        for msg_container in read_ros2_messages(mcap_file, topics=[topic_name]):
            ros_msg = msg_container.ros_message
            log_time_ns = msg_container.log_time_ns # Log time of the message

            if first_msg_time_ns is None:
                first_msg_time_ns = log_time_ns
            last_msg_time_ns = log_time_ns

            cv_image = None
            if isinstance(ros_msg, Image):
                try:
                    cv_image = bridge.imgmsg_to_cv2(ros_msg, desired_encoding=encoding)
                except Exception as e:
                    print(f"Error converting Image message: {e}")
                    # Try common fallback encodings if default fails
                    try:
                        print(f"Attempting fallback encoding passthrough for {ros_msg.encoding}...")
                        cv_image = bridge.imgmsg_to_cv2(ros_msg, desired_encoding="passthrough")
                        # If image is mono, ensure it's 3-channel for color video codecs
                        if len(cv_image.shape) == 2 or cv_image.shape[2] == 1:
                           if encoding.lower() in ["bgr8", "rgb8"]: # if user wants color
                               print("Converting mono image to BGR for color video.")
                               cv_image = cv2.cvtColor(cv_image, cv2.COLOR_GRAY2BGR)
                    except Exception as e_fallback:
                        print(f"Fallback conversion failed: {e_fallback}")
                        continue
            elif isinstance(ros_msg, CompressedImage):
                try:
                    cv_image = bridge.compressed_imgmsg_to_cv2(ros_msg, desired_encoding=encoding)
                except Exception as e:
                    print(f"Error converting CompressedImage message: {e}")
                    try:
                        print(f"Attempting fallback encoding passthrough for {ros_msg.format}...")
                        cv_image = bridge.compressed_imgmsg_to_cv2(ros_msg, desired_encoding="passthrough")
                        if len(cv_image.shape) == 2 or cv_image.shape[2] == 1:
                           if encoding.lower() in ["bgr8", "rgb8"]:
                               print("Converting mono image to BGR for color video.")
                               cv_image = cv2.cvtColor(cv_image, cv2.COLOR_GRAY2BGR)
                    except Exception as e_fallback:
                        print(f"Fallback conversion failed: {e_fallback}")
                        continue
            else:
                print(f"Skipping message of unknown type: {type(ros_msg)} on topic {topic_name}")
                continue

            if cv_image is None:
                print("CV Image is None after conversion attempt, skipping frame.")
                continue

            if video_writer is None:
                height, width = cv_image.shape[:2]
                # Ensure 3 channels if BGR8 is expected by codec, even if original was mono
                if encoding.lower() in ["bgr8", "rgb8"] and (len(cv_image.shape) == 2 or cv_image.shape[2] == 1):
                    print(f"Warning: Image is single channel, but '{encoding}' was requested. Output video will be color.")
                    # VideoWriter expects 3 channels for color codecs
                elif len(cv_image.shape) == 3 and cv_image.shape[2] == 1: # Handle CV_8UC1 but 3-dim shape
                     if encoding.lower() in ["bgr8", "rgb8"]:
                        print("Converting mono image (shaped as 3D) to BGR for color video.")
                        cv_image = cv2.cvtColor(cv_image, cv2.COLOR_GRAY2BGR)


                fourcc = cv2.VideoWriter_fourcc(*'mp4v') # or 'XVID', 'MJPG', etc.
                video_writer = cv2.VideoWriter(output_file, fourcc, fps, (width, height))
                if not video_writer.isOpened():
                    print(f"Error: Could not open video writer for {output_file}")
                    return
                print(f"Video writer initialized: {width}x{height} @ {fps} FPS, Codec: mp4v")

            # Ensure frame is 3 channels if video writer expects color
            if len(cv_image.shape) == 2 and (encoding.lower() in ["bgr8", "rgb8"]):
                 cv_image = cv2.cvtColor(cv_image, cv2.COLOR_GRAY2BGR)
            elif len(cv_image.shape) == 3 and cv_image.shape[2] == 1 and (encoding.lower() in ["bgr8", "rgb8"]):
                 cv_image = cv2.cvtColor(cv_image, cv2.COLOR_GRAY2BGR)


            video_writer.write(cv_image)
            image_count += 1
            if image_count % 100 == 0:
                print(f"Processed {image_count} frames...")

    except FileNotFoundError:
        print(f"Error: MCAP file not found at {mcap_file}")
        return
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if video_writer is not None:
            video_writer.release()
            print(f"Video saved to {output_file} with {image_count} frames.")
            if first_msg_time_ns and last_msg_time_ns and image_count > 1:
                duration_s = (last_msg_time_ns - first_msg_time_ns) / 1e9
                actual_fps = (image_count -1) / duration_s if duration_s > 0 else float('inf')
                print(f"Message duration in MCAP: {duration_s:.2f} s. Actual average FPS from messages: {actual_fps:.2f}")
                if abs(actual_fps - fps) > 5: # Arbitrary threshold
                    print(f"Warning: Specified FPS ({fps}) differs significantly from detected average FPS ({actual_fps:.2f}). Playback speed might be affected.")
            elif image_count <=1 and video_writer is not None:
                 print(f"Warning: Only {image_count} frame(s) processed. Video might be very short or empty.")
        elif image_count == 0:
            print(f"No images found on topic '{topic_name}' in '{mcap_file}'. No video created.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert an image topic from an MCAP file to an MP4 video.")
    parser.add_argument("mcap_file", help="Path to the input MCAP file.")
    parser.add_argument("topic_name", help="Image topic name (e.g., /camera/image_raw).")
    parser.add_argument("output_file", help="Path to the output MP4 file.")
    parser.add_argument("--fps", type=float, default=30.0, help="Frames per second for the output video (default: 30.0).")
    parser.add_argument("--encoding", type=str, default="bgr8", help="Desired OpenCV encoding for frames (e.g., bgr8, rgb8, mono8, passthrough) (default: bgr8).")

    args = parser.parse_args()

    # It's generally best to run this in an environment where ROS 2 is sourced
    # or where cv_bridge and sensor_msgs can be found by Python.
    # For example, source /opt/ros/<distro>/setup.bash

    mcap_to_mp4(args.mcap_file, args.topic_name, args.output_file, args.fps, args.encoding)