from __future__ import absolute_import, print_function, unicode_literals

import logging
import os
import sys

from wolframclient.deserializers import binary_deserialize
from wolframclient.language import wl
from wolframclient.language.decorators import safe_wl_execute_many
from wolframclient.language.side_effects import side_effect_logger
from wolframclient.serializers import export
from wolframclient.utils import six
from wolframclient.utils.api import ast, zmq
from wolframclient.utils.datastructures import Settings
from wolframclient.utils.encoding import force_text
from wolframclient.utils.functional import last
from wolframclient.utils.itertools import safe_len, iter_with_last

HIDDEN_VARIABLES = (
    "__loader__",
    "__builtins__",
    "__traceback_hidden_variables__",
    "absolute_import",
    "print_function",
    "unicode_literals",
)

EXPORT_KWARGS = {"target_format": "wxf", "allow_external_objects": True}

if six.PY_38:

    # https://bugs.python.org/issue35766
    # https://bugs.python.org/issue35894
    # https://github.com/ipython/ipython/issues/11590
    # PY_38 requires type_ignores to be a list, other versions are not accepting a second argument

    def Module(code, type_ignores=[]):
        return ast.Module(code, type_ignores)


else:

    def Module(code):
        return ast.Module(code)





class MergedMessages:

    merge_next = wl.ExternalEvaluate.Private.ExternalEvaluateMergeNext
    missing = object()

    def __init__(self, func, iterable, length = None):
        self.func = func
        self.iterable = iterable
        self.length = length

    def __iter__(self):
        for el, is_last in iter_with_last(self.iterable, length = self.length):
            if is_last:
                yield el
            else:
                yield self.merge_next(self.func, el)


def EvaluationEnvironment(code, session_data={}, constants=None, **extra):

    session_data["__loader__"] = Settings(get_source=lambda module, code=code: code)
    session_data["__traceback_hidden_variables__"] = HIDDEN_VARIABLES
    if constants:
        session_data.update(constants)

    return session_data


def execute_from_file(path, *args, **opts):
    with open(path, "r") as f:
        return execute_from_string(force_text(f.read()), *args, **opts)


def execute_from_string(code, globals={}, **opts):

    __traceback_hidden_variables__ = ["env", "current", "__traceback_hidden_variables__"]

    # this is creating a custom __loader__ that is returning the source code
    # traceback serializers is inspecting global variables and looking for a standard loader that can return source code.

    env = EvaluationEnvironment(code=code, **opts)
    result = None
    expressions = list(
        compile(
            code,
            filename="<unknown>",
            mode="exec",
            flags=ast.PyCF_ONLY_AST | unicode_literals.compiler_flag,
        ).body
    )

    if not expressions:
        return

    last_expr = last(expressions)

    if isinstance(last_expr, ast.Expr):
        result = expressions.pop(-1)

    if expressions:
        exec(compile(Module(expressions), "", "exec"), env)

    if result:
        return eval(compile(ast.Expression(result.value), "", "eval"), env)

    elif isinstance(last_expr, (ast.FunctionDef, ast.ClassDef)):
        return env[last_expr.name]


class SideEffectSender(logging.Handler):
    def emit(self, record):
        if isinstance(sys.stdout, StdoutProxy):
            sys.stdout.send_side_effect(record.msg)


class SocketWriter:
    def __init__(self, socket):
        self.socket = socket

    def write(self, bytes):
        self.socket.send(zmq.Frame(bytes))


class StdoutProxy:

    keep_listening = wl.ExternalEvaluate.Private.ExternalEvaluateKeepListening

    def __init__(self, stream):
        self.stream = stream
        self.clear()

    def clear(self):
        self.current_line = []
        self.lines = []

    def write(self, message):
        messages = force_text(message).split("\n")

        if len(messages) == 1:
            self.current_line.extend(messages)
        else:
            self.current_line.append(messages.pop(0))
            rest = messages.pop(-1)

            self.lines.extend(messages)
            self.flush()
            if rest:
                self.current_line.append(rest)

    def flush(self):
        if self.current_line or self.lines:
            self.send_lines("".join(self.current_line), *self.lines)
            self.clear()

    def send_lines(self, *lines):
        if len(lines) == 1:
            return self.send_side_effect(wl.Print(*lines))
        elif lines:
            return self.send_side_effect(wl.CompoundExpression(*map(wl.Print, lines)))

    def send_side_effect(self, expr):
        self.stream.write(export(self.keep_listening(expr), **EXPORT_KWARGS))


def evaluate_message(input=None, return_type=None, args=None, **opts):

    __traceback_hidden_variables__ = True

    result = None

    if isinstance(input, six.string_types):
        result = execute_from_string(input, **opts)

    if isinstance(args, (list, tuple)):
        # then we have a function call to do
        # first get the function object we need to call
        result = result(*args)

    if return_type == "string":
        # bug 354267 repr returns a 'str' even on py2 (i.e. bytes).
        result = force_text(repr(result))

    return result


def handle_message(socket, evaluate_message=evaluate_message, consumer=None):

    __traceback_hidden_variables__ = True

    message = binary_deserialize(socket.recv(copy=False).buffer, consumer=consumer)

    result = evaluate_message(**message)

    if isinstance(result, MergedMessages):
        for chunk in result:
            yield chunk
    else:
        yield result

    sys.stdout.flush()


def start_zmq_instance(port=None, write_to_stdout=True, **opts):

    # make a reply socket
    sock = zmq.Context.instance().socket(zmq.PAIR)
    # now bind to a open port on localhost
    if port:
        sock.bind("tcp://127.0.0.1:%s" % port)
    else:
        sock.bind_to_random_port("tcp://127.0.0.1")

    if write_to_stdout:
        sys.stdout.write(force_text(sock.getsockopt(zmq.LAST_ENDPOINT)))
        sys.stdout.write(os.linesep)  # writes \n
        sys.stdout.flush()

    return sock


def start_zmq_loop(
    message_limit=float("inf"),
    redirect_stdout=True,
    export_kwargs=EXPORT_KWARGS,
    evaluate_message=evaluate_message,
    exception_class=None,
    consumer=None,
    **opts
):

    socket = start_zmq_instance(**opts)

    handler = lambda *args, **opts: safe_wl_execute_many(
        handle_message,
        opts=dict(socket=socket, evaluate_message=evaluate_message, consumer=consumer),
        exception_class=exception_class,
        export_opts=export_kwargs,
    )

    stream = SocketWriter(socket)

    messages = 0

    if redirect_stdout:
        sys.stdout = StdoutProxy(stream)

    side_effect_logger.addHandler(SideEffectSender())

    # now sit in a while loop, evaluating input
    while messages < message_limit:
        for msg in handler():
            stream.write(msg)
        messages += 1

    if redirect_stdout:
        sys.stdout = sys.__stdout__
