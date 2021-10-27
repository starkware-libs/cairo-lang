import dataclasses
from typing import Any, Dict, List, Optional

from starkware.cairo.lang.compiler.ast.code_elements import (
    BuiltinsDirective,
    CodeElementFunction,
    CodeElementInstruction,
    LangDirective,
)
from starkware.cairo.lang.compiler.identifier_definition import StructDefinition
from starkware.cairo.lang.compiler.identifier_utils import get_struct_definition
from starkware.cairo.lang.compiler.preprocessor.preprocessor import (
    PreprocessedProgram,
    Preprocessor,
)
from starkware.cairo.lang.compiler.preprocessor.preprocessor_error import PreprocessorError
from starkware.cairo.lang.compiler.program import CairoHint
from starkware.cairo.lang.compiler.scoped_name import ScopedName
from starkware.cairo.lang.compiler.type_system import is_type_resolved
from starkware.starknet.compiler.external_wrapper import (
    ENTRY_POINT_DECORATORS,
    VIEW_DECORATOR,
    WRAPPER_SCOPE,
    get_abi_entry_type,
    get_external_decorator,
)
from starkware.starknet.definitions.constants import STARKNET_LANG_DIRECTIVE
from starkware.starknet.public.abi_structs import (
    prepare_type_for_abi,
    struct_definition_to_abi_entry,
)
from starkware.starknet.security.secure_hints import HintsWhitelist, InsecureHintError
from starkware.starknet.services.api.contract_definition import SUPPORTED_BUILTINS
from starkware.starkware_utils.subsequence import is_subsequence


@dataclasses.dataclass
class StarknetPreprocessedProgram(PreprocessedProgram):
    # JSON dict that contains information on the callable functions in the contract.
    abi: Any


class StarknetPreprocessor(Preprocessor):
    def __init__(self, **kwargs):
        kwargs = dict(kwargs)
        supported_decorators = kwargs.pop("supported_decorators", ENTRY_POINT_DECORATORS)

        # A whitelist of allowed hints.
        # None means that any hint is allowed.
        self.hint_whitelist: Optional[HintsWhitelist] = kwargs.pop("hint_whitelist", None)

        super().__init__(supported_decorators=supported_decorators, **kwargs)

        # JSON dict for the ABI output.
        self.abi: List[dict] = []
        # A map from external struct (short) name to its ABI entry.
        self.abi_structs: Dict[str, dict] = {}
        # A map from external struct (short) name to the fully qualified name.
        self.abi_structs_fullnames: Dict[str, ScopedName] = {}

    def visit_BuiltinsDirective(self, directive: BuiltinsDirective):
        super().visit_BuiltinsDirective(directive)
        assert self.builtins is not None

        if not is_subsequence(self.builtins, SUPPORTED_BUILTINS):
            raise PreprocessorError(
                f"{self.builtins} is not a subsequence of {SUPPORTED_BUILTINS}.",
                location=directive.location,
            )

    def visit_LangDirective(self, directive: LangDirective):
        if directive.name != STARKNET_LANG_DIRECTIVE:
            raise PreprocessorError(
                f"Unsupported %lang directive. Are you using the correct compiler?",
                location=directive.location,
            )

    def handle_missing_future_definition(self, name: ScopedName, location):
        if name.path[-1].startswith("__storage_var_temp"):
            return
        if name.path[-1].startswith("__calldata"):
            return
        if name.path[-1].startswith("__return_value"):
            return
        super().handle_missing_future_definition(name=name, location=location)

    def add_abi_entry(
        self,
        name: str,
        arg_struct_def: StructDefinition,
        ret_struct_def: StructDefinition,
        is_view: bool,
        entry_type: str,
    ):
        """
        Adds an entry describing the function to the contract's ABI.
        """
        inputs = []
        outputs = []
        for m_name, member in arg_struct_def.members.items():
            assert is_type_resolved(member.cairo_type)
            abi_type_info = prepare_type_for_abi(member.cairo_type)
            inputs.append(
                {
                    "name": m_name,
                    "type": abi_type_info.modified_type.format(),
                }
            )
            for struct_name in abi_type_info.structs:
                self.add_struct_to_abi(struct_name)
        for m_name, member in ret_struct_def.members.items():
            assert is_type_resolved(member.cairo_type)
            abi_type_info = prepare_type_for_abi(member.cairo_type)
            outputs.append(
                {
                    "name": m_name,
                    "type": abi_type_info.modified_type.format(),
                }
            )
            for struct_name in abi_type_info.structs:
                self.add_struct_to_abi(struct_name)
        res = {
            "name": name,
            "type": entry_type,
            "inputs": inputs,
            "outputs": outputs,
        }
        if is_view:
            res["stateMutability"] = "view"
        self.abi.append(res)

    def add_struct_to_abi(self, struct_name: ScopedName):
        """
        Adds the given struct (add all the structs mentioned in its members) to self.abi_structs.
        """

        struct_definition = get_struct_definition(
            struct_name=struct_name, identifier_manager=self.identifiers
        )

        short_name = struct_name.path[-1]

        if short_name in self.abi_structs:
            existing_full_name = self.abi_structs_fullnames[short_name]
            if existing_full_name != struct_name:
                raise PreprocessorError(
                    f"Found two external structs named {short_name}: "
                    f"{existing_full_name}, {struct_name}.",
                    location=struct_definition.location,
                )
            return

        abi_entry, inner_structs = struct_definition_to_abi_entry(
            struct_definition=struct_definition
        )

        self.abi_structs_fullnames[short_name] = struct_name
        self.abi_structs[short_name] = abi_entry

        # Visit the types of the inner structs recursively.
        for name in inner_structs:
            self.add_struct_to_abi(name)

    def get_program(self) -> StarknetPreprocessedProgram:
        program = super().get_program()
        return StarknetPreprocessedProgram(  # type: ignore
            **program.__dict__,
            abi=list(self.abi_structs.values()) + self.abi,
        )

    def visit_CodeElementFunction(self, elm: CodeElementFunction):
        super().visit_CodeElementFunction(elm)

        external_decorator = get_external_decorator(elm)
        if external_decorator is None or self.current_scope == WRAPPER_SCOPE:
            return

        # Add an entry to the ABI.
        arg_struct_def = self.get_struct_definition(
            name=ScopedName.from_string(elm.name) + CodeElementFunction.ARGUMENT_SCOPE,
            location=elm.identifier.location,
        )

        ret_struct_def = self.get_struct_definition(
            name=ScopedName.from_string(elm.name) + CodeElementFunction.RETURN_SCOPE,
            location=elm.identifier.location,
        )
        self.add_abi_entry(
            name=elm.name,
            arg_struct_def=arg_struct_def,
            ret_struct_def=ret_struct_def,
            is_view=external_decorator.name == VIEW_DECORATOR,
            entry_type=get_abi_entry_type(external_decorator_name=external_decorator.name),
        )

    def visit_CodeElementInstruction(self, elm: CodeElementInstruction):
        if self.hint_whitelist is not None:
            for hint, flow_tracking_data in self.next_instruction_hints:
                try:
                    self.hint_whitelist.verify_hint_secure(
                        hint=CairoHint(
                            code=hint.hint_code,
                            accessible_scopes=self.accessible_scopes,
                            flow_tracking_data=flow_tracking_data,
                        ),
                        reference_manager=self.flow_tracking.reference_manager,
                    )
                except InsecureHintError:
                    raise PreprocessorError(
                        """\
Hint is not whitelisted.
This may indicate that this library function cannot be used in StarkNet contracts.""",
                        location=hint.location,
                    )

        super().visit_CodeElementInstruction(elm)
