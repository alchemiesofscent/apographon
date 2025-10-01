def read_file(file_path):
    """Read the contents of a file and return it as a string."""
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

def write_file(file_path, content):
    """Write the given content to a file."""
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(content)

def log_message(message):
    """Log a message to the console."""
    print(f"[LOG] {message}")

def clean_html_content(html_content):
    """Perform basic cleanup on the HTML content."""
    # Implement cleanup logic here (e.g., removing unnecessary tags)
    return html_content.strip()

def validate_file_path(file_path):
    """Check if the provided file path exists and is a file."""
    import os
    return os.path.isfile(file_path)