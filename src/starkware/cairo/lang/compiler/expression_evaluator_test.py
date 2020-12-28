from starkware.cairo.lang.compiler.expression_evaluator import ExpressionEvaluator
from starkware.cairo.lang.compiler.parser import parse_expr


def test_eval_registers():
    ap = 5
    fp = 10
    prime = 13

    evaluator = ExpressionEvaluator(prime=prime, ap=ap, fp=fp, memory={})
    assert evaluator.eval(parse_expr('2 * ap + 3 * fp - 5')) == (2 * ap + 3 * fp - 5) % prime


def test_eval_with_types():
    ap = 5
    fp = 10
    prime = 13

    evaluator = ExpressionEvaluator(prime=prime, ap=ap, fp=fp, memory={})
    assert evaluator.eval(parse_expr('cast(ap, T*)')) == ap


def test_eval_registers_and_memory():
    ap = 5
    fp = 10
    prime = 13
    memory = {(2 * ap + 3 * fp - 5) % prime: 7, 7: 5, 6: 0}

    evaluator = ExpressionEvaluator(prime=prime, ap=ap, fp=fp, memory=memory)
    assert evaluator.eval(parse_expr('[2 * ap + 3 * fp - 5]')) == 7
    assert evaluator.eval(parse_expr('[[2 * ap + 3 * fp - 5]] + 3 * ap')) == \
        (memory[7] + 3 * ap) % prime
    assert evaluator.eval(parse_expr('[[[2 * ap + 3 * fp - 5]]+1]')) == 0
