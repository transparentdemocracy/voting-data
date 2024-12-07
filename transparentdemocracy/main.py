import logging

from transparentdemocracy import CONFIG
from transparentdemocracy.application import Application

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def main():
    app = Application(CONFIG)
    app.process_plenaries()
    app.download_documents()
    app.publish_to_elastic()


if __name__ == "__main__":
    main()
