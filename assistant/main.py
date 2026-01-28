from pathlib import Path

ASSISTANT_ROOT = Path(__file__).resolve().parent


def main() -> None:
    print(f"Assistant workspace ready at: {ASSISTANT_ROOT}")


if __name__ == "__main__":
    main()
