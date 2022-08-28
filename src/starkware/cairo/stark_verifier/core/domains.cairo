// Information about the domains that are used in the stark proof.
struct StarkDomains {
    // Log2 of the evaluation domain size.
    log_eval_domain_size: felt,
    // The evaluation domain size.
    eval_domain_size: felt,
    // The generator of the evaluation domain (a primitive root of unity of order eval_domain_size).
    eval_generator: felt,
    // Log2 of the trace domain size.
    log_trace_domain_size: felt,
    // The trace domain size.
    trace_domain_size: felt,
    // The generator of the trace domain (a primitive root of unity of order trace_domain_size).
    trace_generator: felt,
}
