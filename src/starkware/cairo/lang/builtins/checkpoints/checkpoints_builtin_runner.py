from typing import List

from starkware.cairo.lang.vm.builtin_runner import SimpleBuiltinRunner
from starkware.python.math_utils import safe_div

# Each sample consists of 2 cells (required pc and required fp).
CELLS_PER_SAMPLE = 2


class CheckpointsBuiltinRunner(SimpleBuiltinRunner):
    def __init__(self, name: str, included: bool, sample_ratio: int):
        self.sample_ratio = sample_ratio
        self.samples: List = []
        super().__init__(name, included, sample_ratio, CELLS_PER_SAMPLE)

    def finalize_segments(self, runner):
        memory = runner.vm.run_context.memory
        memory[self.stop_ptr] = 0
        memory[self.stop_ptr + 1] = 0
        super().finalize_segments(runner)

    def get_used_cells_and_allocated_size(self, runner):
        size = self.get_used_cells(runner)
        return size, size

    def sample(self, step, pc, fp):
        self.samples.append((step, pc, fp))

    def relocate(self, relocate_value):
        self.samples = [tuple(map(relocate_value, sample)) for sample in self.samples]

    def air_private_input(self, runner):
        return {self.name: [
            {
                'index': safe_div(step, self.sample_ratio),
                'pc': hex(pc),
                'fp': hex(fp)
            }
            for step, pc, fp in self.samples]}
