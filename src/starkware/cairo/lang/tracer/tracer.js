/*
  The number of the current step being viewed in the tracer.
*/
var current_step;

var trace;
var memory;
var memory_accesses;

/*
  A list of objects {watch_expr: ..., watch_result: ...} where watch_expr is the <input> element
  and watch_result is the result <span> element.
*/
var watch_exprs = [];

/*
  The maximum number of entries shown in the stack trace.
*/
const MAX_STACK_TRACE = 100;

function load_json() {
    $.getJSON('data.json', function (data) {
        trace = data.trace;
        memory = data.memory;
        memory_accesses = data.memory_accesses;
        for (const filename in data.code) {
            $('#code_div')
                .append($('<div>').addClass('filename').text(filename))
                .append($('<div>').html(data.code[filename]));
        }
        $('#slider_div').append(create_slider());
        $('#memory_div').append(create_memory_table());
        $('#watch_table').append(create_watch_row());
        mark_public_memory(data.public_memory);
        goto_step(0);

        $('.instruction').dblclick(toggle_breakpoint);
        $('.mem_row').dblclick(toggle_breakpoint);
    });
}

/*
  Adds a slider that tracks the progress of the program.
*/
function create_slider() {
    const slider = $('<input>').attr({
        id: 'slider',
        type: 'range',
        min: 0,
        max: trace.length - 1,
        value: 0,
    });

    slider[0].oninput = function () {
        goto_step(parseInt($('#slider').val()));
    };

    return slider;
}

function create_memory_table() {
    const table = $('<table>').addClass('table_with_border');
    for (const addr in memory) {
        table.append($('<tr>')
            .attr({ id: 'mem_row' + addr })
            .addClass('mem_row')
            .append($('<td>').append($('<span>')
                .attr({ id: 'mem_info' + addr })
                .addClass('mem_info')))
            .append($('<td>').text(addr))
            .append($('<td>').text(memory[addr]))
        );
    }
    return table;
}

function mark_public_memory(public_memory) {
    for (const addr of public_memory) {
        $('#mem_row' + addr).addClass('public_memory');
    }
}

function update_current_instruction_view() {
    const entry = trace[current_step];
    const pc = entry.pc;
    const ap = entry.ap;
    const fp = entry.fp;

    $('.instruction').removeClass('current_instruction');
    $('.inst' + pc).addClass('current_instruction');
    $('#pc').text(pc);
    $('#ap').text(ap);
    $('#fp').text(fp);

    const mem_accesses = memory_accesses[current_step];
    $('#dst_addr').text(mem_accesses.dst);
    $('#op0_addr').text(mem_accesses.op0);
    $('#op1_addr').text(mem_accesses.op1);

    $('.mem_row').removeClass('current_pc_mem');
    $('#mem_row' + pc).addClass('current_pc_mem');

    $('.mem_info').text('');
    $('#mem_info' + ap).append('ap ');
    $('#mem_info' + fp).append('fp ');

    update_stack_trace_view();

    if ($('#slider').val() != current_step) {
        $('#slider').val(current_step);
    }

    scrollIntoViewIfNeeded($('.inst' + pc)[0]);

    if ($('#memory_follow').val() == 'pc') {
        scrollIntoViewIfNeeded($('#mem_row' + pc)[0]);
    } else if ($('#memory_follow').val() == 'ap') {
        scrollIntoViewIfNeeded($('#mem_row' + ap)[0]);
    } else if ($('#memory_follow').val() == 'fp') {
        scrollIntoViewIfNeeded($('#mem_row' + fp)[0]);
    }

    update_watch();
}

function scrollIntoViewIfNeeded(target) {
    if (target === undefined) {
        return;
    }

    const rect = target.getBoundingClientRect();
    const scrollParent = getScrollParent(target);
    const scrollParentRect = scrollParent.getBoundingClientRect();
    if (rect.bottom > scrollParentRect.bottom) {
        // Scroll down.
        const scrollMargin = 64;
        const targetBottom = scrollParent.scrollTop + rect.bottom;
        scrollParent.scrollTo({
            top: targetBottom - scrollParent.clientHeight + scrollMargin,
            behavior: 'smooth',
        });
    } else if (rect.top < scrollParentRect.top) {
        // Scroll up.
        const scrollMargin = 32;
        const targetTop = scrollParent.scrollTop + rect.top;
        scrollParent.scrollTo({
            top: targetTop - scrollMargin,
            behavior: 'smooth',
        });
    }
}

function getScrollParent(node) {
    node = node.parentNode;
    while (getComputedStyle(node)['overflow-y'] != 'scroll') {
        node = node.parentNode;
    }
    return node;
}

function update_stack_trace_view() {
    const entry = trace[current_step];
    const initial_fp = trace[0].fp;

    $('.mem_row').css('border-top', '');

    const stack_trace = $('#stack_trace');
    stack_trace
        .empty()
        .append($('<tr>')
            .append($('<th>').append('fp'))
            .append($('<th>').append('return pc')));

    var fp = entry.fp;
    for (var i = 0; i < MAX_STACK_TRACE && fp != initial_fp; i++) {
        const pc = memory[fp - 1];
        stack_trace.append(create_stack_trace_row(fp, pc));
        $('#mem_row' + fp).css('border-top', '2px black solid');
        fp = memory[fp - 2];
    }
}

function create_stack_trace_row(fp, pc) {
    const fp_cell = $('<td>').append(fp);
    const pc_cell = $('<td>').append(pc);
    const row = $('<tr>')
        .append(fp_cell)
        .append(pc_cell);

    pc_cell.mouseenter(function () {
        $('.inst' + pc).addClass('highlight_instruction');
    });
    pc_cell.mouseleave(function () {
        $('.inst' + pc).removeClass('highlight_instruction');
    });

    return row;
}

function create_watch_row() {
    const watch_expr = $('<input>').attr({ type: 'text' });
    const watch_result = $('<span>');

    watch_exprs.push({ watch_expr: watch_expr, watch_result: watch_result });

    watch_expr.keyup(function (event) {
        if (event.key == 'Enter') {
            update_watch();
        }
    });

    const n_watches = watch_exprs.length;
    watch_expr.change(function (event) {
        // Add new watch if needed.
        if (watch_expr.val() != '' && watch_exprs.length == n_watches) {
            $('#watch_table').append(create_watch_row());
        }

        update_watch();
    });

    // Make sure navigation keys (s, n, ...) will not work when watch_expr is focused.
    watch_expr.keypress(function (event) {
        event.stopPropagation();
    });

    return $('<tr>')
        .append($('<td>')
            .append(watch_expr))
        .append($('<td>')
            .append(watch_result));
}

var update_watch_ajax = { abort: function () { } };

function update_watch() {
    var query_str = 'eval.json?step=' + encodeURIComponent(current_step)
    for (const entry of watch_exprs) {
        const expr_txt = entry.watch_expr.val();
        query_str += '&expr=' + encodeURIComponent(expr_txt == '' ? 'null' : expr_txt);
    }
    // Abort previous AJAX request if exists.
    update_watch_ajax.abort();
    update_watch_ajax = $.getJSON(query_str, function (data) {
        for (var idx = 0; idx < data.length; ++idx) {
            watch_exprs[idx].watch_result.text(data[idx]);
        }
    });
}

/*
  Clears the text selection in the window.
  This function was copied from
  https://stackoverflow.com/questions/880512/prevent-text-selection-after-double-click.
*/
function clearSelection() {
    if (document.selection && document.selection.empty) {
        document.selection.empty();
    } else if (window.getSelection) {
        var sel = window.getSelection();
        sel.removeAllRanges();
    }
}

function toggle_breakpoint(event) {
    $(this).toggleClass('breakpoint');
    clearSelection();
    event.stopPropagation();
}

function has_breakpoint(step) {
    return $('.inst' + trace[step].pc).hasClass('breakpoint') ||
        $('#mem_row' + memory_accesses[step].dst).hasClass('breakpoint') ||
        $('#mem_row' + memory_accesses[step].op0).hasClass('breakpoint') ||
        $('#mem_row' + memory_accesses[step].op1).hasClass('breakpoint');
}

function goto_step(i) {
    // Update global variable.
    current_step = i;
    update_current_instruction_view();
}

function step() {
    if (current_step < trace.length - 1) {
        goto_step(current_step + 1);
    }
}

function previous_step() {
    if (current_step > 0) {
        goto_step(current_step - 1);
    }
}

function step_over() {
    const current_fp = trace[current_step].fp;
    for (var i = current_step + 1; i < trace.length; i++) {
        if (trace[i].fp == current_fp || has_breakpoint(i)) {
            goto_step(i);
            return;
        }
    }
}

function previous_step_over() {
    const current_fp = trace[current_step].fp;
    for (var i = current_step - 1; i >= 0; i--) {
        if (trace[i].fp == current_fp) {
            goto_step(i);
            return;
        }
    }
}

function step_out() {
    const current_fp = trace[current_step].fp;
    const previous_fp = memory[current_fp - 2];
    for (var i = current_step + 1; i < trace.length; i++) {
        if (trace[i].fp == previous_fp) {
            goto_step(i);
            return;
        }
    }
}

function next_breakpoint() {
    for (var i = current_step + 1; i < trace.length; i++) {
        if (has_breakpoint(i)) {
            goto_step(i);
            return;
        }
    }
}

function previous_breakpoint() {
    const current_fp = trace[current_step].fp;
    for (var i = current_step - 1; i >= 0; i--) {
        if (has_breakpoint(i)) {
            goto_step(i);
            return;
        }
    }
}

$(document).ready(function () {
    load_json();
});

$(document).keypress(function (event) {
    if (event.key == 's') {
        step();
        event.stopPropagation();
    }
    if (event.key == 'S') {
        previous_step();
        event.stopPropagation();
    }
    if (event.key == 'n') {
        step_over();
        event.stopPropagation();
    }
    if (event.key == 'N') {
        previous_step_over();
        event.stopPropagation();
    }
    if (event.key == 'o') {
        step_out();
        event.stopPropagation();
    }
    if (event.key == 'b') {
        next_breakpoint();
        event.stopPropagation();
    }
    if (event.key == 'B') {
        previous_breakpoint();
        event.stopPropagation();
    }
});
