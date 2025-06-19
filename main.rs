// src/main.rs

use clap::Parser;
use std::fs;
use std::path::PathBuf;
use std::io::Write; // Needed for writing to ffmpeg's stdin
use std::process::{Command, Stdio, Child}; // For running ffmpeg

#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
struct Cli {
    /// Input .mcap file path
    #[arg(short, long)]
    input: PathBuf,

    /// Directory to save the extracted image frames
    #[arg(short, long)]
    output_video: PathBuf,

    /// The compressed image topic to extract from
    #[arg(short, long)]
    topic: String,

    /// Framerate for the output video
    #[arg(long, default_value = "10")]
    framerate: u32,

    /// CRF value for libx264 encoding (0-51, lower is better quality)
    #[arg(long, default_value = "23")]
    crf: u8,

    /// Preset for libx264 encoding (e.g., ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow)
    #[arg(long, default_value = "medium")]
    preset: String,

        /// Optional: Directory to save the individual .h264 frames (if desired)
    #[arg(long)]
    frames_dir: Option<PathBuf>,

    /// Optional: Limit the number of frames to process (for testing)
    #[arg(long)]
    limit_frames: Option<usize>,
}
/*
#[derive(Deserialize, Debug)]
struct Time {
    sec: i32,
    nanosec: u32,
}
#[derive(Deserialize, Debug)]
struct CompressedImage {
    timestamp: Time,
    frame_id: String,
    // A `uint8[]` in ROS maps to a `Vec<u8>` in Rust.
    data: Vec<u8>,
    format: String,
}
*/
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let cli = Cli::parse();
    println!(
        "Extracting H.264 frames from topic '{}' in '{}' and encoding to '{}'",
        cli.topic,
        cli.input.display(),
        cli.output_video.display()
    );

    // 1. Read the entire MCAP file into memory.
    let mcap_data: Vec<u8> = fs::read(&cli.input)?;
    println!("Loaded {} bytes from MCAP file.", mcap_data.len());

    // 2. Create the output directory for individual frames if specified
    if let Some(ref frames_dir) = cli.frames_dir {
        fs::create_dir_all(frames_dir)?;
        println!("Saving individual frames to '{}'", frames_dir.display());
    }

    // 3. Set up the ffmpeg command
    let mut ffmpeg_command = Command::new("ffmpeg");
    ffmpeg_command
        .arg("-y") // Overwrite output files without asking
        .arg("-framerate")
        .arg(cli.framerate.to_string())
        .arg("-i")
        .arg("-") // Read input from stdin
        .arg("-c:v")
        .arg("libx264")
        .arg("-pix_fmt")
        .arg("yuv420p")
        .arg("-crf")
        .arg(cli.crf.to_string())
        .arg("-preset")
        .arg(&cli.preset)
        .arg(&cli.output_video); // Output file path

    // Configure ffmpeg to read from a pipe
    ffmpeg_command.stdin(Stdio::piped());
    // Optionally, capture stdout/stderr for debugging ffmpeg issues
    // ffmpeg_command.stdout(Stdio::piped());
    // ffmpeg_command.stderr(Stdio::piped());

    println!("Spawning ffmpeg with command: {:?}", ffmpeg_command);

    let mut ffmpeg_process: Child = match ffmpeg_command.spawn() { // Explicitly type ffmpeg_process as Child
        Ok(process) => process,
        Err(e) => {
            eprintln!(
                "Failed to spawn ffmpeg. Error",
            //        ffmpeg_executable.display(), e
            );
            return Err(Box::new(e));
        }
    };

    // Get a handle to ffmpeg's stdin
    // The type of ffmpeg_stdin will be std::process::ChildStdin
    let mut ffmpeg_stdin = ffmpeg_process
        .stdin
        .take() // This returns Option<ChildStdin>
        .ok_or_else(|| "Failed to open ffmpeg stdin. Is ffmpeg configured to read from stdin?".to_string())?;
        // Use ok_or_else for a custom error message, or simply .unwrap() if you're sure it will be there.

    let messages_iterator = mcap::MessageStream::new(&mcap_data)?;
    let mut frame_count = 0;
    let mut h264_frames_written = 0;

    println!("Processing MCAP messages...");

    // 4. Loop through all messages
    for (msg_idx, message_result) in messages_iterator.enumerate() {
        let message = match message_result {
            Ok(msg) => msg,
            Err(e) => {
                eprintln!("Error reading message {}: {}", msg_idx, e);
                continue; // Skip malformed messages
            }
        };

        // Filter for the compressed image topic we care about
        if message.channel.topic == cli.topic {
            frame_count += 1;

            // Assuming message.data is the raw H.264 NAL unit(s) for a frame
            // Sometimes, ROS compressed image topics might wrap the H264 data
            // in another structure (like sensor_msgs/CompressedImage).
            // For H264, message.data should be directly pipeable.
            // If the message.data is a serialized ROS CompressedImage, you'd need to deserialize it first.
            // Based on your original code, it seems message.data is already the raw H264 payload.

            // Write the H.264 frame data to ffmpeg's stdin
            if let Err(e) = ffmpeg_stdin.write_all(&message.data) {
                eprintln!("\nError writing frame {} to ffmpeg: {}", frame_count, e);
                // Optionally break or try to close ffmpeg gracefully
                break;
            }
            h264_frames_written += 1;

            // Optionally save individual frames
            if let Some(ref frames_dir) = cli.frames_dir {
                let filename = format!("frame_{:05}.h264", frame_count);
                let output_path = frames_dir.join(filename);
                if let Err(e) = fs::write(&output_path, &message.data) {
                    eprintln!("\nError writing frame file {}: {}", output_path.display(), e);
                }
            }

            print!("\rProcessed {} messages, written {} H.264 frames to ffmpeg...", msg_idx + 1, h264_frames_written);
            std::io::stdout().flush()?; // Ensure the print! output is displayed immediately

            // Debug/limit code
            if let Some(limit) = cli.limit_frames {
                if h264_frames_written >= limit {
                    println!("\nReached frame limit of {}. Stopping.", limit);
                    break;
                }
            }
        }
    }

    println!(); // Newline after the progress indicator

    drop(ffmpeg_stdin);

    // 6. Wait for ffmpeg to finish
    println!("Waiting for ffmpeg to finish encoding...");
    let ffmpeg_output = ffmpeg_process.wait_with_output()?;

    if ffmpeg_output.status.success() {
        println!(
            "\nSuccessfully created video '{}' with {} H.264 frames.",
            cli.output_video.display(),
            h264_frames_written
        );
    } else {
        eprintln!(
            "\nffmpeg failed with status: {}",
            ffmpeg_output.status
        );
        eprintln!("ffmpeg stdout: {}", String::from_utf8_lossy(&ffmpeg_output.stdout));
        eprintln!("ffmpeg stderr: {}", String::from_utf8_lossy(&ffmpeg_output.stderr));
        return Err("ffmpeg command failed".into());
    }

    if h264_frames_written == 0 {
        println!("\nWarning: No messages found on topic '{}' or no H.264 data written. Video might be empty or not created.", cli.topic);
    }
    Ok(())
}
