
from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

import threading, code, logging, queue
from contextlib import contextmanager

log = logging.getLogger(__name__)

import muz
from muz.util import forever
from .frontend.misc import QuitRequest

CMD_UNHANDLED, CMD_HANDLED, CMD_UNFINISHED = range(3)

class Console(object):
    def __init__(self, handlers=None):
        if handlers is None:
            handlers = []

        self.handlers = handlers
        self.inputQueue = queue.Queue()
        self.syncQueue = queue.Queue()
        self.buffer = ""

        self.syncQueue.put(True)

    def process(self):
        try:
            inp = self.inputQueue.get(block=False)
        except queue.Empty:
            return

        self.inputQueue.task_done()

        if inp is QuitRequest:
            raise QuitRequest

        self.buffer += inp

        try:
            for handler in self.handlers:
                c = handler(self.buffer)

                if c == CMD_UNHANDLED:
                    continue

                handled = True

                if c == CMD_HANDLED:
                    self.buffer = ""
                elif c == CMD_UNFINISHED:
                    self.buffer += "\n"
                else:
                    raise ValueError("handler returned invalid status %s" % repr(c))

                break
            else:
                raise RuntimeError("Command %s couldn't be handled" % repr(self.buffer))

            self.syncQueue.put(True)
        except (QuitRequest, SystemExit, EOFError):
            raise QuitRequest
        except Exception as e:
            log.exception("console error: %s", e)
            self.buffer = ""
            self.syncQueue.put(True)

    @contextmanager
    def sync(self):
        self.syncQueue.get()
        yield
        self.syncQueue.task_done()

    def push(self, inp):
        self.inputQueue.put(inp)

class PythonHandler(object):
    def __init__(self, scope=None):
        if scope is None:
            scope = {}
        self.scope = scope

    def __call__(self, buf):
        c = code.compile_command(buf, "<console>")
        if c is None:
            return CMD_UNFINISHED

        exec(c, self.scope)
        return CMD_HANDLED

class AsyncInput(object):
    @staticmethod
    def initReadline(scope=None):
        try:
            import readline
        except ImportError:
            log.warning("readline is not available")
            return

        import rlcompleter
        readline.parse_and_bind("tab: complete")

        @readline.set_completer
        def completer(text, state, oldcomp=readline.get_completer()):
            stext = text.strip()
            if not stext:
                if state:
                    return None
                return "\t"

            if scope is not None:
                l = tuple(n for n in scope if n.startswith(stext))
                if l:
                    if len(l) > state:
                        return l[state]
                    return None

            if oldcomp:
                return oldcomp(text, state)

    def __init__(self, console, inputFunc=input):
        prompt = "[%s] " % muz.main.NAME

        @forever
        def worker():
            with console.sync():
                try:
                    i = inputFunc(prompt + ("... " if console.buffer else ">>> "))
                except EOFError:
                    print()
                    console.push(QuitRequest)
                else:
                    console.push(i)

        thread = threading.Thread(name="console", target=worker)
        thread.daemon = True
        self.thread = thread

    def start(self):
        self.thread.start()
