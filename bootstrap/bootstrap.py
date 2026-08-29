#!/usr/bin/env python3
import sys
import re
import os

class Parser:
    def __init__(self, src):
        self.src = src
        self.tokens = self.tokenize(src)
        self.idx = 0

    def tokenize(self, src):
        tokens = []
        i = 0
        n = len(src)
        while i < n:
            c = src[i]
            # skip whitespace
            if c in ' \t\n\r':
                i += 1
                continue
            # skip comments: (| ... |)
            if c == '(' and i+1 < n and src[i+1] == '|':
                i += 2
                while i < n and not (src[i] == '|' and i+1 < n and src[i+1] == ')'):
                    i += 1
                i += 2
                continue
            # string literal
            if c == '"':
                i += 1
                start = i
                while i < n and src[i] != '"':
                    if src[i] == '\\':
                        i += 2
                    else:
                        i += 1
                if i >= n:
                    raise SyntaxError("unclosed string")
                text = src[start:i]
                i += 1
                tokens.append(('string', text))
                continue
            # number
            if c.isdigit():
                start = i
                while i < n and src[i].isdigit():
                    i += 1
                tokens.append(('number', src[start:i]))
                continue
            # arrow -> 
            if c == '-' and i+1 < n and src[i+1] == '>':
                tokens.append(('punct', '->'))
                i += 2
                continue
            # identifier or keyword
            if c.isalpha() or c == '_':
                start = i
                while i < n and (src[i].isalnum() or src[i] == '_'):
                    i += 1
                ident = src[start:i]
                tokens.append(('ident', ident))
                continue
            # assignment ≈
            if c == '≈':
                tokens.append(('assign', '≈'))
                i += 1
                continue
            # single punctuation
            if c in '{}()[]:,;':
                tokens.append(('punct', c))
                i += 1
                continue
            # anything else (should not happen)
            raise SyntaxError(f"unexpected character '{c}' at position {i}")
        return tokens

    def peek(self):
        if self.idx < len(self.tokens):
            return self.tokens[self.idx]
        return None

    def next_token(self):
        tok = self.peek()
        if tok:
            self.idx += 1
        return tok

    def expect(self, typ, val=None):
        tok = self.next_token()
        if tok is None:
            raise SyntaxError(f"expected {typ} but got EOF")
        if tok[0] != typ:
            raise SyntaxError(f"expected {typ} but got {tok[0]} (value: {tok[1]})")
        if val is not None and tok[1] != val:
            raise SyntaxError(f"expected '{val}' but got '{tok[1]}'")
        return tok

    def parse(self):
        # daemon
        daemon_tok = self.next_token()
        if daemon_tok is None or daemon_tok[1] != 'daemon':
            raise SyntaxError("expected 'daemon'")
        name_tok = self.expect('ident')
        self.expect('punct', '(')
        self.expect('punct', ')')
        self.expect('punct', '{')
        daemon = {'name': name_tok[1], 'functions': [], 'intercepts': [], 'builds': []}
        while True:
            tok = self.peek()
            if tok is None or (tok[0] == 'punct' and tok[1] == '}'):
                break
            if tok[1] == 'fn':
                daemon['functions'].append(self.parse_function())
            elif tok[1] == 'intercept':
                daemon['intercepts'].append(self.parse_intercept())
            elif tok[1] == 'build':
                daemon['builds'].append(self.parse_build())
            else:
                raise SyntaxError(f"unexpected token {tok}")
        self.expect('punct', '}')
        return daemon

    def parse_function(self):
        self.expect('ident', 'fn')
        name_tok = self.expect('ident')
        self.expect('punct', '(')
        params = []
        while True:
            tok = self.peek()
            if tok[0] == 'punct' and tok[1] == ')':
                break
            pname = self.expect('ident')
            self.expect('punct', ':')
            ptype = self.expect('ident')
            params.append({'name': pname[1], 'type': ptype[1]})
            if self.peek() and self.peek()[0] == 'punct' and self.peek()[1] == ',':
                self.next_token()
        self.expect('punct', ')')
        self.expect('punct', '->')
        rettype = self.expect('ident')
        self.expect('punct', '{')
        body = self.parse_expr()
        self.expect('punct', '}')
        return {'name': name_tok[1], 'params': params, 'rettype': rettype[1], 'body': body}

    def parse_intercept(self):
        self.expect('ident', 'intercept')
        name_tok = self.expect('ident')
        self.expect('punct', '(')
        params = []
        while True:
            tok = self.peek()
            if tok[0] == 'punct' and tok[1] == ')':
                break
            pname = self.expect('ident')
            self.expect('punct', ':')
            ptype = self.expect('ident')
            params.append({'name': pname[1], 'type': ptype[1]})
            if self.peek() and self.peek()[0] == 'punct' and self.peek()[1] == ',':
                self.next_token()
        self.expect('punct', ')')
        self.expect('punct', '->')
        rettype = self.expect('ident')
        self.expect('punct', '{')
        body = self.parse_expr()
        self.expect('punct', '}')
        return {'name': name_tok[1], 'params': params, 'rettype': rettype[1], 'body': body}

    def parse_build(self):
        self.expect('ident', 'build')
        self.expect('punct', '{')
        expr = self.parse_expr()
        self.expect('punct', '}')
        return expr

    def parse_expr(self):
        expr_list = []
        while True:
            tok = self.peek()
            if tok is None or (tok[0] == 'punct' and tok[1] == '}'):
                break
            if tok[0] == 'punct' and tok[1] == ';':
                self.next_token()
                continue
            expr = self.parse_atom()
            expr_list.append(expr)
            if self.peek() and self.peek()[0] == 'punct' and self.peek()[1] == ';':
                self.next_token()
        return expr_list if len(expr_list) > 1 else expr_list[0] if expr_list else None

    def parse_atom(self):
        tok = self.peek()
        if tok is None:
            return None
        if tok[0] == 'ident':
            if tok[1] == 'if':
                return self.parse_if()
            elif tok[1] == 'while':
                return self.parse_while()
            elif tok[1] == 'return':
                return self.parse_return()
            elif tok[1] == 'print':
                return self.parse_print()
            else:
                return self.parse_call_or_var()
        elif tok[0] == 'punct' and tok[1] == '(':
            return self.parse_paren()
        elif tok[0] == 'punct' and tok[1] == '[':
            return self.parse_array()
        elif tok[0] == 'number' or tok[0] == 'string':
            self.next_token()
            return tok
        else:
            raise SyntaxError(f"unexpected token {tok}")

    def parse_if(self):
        self.next_token()
        self.expect('punct', '(')
        cond = self.parse_atom()
        self.expect('punct', ')')
        then_expr = self.parse_atom()
        else_expr = None
        if self.peek() and self.peek()[0] == 'ident' and self.peek()[1] == 'else':
            self.next_token()
            else_expr = self.parse_atom()
        return ('if', cond, then_expr, else_expr)

    def parse_while(self):
        self.next_token()
        self.expect('punct', '(')
        cond = self.parse_atom()
        self.expect('punct', ')')
        body = self.parse_atom()
        return ('while', cond, body)

    def parse_return(self):
        self.next_token()
        val = self.parse_atom()
        return ('return', val)

    def parse_print(self):
        self.next_token()
        self.expect('punct', '(')
        args = []
        while True:
            arg = self.parse_atom()
            args.append(arg)
            if self.peek() and self.peek()[0] == 'punct' and self.peek()[1] == ',':
                self.next_token()
            else:
                break
        self.expect('punct', ')')
        return ('print', args)

    def parse_call_or_var(self):
        name_tok = self.next_token()
        if self.peek() and self.peek()[0] == 'assign':
            self.next_token()
            rhs = self.parse_atom()
            return ('assign', name_tok[1], rhs)
        if self.peek() and self.peek()[0] == 'punct' and self.peek()[1] == '(':
            self.next_token()
            args = []
            while True:
                arg = self.parse_atom()
                args.append(arg)
                if self.peek() and self.peek()[0] == 'punct' and self.peek()[1] == ',':
                    self.next_token()
                else:
                    break
            self.expect('punct', ')')
            return ('call', name_tok[1], args)
        return ('var', name_tok[1])

    def parse_paren(self):
        self.next_token()
        expr = self.parse_atom()
        self.expect('punct', ')')
        return expr

    def parse_array(self):
        self.next_token()
        elems = []
        while True:
            if self.peek() and self.peek()[0] == 'punct' and self.peek()[1] == ']':
                break
            elem = self.parse_atom()
            elems.append(elem)
            if self.peek() and self.peek()[0] == 'punct' and self.peek()[1] == ',':
                self.next_token()
        self.expect('punct', ']')
        return ('array', elems)

def codegen(daemon):
    c_funcs = ''
    c_intercepts = ''
    c_main = ''
    for fn in daemon['functions']:
        c_funcs += generate_function(fn)
    for inter in daemon['intercepts']:
        c_intercepts += generate_intercept(inter)
    c_main = generate_main(daemon)
    return f'''
#include <stdio.h>
#include <unistd.h>
#include <signal.h>
#include <string.h>
#include <stdlib.h>

int running = 1;
void handle_sigterm(int s) {{ running = 0; }}

{c_funcs}
{c_intercepts}
{c_main}
'''

def generate_function(fn):
    params = ', '.join([f'const char* {p["name"]}' if p["type"] == 'str' else f'int {p["name"]}' for p in fn['params']])
    body = generate_expr(fn['body'])
    return f'''
int {fn['name']}({params}) {{
    {body}
}}
'''

def generate_intercept(inter):
    params = ', '.join([f'const char* {p["name"]}' if p["type"] == 'str' else f'int {p["name"]}' for p in inter['params']])
    body = generate_expr(inter['body'])
    return f'''
int {inter['name']}_intercept({params}) {{
    {body}
    return 0;
}}
'''

def generate_main(daemon):
    body = generate_expr(daemon['builds'][0]) if daemon['builds'] else ''
    return f'''
int main() {{
    signal(SIGTERM, handle_sigterm);
    {body}
    printf("grind daemon started\\n");
    while (running) {{ sleep(1); }}
    return 0;
}}
'''

def generate_expr(expr):
    if expr is None:
        return ''
    if isinstance(expr, list):
        return ';\n    '.join([generate_expr(e) for e in expr if e is not None])
    if isinstance(expr, tuple):
        op = expr[0]
        if op == 'if':
            cond = generate_expr(expr[1])
            then_part = generate_expr(expr[2])
            else_part = generate_expr(expr[3]) if expr[3] is not None else ''
            return f'if ({cond}) {{ {then_part} }} else {{ {else_part} }}'
        elif op == 'while':
            cond = generate_expr(expr[1])
            body = generate_expr(expr[2])
            return f'while ({cond}) {{ {body} }}'
        elif op == 'return':
            val = generate_expr(expr[1]) if expr[1] is not None else ''
            return f'return {val};'
        elif op == 'print':
            args = ', '.join([generate_expr(a) for a in expr[1]])
            # convert string tokens to quoted strings
            arg_strs = []
            for a in expr[1]:
                if isinstance(a, tuple) and a[0] == 'string':
                    arg_strs.append(f'"{a[1]}"')
                else:
                    arg_strs.append(generate_expr(a))
            return f'printf({", ".join(arg_strs)})'
        elif op == 'assign':
            rhs = generate_expr(expr[2])
            return f'{expr[1]} = {rhs}'
        elif op == 'call':
            name = expr[1]
            args = ', '.join([generate_expr(a) for a in expr[2]])
            return f'{name}({args})'
        elif op == 'var':
            return expr[1]
        elif op == 'array':
            elems = ', '.join([generate_expr(e) for e in expr[1]])
            return f'({elems})'
    if isinstance(expr, tuple) and len(expr)==2 and expr[0] == 'string':
        return f'"{expr[1]}"'
    if isinstance(expr, tuple) and len(expr)==2 and expr[0] == 'number':
        return expr[1]
    return str(expr)

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 bootstrap/bootstrap.py <file.gr>")
        sys.exit(1)

    gr_file = sys.argv[1]
    with open(gr_file, 'r') as f:
        src = f.read()

    parser = Parser(src)
    try:
        daemon = parser.parse()
    except SyntaxError as e:
        print(f"Parse error: {e}")
        sys.exit(1)

    c_code = codegen(daemon)
    c_file = gr_file + '.c'
    with open(c_file, 'w') as f:
        f.write(c_code)

    out_file = gr_file + '.out'
    os.system(f'gcc -o {out_file} {c_file}')
    print(f'compiled: {out_file}')

if __name__ == '__main__':
    main()
