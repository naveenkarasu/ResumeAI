mod service;

pub use service::MlServiceImpl;

// Include generated protobuf code
pub mod ml {
    tonic::include_proto!("ml");
}
