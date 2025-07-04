from tqdm import tqdm
import requests
import os


def download_file_with_progress(url, path):
    response = requests.get(url, stream=True)
    total_length = int(response.headers.get('content-length', 0))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as f, tqdm(
        total=total_length, unit='B', unit_scale=True, desc=os.path.basename(path)
    ) as pbar:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)
                pbar.update(len(chunk))
