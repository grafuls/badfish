import sys


def progress_bar(value, end_value, state, prompt="Host state", bar_length=20):
    """Display a progress bar for long-running operations."""
    ratio = float(value) / end_value
    arrow = "-" * int(round(ratio * bar_length) - 1) + ">"
    spaces = " " * (bar_length - len(arrow))
    percent = int(round(ratio * 100))

    if state.lower() == "on":
        state = "On  "
    ret = "\r" if percent != 100 else "\n"
    sys.stdout.write(f"\r- POLLING: [{arrow + spaces}] {percent}% - {prompt}: {state}{ret}")
    sys.stdout.flush() 