from io import TextIOWrapper
import subprocess
import json
import sys
from typing import Dict, Any, List

OVERRIDE_PACKAGES = {}
IGNORE_PACKAGES = ["common", "cli", "nidus-mcp", "mcp-server"]

SAFE_LICENSES = [
    "Apache Software License",
    "Apache-2.0",
    "Mozilla Public License 2.0 (MPL 2.0)",
    "Apache-2.0 OR BSD-3-Clause",
    "Apache 2.0 License",
    "Apache Software License; BSD License",
    "MIT",
    "MIT License",
    "MIT License; Mozilla Public License 2.0 (MPL 2.0)",
    "ISC License (ISCL)",
    "PSF-2.0",
    "BSD License",
    "BSD-3-Clause",
]


def fetch_license_data() -> List[Dict[str, Any]]:
    """pip-licensesを使用してJSON形式で依存関係を取得する"""
    command = ["pip-licenses", "--format=json", "--with-license-file"]
    if IGNORE_PACKAGES:
        command.append("--ignore-packages")
        command.extend(IGNORE_PACKAGES)
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error: pip-licenses failed. {e.stderr}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print(
            "Error: 'pip-licenses' is not installed. Please run 'pip install pip-licenses'.",
            file=sys.stderr,
        )
        sys.exit(1)


def generate_notices(output_path: str = "THIRD-PARTY-NOTICES.txt"):
    """ライセンス通知ファイルを生成する"""
    data = fetch_license_data()

    with open(output_path, "w", encoding="utf-8") as f:
        # ヘッダーの書き込み
        f.write(
            (
                "THIRD-PARTY SOFTWARE NOTICES AND INFORMATION\n\n"
                "This project incorporates components from the projects listed below.\n\n"
            )
        )

        f.write(
            "================================================================================\n\n"
        )

        for entry in data:
            write_entry(f, entry)

    print(f"Done! Created: {output_path}")


def write_entry(f: TextIOWrapper, entry: Dict[str, Any]):
    name = entry["Name"]
    version = entry["Version"]
    override = OVERRIDE_PACKAGES.get(name.lower())
    license_name = override["License"] if override else entry.get("License", "Unknown")
    license_text = (
        override["LicenseText"]
        if override
        else entry.get("LicenseText", "No license text found.")
    )

    # 各パッケージ情報の書き込み
    f.write(f"Package: {name}\n")
    f.write(f"Version: {version}\n")
    f.write(f"License: {license_name}\n")
    f.write("-" * 40 + "\n")
    f.write(f"{license_text.strip()}\n")
    f.write("\n" + "=" * 60 + "\n\n")
    if license_name not in SAFE_LICENSES:
        print(f"{name} ({version} | {license_name})")


if __name__ == "__main__":
    generate_notices()
