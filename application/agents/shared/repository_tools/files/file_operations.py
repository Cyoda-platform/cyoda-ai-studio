"""File saving and directory operations."""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def _save_file_to_disk(filename: str, content: str, target_dir: Path) -> bool:
    """Write a single file to disk.

    Args:
        filename: Name of the file to save (sanitized of path traversal).
        content: File content to write.
        target_dir: Directory to write file into.

    Returns:
        True if file was saved successfully, False otherwise.
    """
    # Sanitize filename (prevent directory traversal)
    safe_filename = Path(filename).name

    file_path = target_dir / safe_filename

    try:
        file_path.write_text(content, encoding="utf-8")
        logger.info(f"✅ Saved file: {file_path}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to save file {safe_filename}: {e}")
        return False


def _log_directory_debug_info(func_req_dir: Path, saved_files: list[str]) -> None:
    """Log debug information about the directory and saved files.

    Args:
        func_req_dir: Directory containing saved files.
        saved_files: List of filenames that were saved.
    """
    logger.info(f"   Saved files: {saved_files}")
    logger.info(f"   func_req_dir: {func_req_dir}")
    try:
        dir_contents = list(func_req_dir.iterdir())
        logger.info(f"   Directory contents: {[f.name for f in dir_contents]}")
    except Exception as e:
        logger.error(f"   Failed to list directory: {e}")


async def _save_all_files(files: list[dict[str, str]], target_dir: Path) -> list[str]:
    """Save all provided files to target directory.

    Args:
        files: List of file dictionaries with 'filename' and 'content' keys.
        target_dir: Directory to save files into.

    Returns:
        List of successfully saved filenames.
    """
    saved_files = []
    for file_info in files:
        if not isinstance(file_info, dict):
            logger.warning(f"⚠️ Skipping invalid file info (not a dict): {file_info}")
            continue

        filename = file_info.get("filename")
        content = file_info.get("content")

        if not filename or not content:
            logger.warning(f"⚠️ Skipping file with missing filename or content: {file_info}")
            continue

        if _save_file_to_disk(filename, content, target_dir):
            saved_files.append(filename)
        else:
            return []  # Fail on first error

    return saved_files
