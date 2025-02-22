import os
import resource
import subprocess
import uuid
from functools import cache
from pathlib import Path

from loguru import logger


@cache
def blueos_version() -> str:
    return os.environ.get("GIT_DESCRIBE_TAGS", "null")


def limit_ram_usage(memory_limit_mb: int = 100) -> None:
    resource.setrlimit(resource.RLIMIT_AS, (memory_limit_mb * 1024 * 1024, -1))


def delete_everything(path: Path) -> None:
    if path.is_file() and not file_is_open(path):
        path.unlink()
        return

    for item in path.glob("*"):
        try:
            if item.is_file() and not file_is_open(item):
                item.unlink()
            if item.is_dir() and not item.is_symlink():
                # Delete folder contents
                delete_everything(item)
        except Exception as exception:
            logger.warning(f"Failed to delete: {item}, {exception}")


def file_is_open(path: Path) -> bool:
    result = subprocess.run(["lsof", path.resolve()], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    return result.returncode == 0


@cache
def local_unique_identifier() -> str:
    blueos_uuid_path = "/etc/blueos/uuid"

    # Try to get an uuid4 from BlueOS of previous boots
    try:
        with open(blueos_uuid_path, "r", encoding="utf-8") as f:
            uuid4 = "".join(f.read().split())
            try:
                uuid.UUID(uuid4, version=4)
                return uuid4
            except ValueError:
                logger.warning(f"Local BlueOS uuid is not valid: {uuid4}")
    except Exception as error:
        logger.warning(f"Could not get BlueOS's uuid. {error}")

    # We failed, going to generate a new BlueOS uuid
    uuid4 = uuid.uuid4().hex
    try:
        with open(blueos_uuid_path, "w+", encoding="utf-8") as f:
            f.write(uuid4)
            f.flush()
        return uuid4
    except Exception as error:
        logger.warning(f"Failed to write uuid {uuid4} to {blueos_uuid_path}, {error}")

    # There is something really wrong here and this line should never run
    # But at least we are going to identify that something is wrong
    return "00000000000040000000000000000000"


@cache
def local_hardware_identifier() -> str:
    blueos_uuid_path = "/etc/blueos/hardware-uuid"

    # Try to get an uuid from hardware configuration
    try:
        with open(blueos_uuid_path, "r", encoding="utf-8") as f:
            hardware_uuid = "".join(f.read().split())
            try:
                uuid.UUID(hardware_uuid)
                return hardware_uuid
            except ValueError:
                logger.warning(f"Local hardware uuid is not valid: {hardware_uuid}")
    except Exception as error:
        logger.warning(f"Could not get hardware uuid. {error}")

    # There is something really wrong here and this line should never run
    # But at least we are going to identify that something is wrong
    return "00000000000030000000000000000000"


def is_running_as_root() -> bool:
    return os.geteuid() == 0


def device_id() -> str:
    try:
        with open("/sys/firmware/devicetree/base/serial-number", "r", encoding="utf-8") as f:
            return f.read()
    except Exception as error:
        logger.exception(f"Could not get device's serial-number. {error}")

    try:
        with open("/etc/machine-id", "r", encoding="utf-8") as f:
            return "".join(f.read().split())
    except Exception as error:
        logger.exception(f"Could not get device's machine-id. {error}")

    raise ValueError("Could not get device id.")
