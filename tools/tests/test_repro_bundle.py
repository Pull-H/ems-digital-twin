import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile

from tools import repro_bundle


class ReproBundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.archive = self.root / "evidence.zip"

    def write_archive(self, path, content=b"example", manifest_content=None):
        manifest = {
            "schema_version": 1,
            "snapshot_id": repro_bundle.SNAPSHOT,
            "files": [{"path": path, "size": len(content), "sha256": hashlib.sha256(content).hexdigest()}],
        }
        with ZipFile(self.archive, "w") as bundle:
            bundle.writestr(path, content)
            bundle.writestr(repro_bundle.MANIFEST_NAME, json.dumps(manifest_content or manifest))

    def test_valid_archive_installs_only_under_destination(self):
        path = f"data/nyc_ems/{repro_bundle.SNAPSHOT}/raw/sample.json.gz"
        self.write_archive(path)
        repro_bundle.install(self.archive, self.root / "install")
        self.assertEqual((self.root / "install" / path).read_bytes(), b"example")
        with self.assertRaises(FileExistsError):
            repro_bundle.install(self.archive, self.root / "install")

    def test_tampered_file_is_rejected(self):
        path = f"data/nyc_ems/{repro_bundle.SNAPSHOT}/raw/sample.json.gz"
        self.write_archive(path, content=b"tampered", manifest_content={
            "schema_version": 1,
            "snapshot_id": repro_bundle.SNAPSHOT,
            "files": [{"path": path, "size": 8, "sha256": "0" * 64}],
        })
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            repro_bundle.inspect(self.archive)

    def test_path_traversal_is_rejected(self):
        self.write_archive(f"data/nyc_ems/{repro_bundle.SNAPSHOT}/../outside.txt")
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            repro_bundle.inspect(self.archive)


if __name__ == "__main__":
    unittest.main()
