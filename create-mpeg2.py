import argparse
import cv2
import numpy as np
from mcap_ros2.reader import read_ros2_messages # mcap-ros2-support handles deserialization

# We will try to get message types from mcap_ros2_support's bundled types
# or from pip-installed standalone packages if mcap_ros2_support doesn't find them.
# The `ros_message` attribute from read_ros2_messages will be an instance
# of the appropriate message class if deserialization is successful.

def get_image_info(ros_msg):
    """
    Extracts common image information from a deserialized ROS Image or CompressedImage message.
    The ros_msg object here is assumed to be the deserialized message object provided
    by mcap-ros2-support.
    """
    msg_type = type(ros_msg).__name__

    if msg_type == "Image":
        return {
            "type": "Image",
            "height": ros_msg.height,
            "width": ros_msg.width,
            "encoding": ros_msg.encoding,
            "is_bigendian": ros_msg.is_bigendian, # Often 0 (little endian)
            "step": ros_msg.step, # Full row length in bytes
            "data": ros_msg.data # This should be a bytes object or list of ints
        }
    elif msg_type == "CompressedImage":
        return {
            "type": "CompressedImage",
            "format": ros_msg.format, # e.g., "jpeg", "png"
            "data": ros_msg.data # Compressed data as bytes or list of ints
        }
    else:
        print(f"Unsupported message type for image extraction: {msg_type}")
        return None

def image_msg_to_cv2_manual(img_info, desired_encoding="bgr8"):
    """
    Manually converts ROS Image data (from get_image_info) to an OpenCV image.
    """
    if img_info is None or img_info["type"] != "Image":
        return None

    height = img_info["height"]
    width = img_info["width"]
    encoding = img_info["encoding"].lower()
    step = img_info["step"]
    data = img_info["data"]

    # Convert data (which might be list of ints) to numpy array of uint8
    # If data is already 'bytes', np.frombuffer is efficient.
    # If it's a list of ints (common from some deserializers), convert.
    if isinstance(data, (bytes, bytearray)):
        cv_image_data = np.frombuffer(data, dtype=np.uint8)
    elif isinstance(data, list):
        cv_image_data = np.array(data, dtype=np.uint8)
    else:
        raise TypeError(f"Unsupported data type for image data: {type(data)}")


    # Determine number of channels and element size from encoding
    # This is a simplified version; ROS has many encodings.
    if encoding in ["mono8", "8uc1", "gray", "grey"]:
        channels = 1
        dtype = np.uint8
    elif encoding in ["rgb8", "bgr8"]: # Assuming 8-bit, 3 channels
        channels = 3
        dtype = np.uint8
    elif encoding in ["rgba8", "bgra8"]:
        channels = 4
        dtype = np.uint8
    elif encoding in ["mono16", "16uc1"]:
        channels = 1
        dtype = np.uint16 # OpenCV handles CV_16UC1
        # Data might need conversion from bytes to uint16 if bigendian or not aligned
        if img_info["is_bigendian"]:
            cv_image_data = cv_image_data.view(dtype=dtype).byteswap() # if stored as bytes
        else:
            cv_image_data = cv_image_data.view(dtype=dtype) # if stored as bytes
        # If data was already list of uint16 numbers, this view() part might not be needed.
    else:
        print(f"Unsupported encoding for manual conversion: {encoding}")
        return None

    try:
        # Reshape the image data.
        # If step is greater than width * channels * itemsize, there's padding.
        # OpenCV generally handles images with padding if the step is correct.
        # However, for simplicity here, we'll assume tight packing or handle common cases.
        expected_min_data_size = height * width * channels * np.dtype(dtype).itemsize
        if len(cv_image_data) < expected_min_data_size:
            print(f"Warning: Data size {len(cv_image_data)} is less than expected {expected_min_data_size} for {width}x{height} {encoding}. Skipping.")
            return None

        if step == width * channels * np.dtype(dtype).itemsize:
            # Tightly packed data
            cv_image = cv_image_data.reshape(height, width, channels) if channels > 1 else cv_image_data.reshape(height, width)
        else:
            # Data has padding, copy row by row
            # print(f"Data has padding: step={step}, width_bytes={width * channels * np.dtype(dtype).itemsize}")
            cv_image = np.empty((height, width, channels) if channels > 1 else (height, width), dtype=dtype)
            bytes_per_pixel_channel = np.dtype(dtype).itemsize
            actual_row_width_bytes = width * channels * bytes_per_pixel_channel
            for i in range(height):
                row_start = i * step
                row_data = cv_image_data[row_start : row_start + actual_row_width_bytes]
                if channels > 1:
                    cv_image[i] = row_data.reshape(width, channels)
                else:
                    cv_image[i] = row_data.reshape(width)


    except ValueError as e:
        print(f"Error reshaping image data for encoding {encoding} (H:{height}, W:{width}, C:{channels}, Step:{step}, DataLen:{len(cv_image_data)}): {e}")
        return None

    # Handle color conversions if necessary (e.g., RGB to BGR for OpenCV)
    if encoding == "rgb8" and desired_encoding == "bgr8":
        cv_image = cv2.cvtColor(cv_image, cv2.COLOR_RGB2BGR)
    elif encoding == "rgba8" and desired_encoding == "bgr8": # common request
        cv_image = cv2.cvtColor(cv_image, cv2.COLOR_RGBA2BGR) # drop alpha
    elif encoding == "bgra8" and desired_encoding == "bgr8":
        cv_image = cv2.cvtColor(cv_image, cv2.COLOR_BGRA2BGR) # drop alpha
    # Add more conversions as needed

    if desired_encoding == "mono8" and channels > 1:
        if encoding in ["rgb8", "bgr8", "rgba8", "bgra8"]: # Crude check
             cv_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY if "bgr" in encoding else cv2.COLOR_RGB2GRAY)
        else:
            print(f"Cannot automatically convert {encoding} to mono8, taking first channel if multi-channel.")
            if len(cv_image.shape) > 2: cv_image = cv_image[:,:,0]


    # If the output needs to be 3-channel (e.g., for color video codecs) but image is mono
    if (desired_encoding == "bgr8" or desired_encoding == "rgb8") and (len(cv_image.shape) == 2 or cv_image.shape[2] == 1):
        cv_image = cv2.cvtColor(cv_image, cv2.COLOR_GRAY2BGR)


    return cv_image

def compressed_imgmsg_to_cv2_manual(img_info, desired_encoding="bgr8"):
    """
    Manually decodes ROS CompressedImage data (from get_image_info) to an OpenCV image.
    """
    if img_info is None or img_info["type"] != "CompressedImage":
        return None

    data = img_info["data"]
    # compressed_format = img_info["format"] # e.g. "jpeg", "png"

    # Convert data (which might be list of ints) to numpy array of uint8
    if isinstance(data, (bytes, bytearray)):
        image_data_np = np.frombuffer(data, dtype=np.uint8)
    elif isinstance(data, list):
        image_data_np = np.array(data, dtype=np.uint8)
    else:
        raise TypeError(f"Unsupported data type for compressed image data: {type(data)}")

    cv_image = cv2.imdecode(image_data_np, cv2.IMREAD_COLOR) # IMREAD_COLOR tries to make it 3-channel BGR

    if cv_image is None:
        print("cv2.imdecode failed. Invalid compressed data or unsupported format.")
        return None

    # Handle desired encoding (mostly for mono vs color)
    if desired_encoding == "mono8" and (len(cv_image.shape) == 3 and cv_image.shape[2] == 3):
        cv_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
    elif (desired_encoding == "bgr8" or desired_encoding == "rgb8") and len(cv_image.shape) == 2:
        cv_image = cv2.cvtColor(cv_image, cv2.COLOR_GRAY2BGR)
    # Note: imdecode usually gives BGR. If RGB desired, cvtColor needed.

    return cv_image

def mcap_to_mp4_standalone(mcap_file, topic_name, output_file, fps=30.0, desired_cv_encoding="bgr8"):
    video_writer = None
    image_count = 0
    first_msg_time_ns = None
    last_msg_time_ns = None

    print(f"Reading MCAP file: {mcap_file}")
    print(f"Looking for topic: {topic_name}")
    print(f"Desired OpenCV encoding for video frames: {desired_cv_encoding}")

    try:
        # `mcap_ros2_support` will attempt to deserialize messages
        # based on bundled IDL definitions or those it can find.
        # The `ros_message` attribute will be the deserialized message object.
        for msg_container in read_ros2_messages(mcap_file, topics=[topic_name]):
            ros_msg = msg_container.ros_message # This is the deserialized object
            log_time_ns = msg_container.log_time_ns

            if ros_msg is None:
                print(f"Warning: Failed to deserialize message on topic {topic_name} at time {log_time_ns}. Schema might be missing or corrupted.")
                continue

            if first_msg_time_ns is None:
                first_msg_time_ns = log_time_ns
            last_msg_time_ns = log_time_ns

            img_meta_info = get_image_info(ros_msg)
            if not img_meta_info:
                # print(f"Skipping non-image or unsupported message type: {type(ros_msg)}")
                continue

            cv_image = None
            if img_meta_info["type"] == "Image":
                cv_image = image_msg_to_cv2_manual(img_meta_info, desired_encoding=desired_cv_encoding)
            elif img_meta_info["type"] == "CompressedImage":
                cv_image = compressed_imgmsg_to_cv2_manual(img_meta_info, desired_encoding=desired_cv_encoding)

            if cv_image is None:
                print("Failed to convert ROS message to CV image, skipping frame.")
                continue

            if video_writer is None:
                height, width = cv_image.shape[:2]
                # Ensure 3 channels if BGR8/RGB8 is expected by codec, even if original was mono
                # This check should ideally be based on `desired_cv_encoding`
                is_color_output = desired_cv_encoding.lower() in ["bgr8", "rgb8"]
                
                fourcc = cv2.VideoWriter_fourcc(*'mp4v') # or 'XVID', 'avc1'
                video_writer = cv2.VideoWriter(output_file, fourcc, fps, (width, height), is_color=is_color_output)
                if not video_writer.isOpened():
                    print(f"Error: Could not open video writer for {output_file}")
                    return
                print(f"Video writer initialized: {width}x{height} @ {fps} FPS. Color: {is_color_output}")


            # Ensure frame format matches video writer's expectation (color/mono)
            is_color_output = desired_cv_encoding.lower() in ["bgr8", "rgb8"]
            if is_color_output and (len(cv_image.shape) == 2 or cv_image.shape[2] == 1):
                cv_image = cv2.cvtColor(cv_image, cv2.COLOR_GRAY2BGR)
            elif not is_color_output and len(cv_image.shape) == 3 and cv_image.shape[2] > 1:
                cv_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY) # Assuming BGR if it's color


            video_writer.write(cv_image)
            image_count += 1
            if image_count % 100 == 0:
                print(f"Processed {image_count} frames...")

    except FileNotFoundError:
        print(f"Error: MCAP file not found at {mcap_file}")
        return
    except ImportError as e:
        print(f"ImportError: {e}. A required Python package might be missing.")
        print("Try: pip install mcap-ros2-support numpy opencv-python")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if video_writer is not None:
            video_writer.release()
            print(f"Video saved to {output_file} with {image_count} frames.")
            if first_msg_time_ns and last_msg_time_ns and image_count > 1:
                duration_s = (last_msg_time_ns - first_msg_time_ns) / 1e9
                actual_fps = (image_count -1) / duration_s if duration_s > 0 else float('inf')
                print(f"Message duration in MCAP: {duration_s:.2f} s. Actual average FPS from messages: {actual_fps:.2f}")
                if abs(actual_fps - fps) > 5:
                    print(f"Warning: Specified FPS ({fps}) differs significantly from detected average FPS ({actual_fps:.2f}). Playback speed might be affected.")
            elif image_count <=1 and video_writer is not None :
                 print(f"Warning: Only {image_count} frame(s) processed. Video might be very short or empty.")

        elif image_count == 0:
            print(f"No images found or processed on topic '{topic_name}' in '{mcap_file}'. No video created.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert an image topic from an MCAP file to an MP4 video (standalone).")
    parser.add_argument("mcap_file", help="Path to the input MCAP file.")
    parser.add_argument("topic_name", help="Image topic name (e.g., /camera/image_raw).")
    parser.add_argument("output_file", help="Path to the output MP4 file.")
    parser.add_argument("--fps", type=float, default=30.0, help="Frames per second for the output video (default: 30.0).")
    parser.add_argument("--encoding", type=str, default="bgr8",
                        help="Desired OpenCV encoding for video frames (e.g., bgr8, rgb8, mono8). "
                             "The script will attempt to convert to this. (default: bgr8)")

    args = parser.parse_args()
    mcap_to_mp4_standalone(args.mcap_file, args.topic_name, args.output_file, args.fps, args.encoding)