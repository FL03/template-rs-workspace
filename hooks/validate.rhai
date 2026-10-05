let authors = variable::get("authors");
for character in authors.chars() {
    if character == '"' || character == '\\' || character < ' ' || character == '\u007f' {
        abort("Cargo author must not contain quotes, backslashes, or control characters");
    }
}
