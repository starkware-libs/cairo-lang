from starkware.cairo.lang.compiler.preprocessor.bool_expr.lowering_test_utils import (
    lower_and_format,
    verify_exception,
)


def test_lowers_single_and_without_else():
    code = """
func main():
    let a = 10
    let b = 12
    if a == 10 and b == 12:
        let x = a + b
    end
    ret
end
"""
    assert (
        lower_and_format(code)
        == """\
func main():
    let a = 10
    let b = 12
    if a == 10:
        if b == 12:
            let x = a + b
        end
    end
    ret
end
"""
    )


def test_lowers_nested_and_without_else():
    code = """
func main():
    let a = 10
    let b = 12
    let c = 14
    if a == 10 and b == 12 and c == 14:
        let x = a + b + c
    end
    ret
end
"""
    assert (
        lower_and_format(code)
        == """\
func main():
    let a = 10
    let b = 12
    let c = 14
    if a == 10:
        if b == 12:
            if c == 14:
                let x = a + b + c
            end
        end
    end
    ret
end
"""
    )


def test_else_is_not_supported():
    verify_exception(
        """
func main():
    let a = 10
    let b = 12
    if a == 10 and b == 12:
        let x = a + b
    else:
        let x = a - b
    end
    ret
end
""",
        """
file:?:?: Else blocks are not supported with boolean logic expressions yet.
    if a == 10 and b == 12:
    ^^
""",
    )
