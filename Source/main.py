"""Entry point: launches the Bloxorz GUI."""

from bloxorz.gui import BloxorzApp


def main() -> None:
    app = BloxorzApp()
    app.run()


if __name__ == "__main__":
    main()

