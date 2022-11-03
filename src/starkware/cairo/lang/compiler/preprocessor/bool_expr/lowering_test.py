from starkware.cairo.lang.compiler.preprocessor.bool_expr.lowering_test_utils import (
    lower_and_format,
    verify_exception,
)


def test_lowers_single_and_without_else():
    code = """
func main() {
    let a = 10;
    let b = 12;
    if (a == 10 and b == 12) {
        let x = a + b;
    }
    ret;
}
"""
    assert (
        lower_and_format(code)
        == """\
func main() {
    let a = 10;
    let b = 12;
    if (a == 10) {
        if (b == 12) {
            let x = a + b;
        }
    }
    ret;
}
"""
    )


def test_lowers_nested_ifs():
    code = """
func main() -> (res: felt) {
    if (1 == 2 and 3 == 4) {
        if (5 == 6) {
            if (7 == 8 and 9 == 10) {
                return (res=1);
            }
            return (res=2);
        }
        return (res=3);
    }
    return (res=4);
}
"""
    assert (
        lower_and_format(code)
        == """\
func main() -> (res: felt) {
    if (1 == 2) {
        if (3 == 4) {
            if (5 == 6) {
                if (7 == 8) {
                    if (9 == 10) {
                        return (res=1);
                    }
                }
                return (res=2);
            }
            return (res=3);
        }
    }
    return (res=4);
}
"""
    )


def test_lowers_nested_and_without_else():
    code = """
func main() {
    let a = 10;
    let b = 12;
    let c = 14;
    if (a == 10 and b == 12 and c == 14) {
        let x = a + b + c;
    }
    ret;
}
"""
    assert (
        lower_and_format(code)
        == """\
func main() {
    let a = 10;
    let b = 12;
    let c = 14;
    if (a == 10) {
        if (b == 12) {
            if (c == 14) {
                let x = a + b + c;
            }
        }
    }
    ret;
}
"""
    )


def test_else_is_not_supported():
    verify_exception(
        """
func main() {
    let a = 10;
    let b = 12;
    if (a == 10 and b == 12) {
        let x = a + b;
    } else {
        let x = a - b;
    }
    ret;
}
""",
        """
file:?:?: Else blocks are not supported with boolean logic expressions yet.
    if (a == 10 and b == 12) {
    ^^
""",
    )
