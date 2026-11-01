//! Shared starting point for {{ project-name }}.
#![cfg_attr(not(feature = "std"), no_std)]

#[cfg(feature = "alloc")]
extern crate alloc;

#[cfg(not(any(feature = "alloc", feature = "std")))]
compile_error!("Enable `alloc` or `std` for the starter library.");

/// Return the package version inherited from the workspace.
pub fn version() -> &'static str {
    env!("CARGO_PKG_VERSION")
}
