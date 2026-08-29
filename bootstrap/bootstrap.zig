const std = @import("std");

const TokenKind = enum {
    ident, number, string,
    kw_daemon, kw_fn, kw_intercept, kw_schedule, kw_hotswap, kw_build,
    kw_return, kw_if, kw_while, kw_print, kw_none,
    lparen, rparen, lbrace, rbrace, comma, colon,
    eq, arrow, forall, eof,
};

const Token = struct {
    kind: TokenKind,
    text: []const u8,
    line: usize,
    col: usize,
};

const Lexer = struct {
    source: []const u8,
    pos: usize,
    line: usize,
    col: usize,

    fn init(source: []const u8) Lexer {
        return Lexer{ .source = source, .pos = 0, .line = 1, .col = 1 };
    }

    fn peek(self: *Lexer) u8 {
        if (self.pos >= self.source.len) return 0;
        return self.source[self.pos];
    }

    fn next(self: *Lexer) u8 {
        if (self.pos >= self.source.len) return 0;
        const c = self.source[self.pos];
        self.pos += 1;
        if (c == '\n') { self.line += 1; self.col = 1; } else self.col += 1;
        return c;
    }

    fn skipWhitespace(self: *Lexer) void {
        while (true) {
            const c = self.peek();
            if (c == ' ' or c == '\t' or c == '\n' or c == '\r') {
                _ = self.next();
                continue;
            }
            if (c == '(' and self.pos + 1 < self.source.len and self.source[self.pos + 1] == '|') {
                _ = self.next(); _ = self.next();
                while (!(self.peek() == '|' and self.pos + 1 < self.source.len and self.source[self.pos + 1] == ')')) {
                    if (self.peek() == 0) return;
                    _ = self.next();
                }
                _ = self.next(); _ = self.next();
                continue;
            }
            break;
        }
    }

    fn peekToken(self: *Lexer) Token {
        const saved_pos = self.pos;
        const saved_line = self.line;
        const saved_col = self.col;
        const tok = self.token();
        self.pos = saved_pos;
        self.line = saved_line;
        self.col = saved_col;
        return tok;
    }

    fn token(self: *Lexer) Token {
        self.skipWhitespace();
        const start_line = self.line;
        const start_col = self.col;
        const c = self.peek();
        if (c == 0) return Token{ .kind = .eof, .text = "", .line = start_line, .col = start_col };
        if (c == '"') {
            _ = self.next();
            const start = self.pos;
            while (self.peek() != '"' and self.peek() != 0) {
                if (self.peek() == '\\') _ = self.next();
                _ = self.next();
            }
            const text = self.source[start..self.pos];
            _ = self.next();
            return Token{ .kind = .string, .text = text, .line = start_line, .col = start_col };
        }
        if (isDigit(c)) {
            const start = self.pos;
            while (isDigit(self.peek())) _ = self.next();
            const text = self.source[start..self.pos];
            return Token{ .kind = .number, .text = text, .line = start_line, .col = start_col };
        }
        if (c == '-' and self.pos + 1 < self.source.len and self.source[self.pos + 1] == '>') {
            _ = self.next(); _ = self.next();
            return Token{ .kind = .arrow, .text = "->", .line = start_line, .col = start_col };
        }
        if (isAlpha(c)) {
            const start = self.pos;
            while (isAlpha(self.peek()) or isDigit(self.peek())) _ = self.next();
            const text = self.source[start..self.pos];
            var kind: TokenKind = .ident;
            if (std.mem.eql(u8, text, "daemon")) {
                kind = .kw_daemon;
            } else if (std.mem.eql(u8, text, "fn")) {
                kind = .kw_fn;
            } else if (std.mem.eql(u8, text, "intercept")) {
                kind = .kw_intercept;
            } else if (std.mem.eql(u8, text, "schedule")) {
                kind = .kw_schedule;
            } else if (std.mem.eql(u8, text, "hotswap")) {
                kind = .kw_hotswap;
            } else if (std.mem.eql(u8, text, "build")) {
                kind = .kw_build;
            } else if (std.mem.eql(u8, text, "return")) {
                kind = .kw_return;
            } else if (std.mem.eql(u8, text, "if")) {
                kind = .kw_if;
            } else if (std.mem.eql(u8, text, "while")) {
                kind = .kw_while;
            } else if (std.mem.eql(u8, text, "print")) {
                kind = .kw_print;
            } else if (std.mem.eql(u8, text, "none")) {
                kind = .kw_none;
            }
            return Token{ .kind = kind, .text = text, .line = start_line, .col = start_col };
        }
        if (c == '(') { _ = self.next(); return Token{ .kind = .lparen, .text = "(", .line = start_line, .col = start_col }; }
        if (c == ')') { _ = self.next(); return Token{ .kind = .rparen, .text = ")", .line = start_line, .col = start_col }; }
        if (c == '{') { _ = self.next(); return Token{ .kind = .lbrace, .text = "{", .line = start_line, .col = start_col }; }
        if (c == '}') { _ = self.next(); return Token{ .kind = .rbrace, .text = "}", .line = start_line, .col = start_col }; }
        if (c == ',') { _ = self.next(); return Token{ .kind = .comma, .text = ",", .line = start_line, .col = start_col }; }
        if (c == ':') { _ = self.next(); return Token{ .kind = .colon, .text = ":", .line = start_line, .col = start_col }; }
        if (c == '≈') { _ = self.next(); return Token{ .kind = .eq, .text = "≈", .line = start_line, .col = start_col }; }
        if (c == '→') { _ = self.next(); return Token{ .kind = .arrow, .text = "→", .line = start_line, .col = start_col }; }
        if (c == '∀') { _ = self.next(); return Token{ .kind = .forall, .text = "∀", .line = start_line, .col = start_col }; }
        return Token{ .kind = .eof, .text = "", .line = start_line, .col = start_col };
    }

    fn expect(self: *Lexer, kind: TokenKind) Token {
        const t = self.token();
        if (t.kind != kind) {
            std.debug.print("error: expected {s} at {}:{}\n", .{ @tagName(kind), t.line, t.col });
            std.process.exit(1);
        }
        return t;
    }
};

fn isAlpha(c: u8) bool {
    return (c >= 'a' and c <= 'z') or (c >= 'A' and c <= 'Z') or c == '_';
}

fn isDigit(c: u8) bool {
    return c >= '0' and c <= '9';
}

const Expr = struct {
    const Kind = enum { call, ident, number, string, block, ifexpr, whileexpr, ret, assign };
    kind: Kind,
    text: []const u8 = "",
    ival: i64 = 0,
    children: std.ArrayList(*Expr),
    allocator: std.mem.Allocator,

    fn init(allocator: std.mem.Allocator, kind: Kind) *Expr {
        const e = allocator.create(Expr) catch @panic("alloc");
        e.* = .{
            .kind = kind,
            .children = std.ArrayList(*Expr).init(allocator),
            .allocator = allocator,
        };
        return e;
    }

    fn deinit(self: *Expr) void {
        for (self.children.items) |c| c.deinit();
        self.children.deinit();
        self.allocator.destroy(self);
    }
};

const Parser = struct {
    lexer: *Lexer,
    allocator: std.mem.Allocator,
    current: Token,

    fn init(allocator: std.mem.Allocator, lexer: *Lexer) Parser {
        const p = Parser{
            .lexer = lexer,
            .allocator = allocator,
            .current = lexer.token(),
        };
        return p;
    }

    fn advance(self: *Parser) void {
        self.current = self.lexer.token();
    }

    fn parseExpr(self: *Parser) *Expr {
        const tok = self.current;
        if (tok.kind == .kw_return) {
            self.advance();
            const expr = self.parseExpr();
            const ret = Expr.init(self.allocator, .ret);
            ret.children.append(expr) catch @panic("append");
            return ret;
        }
        if (tok.kind == .kw_if) {
            self.advance();
            _ = self.lexer.expect(.lparen);
            const cond = self.parseExpr();
            _ = self.lexer.expect(.rparen);
            const then_expr = self.parseExpr();
            const else_expr = self.parseExpr();
            const node = Expr.init(self.allocator, .ifexpr);
            node.children.append(cond) catch @panic("append");
            node.children.append(then_expr) catch @panic("append");
            node.children.append(else_expr) catch @panic("append");
            return node;
        }
        if (tok.kind == .kw_while) {
            self.advance();
            _ = self.lexer.expect(.lparen);
            const cond = self.parseExpr();
            _ = self.lexer.expect(.rparen);
            const body = self.parseExpr();
            const node = Expr.init(self.allocator, .whileexpr);
            node.children.append(cond) catch @panic("append");
            node.children.append(body) catch @panic("append");
            return node;
        }
        if (tok.kind == .lbrace) {
            self.advance();
            const block = Expr.init(self.allocator, .block);
            while (self.current.kind != .rbrace) {
                const expr = self.parseExpr();
                block.children.append(expr) catch @panic("append");
            }
            _ = self.lexer.token();
            return block;
        }
        if (tok.kind == .ident) {
            self.advance();
            if (self.current.kind == .eq) {
                self.advance();
                const rhs = self.parseExpr();
                const node = Expr.init(self.allocator, .assign);
                node.text = tok.text;
                node.children.append(rhs) catch @panic("append");
                return node;
            }
            if (self.current.kind == .lparen) {
                self.advance();
                const call = Expr.init(self.allocator, .call);
                call.text = tok.text;
                while (self.current.kind != .rparen) {
                    const arg = self.parseExpr();
                    call.children.append(arg) catch @panic("append");
                    if (self.current.kind == .comma) self.advance();
                }
                _ = self.lexer.token();
                return call;
            }
            const ident = Expr.init(self.allocator, .ident);
            ident.text = tok.text;
            return ident;
        }
        if (tok.kind == .number) {
            self.advance();
            const num = Expr.init(self.allocator, .number);
            num.ival = std.fmt.parseInt(i64, tok.text, 10) catch 0;
            return num;
        }
        if (tok.kind == .string) {
            self.advance();
            const str = Expr.init(self.allocator, .string);
            str.text = tok.text;
            return str;
        }
        if (tok.kind == .lparen) {
            self.advance();
            const expr = self.parseExpr();
            _ = self.lexer.expect(.rparen);
            return expr;
        }
        std.debug.print("unexpected token {s} at {}:{}\n", .{ @tagName(tok.kind), tok.line, tok.col });
        std.process.exit(1);
    }

    fn parseParams(self: *Parser) std.ArrayList([]const u8) {
        var params = std.ArrayList([]const u8).init(self.allocator);
        _ = self.lexer.expect(.lparen);
        while (true) {
            if (self.lexer.peekToken().kind == .rparen) {
                _ = self.lexer.token();
                break;
            }
            const id = self.lexer.expect(.ident);
            _ = self.lexer.expect(.colon);
            _ = self.lexer.expect(.ident);
            params.append(id.text) catch @panic("append");
            if (self.lexer.peekToken().kind == .comma) {
                _ = self.lexer.token();
            }
        }
        return params;
    }
};

const Intercept = struct {
    name: []const u8,
    params: std.ArrayList([]const u8),
    body: *Expr,
};

const Daemon = struct {
    name: []const u8,
    intercepts: std.ArrayList(Intercept),
    builds: std.ArrayList(*Expr),
    allocator: std.mem.Allocator,

    fn init(allocator: std.mem.Allocator) Daemon {
        return Daemon{
            .name = "",
            .intercepts = std.ArrayList(Intercept).init(allocator),
            .builds = std.ArrayList(*Expr).init(allocator),
            .allocator = allocator,
        };
    }

    fn deinit(self: *Daemon) void {
        for (self.intercepts.items) |i| {
            i.params.deinit();
            i.body.deinit();
        }
        self.intercepts.deinit();
        for (self.builds.items) |b| b.deinit();
        self.builds.deinit();
    }
};

fn parseDaemon(allocator: std.mem.Allocator, lexer: *Lexer) Daemon {
    var daemon = Daemon.init(allocator);
    _ = lexer.expect(.kw_daemon);
    const name_tok = lexer.expect(.ident);
    daemon.name = name_tok.text;
    _ = lexer.expect(.lparen);
    _ = lexer.expect(.rparen);
    _ = lexer.expect(.lbrace);

    var parser = Parser.init(allocator, lexer);
    parser.current = lexer.token();

    while (parser.current.kind != .rbrace) {
        if (parser.current.kind == .kw_intercept) {
            parser.advance();
            const name_tok2 = lexer.expect(.ident);
            const params = parser.parseParams();
            _ = lexer.expect(.arrow);
            _ = lexer.expect(.ident);
            const body = parser.parseExpr();
            daemon.intercepts.append(.{ .name = name_tok2.text, .params = params, .body = body }) catch @panic("append");
        } else if (parser.current.kind == .kw_build) {
            parser.advance();
            const body = parser.parseExpr();
            daemon.builds.append(body) catch @panic("append");
        } else {
            _ = parser.parseExpr();
        }
    }
    _ = lexer.token();
    return daemon;
}

fn codegenExpr(expr: *Expr, code: *std.ArrayList(u8)) !void {
    switch (expr.kind) {
        .number => try code.writer().print("{}", .{expr.ival}),
        .string => try code.writer().print("\"{s}\"", .{expr.text}),
        .ident => try code.appendSlice(expr.text),
        .assign => {
            try code.writer().print("{s} = ", .{expr.text});
            try codegenExpr(expr.children.items[0], code);
        },
        .call => {
            if (std.mem.eql(u8, expr.text, "print")) {
                try code.appendSlice("printf(");
                for (expr.children.items, 0..) |arg, idx| {
                    if (idx > 0) try code.appendSlice(", ");
                    try codegenExpr(arg, code);
                }
                try code.appendSlice(")");
            } else {
                try code.writer().print("{s}(", .{expr.text});
                for (expr.children.items, 0..) |arg, idx| {
                    if (idx > 0) try code.appendSlice(", ");
                    try codegenExpr(arg, code);
                }
                try code.appendSlice(")");
            }
        },
        .ret => {
            try code.appendSlice("return ");
            if (expr.children.items.len > 0) {
                try codegenExpr(expr.children.items[0], code);
            } else {
                try code.appendSlice("0");
            }
        },
        .ifexpr => {
            try code.appendSlice("if (");
            try codegenExpr(expr.children.items[0], code);
            try code.appendSlice(") ");
            try codegenExpr(expr.children.items[1], code);
            try code.appendSlice(" else ");
            try codegenExpr(expr.children.items[2], code);
        },
        .whileexpr => {
            try code.appendSlice("while (");
            try codegenExpr(expr.children.items[0], code);
            try code.appendSlice(") ");
            try codegenExpr(expr.children.items[1], code);
        },
        .block => {
            try code.appendSlice("{\n");
            for (expr.children.items) |child| {
                try code.appendSlice("        ");
                try codegenExpr(child, code);
                try code.appendSlice(";\n");
            }
            try code.appendSlice("    }");
        },
    }
}

fn generateC(daemon: *Daemon, allocator: std.mem.Allocator) ![]u8 {
    var code = std.ArrayList(u8).init(allocator);

    try code.appendSlice(
        "#include <stdio.h>\n" ++
        "#include <unistd.h>\n" ++
        "#include <signal.h>\n" ++
        "#include <string.h>\n" ++
        "\n" ++
        "int running = 1;\n" ++
        "void handle_sigterm(int s) { running = 0; }\n" ++
        "\n"
    );

    for (daemon.intercepts.items) |inter| {
        try code.appendSlice("int ");
        try code.appendSlice(inter.name);
        try code.appendSlice("_intercept(");
        for (inter.params.items, 0..) |p, idx| {
            if (idx > 0) try code.appendSlice(", ");
            try code.appendSlice("const char* ");
            try code.appendSlice(p);
        }
        try code.appendSlice(") {\n");
        try code.appendSlice("    ");

        const body = inter.body;
        if (body.kind == .block) {
            for (body.children.items) |child| {
                try codegenExpr(child, &code);
                try code.appendSlice(";\n    ");
            }
        } else {
            try codegenExpr(body, &code);
            try code.appendSlice(";\n");
        }
        try code.appendSlice("    return 0;\n");
        try code.appendSlice("}\n\n");
    }

    try code.appendSlice(
        "int main() {\n" ++
        "    signal(SIGTERM, handle_sigterm);\n" ++
        "    printf(\"grind daemon started\\n\");\n" ++
        "    while (running) { sleep(1); }\n" ++
        "    return 0;\n" ++
        "}\n"
    );

    return code.toOwnedSlice();
}

pub fn main() !void {
    var gpa = std.heap.GeneralPurposeAllocator(.{}){};
    defer _ = gpa.deinit();
    const alloc = gpa.allocator();

    const args = try std.process.argsAlloc(alloc);
    defer std.process.argsFree(alloc, args);

    if (args.len < 2) {
        std.debug.print("Usage: gristc <file.gr>\n", .{});
        return;
    }

    const path = args[1];
    const source = try std.fs.cwd().readFileAlloc(alloc, path, std.math.maxInt(usize));
    defer alloc.free(source);

    var lexer = Lexer.init(source);
    var daemon = parseDaemon(alloc, &lexer);
    defer daemon.deinit();

    const c_code = try generateC(&daemon, alloc);
    defer alloc.free(c_code);

    const c_path = try std.fmt.allocPrint(alloc, "{s}.c", .{path});
    defer alloc.free(c_path);

    try std.fs.cwd().writeFile(.{ .sub_path = c_path, .data = c_code });

    const out_name = try std.fmt.allocPrint(alloc, "{s}.out", .{path});
    defer alloc.free(out_name);

    const cc = "cc";
    var child = std.process.Child.init(&[_][]const u8{ cc, "-o", out_name, c_path }, alloc);
    const term = try child.spawnAndWait();
    if (term != .Exited or term.Exited != 0) {
        std.debug.print("compilation failed\n", .{});
        return;
    }

    std.debug.print("compiled: {s}\n", .{out_name});
}
