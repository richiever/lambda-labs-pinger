"""Lambda Cloud GPU Pinger - polls for available GPUs and alerts you."""

import time
import sys
from datetime import datetime

try:
    import requests
except ImportError:
    print("Missing 'requests' package. Install with: pip install requests")
    sys.exit(1)

API_BASE = "https://cloud.lambdalabs.com/api/v1"


def get_available_gpus(api_key):
    resp = requests.get(
        f"{API_BASE}/instance-types",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json().get("data", {})

    available = {}
    for key, entry in data.items():
        regions = entry.get("regions_with_capacity_available", [])
        if regions:
            info = entry.get("instance_type", {})
            available[key] = {
                "name": info.get("name", key),
                "description": info.get("description", ""),
                "price_cents_per_hour": info.get("price_cents_per_hour", 0),
                "specs": info.get("specs", {}),
                "regions": [r.get("description", r.get("name", "")) for r in regions],
            }
    return available


def print_table(available):
    print(f"\n{'GPU':<35} {'$/hr':<8} {'Regions'}")
    print("-" * 80)
    for key, gpu in sorted(available.items()):
        price = f"${gpu['price_cents_per_hour'] / 100:.2f}"
        regions = ", ".join(gpu["regions"])
        print(f"{gpu['description']:<35} {price:<8} {regions}")


def main():
    print("=== Lambda Cloud GPU Pinger ===\n")
    api_key = input("Enter your Lambda Cloud API key: ").strip()
    if not api_key:
        print("No API key provided. Exiting.")
        return

    interval_str = input("Poll interval in seconds [30]: ").strip()
    interval = int(interval_str) if interval_str else 30

    print(f"\nPolling every {interval}s. Press Ctrl+C to stop.\n")

    prev_available = set()

    while True:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            available = get_available_gpus(api_key)
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 401:
                print(f"[{now}] ERROR: Invalid API key (401 Unauthorized).")
                return
            print(f"[{now}] HTTP error: {e}")
            time.sleep(interval)
            continue
        except requests.exceptions.RequestException as e:
            print(f"[{now}] Network error: {e}")
            time.sleep(interval)
            continue

        current = set(available.keys())
        newly_available = current - prev_available

        if available:
            print(f"[{now}] {len(available)} GPU type(s) available:")
            print_table(available)

            if newly_available:
                new_names = ", ".join(available[k]["description"] for k in newly_available)
                print(f"\n  >>> NEW GPU AVAILABLE: {new_names} <<<\a")
        else:
            print(f"[{now}] No GPUs available.")

        prev_available = current
        time.sleep(interval)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nStopped.")
