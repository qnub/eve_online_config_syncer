import logging
import os
import re
import shutil
from argparse import ArgumentParser
from pathlib import Path
from typing import Optional, Set


SCRIPT = Path(__file__)

log_format = "%(asctime)s [%(levelname)s] <%(filename)s:%(lineno)d> %(message)s"
logging.basicConfig(format=log_format, level=logging.INFO)
log = logging.getLogger(SCRIPT.name)

SCRIPT_DIR_PATH = SCRIPT.parent

USER_HOME = str(Path.home())
PROFILE_NAME_FILE = "profile_name.txt"
PROFILE_NAME_FILE_PATH = SCRIPT_DIR_PATH / Path(PROFILE_NAME_FILE)

SETTINGS_DIR_PREFIX = "settings_"
SETTINGS_DIR_RE = re.compile(rf"{SETTINGS_DIR_PREFIX}(?P<config_name>.*)")
SETTINGS_DEFAULT_NAME = "Default"

SETTINGS_USER_FILE_PREFIX = "core_user_"
SYSTEM_USER_ID = "_"
SETTINGS_CHAR_FILE_PREFIX = "core_char_"
SYSTEM_CHAR_ID = "_"

NON_ALPHABET_RE = re.compile(r"\W+", re.I | re.U)
GAME_FODLER_FILE = "game_folder.txt"
GAME_FODLER_FILE_PATH = SCRIPT_DIR_PATH / Path(GAME_FODLER_FILE)
GAME_FOLDER_DEFAULT_PATH = r"C:\CCP\EVE online"


def get_profile_folder():
    game_path = get_game_path()
    prefix = NON_ALPHABET_RE.sub("_", game_path).lower()

    return f"{prefix}_tq_tranquility"


def get_game_path() -> str:
    if GAME_FODLER_FILE_PATH.exists():
        with open(GAME_FODLER_FILE_PATH) as f:
            game_path = f.readline().strip()
    else:
        game_path = GAME_FOLDER_DEFAULT_PATH

    return game_path


GAME_DIR_WINDOWS = USER_HOME / Path("AppData\Local\CCP\EVE") / get_profile_folder()


class FileRegEx:
    extension: str = "dat"
    group_name: str = "id"
    prefix: str
    system_id: str
    _regex: re.Pattern = None

    def __init__(
        self,
        prefix: str,
        system_id: str,
        extension: Optional[str] = None,
        group_name: Optional[str] = None,
    ) -> None:
        self.prefix = prefix
        self.system_id = system_id

        if extension:
            self.extension = extension

        if group_name:
            self.group_name = group_name

    @property
    def regex(self):
        if self._regex is None:
            self._regex = re.compile(
                rf"{self.prefix}(?P<{self.group_name}>.*)\.{self.extension}"
            )

        return self._regex

    def match(self, string: str) -> re.Match:
        return self.regex.match(string)


user_regex = FileRegEx(SETTINGS_USER_FILE_PREFIX, SYSTEM_USER_ID)
char_regex = FileRegEx(SETTINGS_CHAR_FILE_PREFIX, SYSTEM_CHAR_ID)


def replace(file_path: str):
    if file_path:
        path = Path(file_path)

        log.info("Replace settings with provided path: %s", path)

        regex = get_regex(path)
        replace_with_latest(regex, path)
    else:
        profile_name = get_profile_name()

        log.info("Replace all settings in profile: %s", profile_name)

        replace_by_profile_name(profile_name)


def replace_by_profile_name(profile_name: str):
    path = get_settings_path(profile_name)
    replace_latest_in_dir(path)


def replace_by_default():
    path = get_settings_path(SETTINGS_DEFAULT_NAME)
    replace_latest_in_dir(path)


def get_settings_path(name: str) -> Path:
    return get_game_dir() / get_settings_dir(name)


def get_game_dir() -> Path:
    return GAME_DIR_WINDOWS


def get_settings_dir(name: str) -> Path:
    return Path(f"{SETTINGS_DIR_PREFIX}{name}")


def replace_latest_in_dir(path: Path):
    user = get_latest(user_regex, path)

    if user:
        replace_with_latest(user_regex, user)

    char = get_latest(char_regex, path)

    if char:
        replace_with_latest(char_regex, char)


def get_latest(regex: FileRegEx, path: Path) -> Optional[Path]:
    if path.exists:
        files = collect_files(regex, path)

        return select_latest(files)


def collect_files(regex: FileRegEx, path: Path) -> Set[Path]:
    files = set()

    for filepath in path.iterdir():
        if filepath.is_dir():
            continue

        matched = regex.match(filepath.name)

        if matched:
            target_id = matched.group(regex.group_name)

            if target_id != regex.system_id:
                files.add(filepath)

    return files


def select_latest(files: Set[Path]) -> Optional[Path]:
    latest: Optional[Path] = None

    for file in files:
        if latest is None or file.stat().st_mtime > latest.stat().st_mtime:
            log.debug("File %s modified %s", file, file.stat().st_mtime)
            latest = file

    log.info("Latest modified config file is: %s", latest.name)

    return latest


def replace_with_latest(regex: FileRegEx, latest: Path):
    files = collect_files(regex, latest.parent)
    replace_files(files, latest)


def replace_files(files: Set[Path], replacemet: Path):
    log.info("Replacment directory: %s", replacemet.parent)
    count = 0

    for file in files:
        if file == replacemet:
            continue

        log.debug("Replace %s", file.name)

        file.unlink()
        shutil.copyfile(replacemet, file)
        count += 1

    log.info("Replaced %d files", count)


def get_profile_name() -> str:
    if PROFILE_NAME_FILE_PATH.exists():
        with open(PROFILE_NAME_FILE_PATH) as f:
            profile_name = f.readline().strip()
    else:
        profile_name = SETTINGS_DEFAULT_NAME

    return profile_name


def get_regex(path: Path) -> Optional[re.Pattern]:
    if user_regex.match(path.name):
        return user_regex

    if char_regex.match(path.name):
        return char_regex


if __name__ == "__main__":
    parser = ArgumentParser(
        description="Replace other settings to provided or to latest updated in folder"
    )
    parser.add_argument("-f", "--file", type=str, default="")
    parser.add_argument("-o", "--open", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    if args.verbose:
        log.setLevel(logging.DEBUG)
        log.debug("Enabled verbose mode")

    if args.open:
        os.startfile(GAME_DIR_WINDOWS)
        exit()
        
    replace(args.file)
