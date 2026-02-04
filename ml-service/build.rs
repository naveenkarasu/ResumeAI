fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Compile protobuf files
    tonic_build::configure()
        .build_server(true)
        .build_client(false)
        .compile_protos(&["proto/ml.proto"], &["proto"])?;

    println!("cargo:rerun-if-changed=proto/ml.proto");
    Ok(())
}
