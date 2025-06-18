// src/main.rs

use clap::Parser;
use std::fs;
use std::path::PathBuf;
use mcap::Message; // Need Message for accessing channel.topic
use std::io::Write; // Need Write for writing raw bytes


/// A simple tool to extract raw image frames from an MCAP file.
#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
struct Cli {
    /// Input .mcap file path
    #[arg(short, long)]
    input: PathBuf,

    /// Directory to save the extracted image frames
    #[arg(short, long)]
    output: PathBuf,

    /// The raw image topic to extract from
    #[arg(short, long)]
    topic: String,
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let cli = Cli::parse();
    println!(
        "Extracting raw images from topic '{}' in '{}'",
        cli.topic,
        cli.input.display()
    );

    // 1. Create the output directory if it doesn't exist
    fs::create_dir_all(&cli.output)?;
    println!("Saving frames to '{}'", cli.output.display());

    // 2. Read the entire MCAP file into memory.
    let mcap_data: Vec<u8> = fs::read(&cli.input)?;
    println!("Loaded {} bytes from MCAP file.", mcap_data.len());

    // 3. Use MessageStream to iterate over the loaded data.
    let messages_iterator = mcap::MessageStream::new(&mcap_data)?;

    let mut frame_count = 0;

    // 4. Loop through all messages
    for message_result in messages_iterator {
        let message = message_result?; // Handle potential errors during iteration

        // Filter for the raw image topic we care about
        if message.channel.topic == cli.topic {
            frame_count += 1;

            // Extract image metadata
            let height = message.channel.message_encoding.height.ok_or_else(|| {
                mcap::McapError::MissingField("height".to_string())
            })?;
            let width = message.channel.message_encoding.width.ok_or_else(|| {
                mcap::McapError::MissingField("width".to_string())
            })?;
            let encoding = &message.channel.message_encoding.encoding;
            // We need the raw data itself
            let raw_data = &message.data;

            // Save the raw image data to a file.
            // We need to store width, height, and encoding for FFmpeg later.
            // A common practice is to use a `.raw` extension or specific format extension,
            // but FFmpeg often needs more explicit parameters.
            // Let's save as .rgb32f for now.

            // The 'data' field is a byte slice.
            // For 32FC3, each pixel is 3 floats * 4 bytes/float = 12 bytes.
            // Total bytes should be width * height * 12.
            // We can add a check for this.

            if encoding != "32FC3" {
                eprintln!(
                    "Warning: Unexpected encoding '{}' for topic '{}'. Expected '32FC3'. Skipping frame {}.",
                    encoding, cli.topic, frame_count
                );
                continue;
            }

            let expected_data_len = (width as usize) * (height as usize) * 12; // 3 floats * 4 bytes/float
            if raw_data.len() != expected_data_len {
                eprintln!(
                    "Warning: Data length mismatch for frame {} on topic '{}'. Expected {} bytes, got {}. Skipping.",
                    frame_count, cli.topic, expected_data_len, raw_data.len()
                );
                continue;
            }

            // Use a filename that indicates the format and dimensions for clarity.
            let filename = format!("frame_{:05}_w{}_h{}_{}.rgb32f", frame_count, width, height, encoding);
            let output_path = cli.output.join(filename);

            // Write the raw bytes directly.
            fs::write(&output_path, raw_data)?;

            print!("\rSaved {} frames...", frame_count);
        }
    }

    if frame_count == 0 {
        println!("\n\nWarning: No messages found on topic '{}' with expected encoding. No frames were extracted.", cli.topic);
    } else {
        println!("\n\nDone! Extracted {} frames.", frame_count);
    }

    Ok(())
}
