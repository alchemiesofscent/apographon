import subprocess
import sys

def check_dependency(command):
    """Check if a command is available in the environment."""
    try:
        subprocess.run([command, '--version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def main():
    dependencies = {
        'pandoc': 'Pandoc is required for converting documents.',
        'python3': 'Python 3 is required to run this project.',
    }

    missing_dependencies = []

    for command, message in dependencies.items():
        if not check_dependency(command):
            missing_dependencies.append(message)

    if missing_dependencies:
        print("Missing dependencies:")
        for msg in missing_dependencies:
            print(f"- {msg}")
        sys.exit(1)
    else:
        print("All dependencies are satisfied.")

if __name__ == "__main__":
    main()