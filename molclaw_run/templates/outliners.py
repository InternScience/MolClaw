# ANSI color codes and colored output utilities

class Colors:
    RESET = '\033[0m'
    BLUE = '\033[34m'
    GREEN = '\033[32m'
    WHITE = '\033[37m'
    CYAN = '\033[36m'
    YELLOW = '\033[33m'
    RED = '\033[31m'
    BOLD = '\033[1m'
    LIGHT_PURPLE = '\033[95m'

def print_colored(text: str, color: str = Colors.WHITE, bold: bool = False):
    """Print colored text."""
    prefix = Colors.BOLD if bold else ''
    print(f"{prefix}{color}{text}{Colors.RESET}")

