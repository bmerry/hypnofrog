"""Property-based testing for competitive programming.

Still to do:
- Graceful SIGINT handling
"""

import argparse
import contextlib
import io
import resource
import subprocess
import sys
import tempfile
import time

from hypothesis import given, settings, Verbosity


class FailedCase(Exception):
    def __init__(self, message, input):
        super().__init__(message)
        self.files = {'hypnofrog.in': input}
        self.logs = {'input': input}


class BadAnswer(FailedCase):
    def __init__(self, message, input, output):
        super().__init__(message, input)
        self.files['hypnofrog.out'] = output


class AnswerMismatch(BadAnswer):
    def __init__(self, input, output, reference):
        super().__init__('Answer does not match the reference', input, output)
        self.files['hypnofrog.ref'] = reference


class CrashError(FailedCase):
    def __init__(self, input, error):
        super().__init__(f'Target crashed: {error}', input)
        if hasattr(error, 'stderr'):
            self.logs['stderr'] = error.stderr


class BadReferenceError(FailedCase):
    def __init__(self, input, error):
        super().__init__(f'Reference crashed: {error}', input)
        if hasattr(error, 'stderr'):
            self.logs['stderr'] = error.stderr


class FailedCheckerError(BadAnswer):
    def __init__(self, input, output, error):
        super().__init__(f'Checker failed: {error}', input, output)
        if hasattr(error, 'stdout'):
            self.logs['stderr'] = error.stdout


@contextlib.contextmanager
def capture_stdout():
    """Context manager that captures standard out, returning a StringIO.

    Use like this::

        with capture_stdout() as stdout:
            ...
        print(stdout.getvalue())
    """
    out = io.StringIO()
    real_stdout = sys.stdout
    sys.stdout = out
    yield out
    sys.stdout = real_stdout


def make_input(*args):
    """Convert lines of items into input text.

    Each element of *args corresponds to a line of input. Items that are
    themselves lists/tuples are space-separated.
    """
    return ''.join(
        (' '.join(str(x) for x in inner) if isinstance(inner, (tuple, list)) else str(inner)) + '\n'
        for inner in args
    )


def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('target', help='Program to test')
    parser.add_argument('--reference', help='Reference implementation')
    parser.add_argument('--checker', help='Checker implementation (takes input, output as args)')
    parser.add_argument('--mem-limit', '-m', type=int, help='Virtual memory limit (MB)')
    # TODO: add --checker, --base, --files
    args = parser.parse_args(argv if argv is not None else sys.argv[1:])
    return args



def invoke(program, input, mem_limit=None):
    def preexec():
        mem_limit_bytes = mem_limit * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (mem_limit_bytes, mem_limit_bytes))

    result = subprocess.run(
        [program],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        input=input,
        encoding='utf-8',
        check=True,
        close_fds=True,
        preexec_fn=preexec if mem_limit is not None else None
    )
    return result.stdout


def trial(input, args):
    try:
        start = time.monotonic()
        try:
            actual = invoke(args.target, input, args.mem_limit)
        except (subprocess.CalledProcessError, OSError) as exc:
            raise CrashError(input, exc) from exc
        end = time.monotonic()
        if args.reference is not None:
            try:
                expected = invoke(args.reference, input)
            except (subprocess.CalledProcessError, OSError) as exc:
                raise BadReferenceError(input, exc) from exc
            if expected != actual:
                raise AnswerMismatch(input, actual, expected)
        if args.checker is not None:
            with tempfile.NamedTemporaryFile('w+', encoding='utf-8', suffix='.in') as inf, \
                    tempfile.NamedTemporaryFile('w+', encoding='utf-8', suffix='.out') as outf:
                inf.write(input)
                inf.flush()
                outf.write(actual)
                outf.flush()
                try:
                    result = subprocess.run(
                        [args.checker, inf.name, outf.name],
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        encoding='utf-8',
                        check=True)
                except (subprocess.CalledProcessError, OSError) as exc:
                    raise FailedCheckerError(input, actual, exc) from exc
    except FailedCase:
        raise
    except Exception as exc:
        raise FailedCase(f'Unexpected error: {exc}', input) from exc
    return end - start


def run(strategy, args=None):
    @given(strategy)
    @settings(max_examples=1000000, verbosity=Verbosity.quiet)
    def test_function(data):
        nonlocal done, max_elapsed
        elapsed = trial(data, args)
        max_elapsed = max(max_elapsed, elapsed)
        done += 1
        print(f'\033[1G\033[K{done:6} iterations, max time {max_elapsed:.3f}', end='', flush=True)

    done = 0
    max_elapsed = 0.0
    if args is None:
        args = parse_args()
    try:
        test_function()
    except FailedCase as exc:
        print()
        print()
        print(exc)
        for name, content in exc.logs.items():
            if content:
                print()
                print(name)
                print()
                print(content.rstrip())
        print()
        print('Writing', ', '.join(exc.files.keys()))
        for name, content in exc.files.items():
            with open(name, 'w') as f:
                f.write(content)
        return 1
    else:
        return 0
