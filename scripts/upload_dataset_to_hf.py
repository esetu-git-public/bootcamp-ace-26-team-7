import os
import zipfile
import tempfile
import argparse
from huggingface_hub import HfApi, login

REPO_ID = "amruthjakku/surface-crack-detection-model"
RAW_DATA_DIR = "data/raw"


def zip_data(data_dir, output_zip):

    if not os.path.isdir(data_dir):
        print(f"Error: Data directory '{data_dir}' not found.")
        print("Run this script from the project root (e.g., bootcamp/).")
        return False

    items = os.listdir(data_dir)
    if not items:
        print(f"Error: Data directory '{data_dir}' is empty.")
        return False

    print(f"Zipping contents of '{data_dir}/' ({len(items)} items) to '{output_zip}'...")
    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(data_dir):
            for fn in files:
                file_path = os.path.join(root, fn)
                arcname = os.path.relpath(file_path, start=os.path.dirname(data_dir))
                zf.write(file_path, arcname)
    print(f"Created {output_zip} ({os.path.getsize(output_zip) / 1024 / 1024:.1f} MB)")
    return True


def upload_to_hf(zip_path, token):

    print(f"Logging into HuggingFace Hub...")
    login(token=token)
    api = HfApi()
    api.upload_file(
        path_or_fileobj=zip_path,
        path_in_repo="dataset.zip",
        repo_id=REPO_ID,
        repo_type="model",
    )
    print(f"Uploaded '{zip_path}' as 'dataset.zip' to {REPO_ID}")


def main():
    parser = argparse.ArgumentParser(description="Upload dataset to HuggingFace Hub for auto-download in Colab.")
    parser.add_argument("--token", required=True, help="HuggingFace API token (write access)")
    parser.add_argument("--data-dir", default=RAW_DATA_DIR, help=f"Path to raw data directory (default: {RAW_DATA_DIR})")
    args = parser.parse_args()

    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        zip_path = tmp.name

    try:
        if zip_data(args.data_dir, zip_path):
            upload_to_hf(zip_path, args.token)
    finally:
        if os.path.exists(zip_path):
            os.remove(zip_path)
            print(f"Cleaned up temp file '{zip_path}'.")

    print("Done. Dataset is now available for auto-download in Colab notebooks.")


if __name__ == "__main__":
    main()
