import importlib.util
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

spec = importlib.util.spec_from_file_location(
    "updater", Path(__file__).resolve().parents[1] / "scripts/update.py"
)
u = importlib.util.module_from_spec(spec)
spec.loader.exec_module(u)


def block(version, digest="01" * 32, package=None, arch="amd64"):
    package = package or u.PACKAGE
    return (
        f"Package: {package}\nArchitecture: {arch}\nVersion: {version}\n"
        f"Filename: pool/main/{package[0]}/{package}/{package}_{version}_{arch}.deb\nSHA256: {digest}\n"
    )


class UpdateTests(unittest.TestCase):
    def test_newest_version_is_not_index_order_or_lexical_order(self):
        data = "\n".join([block("2.9.0"), block("2.100.0"), block("2.10.0")])
        self.assertEqual(u.select_release(data)[0], "2.100.0")

    def test_exact_package_and_architecture(self):
        data = "\n".join(
            [
                block("2.0"),
                block("99.0", package=u.PACKAGE + "-other"),
                block("98.0", arch="arm64"),
            ]
        )
        self.assertEqual(u.select_release(data)[0], "2.0")

    def test_missing_package(self):
        with self.assertRaises(ValueError):
            u.select_release(block("1.0", arch="arm64"))

    def test_bad_metadata(self):
        for data in [
            block("1.0", digest="bad"),
            block("1.0;bad"),
            block("1.0").replace("pool/main/", "../"),
        ]:
            with self.subTest(data=data), self.assertRaises(ValueError):
                u.select_release(data)

    def test_conflicting_hashes(self):
        with self.assertRaises(ValueError):
            u.select_release(block("1.0") + "\n" + block("1.0", "02" * 32))

    def test_updates_are_idempotent_and_handle_repacked_versions(self):
        content = '  version = "1.0";\n    hash = "sha256-old";\n'
        release = u.select_release(block("2.0"))
        updated = u.update_content(content, release)
        self.assertIn('version = "2.0";', updated)
        self.assertEqual(u.update_content(updated, release), updated)
        repack = u.select_release(block("2.0", "02" * 32))
        self.assertNotEqual(u.update_content(updated, repack), updated)

    def test_no_downgrade(self):
        content = '  version = "2.0";\n    hash = "sha256-old";\n'
        with self.assertRaises(ValueError):
            u.update_content(content, u.select_release(block("1.0")))

    def test_unexpected_nix_layout_fails(self):
        with self.assertRaises(ValueError):
            u.update_content('version = "1.0";', u.select_release(block("2.0")))

    def test_candidate_rejects_code_injection_and_invalid_hashes(self):
        for release in [
            ('1.0"; builtins.abort "bad', "sha256-" + "A" * 43 + "="),
            ("2.0", "sha256-not-a-hash"),
            ("2.0", "sha256-" + "B" * 43 + "="),
        ]:
            with self.subTest(release=release), self.assertRaises(ValueError):
                u.update_content(
                    '  version = "1.0";\n    hash = "sha256-old";\n', release
                )

    def test_candidate_publication_applies_only_two_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = '# retained\n  version = "1.0";\n    hash = "sha256-old";\n'
            (root / "package.nix").write_text(original)
            release = u.select_release(block("2.0"))
            candidate = root / "candidate.json"
            candidate.write_text(json.dumps(dict(zip(("version", "hash"), release))))
            output = root / "outputs"
            with (
                mock.patch.object(u, "ROOT", root),
                mock.patch(
                    "sys.argv", ["update.py", "--apply-candidate", str(candidate)]
                ),
                mock.patch.dict(os.environ, {"GITHUB_OUTPUT": str(output)}),
                mock.patch.object(
                    u,
                    "fetch_index",
                    side_effect=AssertionError("Publication must not use the network"),
                ),
            ):
                u.main()
            self.assertEqual(
                (root / "package.nix").read_text(), u.update_content(original, release)
            )
            self.assertIn("has_update=true", output.read_text())
            candidate.write_text(
                json.dumps({"version": "2.0", "hash": release[1], "code": "unexpected"})
            )
            with (
                mock.patch.object(u, "ROOT", root),
                mock.patch(
                    "sys.argv", ["update.py", "--apply-candidate", str(candidate)]
                ),
                self.assertRaises(ValueError),
            ):
                u.main()

    def test_network_failure_retries_then_fails(self):
        with (
            mock.patch.object(
                u.urllib.request, "urlopen", side_effect=OSError("offline")
            ) as fetch,
            mock.patch.object(u.time, "sleep"),
            self.assertRaises(OSError),
        ):
            u.fetch_index()
        self.assertEqual(fetch.call_count, 4)

    def test_lock_refresh_is_restricted_to_forward_official_pin(self):
        original = json.loads(
            (Path(__file__).resolve().parents[1] / "flake.lock").read_text()
        )
        candidate = json.loads(json.dumps(original))
        locked = candidate["nodes"]["nixpkgs"]["locked"]
        locked["rev"] = "a" * 40
        locked["lastModified"] += 1
        u.validate_lock(original, candidate)
        bad = json.loads(json.dumps(candidate))
        bad["nodes"]["nixpkgs"]["locked"]["owner"] = "other-owner"
        with self.assertRaises(ValueError):
            u.validate_lock(original, bad)
        bad = json.loads(json.dumps(candidate))
        bad["nodes"]["nixpkgs"]["original"]["ref"] = "other-branch"
        with self.assertRaises(ValueError):
            u.validate_lock(original, bad)
        bad = json.loads(json.dumps(candidate))
        bad["nodes"]["nixpkgs"]["locked"]["lastModified"] = 0
        with self.assertRaises(ValueError):
            u.validate_lock(original, bad)
        bad = json.loads(json.dumps(candidate))
        bad["nodes"]["nixpkgs"]["locked"]["rev"] = "not-a-commit"
        with self.assertRaises(ValueError):
            u.validate_lock(original, bad)

    def test_dependency_candidate_round_trip_and_idempotence(self):
        original_lock = json.loads(
            (Path(__file__).resolve().parents[1] / "flake.lock").read_text()
        )
        updated_lock = json.loads(json.dumps(original_lock))
        updated_lock["nodes"]["nixpkgs"]["locked"]["rev"] = "a" * 40
        updated_lock["nodes"]["nixpkgs"]["locked"]["lastModified"] += 1
        release = u.select_release(block("2.0"))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = root / "package.nix"
            lock = root / "flake.lock"
            candidate = root / "candidate.json"
            original_package = '  version = "2.0";\n    hash = "' + release[1] + '";\n'
            package.write_text(original_package)
            lock.write_text(json.dumps(updated_lock))
            output = root / "outputs"
            with (
                mock.patch.object(u, "ROOT", root),
                mock.patch(
                    "sys.argv",
                    ["update.py", "--candidate", str(candidate), "--include-lock"],
                ),
                mock.patch.dict(os.environ, {"GITHUB_OUTPUT": str(output)}),
                mock.patch.object(u, "fetch_index", return_value=block("2.0")),
                mock.patch.object(
                    u.subprocess, "check_output", return_value=json.dumps(original_lock)
                ),
            ):
                u.main()
            self.assertIn("has_update=true", output.read_text())
            self.assertEqual(
                json.loads(candidate.read_text())["nixpkgs_lock"], updated_lock
            )
            lock.write_text(json.dumps(original_lock))
            output.unlink()
            with (
                mock.patch.object(u, "ROOT", root),
                mock.patch(
                    "sys.argv", ["update.py", "--apply-candidate", str(candidate)]
                ),
                mock.patch.dict(os.environ, {"GITHUB_OUTPUT": str(output)}),
                mock.patch.object(
                    u,
                    "fetch_index",
                    side_effect=AssertionError("Publication must be offline"),
                ),
            ):
                u.main()
                u.main()
            self.assertEqual(json.loads(lock.read_text()), updated_lock)
            self.assertEqual(package.read_text(), original_package)
            self.assertTrue(
                output.read_text().endswith("has_update=false\nversion=2.0\n")
            )


if __name__ == "__main__":
    unittest.main()
