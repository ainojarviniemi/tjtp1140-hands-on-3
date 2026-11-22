"""Create Nordic Supply Oy and verify the saved third-party record."""
from __future__ import annotations

import os
from api_client import DolibarrClient


def main():
    api = DolibarrClient()

    # Dolibarr expects country_id (the numeric row ID from its country dictionary).
    # Set DOLIBARR_COUNTRY_ID after checking the Finland entry in your instance.
    country_id = os.getenv("DOLIBARR_COUNTRY_ID")
    if not country_id:
        raise ValueError(
            "Set DOLIBARR_COUNTRY_ID to the numeric Finland country ID in this Dolibarr instance."
        )

    submitted = {
        "name": "Nordic Supply Oy",
        "client": 1,
        "country_id": int(country_id),
        "email": "purchasing@nordicsupply.example",
        "phone": "+358 9 123 4567",
    }

    print("Creating third-party record...")
    creation_result = api.post("thirdparties", submitted)

    # Dolibarr versions commonly return the new record ID as an integer.
    # Some installations wrap it in an object.
    if isinstance(creation_result, dict):
        new_id = creation_result.get("id") or creation_result.get("rowid")
    else:
        new_id = creation_result

    if not new_id:
        raise RuntimeError(f"Creation response did not contain a new ID: {creation_result!r}")

    print(f"Created record ID: {new_id}")
    saved = api.get(f"thirdparties/{new_id}")

    expected = {
        "name": submitted["name"],
        "email": submitted["email"],
        "phone": submitted["phone"],
        "country_id": submitted["country_id"],
    }
    actual = {key: saved.get(key) for key in expected}

    print("\nCUSTOMER CREATION VERIFICATION")
    print("-" * 60)
    for field, expected_value in expected.items():
        actual_value = actual[field]
        # API responses can serialize numeric IDs as strings.
        matches = str(actual_value) == str(expected_value)
        status = "OK" if matches else "MISMATCH"
        print(f"{field:12} submitted={expected_value!s:30} saved={actual_value!s:30} [{status}]")

    if all(str(actual[k]) == str(v) for k, v in expected.items()):
        print("\nSuccess: the retrieved record matches the submitted values.")
    else:
        print("\nWarning: at least one saved value differs. Check the API response above.")


if __name__ == "__main__":
    main()
