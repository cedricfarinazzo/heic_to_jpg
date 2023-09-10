import os
import sys
from pathlib import Path
import pyheif
from PIL import Image
import piexif
from tqdm import tqdm
import concurrent.futures


def heic_to_jpg(heic_file: Path) -> Path:
    heif_file_data = pyheif.read(heic_file)

    # Creation of image 
    image = Image.frombytes(
        heif_file_data.mode,
        heif_file_data.size,
        heif_file_data.data,
        "raw",
        heif_file_data.mode,
        heif_file_data.stride,
    )

    # Retrive the metadata
    exif_dict = None
    for metadata in heif_file_data.metadata or []:
        if metadata['type'] == 'Exif':
            exif_dict = piexif.load(metadata['data'])

    # PIL rotates the image according to exif info, so it's necessary to remove the orientation tag otherwise the image will be rotated again (1° time from PIL, 2° from viewer).
    exif_bytes = None
    if exif_dict:
        exif_dict['0th'][274] = 0
        exif_bytes = piexif.dump(exif_dict)

    jpg_file = heic_file.with_suffix(".jpg")
    image.save(jpg_file, "JPEG", exif=exif_bytes)
    
    stat = os.stat(heic_file)
    os.utime(jpg_file, (stat.st_atime, stat.st_mtime))

    heic_file.unlink()

    return jpg_file

def list_heic_recursive(path: Path) -> list[Path]:
    if path.is_file():
        if "heic" in path.suffix.lower():
            return [path]
        return []

    heic_files = []
    if path.is_dir():
        for child in path.iterdir():
            heic_files += list_heic_recursive(child)

    return heic_files

def main():
    FOLDER = sys.argv[1]

    heic_files = list_heic_recursive(Path(FOLDER))
    heic_files_len = len(heic_files)

    print(f"Found {heic_files_len} heic files")

    with tqdm(total=heic_files_len) as pbar:
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(heic_to_jpg, heic_file): heic_file for heic_file in heic_files}
            results = {}
            for future in concurrent.futures.as_completed(futures):
                arg = futures[future]
                results[arg] = future.result()
                print(f"{arg} => {results[arg]}")
                pbar.update(1)

if __name__ == '__main__':
    main()