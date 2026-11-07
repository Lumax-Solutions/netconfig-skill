```python
import json
import urllib.error
import urllib.request

url = "https://api.example.com/data"
request = urllib.request.Request(url, headers={"Accept": "application/json"})

try:
    with urllib.request.urlopen(request, timeout=10) as response:
        if response.status != 200:
            raise ValueError(f"Unexpected HTTP status: {response.status}")

        charset = response.headers.get_content_charset() or "utf-8"
        data = json.loads(response.read().decode(charset))
        print(data)

except urllib.error.HTTPError as exc:
    # HTTP errors such as 404 or 500.
    print(f"HTTP error: {exc.code} {exc.reason}")
except urllib.error.URLError as exc:
    # DNS, connection, TLS, and some timeout failures.
    print(f"Request failed: {exc.reason}")
except TimeoutError:
    print("Request timed out")
except (json.JSONDecodeError, UnicodeDecodeError) as exc:
    print(f"Invalid JSON response: {exc}")
except ValueError as exc:
    print(exc)
```

The timeout is in seconds and applies to blocking network operations; it is not a total request deadline. HTTPS certificate verification is enabled by default.

This example has not been run.