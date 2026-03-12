"""
transpiler.py -- AST-based Python-to-C transpiler.

Converts Python function bodies to C code. Handles:
  - Attribute access (cpu.A -> sys->chip.A)
  - Flag access (cpu.F.Z -> getter/setter calls)
  - Register pairs (cpu.HL -> getter/setter calls)
  - Type annotations (x: uint8 = expr)
  - Cast functions (uint8(expr) -> (uint8_t)(expr))
  - Array declarations (x: array[uint8, 10])
  - Opcode families with variant substitution
  - Cross-component access (ppu.scanline -> sys->ppu.scanline)
  - signal_assert("name") -> signal_assert_{name}(sys)
"""

import ast
import inspect
import textwrap
from typing import Optional, Set, Dict, Callable


TYPE_MAP = {
    "uint8": "uint8_t", "uint16": "uint16_t", "uint32": "uint32_t",
    "uint64": "uint64_t", "int8": "int8_t", "int16": "int16_t",
    "int32": "int32_t", "int64": "int64_t", "bool": "bool", "int": "int",
}

CAST_MAP = {
    "uint8": "uint8_t", "uint16": "uint16_t", "uint32": "uint32_t",
    "uint64": "uint64_t", "int8": "int8_t", "int16": "int16_t",
    "int32": "int32_t", "int": "int",
}

SYS_PREPEND_FUNCS = {
    "mem_read", "mem_write", "mem_read16",
    "read_imm8", "read_imm16",
    "push8", "push16", "pop8", "pop16",
    "internal_op",
}

# Functions that get remapped to per-chip versions in multi-CPU systems
REMAPPABLE_FUNCS = {
    "read_imm8", "read_imm16",
    "push8", "push16", "pop8", "pop16",
    "mem_read16", "internal_op",
}

BUILTIN_FUNCS = {
    "printf", "sprintf", "snprintf", "fprintf",
    "memcpy", "memset", "memmove",
    "malloc", "calloc", "realloc", "free",
    "abs", "sizeof",
}


class Transpiler:
    def __init__(
        self,
        self_param: str = "cpu",
        chip_name: str = "cpu",
        component_names: Optional[Set[str]] = None,
        extern_funcs: Optional[Set[str]] = None,
        flag_register: Optional[str] = None,
        flag_bits: Optional[Dict[str, int]] = None,
        cpu_name: Optional[str] = None,
        register_pairs: Optional[Set[str]] = None,
        variant_args: Optional[tuple] = None,
        # Maps function parameter positions to variant values
        variant_param_names: Optional[list] = None,
        # Per-chip mem_read/write function names
        mem_read_func: str = "mem_read",
        mem_write_func: str = "mem_write",
        func_remap: Optional[dict] = None,
    ):
        self.self_param = self_param
        self.chip_name = chip_name
        self.component_names = component_names or set()
        self.extern_funcs = (extern_funcs or set()) | BUILTIN_FUNCS
        self.flag_register = flag_register
        self.flag_bits = flag_bits or {}
        self.cpu_name = cpu_name or chip_name
        self.register_pairs = register_pairs or set()
        self.variant_args = variant_args
        self.variant_param_names = variant_param_names
        self.mem_read_func = mem_read_func
        self.mem_write_func = mem_write_func
        # Remap table for per-chip function names (multi-CPU)
        self.func_remap: dict = func_remap or {}
        self.local_vars: Set[str] = set()
        self.indent_level = 1  # start indented inside function

    def transpile_function(self, func: Callable) -> str:
        source = inspect.getsource(func)
        source = textwrap.dedent(source)
        tree = ast.parse(source)

        func_def = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                func_def = node
                break

        if not func_def:
            return "    /* transpiler error: no function found */"

        # Build variant substitution map from parameter names
        self._variant_map = {}
        if self.variant_args and self.variant_param_names:
            for pname, pval in zip(self.variant_param_names, self.variant_args):
                self._variant_map[pname] = pval

        self.local_vars = set()
        lines = []
        for stmt in func_def.body:
            if (isinstance(stmt, ast.Expr) and
                    isinstance(stmt.value, ast.Constant) and
                    isinstance(stmt.value.value, str)):
                continue
            line = self._stmt(stmt)
            if line:
                lines.append(line)

        return '\n'.join(lines)

    # =================================================================
    # Statements
    # =================================================================

    def _stmt(self, node: ast.AST) -> str:
        ind = "    " * self.indent_level

        if isinstance(node, ast.Pass):
            return ""
        elif isinstance(node, ast.Assign):
            return self._assign(node, ind)
        elif isinstance(node, ast.AnnAssign):
            return self._ann_assign(node, ind)
        elif isinstance(node, ast.AugAssign):
            target = self._expr(node.target)
            value = self._expr(node.value)
            op = self._binop(node.op)
            return f"{ind}{target} {op}= {value};"
        elif isinstance(node, ast.Return):
            if node.value:
                return f"{ind}return {self._expr(node.value)};"
            return f"{ind}return;"
        elif isinstance(node, ast.Expr):
            return f"{ind}{self._expr(node.value)};"
        elif isinstance(node, ast.If):
            return self._if(node, ind)
        elif isinstance(node, ast.While):
            return self._while(node, ind)
        elif isinstance(node, ast.For):
            return self._for(node, ind)
        elif isinstance(node, ast.Break):
            return f"{ind}break;"
        elif isinstance(node, ast.Continue):
            return f"{ind}continue;"
        return f"{ind}/* unsupported: {type(node).__name__} */"

    def _assign(self, node: ast.Assign, ind: str) -> str:
        target = node.targets[0]
        value = self._expr(node.value)

        # Flag write: cpu.F.Z = expr
        if self._is_flag_write(target):
            optimized = self._optimize_flag_val(node.value)
            return f"{ind}{self.cpu_name}_set_{target.attr}(sys, {optimized});"

        # Register pair write: cpu.HL = expr
        if self._is_pair_write(target):
            pair_name = target.attr
            return f"{ind}{self.cpu_name}_set_{pair_name}(sys, {value});"

        # Attribute or subscript write
        if isinstance(target, (ast.Attribute, ast.Subscript)):
            target_str = self._expr(target)
            return f"{ind}{target_str} = {value};"

        # Local variable
        if isinstance(target, ast.Name):
            var_name = target.id
            if var_name not in self.local_vars:
                self.local_vars.add(var_name)
                c_type = self._infer_type(node.value)
                return f"{ind}{c_type} {var_name} = {value};"
            return f"{ind}{var_name} = {value};"

        return f"{ind}/* unsupported assign */"

    def _ann_assign(self, node: ast.AnnAssign, ind: str) -> str:
        if not isinstance(node.target, ast.Name):
            return f"{ind}/* unsupported annotated assign */"

        var_name = node.target.id
        self.local_vars.add(var_name)

        # Array: x: array[uint8, 160]
        if isinstance(node.annotation, ast.Subscript):
            ann = node.annotation
            if isinstance(ann.value, ast.Name) and ann.value.id == "array":
                return self._array_decl(var_name, ann.slice, ind)

        c_type = self._resolve_type(node.annotation)
        if node.value:
            return f"{ind}{c_type} {var_name} = {self._expr(node.value)};"
        return f"{ind}{c_type} {var_name};"

    def _array_decl(self, name: str, slice_node: ast.AST, ind: str) -> str:
        if isinstance(slice_node, ast.Tuple) and len(slice_node.elts) == 2:
            elem_type = self._resolve_type(slice_node.elts[0])
            size = self._expr(slice_node.elts[1])
            return f"{ind}{elem_type} {name}[{size}];"
        return f"{ind}/* unsupported array decl */"

    def _if(self, node: ast.If, ind: str) -> str:
        lines = [f"{ind}if ({self._expr(node.test)}) {{"]
        self.indent_level += 1
        for s in node.body:
            l = self._stmt(s)
            if l: lines.append(l)
        self.indent_level -= 1

        if node.orelse:
            if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
                elif_str = self._if(node.orelse[0], ind)
                elif_str = elif_str.replace(f"{ind}if", f"{ind}}} else if", 1)
                lines.append(elif_str)
                return '\n'.join(lines)
            else:
                lines.append(f"{ind}}} else {{")
                self.indent_level += 1
                for s in node.orelse:
                    l = self._stmt(s)
                    if l: lines.append(l)
                self.indent_level -= 1

        lines.append(f"{ind}}}")
        return '\n'.join(lines)

    def _while(self, node: ast.While, ind: str) -> str:
        lines = [f"{ind}while ({self._expr(node.test)}) {{"]
        self.indent_level += 1
        for s in node.body:
            l = self._stmt(s)
            if l: lines.append(l)
        self.indent_level -= 1
        lines.append(f"{ind}}}")
        return '\n'.join(lines)

    def _for(self, node: ast.For, ind: str) -> str:
        if not isinstance(node.target, ast.Name):
            return f"{ind}/* unsupported for target */"
        var = node.target.id
        self.local_vars.add(var)

        if (isinstance(node.iter, ast.Call) and
                isinstance(node.iter.func, ast.Name) and
                node.iter.func.id == "range"):
            args = node.iter.args
            if len(args) == 1:
                start, end = "0", self._expr(args[0])
            elif len(args) >= 2:
                start, end = self._expr(args[0]), self._expr(args[1])
            else:
                return f"{ind}/* unsupported range */"

            step = self._expr(args[2]) if len(args) == 3 else None
            step_str = f"{var} += {step}" if step else f"{var}++"

            lines = [f"{ind}for (int {var} = {start}; {var} < {end}; {step_str}) {{"]
            self.indent_level += 1
            for s in node.body:
                l = self._stmt(s)
                if l: lines.append(l)
            self.indent_level -= 1
            lines.append(f"{ind}}}")
            return '\n'.join(lines)

        return f"{ind}/* unsupported for iterator */"

    # =================================================================
    # Expressions
    # =================================================================

    def _expr(self, node: ast.AST) -> str:
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool):
                return "true" if node.value else "false"
            if isinstance(node.value, int):
                if node.value > 255:
                    return f"0x{node.value:X}"
                return str(node.value)
            if isinstance(node.value, str):
                escaped = node.value.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
                return f'"{escaped}"'
            return str(node.value)

        elif isinstance(node, ast.Name):
            name = node.id
            # Variant substitution: if this name is a variant parameter, replace it
            if name in self._variant_map:
                val = self._variant_map[name]
                if isinstance(val, str):
                    # It's a register name — don't substitute the Name itself,
                    # only when used as cpu.{name}
                    pass
                elif isinstance(val, int):
                    if val > 255:
                        return f"0x{val:X}"
                    return str(val)
            if name == self.self_param:
                return f"sys->{self.chip_name}"
            if name in self.component_names:
                return f"sys->{name}"
            return name

        elif isinstance(node, ast.Attribute):
            return self._attribute(node)

        elif isinstance(node, ast.Subscript):
            value = self._expr(node.value)
            idx = self._expr(node.slice)
            return f"{value}[{idx}]"

        elif isinstance(node, ast.BinOp):
            left = self._expr(node.left)
            right = self._expr(node.right)
            op = self._binop(node.op)
            return f"({left} {op} {right})"

        elif isinstance(node, ast.UnaryOp):
            operand = self._expr(node.operand)
            if isinstance(node.op, ast.Not):
                return f"(!{operand})"
            elif isinstance(node.op, ast.Invert):
                return f"(~{operand})"
            elif isinstance(node.op, ast.USub):
                return f"(-{operand})"
            return operand

        elif isinstance(node, ast.BoolOp):
            op = " && " if isinstance(node.op, ast.And) else " || "
            parts = [self._expr(v) for v in node.values]
            return f"({op.join(parts)})"

        elif isinstance(node, ast.Compare):
            left = self._expr(node.left)
            parts = [left]
            for op, comp in zip(node.ops, node.comparators):
                parts.append(f"{self._cmpop(op)} {self._expr(comp)}")
            return f"({' '.join(parts)})"

        elif isinstance(node, ast.Call):
            return self._call(node)

        elif isinstance(node, ast.IfExp):
            test = self._expr(node.test)
            body = self._expr(node.body)
            orelse = self._expr(node.orelse)
            return f"({test} ? {body} : {orelse})"

        return f"/* unsupported expr: {type(node).__name__} */"

    def _attribute(self, node: ast.Attribute) -> str:
        # Flag read: cpu.F.Z -> cpu_get_Z(sys)
        if self._is_flag_read(node):
            return f"{self.cpu_name}_get_{node.attr}(sys)"

        # Register pair read: cpu.HL -> cpu_get_HL(sys)
        if self._is_pair_read(node):
            return f"{self.cpu_name}_get_{node.attr}(sys)"

        if isinstance(node.value, ast.Name):
            obj_name = node.value.id
            attr = node.attr

            # Variant register substitution: cpu.dst where dst='A' -> cpu.A
            if attr in self._variant_map:
                val = self._variant_map[attr]
                if isinstance(val, str):
                    attr = val
                    # Check if the substituted name is a register pair
                    if attr in self.register_pairs:
                        if obj_name == self.self_param:
                            return f"{self.cpu_name}_get_{attr}(sys)"

            if obj_name == self.self_param:
                return f"sys->{self.chip_name}.{attr}"
            if obj_name in self.component_names:
                return f"sys->{obj_name}.{attr}"

        value = self._expr(node.value)
        return f"{value}.{node.attr}"

    def _call(self, node: ast.Call) -> str:
        if isinstance(node.func, ast.Name):
            func_name = node.func.id

            # Type cast
            if func_name in CAST_MAP:
                if node.args:
                    arg = self._expr(node.args[0])
                    return f"(({CAST_MAP[func_name]})({arg}))"
                return f"(({CAST_MAP[func_name]})(0))"

            # signal_assert("name") -> signal_assert_{name}(sys)
            if func_name == "signal_assert":
                if node.args and isinstance(node.args[0], ast.Constant):
                    sig_name = node.args[0].value
                    return f"signal_assert_{sig_name}(sys)"

            args = [self._expr(a) for a in node.args]

            # Remap mem_read/mem_write to per-chip versions
            if func_name == "mem_read":
                return f"{self.mem_read_func}(sys, {', '.join(args)})" if args else f"{self.mem_read_func}(sys)"
            if func_name == "mem_write":
                return f"{self.mem_write_func}(sys, {', '.join(args)})" if args else f"{self.mem_write_func}(sys)"

            if func_name in SYS_PREPEND_FUNCS:
                # Apply per-chip remapping if available
                actual_name = self.func_remap.get(func_name, func_name)
                return f"{actual_name}(sys, {', '.join(args)})" if args else f"{actual_name}(sys)"
            elif func_name in self.extern_funcs:
                return f"{func_name}({', '.join(args)})"
            else:
                # Default: prepend sys
                if args:
                    return f"{func_name}(sys, {', '.join(args)})"
                return f"{func_name}(sys)"

        elif isinstance(node.func, ast.Attribute):
            func_str = self._expr(node.func)
            args = [self._expr(a) for a in node.args]
            return f"{func_str}({', '.join(args)})"

        return "/* unsupported call */"

    # =================================================================
    # Flag / pair helpers
    # =================================================================

    def _is_flag_read(self, node: ast.Attribute) -> bool:
        return (self.flag_register and
                isinstance(node.value, ast.Attribute) and
                node.value.attr == self.flag_register and
                node.attr in self.flag_bits)

    def _is_flag_write(self, node: ast.AST) -> bool:
        return (isinstance(node, ast.Attribute) and
                self.flag_register and
                isinstance(node.value, ast.Attribute) and
                node.value.attr == self.flag_register and
                node.attr in self.flag_bits)

    def _is_pair_read(self, node: ast.Attribute) -> bool:
        if isinstance(node.value, ast.Name):
            obj = node.value.id
            if (obj == self.self_param or obj in self.component_names):
                return node.attr in self.register_pairs
        return False

    def _is_pair_write(self, node: ast.AST) -> bool:
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            obj = node.value.id
            if (obj == self.self_param or obj in self.component_names):
                return node.attr in self.register_pairs
        return False

    def _optimize_flag_val(self, node: ast.AST) -> str:
        if isinstance(node, ast.IfExp):
            if (isinstance(node.body, ast.Constant) and node.body.value == 1 and
                    isinstance(node.orelse, ast.Constant) and node.orelse.value == 0):
                return self._expr(node.test)
            if (isinstance(node.body, ast.Constant) and node.body.value == 0 and
                    isinstance(node.orelse, ast.Constant) and node.orelse.value == 1):
                return f"(!{self._expr(node.test)})"
        return self._expr(node)

    # =================================================================
    # Type inference
    # =================================================================

    def _resolve_type(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return TYPE_MAP.get(node.id, node.id)
        return "uint16_t"

    def _infer_type(self, node: ast.AST) -> str:
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            name = node.func.id
            if name in ("read_imm8", "pop8", "mem_read"):
                return "uint8_t"
            if name in ("read_imm16", "pop16", "mem_read16"):
                return "uint16_t"
            if name in CAST_MAP:
                return CAST_MAP[name]
        if isinstance(node, ast.Constant) and isinstance(node.value, int):
            if node.value > 0xFFFF:
                return "uint32_t"
            if node.value > 0xFF:
                return "uint16_t"
            return "uint8_t"
        return "uint16_t"

    # =================================================================
    # Operators
    # =================================================================

    def _binop(self, op):
        ops = {
            ast.Add: "+", ast.Sub: "-", ast.Mult: "*",
            ast.Div: "/", ast.Mod: "%", ast.FloorDiv: "/",
            ast.BitAnd: "&", ast.BitOr: "|", ast.BitXor: "^",
            ast.LShift: "<<", ast.RShift: ">>",
        }
        return ops.get(type(op), "?")

    def _cmpop(self, op):
        ops = {
            ast.Eq: "==", ast.NotEq: "!=",
            ast.Lt: "<", ast.Gt: ">",
            ast.LtE: "<=", ast.GtE: ">=",
        }
        return ops.get(type(op), "?")
