#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
# Copyright 2023-2024 NXP
#
# SPDX-License-Identifier: BSD-3-Clause

"""Test functionality of nxpmemcfg application."""

import os

import pytest

from spsdk.apps import nxpmemcfg
from spsdk.memcfg.memcfg import MemoryConfig
from tests.cli_runner import CliRunner


def test_app_help(cli_runner: CliRunner):
    """Simple test that application works at least with help."""
    ret = cli_runner.invoke(nxpmemcfg.main, "")
    assert "nxpmemcfg" in ret.output
    assert "export" in ret.output
    assert "parse" in ret.output


@pytest.mark.parametrize(
    "family,peripheral,checks_output,not_in_output",
    [
        (
            None,
            None,
            ["lpc55s3x", "rw61x", "Opt0: 0xC1020026, Opt1: 0x000000A1", "Opt0: 0xD0000003"],
            ["invalid"],
        ),
        ("rt118x", None, ["rt118x", "flexspi_nand"], ["lpc55s3x"]),
        ("rt118x", "flexspi_nor", ["rt118x"], ["lpc55s3x", "flexspi_nand"]),
    ],
)
def test_app_family_info(cli_runner: CliRunner, family, peripheral, checks_output, not_in_output):
    """Test of family info command."""
    cmd = "family-info"
    if family:
        cmd += f" -f {family}"
    if peripheral:
        cmd += f" -p {peripheral}"
    ret = cli_runner.invoke(nxpmemcfg.main, cmd)

    for check in checks_output:
        assert check in ret.output

    for check in not_in_output:
        assert check not in ret.output


@pytest.mark.parametrize(
    "family,peripheral,ow",
    [
        ("rt118x", "flexspi_nor", [0xC000_0001]),
        ("rt118x", "flexspi_nor", [0xC100_0007, 0x0000_0001]),
        ("rt118x", "flexspi_nand", [0xC1020026, 0x000000C2]),
        ("rt118x", "sd", [0xD0000002]),
        ("lpc55s3x", "flexspi_nor", [0xC100_0007, 0x0000_0001]),
    ],
)
def test_app_parse_export(cli_runner: CliRunner, tmpdir, family, peripheral, ow):
    """Test of family info command."""
    cmd = f"parse -f {family} -p {peripheral} "
    for x in ow:
        cmd += f"-w {str(x)} "
    cfg_file = os.path.join(tmpdir, "memcfg.yaml").replace("\\", "/")
    cmd += f"-o {cfg_file}"
    ret = cli_runner.invoke(nxpmemcfg.main, cmd)
    assert ret.exit_code == 0

    ret = cli_runner.invoke(nxpmemcfg.main, f"export -c {cfg_file}")

    assert ret.exit_code == 0
    for x in ow:
        assert f"0x{x:08X}" in ret.output


def test_app_parse_export_all(cli_runner: CliRunner, tmpdir):
    """Test of family info command."""
    all_known = MemoryConfig.get_all_known_option_words()
    for peripheral, p_db in all_known.items():
        for manufacturer, man_db in p_db.items():
            for chip_name, chip_db in man_db.items():
                for interface, ow in chip_db.items():
                    cmd = f"parse -f rt118x -p {peripheral} "
                    for x in ow:
                        cmd += f"-w {str(x)} "
                    cfg_file = os.path.join(
                        tmpdir, f"{manufacturer}_{chip_name}_{interface}.yaml"
                    ).replace("\\", "/")
                    cmd += f"-o {cfg_file}"
                    ret = cli_runner.invoke(nxpmemcfg.main, cmd)
                    assert ret.exit_code == 0

                    ret = cli_runner.invoke(nxpmemcfg.main, f"export -c {cfg_file}")

                    assert ret.exit_code == 0
                    for x in ow:
                        assert f"0x{x:08X}" in ret.output


@pytest.mark.parametrize("family", MemoryConfig.get_supported_families())
def test_get_templates(cli_runner: CliRunner, family, tmpdir: str):
    """Simple test that application works at least with help."""
    output = f"{tmpdir}".replace("\\", "/")
    ret = cli_runner.invoke(nxpmemcfg.main, f"get-templates -f {family} -o {output}")
    assert ret.exit_code == 0


@pytest.mark.parametrize(
    "family,instance,interface,chip_name,fcb,output_checks",
    [
        (
            "rt118x",
            1,
            "quad_spi",
            "W25QxxxJV",
            True,
            [
                "fill-memory 0x1FFE0000 4 0xCF900001",
                "fill-memory 0x1FFE0000 4 0xCF900001",
                "fill-memory 0x1FFE0000 4 0xC0000207",
                "configure-memory 9 0x1FFE0000",
                "fill-memory 0x1FFE0000 4 0xF000000F",
                "read-memory",
            ],
        ),
        (
            "rt118x",
            2,
            "quad_spi",
            "W25N01G",
            True,
            [
                "fill-memory 0x1FFE0000 4 0xCF900002",
                "fill-memory 0x1FFE0000 4 0xC1010026",
                "fill-memory 0x1FFE0004 4 0x000000EF",
                "configure-memory 257 0x1FFE0000",
                "#FCB read back is supported just only for",
            ],
        ),
        (
            "rt5xx",
            0,
            "quad_spi",
            "W25QxxxJV",
            True,
            [
                "fill-memory 0x0010C000 4 0xCF900000",
                "fill-memory 0x0010C000 4 0xC0000207",
                "configure-memory 9 0x0010C000",
                "fill-memory 0x0010C000 4 0xF000000F",
                "read-memory",
            ],
        ),
    ],
)
def test_blhost_script(
    cli_runner: CliRunner,
    family: str,
    instance: int,
    interface: str,
    chip_name: str,
    fcb: bool,
    output_checks: str,
    tmpdir: str,
):
    """Simple test that application works at least with help."""
    output = f"{tmpdir}".replace("\\", "/")
    output_cfg = output + "/cfg.yaml"
    output_fcb = output + "/fcb.bin"
    ret = cli_runner.invoke(
        nxpmemcfg.main, f"parse -f {family} -m {chip_name} -i {interface} -o {output_cfg}"
    )
    assert ret.exit_code == 0
    ret = cli_runner.invoke(
        nxpmemcfg.main,
        f"blhost-script -c {output_cfg}{f' -ix {str(instance)}' if instance is not None else ''} {f' --fcb {output_fcb}' if fcb else ''}",
    )
    assert ret.exit_code == 0
    for x in output_checks:
        assert x in ret.output


@pytest.mark.parametrize("family", MemoryConfig.get_supported_families())
def test_app_blhost_script_flexspi_nor(cli_runner: CliRunner, family: str, tmpdir):
    """Test of blhost script generation for all chips command."""
    if MemoryConfig.get_peripheral_cnt(family, "flexspi_nor") > 0:
        output = f"{tmpdir}".replace("\\", "/")
        output_cfg = output + "/cfg.yaml"
        output_fcb = output + "/fcb.bin"
        ret = cli_runner.invoke(
            nxpmemcfg.main, f"parse -f {family} -m W25QxxxJV -i quad_spi -o {output_cfg}"
        )
        assert ret.exit_code == 0
        instances = MemoryConfig.get_peripheral_instances(family, "flexspi_nor")
        ret = cli_runner.invoke(
            nxpmemcfg.main,
            f"blhost-script -c {output_cfg}{f' -ix {instances[0]}' if len(instances) > 1 else ''} --fcb {output_fcb}",
        )
        assert ret.exit_code == 0
