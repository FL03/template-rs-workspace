//! {{ description }}

#[cfg(not(feature = "std"))]
compile_error!("Command packages require the `std` feature.");

fn main() {
    println!("{{ project-name }} {}", starter::version());
}
