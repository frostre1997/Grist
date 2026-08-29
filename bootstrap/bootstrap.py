#!/usr/bin/env python3
import sys
import re
import os

def parse_gr(filename):
    with open(filename, 'r') as f:
        src = f.read()

    # Extract daemon name
    daemon_match = re.search(r'daemon\s+(\w+)\s*\(', src)
    if not daemon_match:
        print("No daemon found")
        sys.exit(1)
    daemon_name = daemon_match.group(1)

    # Find intercept block
    intercept_match = re.search(
        r'intercept\s+(\w+)\s*\(([^)]*)\)\s*->\s*\w+\s*\{([^}]*)\}',
        src, re.DOTALL
    )
    if not intercept_match:
        print("No intercept found")
        sys.exit(1)

    func_name = intercept_match.group(1)
    params_str = intercept_match.group(2).strip()
    body = intercept_match.group(3).strip()

    # Parse parameters
    params = []
    if params_str:
        for p in params_str.split(','):
            parts = p.strip().split(':')
            if len(parts) == 2:
                params.append(parts[0].strip())

    # Generate C code
    c_code = f'''
#include <stdio.h>
#include <unistd.h>
#include <signal.h>
#include <string.h>

int running = 1;
void handle_sigterm(int s) {{ running = 0; }}

int {func_name}_intercept({', '.join([f'const char* {p}' for p in params])}) {{
    printf("intercepted: %s\\n", {params[0] if params else '""'});
    return 0;
}}

int main() {{
    signal(SIGTERM, handle_sigterm);
    printf("grind daemon started\\n");
    while (running) {{ sleep(1); }}
    return 0;
}}
'''
    return c_code

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 bootstrap/bootstrap.py <file.gr>")
        sys.exit(1)

    gr_file = sys.argv[1]
    c_code = parse_gr(gr_file)
    c_file = gr_file + '.c'
    with open(c_file, 'w') as f:
        f.write(c_code)

    out_file = gr_file + '.out'
    os.system(f'gcc -o {out_file} {c_file}')
    print(f'compiled: {out_file}')
