"""
Tier 1B -- Codegen integration tests.

Generates C from the example Python definitions, compiles with gcc,
executes the binaries, and checks exit codes + output.

Requires: gcc in PATH.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import pytest


# Skip all tests if gcc is not available
GCC = shutil.which("gcc")
pytestmark = pytest.mark.skipif(GCC is None, reason="gcc not found in PATH")

EXAMPLES_DIR = os.path.join(os.path.dirname(__file__), "..", "examples")
SRC_DIR = os.path.join(os.path.dirname(__file__), "..", "src")


def _run(cmd, **kwargs):
    """Run a command and return the CompletedProcess."""
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=30,
        **kwargs,
    )


def _generate_and_compile_and_run(example_py, expected_output_substr=None):
    """
    Full pipeline:
      1. Run the Python example script to generate .c
      2. Compile the .c with gcc
      3. Execute the binary
      4. Assert exit code 0
      5. Optionally check output contains expected substring
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Copy the example into tmpdir so generated files land there
        example_name = os.path.splitext(os.path.basename(example_py))[0]
        c_file = os.path.join(tmpdir, f"{example_name}.c")
        exe_file = os.path.join(tmpdir, f"{example_name}.exe")

        # Generate C code by running the Python script
        env = os.environ.copy()
        env["PYTHONPATH"] = SRC_DIR + os.pathsep + env.get("PYTHONPATH", "")
        result = _run(
            [sys.executable, example_py],
            cwd=tmpdir,
            env=env,
        )
        assert result.returncode == 0, (
            f"Python generation failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )

        # Verify C file was generated
        assert os.path.exists(c_file), f"Expected {c_file} to be generated"

        # Compile with gcc
        result = _run([GCC, "-O2", "-o", exe_file, c_file])
        assert result.returncode == 0, (
            f"gcc compilation failed:\nstderr: {result.stderr}"
        )

        # Run the binary
        result = _run([exe_file])
        assert result.returncode == 0, (
            f"Binary exited with code {result.returncode}:\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

        # Check output if expected
        if expected_output_substr:
            assert expected_output_substr in result.stdout, (
                f"Expected '{expected_output_substr}' in output:\n{result.stdout}"
            )

        return result.stdout


class TestFibonacciIntegration:

    def test_generates_compiles_and_runs(self):
        example = os.path.join(EXAMPLES_DIR, "fibonacci.py")
        output = _generate_and_compile_and_run(example, "Done!")

    def test_fibonacci_sequence_correct(self):
        example = os.path.join(EXAMPLES_DIR, "fibonacci.py")
        output = _generate_and_compile_and_run(example)
        # Check some Fibonacci numbers appear in output
        for n in [0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233]:
            assert f"  {n}" in output or f" {n}\n" in output


class TestTinyBoyIntegration:

    def test_generates_compiles_and_runs(self):
        example = os.path.join(EXAMPLES_DIR, "tinyboy.py")
        output = _generate_and_compile_and_run(example, "ALL TESTS PASSED")

    def test_register_values(self):
        example = os.path.join(EXAMPLES_DIR, "tinyboy.py")
        output = _generate_and_compile_and_run(example)
        assert "A = 0x42" in output
        assert "RAM[0] = 0x08" in output


class TestTinySuperIntegration:

    def test_generates_compiles_and_runs(self):
        example = os.path.join(EXAMPLES_DIR, "tinysuper.py")
        output = _generate_and_compile_and_run(
            example, "DUAL-CPU PORT COMMUNICATION TEST PASSED"
        )

    def test_result_values(self):
        example = os.path.join(EXAMPLES_DIR, "tinysuper.py")
        output = _generate_and_compile_and_run(example)
        assert "RAM[0]    = 0x2A" in output
