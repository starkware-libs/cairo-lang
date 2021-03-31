#!/usr/bin/env python3

import argparse
import http.server
import json
import os
import socket
import socketserver
import sys
import urllib.parse

from starkware.cairo.lang.tracer.tracer_data import TracerData, WatchEvaluator, field_element_repr


def trace_runner(runner):
    if len(runner.segments.segment_sizes) != runner.segments.n_segments:
        runner.finalize_segments_by_effective_size()
    if not hasattr(runner, 'relocated_trace'):
        runner.relocate()

    # Print the non-relocated registers, the relocated values are available in the tracer.
    runner.print_info(relocated=False)

    memory = runner.relocated_memory
    trace = runner.relocated_trace

    run_tracer(
        TracerData(
            program=runner.program, memory=memory, trace=trace,
            program_base=runner.relocate_value(runner.program_base)))


class SimpleTCPServer(socketserver.TCPServer):
    def server_bind(self):
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(self.server_address)


def run_tracer(tracer_data: TracerData):
    # Change directory for the SimpleHTTPRequestHandler.
    os.chdir(os.path.abspath(os.path.dirname(__file__)))

    # Create a simple web server which allows loading *.js files and other static file as well as
    # a dynamically generated data.json file which is loaded using AJAX.
    class Handler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            parsed_path = urllib.parse.urlparse(self.path)
            query = urllib.parse.parse_qs(parsed_path.query)
            if parsed_path.path == '/data.json':
                # Create the returned json file.
                self.write_json({
                    'code': {
                        filename: input_file.to_html()
                        for filename, input_file in tracer_data.input_files.items()},
                    'trace': [
                        {'pc': entry.pc, 'ap': entry.ap, 'fp': entry.fp}
                        for entry in tracer_data.trace],
                    'memory': {
                        addr: field_element_repr(val, tracer_data.program.prime)
                        for addr, val in tracer_data.memory.items()},
                    'public_memory': tracer_data.public_memory,
                    'memory_accesses': tracer_data.memory_accesses,
                })
            elif parsed_path.path == '/eval.json':
                evaluator = WatchEvaluator(
                    tracer_data, entry=tracer_data.trace[int(query['step'][0])])
                self.write_json([evaluator.eval_suppress_errors(expr) for expr in query['expr']])
            else:
                super().do_GET()

        def write_json(self, json_obj):
            json_str = json.dumps(json_obj)

            try:
                self.send_response(200)
                self.send_header('Content-type', 'text/json')
                self.send_header('Content-Length', str(len(json_str)))
                self.end_headers()
                self.wfile.write(json_str.encode('utf8'))
            except BrokenPipeError:
                # Request was canceled.
                pass

    def start_server():
        port = 8100
        while True:
            try:
                return SimpleTCPServer(('localhost', port), Handler)
            except OSError:
                pass
            # port was not available. Try the next one.
            port += 1

    httpd = start_server()
    print('Running tracer on http://localhost:%d/' % httpd.server_address[1])
    print()
    httpd.serve_forever()


def main():
    parser = argparse.ArgumentParser(
        description='A tool to view the trace of a Cairo program execution.')
    parser.add_argument(
        '--program', type=str, required=True, help='A path to the program json file.')
    parser.add_argument(
        '--memory', type=str, required=True, help='A path to the memory file.')
    parser.add_argument(
        '--trace', type=str, required=True, help='A path to the trace file.')
    parser.add_argument(
        '--air_public_input', type=str, help='A path to the AIR public input file.')
    parser.add_argument(
        '--debug_info', type=str, help='A path to the run time debug info file.')

    args = parser.parse_args()

    tracer_data = TracerData.from_files(
        program_path=args.program,
        memory_path=args.memory,
        trace_path=args.trace,
        air_public_input=args.air_public_input,
        debug_info_path=args.debug_info,
    )

    run_tracer(tracer_data)
    return 0


if __name__ == '__main__':
    sys.exit(main())
