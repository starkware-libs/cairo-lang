import asyncio
import sys
from typing import List, Union


async def async_check_output(args: Union[str, List[str]], shell: bool = False, cwd=None, env=None):
    """
    An async equivalent to subprocess.check_output().
    """
    if shell:
        assert isinstance(args, str), "args must be a string where shell=True."
        # Pass '-e' to stop after failure if args consists of multiple commands.
        args = ["bash", "-e", "-c", args]
    proc = await asyncio.create_subprocess_exec(
        *args,
        cwd=cwd,
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout_data, stderr_data = await proc.communicate()
    decoded_stderr = stderr_data.decode()
    print(decoded_stderr, file=sys.stderr)
    assert (
        proc.returncode == 0
    ), f"""\
stderr: {decoded_stderr}
stdout: {stdout_data.decode()}
"""
    return stdout_data
