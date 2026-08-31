#!/usr/bin/env python3
"""Interactive Garmin Connect login. Run once per machine.

Writes an OAuth token to ~/.garminconnect/. Password is never saved,
never written to disk, and never enters shell history.
"""

from getpass import getpass       # reads a password without echoing it
from pathlib import Path          # filesystem paths; uses / to join

from garminconnect import Garmin

# Path.home() is ~ . The / operator joins path segments.
TOKENSTORE = Path.home() / ".garminconnect"


def main() -> None:
    """`-> None` is a type hint meaning 'returns nothing'. Documentation only."""
    email = input("Garmin email: ")
    password = getpass("Garmin password: ")   # not echoed to the terminal

    # `prompt_mfa` is a callback the library calls if MFA is required.
    # `lambda: x` is an anonymous function taking no arguments, like `() => x`.
    client = Garmin(
        email=email,
        password=password,
        prompt_mfa=lambda: input("MFA one-time code: "),
    )

    # login() with a path argument saves the token there for reuse.
    client.login(str(TOKENSTORE))

    print(f"✓ Token written to {TOKENSTORE}")
    print("  Your password was not saved. Daily syncs resume from this token.")


# Only run main() when this file is executed directly, not when imported.
if __name__ == "__main__":
    main()

