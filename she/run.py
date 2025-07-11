from .lexer import Lexer
from .parser import Parser
from .interpreter import Interpreter
from .context import Context, SymbolTable
from .values import Number, BuiltInFunction, String
from .errors import RTError
from .builtins import BuiltInFunction

global_symbol_table = SymbolTable()
global_symbol_table.set("NULL", Number.null)
global_symbol_table.set("FALSE", Number.false)
global_symbol_table.set("TRUE", Number.true)
global_symbol_table.set("MATH_PI", Number.math_PI)
global_symbol_table.set("PRINT", BuiltInFunction("print"))
global_symbol_table.set("PRINT_RET", BuiltInFunction("print_ret"))
global_symbol_table.set("INPUT", BuiltInFunction("input"))
global_symbol_table.set("INPUT_INT", BuiltInFunction("input_int"))
global_symbol_table.set("CLEAR", BuiltInFunction("clear"))
global_symbol_table.set("CLS", BuiltInFunction("clear"))
global_symbol_table.set("IS_NUM", BuiltInFunction("is_number"))
global_symbol_table.set("IS_STR", BuiltInFunction("is_string"))
global_symbol_table.set("IS_LIST", BuiltInFunction("is_list"))
global_symbol_table.set("IS_FUN", BuiltInFunction("is_function"))
global_symbol_table.set("APPEND", BuiltInFunction("append"))
global_symbol_table.set("POP", BuiltInFunction("pop"))
global_symbol_table.set("EXTEND", BuiltInFunction("extend"))
global_symbol_table.set("LEN", BuiltInFunction("len"))
global_symbol_table.set("RUN", BuiltInFunction("run"))
global_symbol_table.set("KAALKA_ENCRYPT", BuiltInFunction("kaalka_encrypt"))
global_symbol_table.set("KAALKA_DECRYPT", BuiltInFunction("kaalka_decrypt"))

def run(fn, text):
  # Generate tokens
  lexer = Lexer(fn, text)
  tokens, error = lexer.make_tokens()
  if error: return None, error
  
  # Generate AST
  parser = Parser(tokens)
  ast = parser.parse()
  if ast.error: return None, ast.error

  # Run program
  interpreter = Interpreter()
  context = Context('<program>')
  context.symbol_table = global_symbol_table
  result = interpreter.visit(ast.node, context)

  # Always return None to suppress printing extra zero after script execution
  return None, result.error
