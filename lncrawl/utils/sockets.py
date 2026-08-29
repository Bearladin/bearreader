import socket


def free_port(host: str = "127.0.0.1", desired_port: int = 0) -> int:
    """
    Returns desired_port if it is free, otherwise returns a random free port.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, desired_port))
        except OSError:
            s.bind((host, 0))
        return s.getsockname()[1]
