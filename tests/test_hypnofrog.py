import argparse
import os

import pytest

import hypnofrog


def solution(basename):
    return os.path.join(os.path.dirname(__file__), basename)


def test_capture_stdout():
    with hypnofrog.capture_stdout() as stdout:
        print('Hello world')
    assert stdout.getvalue() == 'Hello world\n'


def test_make_input():
    input = hypnofrog.make_input(1, [2, 3], (4, 5), 'hello', ['wo', 'rld'])
    assert input == '1\n2 3\n4 5\nhello\nwo rld\n'
    assert hypnofrog.make_input() == ''


def test_trial_success():
    args = hypnofrog.parse_args([solution('passthrough'), '--reference', solution('helloworld')])
    hypnofrog.trial('hello world\n', args)


def test_trial_mismatch():
    args = hypnofrog.parse_args([solution('passthrough'), '--reference', solution('helloworld')])
    with pytest.raises(hypnofrog.AnswerMismatch) as excinfo:
        hypnofrog.trial('wrong answer\n', args)
    assert excinfo.value.files == {
        'hypnofrog.in': 'wrong answer\n',
        'hypnofrog.out': '1\nwrong answer\n',
        'hypnofrog.ref': '1\nhello world\n'
    }
    assert excinfo.value.logs == {'input': 'wrong answer\n'}


def test_trial_crash():
    args = hypnofrog.parse_args([solution('crash'), '--reference', solution('helloworld')])
    with pytest.raises(hypnofrog.CrashError,
                       match='Target crashed: .* returned non-zero exit status 1') as excinfo:
        hypnofrog.trial('crash\n', args)
    assert excinfo.value.files == {'hypnofrog.in': 'crash\n'}
    assert excinfo.value.logs == {'input': 'crash\n', 'stderr': 'I crash\n'}


def test_trial_target_not_found():
    args = hypnofrog.parse_args([solution('does not exist'), '--reference', solution('helloworld')])
    with pytest.raises(hypnofrog.CrashError,
                       match='Target crashed: .* No such file.*') as excinfo:
        hypnofrog.trial('crash\n', args)
    assert excinfo.value.files == {'hypnofrog.in': 'crash\n'}
    assert excinfo.value.logs == {'input': 'crash\n'}


def test_trial_mem_limit():
    args = hypnofrog.parse_args([
        solution('memory_hog'),
        '--reference', solution('helloworld'),
        '--mem-limit', '64'
    ])
    with pytest.raises(hypnofrog.CrashError):
        hypnofrog.trial('hello world\n', args)
    # Make sure it passes without the memory limit
    args.mem_limit = None
    hypnofrog.trial('hello world\n', args)


def test_trial_bad_reference():
    args = hypnofrog.parse_args([solution('passthrough'), '--reference', solution('crash')])
    with pytest.raises(hypnofrog.BadReferenceError,
                       match='Reference crashed: .* returned non-zero exit status 1') as excinfo:
        hypnofrog.trial('crash\n', args)
    assert excinfo.value.files == {'hypnofrog.in': 'crash\n'}
    assert excinfo.value.logs == {'input': 'crash\n', 'stderr': 'I crash\n'}


def test_trial_no_reference():
    args = hypnofrog.parse_args([solution('passthrough')])
    hypnofrog.trial('hello world\n', args)


def test_trial_no_reference_crash():
    args = hypnofrog.parse_args([solution('crash')])
    with pytest.raises(hypnofrog.CrashError,
                       match='Target crashed: .* returned non-zero exit status 1') as excinfo:
        hypnofrog.trial('crash\n', args)
    assert excinfo.value.files == {'hypnofrog.in': 'crash\n'}
    assert excinfo.value.logs == {'input': 'crash\n', 'stderr': 'I crash\n'}


def test_trial_checker_pass():
    args = hypnofrog.parse_args([solution('helloworld'), '--checker', solution('check_same')])
    hypnofrog.trial('1\nhello world\n', args)


def test_trial_checker_fail():
    args = hypnofrog.parse_args([solution('helloworld'), '--checker', solution('check_same')])
    with pytest.raises(hypnofrog.FailedCheckerError,
                       match='Checker failed: .* returned non-zero exit status 1') as excinfo:
        hypnofrog.trial('wrong\n', args)
    assert excinfo.value.files == {
        'hypnofrog.in': 'wrong\n',
        'hypnofrog.out': '1\nhello world\n'
    }
    assert excinfo.value.logs == {
        'input': 'wrong\n',
        'stderr': 'Answers differ\n'
    }
