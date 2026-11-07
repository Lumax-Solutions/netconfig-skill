This script accepts a hostname as a command-line argument, prints unique IPv4 and IPv6 addresses, and handles DNS errors gracefully.

```python
import socket
import sys


def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <hostname>", file=sys.stderr)
        return 1

    hostname = sys.argv[1]

    try:
        results = socket.getaddrinfo(
            hostname, None,
            family=socket.AF_UNSPEC,
            type=socket.SOCK_STREAM,
        )
    except (socket.gaierror, UnicodeError) as exc:
        print(f"Could not resolve {hostname!r}: {exc}", file=sys.stderr)
        return 1

    addresses = {
        (family, sockaddr[0])
        for family, _, _, _, sockaddr in results
        if family in (socket.AF_INET, socket.AF_INET6)
    }

    for family, address in sorted(addresses):
        label = "IPv4" if family == socket.AF_INET else "IPv6"
        print(f"{label}: {address}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Example usage:

```bash
python resolve.py example.com
```

Only address families available through your system’s resolver will appear.