import dataclasses
import logging

from pykeepass import PyKeePass
import re
import os

KEEPASS_PATH = os.path.expanduser(os.environ['WDDP_KEEPASS'])
KEEPASS_PASSWORD = os.environ['WDDP_KEEPASS_PASSWORD']

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class WddpSecrets:
    storage_service_account_credentials: str
    es_auth: str


def get_wddp_secrets(kdbx_file=KEEPASS_PATH, password=KEEPASS_PASSWORD):
    kp = PyKeePass(kdbx_file, password=password)
    storage_service_account_credentials = kp.find_entries_by_title(title="wddp storage service account")[0].attachments[
        0].binary.decode('utf-8')
    bonsai_user = kp.find_entries_by_title("bonsai wddp publisher")[0].username
    bonsai_pass = kp.find_entries_by_title("bonsai wddp publisher")[0].password
    return WddpSecrets(
        storage_service_account_credentials,
        f"{bonsai_user}:{bonsai_pass}"
    )


def get_keepass_entry(kdbx_file, password, entry, field):
    """Get a specific field from a KeePass entry."""
    kp = PyKeePass(kdbx_file, password=password)

    for kp_entry in kp.entries:
        if kp_entry.title == entry:
            return getattr(kp_entry, field, None)

    return None


def list_keepass_entries(kdbx_file, password):
    """List all entries in the KeePass database."""
    kp = PyKeePass(kdbx_file, password=password)
    return [(entry.title, entry) for entry in kp.entries]


def keepass_dotenv(kdbx_file=KEEPASS_PATH, password=KEEPASS_PASSWORD):
    """Read .env file and set environment variables with KeePass values resolved."""
    if not os.path.exists('.env'):
        logger.info("No .env file found. Skipping keepass_dotenv."")
        return

    if not os.path.exists(kdbx_file):
        logger.warning(f"KeePass database not found at {kdbx_file}. Skipping keepass_dotenv.")
        return

    with open('.env', 'r') as f:
        lines = f.readlines()

    def replace_keepass_ref(match):
        entry, field_or_attachment = match.group(1), match.group(2)

        if field_or_attachment.startswith('@'):
            # Attachment reference
            attachment_name = field_or_attachment[1:]
            kp = PyKeePass(kdbx_file, password=password)
            for kp_entry in kp.entries:
                if kp_entry.title == entry:
                    for attachment in kp_entry.attachments:
                        if attachment.filename == attachment_name:
                            return attachment.binary.decode('utf-8')
            return match.group(0)
        else:
            # Field reference
            value = get_keepass_entry(kdbx_file, password, entry, field_or_attachment)
            return value if value else match.group(0)

    for line in lines:
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            key, value = line.split('=', 1)
            resolved_value = re.sub(r'keepass://([^/]+)/([^/\s]+)', replace_keepass_ref, value)
            os.environ[key] = resolved_value


def main():
    print(get_wddp_secrets())


if __name__ == "__main__":
    main()
