#!/usr/bin/env python3
import sys
import os
import subprocess

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
            if c in ' \t\n\r':
                i += 1
                continue
            if c == '(' and i+1 < n and src[i+1] == '|':
                i += 2
                while i < n and not (src[i] == '|' and i+1 < n and src[i+1] == ')'):
                    i += 1
                i += 2
                continue
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
            if c.isdigit():
                start = i
                while i < n and src[i].isdigit():
                    i += 1
                tokens.append(('number', src[start:i]))
                continue
            if c == '-' and i+1 < n and src[i+1] == '>':
                tokens.append(('punct', '->'))
                i += 2
                continue
            if c.isalpha() or c == '_':
                start = i
                while i < n and (src[i].isalnum() or src[i] == '_'):
                    i += 1
                ident = src[start:i]
                tokens.append(('ident', ident))
                continue
            # operators as punctuation
            if c in '+-*/<=>':
                tokens.append(('punct', c))
                i += 1
                continue
            # assignment
            if c == '=':
                tokens.append(('assign', '='))
                i += 1
                continue
            if c == '≈':
                tokens.append(('assign', '≈'))
                i += 1
                continue
            if c in '{}()[]:,;':
                tokens.append(('punct', c))
                i += 1
                continue
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

    def parse_type(self):
        if self.peek() and self.peek()[0] == 'punct' and self.peek()[1] == '[':
            self.next_token()
            inner = self.expect('ident')[1]
            self.expect('punct', ']')
            return f'[{inner}]'
        else:
            return self.expect('ident')[1]

    def parse(self):
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
            ptype = self.parse_type()
            params.append({'name': pname[1], 'type': ptype})
            if self.peek() and self.peek()[0] == 'punct' and self.peek()[1] == ',':
                self.next_token()
        self.expect('punct', ')')
        self.expect('punct', '->')
        rettype = self.parse_type()
        self.expect('punct', '{')
        body = self.parse_sexpr()
        self.expect('punct', '}')
        return {'name': name_tok[1], 'params': params, 'rettype': rettype, 'body': body}

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
            ptype = self.parse_type()
            params.append({'name': pname[1], 'type': ptype})
            if self.peek() and self.peek()[0] == 'punct' and self.peek()[1] == ',':
                self.next_token()
        self.expect('punct', ')')
        self.expect('punct', '->')
        rettype = self.parse_type()
        self.expect('punct', '{')
        body = self.parse_sexpr()
        self.expect('punct', '}')
        return {'name': name_tok[1], 'params': params, 'rettype': rettype, 'body': body}

    def parse_build(self):
        self.expect('ident', 'build')
        self.expect('punct', '{')
        expr = self.parse_sexpr()
        self.expect('punct', '}')
        return expr

    def parse_sexpr(self):
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
        if tok[0] == 'punct' and tok[1] == '(':
            return self.parse_paren_expr()
        elif tok[0] == 'punct' and tok[1] == '[':
            return self.parse_array()
        elif tok[0] == 'ident' or tok[0] == 'punct':
            # a token that could be a variable or function name
            # if it's punctuation (like +, -, etc.) treat it as a variable
            self.next_token()
            if self.peek() and self.peek()[0] == 'assign':
                self.next_token()
                rhs = self.parse_atom()
                return ('assign', tok[1], rhs)
            return ('var', tok[1])
        elif tok[0] == 'number':
            self.next_token()
            return ('number', tok[1])
        elif tok[0] == 'string':
            self.next_token()
            return ('string', tok[1])
        else:
            raise SyntaxError(f"unexpected token {tok}")

    def parse_paren_expr(self):
        self.next_token()  # consume '('
        func_tok = self.next_token()
        if func_tok is None:
            raise SyntaxError("unexpected EOF inside parentheses")
        # allow both ident and punctuation as function name
        if func_tok[0] not in ('ident', 'punct'):
            raise SyntaxError(f"expected function name, got {func_tok}")
        func_name = func_tok[1]
        args = []
        while True:
            tok = self.peek()
            if tok is None:
                raise SyntaxError("unexpected EOF inside parentheses")
            if tok[0] == 'punct' and tok[1] == ')':
                break
            arg = self.parse_atom()
            args.append(arg)
        self.expect('punct', ')')
        if func_name == 'return':
            return ('return', args[0] if args else None)
        elif func_name == 'print':
            return ('print', args)
        elif func_name == 'if':
            if len(args) < 2:
                raise SyntaxError("if needs at least 2 arguments")
            # take first 3 arguments, ignore extras
            if len(args) > 3:
                args = args[:3]
            return ('if', args[0], args[1], args[2])
        elif func_name == 'while':
            if len(args) < 2:
                raise SyntaxError("while needs at least 2 arguments")
            args = args[:2]
            return ('while', args[0], args[1])
        elif func_name in ('str-len', 'str-sub', 'str-concat', 'str-split', 'len', 'at', 'push', 'pop',
                           'read-file', 'write-file', 'exec', 'ord', 'ge', 'le', 'gt', 'or', 'and', 'not',
                           'add', 'sub', 'lt'):
            return (func_name, args)
        else:
            return ('call', func_name, args)

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

RUNTIME = '''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

int grist_str_len(const char* s) { return s ? strlen(s) : 0; }
char* grist_str_sub(const char* s, int start, int end) {
    int len = s ? strlen(s) : 0;
    if (start < 0) start = 0;
    if (end > len) end = len;
    if (start >= end) return strdup("");
    char* r = malloc(end - start + 1);
    if (!r) return strdup("");
    memcpy(r, s+start, end-start);
    r[end-start] = 0;
    return r;
}
char* grist_str_concat(const char* a, const char* b) {
    int la = a ? strlen(a) : 0;
    int lb = b ? strlen(b) : 0;
    char* r = malloc(la + lb + 1);
    if (!r) return strdup("");
    if (a) memcpy(r, a, la);
    if (b) memcpy(r+la, b, lb);
    r[la+lb] = 0;
    return r;
}
char** grist_list_new() {
    char** r = malloc(sizeof(char*));
    if (r) r[0] = NULL;
    return r;
}
int grist_list_len(char** lst) {
    int c = 0;
    if (lst) while (lst[c]) c++;
    return c;
}
char* grist_list_at(char** lst, int idx) {
    if (!lst) return NULL;
    int c = 0;
    while (lst[c]) c++;
    if (idx < 0 || idx >= c) return NULL;
    return lst[idx];
}
char** grist_list_push(char** lst, const char* val) {
    if (!lst) { lst = grist_list_new(); }
    int c = 0;
    while (lst[c]) c++;
    char** new = malloc((c + 2) * sizeof(char*));
    if (!new) return lst;
    for (int i=0; i<c; i++) new[i] = lst[i] ? strdup(lst[i]) : NULL;
    new[c] = val ? strdup(val) : NULL;
    new[c+1] = NULL;
    free(lst);
    return new;
}
char** grist_list_pop(char** lst) {
    if (!lst) return NULL;
    int c = 0;
    while (lst[c]) c++;
    if (c == 0) return lst;
    char** new = malloc(c * sizeof(char*));
    if (!new) return lst;
    for (int i=0; i<c-1; i++) new[i] = lst[i] ? strdup(lst[i]) : NULL;
    new[c-1] = NULL;
    free(lst);
    return new;
}
char** grist_str_split(const char* s, const char* delim) {
    char** r = grist_list_new();
    char* copy = s ? strdup(s) : strdup("");
    char* tok = strtok(copy, delim);
    while (tok) {
        r = grist_list_push(r, tok);
        tok = strtok(NULL, delim);
    }
    free(copy);
    return r;
}
char* grist_read_file(const char* path) {
    FILE* f = fopen(path, "r");
    if (!f) return strdup("");
    fseek(f, 0, SEEK_END);
    long len = ftell(f);
    fseek(f, 0, SEEK_SET);
    char* buf = malloc(len + 1);
    if (!buf) { fclose(f); return strdup(""); }
    fread(buf, 1, len, f);
    fclose(f);
    buf[len] = 0;
    return buf;
}
int grist_write_file(const char* path, const char* content) {
    FILE* f = fopen(path, "w");
    if (!f) return 1;
    fputs(content, f);
    fclose(f);
    return 0;
}
int grist_exec(const char* cmd) {
    return system(cmd);
}
// arithmetic helpers
int grist_add(int a, int b) { return a + b; }
int grist_sub(int a, int b) { return a - b; }
int grist_lt(int a, int b) { return a < b; }
int grist_gt(int a, int b) { return a > b; }
int grist_le(int a, int b) { return a <= b; }
int grist_ge(int a, int b) { return a >= b; }
int grist_and(int a, int b) { return a && b; }
int grist_or(int a, int b) { return a || b; }
int grist_not(int a) { return !a; }
int grist_ord(const char* c) { return c[0]; }
'''

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

{RUNTIME}

int running = 1;
void handle_sigterm(int s) {{ running = 0; }}

{c_funcs}
{c_intercepts}
{c_main}
'''

def generate_function(fn):
    params = ', '.join([f'const char* {p["name"]}' if p["type"] == 'str' else f'int {p["name"]}' for p in fn['params']])
    body = generate_expr(fn['body'], is_returning_int=False)
    return f'''
int {fn['name']}({params}) {{
    {body}
    return 0;
}}
'''

def generate_intercept(inter):
    params = ', '.join([f'const char* {p["name"]}' if p["type"] == 'str' else f'int {p["name"]}' for p in inter['params']])
    body = generate_expr(inter['body'], is_returning_int=True)
    return f'''
int {inter['name']}_intercept({params}) {{
    {body}
    return 0;
}}
'''

def generate_main(daemon):
    body = generate_expr(daemon['builds'][0] if daemon['builds'] else None, is_returning_int=False)
    if body:
        body = body.rstrip(';') + ';'
    return f'''
int main() {{
    signal(SIGTERM, handle_sigterm);
    {body}
    printf("grind daemon started\\n");
    while (running) {{ sleep(1); }}
    return 0;
}}
'''

def generate_expr(expr, is_returning_int=False):
    if expr is None:
        return ''
    if isinstance(expr, list):
        return ';\n    '.join([generate_expr(e, is_returning_int) for e in expr if e is not None])
    if isinstance(expr, tuple):
        op = expr[0]
        if op == 'if':
            cond = generate_expr(expr[1], False)
            then_part = generate_expr(expr[2], is_returning_int)
            else_part = generate_expr(expr[3], is_returning_int) if expr[3] is not None else ''
            return f'if ({cond}) {{ {then_part} }} else {{ {else_part} }}'
        elif op == 'while':
            cond = generate_expr(expr[1], False)
            body = generate_expr(expr[2], is_returning_int)
            return f'while ({cond}) {{ {body} }}'
        elif op == 'return':
            arg = expr[1]
            if arg is None:
                return 'return 0;'
            if isinstance(arg, tuple):
                if arg[0] == 'var' and arg[1] == 'none':
                    return 'return 0;'
                if arg[0] == 'array' and not arg[1]:
                    return 'return 0;'
                if arg[0] == 'string' and arg[1] == '':
                    return 'return 0;'
            val = generate_expr(arg, False)
            return f'return {val};'
        elif op == 'print':
            args = []
            for a in expr[1]:
                if isinstance(a, tuple) and a[0] == 'string':
                    args.append(f'"{a[1]}"')
                elif isinstance(a, tuple) and a[0] == 'var':
                    args.append(f'"%s", {a[1]}')
                else:
                    args.append(generate_expr(a, False))
            return f'printf({", ".join(args)})'
        elif op == 'assign':
            rhs = generate_expr(expr[2], False)
            return f'{expr[1]} = {rhs}'
        elif op == 'call':
            name = expr[1]
            args = ', '.join([generate_expr(a, False) for a in expr[2]])
            return f'{name}({args})'
        elif op == 'str-len':
            arg = generate_expr(expr[1][0], False)
            return f'grist_str_len({arg})'
        elif op == 'str-sub':
            s = generate_expr(expr[1][0], False)
            start = generate_expr(expr[1][1], False)
            end = generate_expr(expr[1][2], False)
            return f'grist_str_sub({s}, {start}, {end})'
        elif op == 'str-concat':
            a = generate_expr(expr[1][0], False)
            b = generate_expr(expr[1][1], False)
            return f'grist_str_concat({a}, {b})'
        elif op == 'str-split':
            s = generate_expr(expr[1][0], False)
            d = generate_expr(expr[1][1], False)
            return f'grist_str_split({s}, {d})'
        elif op == 'len':
            arg = generate_expr(expr[1][0], False)
            return f'grist_list_len((char**){arg})'
        elif op == 'at':
            lst = generate_expr(expr[1][0], False)
            idx = generate_expr(expr[1][1], False)
            return f'grist_list_at((char**){lst}, {idx})'
        elif op == 'push':
            lst = generate_expr(expr[1][0], False)
            val = generate_expr(expr[1][1], False)
            return f'grist_list_push((char**){lst}, {val})'
        elif op == 'pop':
            lst = generate_expr(expr[1][0], False)
            return f'grist_list_pop((char**){lst})'
        elif op == 'read-file':
            path = generate_expr(expr[1][0], False)
            return f'grist_read_file({path})'
        elif op == 'write-file':
            path = generate_expr(expr[1][0], False)
            content = generate_expr(expr[1][1], False)
            return f'grist_write_file({path}, {content})'
        elif op == 'exec':
            cmd = generate_expr(expr[1][0], False)
            return f'grist_exec({cmd})'
        elif op in ('add', 'sub', 'lt', 'gt', 'le', 'ge', 'and', 'or', 'not', 'ord'):
            # built-in operations
            if op == 'add':
                a = generate_expr(expr[1][0], False)
                b = generate_expr(expr[1][1], False)
                return f'grist_add({a}, {b})'
            elif op == 'sub':
                a = generate_expr(expr[1][0], False)
                b = generate_expr(expr[1][1], False)
                return f'grist_sub({a}, {b})'
            elif op == 'lt':
                a = generate_expr(expr[1][0], False)
                b = generate_expr(expr[1][1], False)
                return f'grist_lt({a}, {b})'
            elif op == 'gt':
                a = generate_expr(expr[1][0], False)
                b = generate_expr(expr[1][1], False)
                return f'grist_gt({a}, {b})'
            elif op == 'le':
                a = generate_expr(expr[1][0], False)
                b = generate_expr(expr[1][1], False)
                return f'grist_le({a}, {b})'
            elif op == 'ge':
                a = generate_expr(expr[1][0], False)
                b = generate_expr(expr[1][1], False)
                return f'grist_ge({a}, {b})'
            elif op == 'and':
                a = generate_expr(expr[1][0], False)
                b = generate_expr(expr[1][1], False)
                return f'grist_and({a}, {b})'
            elif op == 'or':
                a = generate_expr(expr[1][0], False)
                b = generate_expr(expr[1][1], False)
            elif op == 'not':
                a = generate_expr(expr[1][0], False)
                return f'grist_not({a})'
            elif op == 'ord':
                a = generate_expr(expr[1][0], False)
                return f'grist_ord({a})'
        elif op == 'var':
            return expr[1]
        elif op == 'array':
            if not expr[1]:
                return 'grist_list_new()'
            else:
                lst = 'grist_list_new()'
                for e in expr[1]:
                    val = generate_expr(e, False)
                    lst = f'grist_list_push({lst}, {val})'
                return lst
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
    os.system(f'cc -o {out_file} {c_file}')
    print(f'compiled: {out_file}')

if __name__ == '__main__':
    main()
