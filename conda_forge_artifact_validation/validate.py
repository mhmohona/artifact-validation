import os
import tempfile
import subprocess
import traceback
import glob

import conda_package_handling.api

from .utils import split_pkg


def _validate_one(validate_yaml, pkg_dir):
    for file in validate_yaml["files"]:
        pkg_dir_file = os.path.join(pkg_dir, file)
        if "*" in file:
            pths = glob.glob(pkg_dir_file, recursive=True)
        elif os.path.isdir(pkg_dir_file):
            pths = glob.glob(os.path.join(pkg_dir_file, "**"), recursive=True)
        else:
            pths = [pkg_dir_file]

        for pth in pths:
            if os.path.exists(pth):
                return False, [pth.replace(pkg_dir, "$PREFIX")]

    return True, []


def download_and_validate(channel_url, subdir_pkg, validate_yamls):
    valid = True
    bad_pths = {}

    subdir, pkg = subdir_pkg.split(os.path.sep)
    _, output_name, _, _ = split_pkg(subdir_pkg)

    with tempfile.TemporaryDirectory(dir=os.environ.get("RUNNER_TEMP")) as tmpdir:
        try:
            # download
            subprocess.run(
                f"cd {tmpdir} && curl -s -L {channel_url}/{subdir_pkg} --output {pkg}",
                shell=True,
            )

            # unpack and validate
            if os.path.exists(f"{tmpdir}/{pkg}"):
                conda_package_handling.api.extract(f"{tmpdir}/{pkg}")

                if pkg.endswith(".tar.bz2"):
                    pkg_nm = pkg[: -len(".tar.bz2")]
                else:
                    pkg_nm = pkg[: -len(".conda")]

                pkg_dir = f"{tmpdir}/{pkg_nm}"

                for validate_name, validate_yaml in validate_yamls.items():
                    if output_name not in validate_yaml["allowed"]:
                        _valid, _bad_pths = _validate_one(
                            validate_yaml,
                            pkg_dir,
                            output_name,
                        )
                        valid = valid and _valid
                        if not _valid:
                            bad_pths[validate_name] = {
                                "valid": _valid,
                                "bad_files": sorted(_bad_pths),
                            }
            else:
                valid = False

        except Exception:
            traceback.print_exc()
            valid = False

    return valid, bad_pths
