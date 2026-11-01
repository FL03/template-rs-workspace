//! Optional client-side entry point for {{ project-name }}.
#![cfg_attr(not(feature = "std"), no_std)]

#[cfg(feature = "alloc")]
extern crate alloc;

#[cfg(not(any(feature = "alloc", feature = "std")))]
compile_error!("Enable `alloc` or `std` for the client library.");

/// Return the shared workspace version through the starter API.
pub fn version() -> &'static str {
    starter::version()
}
