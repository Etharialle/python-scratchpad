// src/main.rs

use clap::Parser;
use std::fs;
use std::path::PathBuf;

#[derive(Parser, Debug)]
#[command(author, version, about, long_about = None)]
struct Cli {
    /// Input .mcap file path
    #[arg(short, long)]
    input: PathBuf,

    /// Directory to save the extracted image frames
    #[arg(short, long)]
    output: PathBuf,

    /// The compressed image topic to extract from
    #[arg(short, long)]
    topic: String,
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
        "Extracting images from topic '{}' in '{}'",
        cli.topic,
        cli.input.display()
    );
    // 1. Read the entire MCAP file into memory.
    let mcap_data: Vec<u8> = fs::read(&cli.input)?;
    println!("Loaded {} bytes from MCAP file.", mcap_data.len());

    // 2. Create the output directory if it doesn't exist
    fs::create_dir_all(&cli.output)?;
    println!("Saving frames to '{}'", cli.output.display());


    let messages_iterator = mcap::MessageStream::new(&mcap_data)?;

    let mut frame_count = 0;

    // 4. Loop through all messages
    for message_result in messages_iterator {

        let message = message_result?;

        print!("message data full: {:?}",message.data);

        // Filter for the compressed image topic we care about
        if message.channel.topic == cli.topic {

            frame_count += 1;
            
            // Debug code to break the loop early
            if frame_count > 4 {
                println!("topic count:{}", frame_count);
                break;
            }

            // 4. Create a unique, zero-padded filename for each frame
            let filename = format!("frame_{:05}.h264", frame_count);
            let output_path = cli.output.join(filename);

            // 5. Write the raw message data directly to the file
            fs::write(&output_path, &message.data)?;

            print!("\rSaved {} frames...", frame_count);
            
        }
    }

    if frame_count == 0 {
        println!("\n\nWarning: No messages found on topic '{}'. No frames were extracted.", cli.topic);
    } else {
        println!("\n\nDone! Extracted {} frames.", frame_count);
    }

    Ok(())
}
