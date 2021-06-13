import asyncio
from typing import List, Union


async def async_check_output(args: Union[str, List[str]], shell: bool = False, cwd=None, env=None):
    """
    An async equivalent to subprocess.check_output().
    """
    if shell:
        assert isinstance(args, str), 'args must be a string where shell=True.'
        # Pass '-e' to stop after failure if args consists of multiple commands.
        args = ['bash', '-e', '-c', args]
    proc = await asyncio.create_subprocess_exec(
        *args, cwd=cwd, env=env, stdout=asyncio.subprocess.PIPE)
    return_code = await proc.wait()
    assert return_code == 0
    assert proc.stdout is not None
    return await proc.stdout.read()
