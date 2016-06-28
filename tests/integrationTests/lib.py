"""

"""
# pylint: disable=fixme,redefined-builtin,global-statement,broad-except
from __future__ import print_function
from collections import defaultdict
import datetime
import inspect
import json
import os
import subprocess
import traceback
import sys

# global variable available to be used by the test suite modules
SUBMITTY_INSTALL_DIR = "__INSTALL__FILLIN__SUBMITTY_INSTALL_DIR__"

GRADING_SOURCE_DIR = SUBMITTY_INSTALL_DIR + "/src/grading"

LOG_FILE = None
LOG_DIR = SUBMITTY_INSTALL_DIR + "/test_suite/log"


def print(*args, **kwargs):
    """
    Define the builtin print function such that in addition to outputting to the the stdout, we
    also log the message into a file that is timestamped in case we want to review the output
    from running the test suite

    :param args: strings to print
    :param kwargs: map of arguments for the string. 'end' for what should be appended to the end
    of the string and 'sep' for what should seperate the various *args
    :return:
    """
    global LOG_FILE
    if "sep" not in kwargs:
        kwargs["sep"] = " "
    if "end" not in kwargs:
        kwargs["end"] = '\n'

    message = kwargs["sep"].join([str(i) for i in args]) + kwargs["end"]
    if LOG_FILE is None:
        # include a couple microseconds in string so that we have unique log file
        # per test run
        LOG_FILE = datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]
    with open(os.path.join(LOG_DIR, LOG_FILE), 'a') as write_file:
        write_file.write(message)
    sys.stdout.write(message)


class TestcaseFile(object):
    # pylint: disable=too-few-public-methods
    def __init__(self):
        self.prebuild = lambda: None
        self.testcases = []

TO_RUN = defaultdict(lambda: TestcaseFile())  # pylint: disable=unnecessary-lambda


# Helpers for color
class ASCIIEscapeManager(object):
    # pylint: disable=too-few-public-methods
    def __init__(self, codes):
        self.codes = [str(code) for code in codes]

    def __enter__(self):
        sys.stdout.write("\033[" + ";".join(self.codes) + "m")

    def __exit__(self, exc_type, exc_value, trace_back):
        sys.stdout.write("\033[0m")

    def __add__(self, other):
        return ASCIIEscapeManager(self.codes + other.codes)

BOLD = ASCIIEscapeManager([1])
UNDERSCORE = ASCIIEscapeManager([4])
BLINK = ASCIIEscapeManager([5])

BLACK = ASCIIEscapeManager([30])
RED = ASCIIEscapeManager([31])
GREEN = ASCIIEscapeManager([32])
YELLOW = ASCIIEscapeManager([33])
BLUE = ASCIIEscapeManager([34])
MAGENTA = ASCIIEscapeManager([35])
CYAN = ASCIIEscapeManager([36])
WHITE = ASCIIEscapeManager([37])


# Run the given list of test case names
def run_tests(names):
    totalmodules = len(names)
    for key in names:
        val = TO_RUN[key]
        modsuccess = True
        with BOLD:
            print("--- BEGIN TEST MODULE " + key.upper() + " ---")
        cont = True
        try:
            print("* Starting compilation...")
            val.prebuild()
            val.wrapper.build()
            print("* Finished compilation")
        except Exception as exception:
            print("Build failed with exception: %s" % str(exception))
            modsuccess = False
            cont = False
        if cont:
            total = len(val.testcases)
            for index, func in zip(range(1, total + 1), val.testcases):
                try:
                    func()
                except Exception as exception:
                    with BOLD + RED:
                        lineno = None
                        trace = traceback.extract_tb(sys.exc_info()[2])
                        # Go through the trace to find exactly when __init__.py threw an exception
                        # as that would be coming from the running test module
                        for i in range(len(trace)-1, -1, -1):
                            if os.path.basename(trace[i][0]) == '__init__.py':
                                lineno = trace[i][1]
                        print("Testcase " + str(index) + " failed on line " + str(lineno) +
                              " with exception: ", exception)
                        sys.exc_info()
                        total -= 1
            if total == len(val.testcases):
                with BOLD + GREEN:
                    print("All testcases passed")
            else:
                with BOLD + RED:
                    print(str(total) + "/" + str(len(val.testcases)) + " testcases passed")
                    modsuccess = False
        with BOLD:
            print("--- END TEST MODULE " + key.upper() + " ---")
        print()
        if not modsuccess:
            totalmodules -= 1
    if totalmodules == len(names):
        with BOLD + GREEN:
            print("All modules passed")
    else:
        with BOLD + RED:
            print(str(totalmodules) + "/" + str(len(names)) + " modules passed")
        sys.exit(1)


# Run every test currently loaded
def run_all():
    run_tests(TO_RUN.keys())


# Helper class used to remove the burden of paths from the testcase author.
# The path (in /var/local) of the testcase is provided to the constructor,
# and is subsequently used in all methods for compilation, linkage, etc.
# The resulting object is passed to each function defined within the testcase
# package. Typically, one would use the @testcase decorator defined below,
# as it uses inspection to fully handle all paths with no input from the
# testcase author.
class TestcaseWrapper:
    def __init__(self, path):
        self.testcase_path = path

    # Compile each .cpp file into an object file in the current directory. Those
    # object files are then moved into the appropriate directory in the /var/local
    # tree. Unfortunately, this presents some issues, for example non-grading
    # object files in that directory being moved and subsequently linked with the
    # rest of the program. gcc/clang do not provide an option to specify an output
    # directory when compiling source files in bulk in this manner. The solution
    # is likely to run the compiler with a different working directory alongside
    # using relative paths.
    def build(self):
        try:
            # the log directory will contain various log files
            os.mkdir(os.path.join(self.testcase_path, "log"))
            # the build directory will contain the intermediate cmake files
            os.mkdir(os.path.join(self.testcase_path, "build"))
            # the bin directory will contain the autograding executables
            os.mkdir(os.path.join(self.testcase_path, "bin"))
        except OSError:
            pass
        # copy the cmake file to the build directory
        subprocess.call(["cp",
                         os.path.join(GRADING_SOURCE_DIR, "Sample_CMakeLists.txt"),
                         os.path.join(self.testcase_path, "build", "CMakeLists.txt")])
        filename = os.path.join(self.testcase_path, "log", "cmake_output.txt")
        with open(filename, "w") as cmake_output:
            return_code = subprocess.call(["cmake", "-DASSIGNMENT_INSTALLATION=OFF", "."],
                                          cwd=os.path.join(self.testcase_path, "build"),
                                          stdout=cmake_output, stderr=cmake_output)
            if return_code != 0:
                raise RuntimeError("Build (cmake) exited with exit code " + str(return_code))
        with open(os.path.join(self.testcase_path, "log", "make_output.txt"), "w") as make_output:
            return_code = subprocess.call(["make"],
                                          cwd=os.path.join(self.testcase_path, "build"),
                                          stdout=make_output, stderr=make_output)
            if return_code != 0:
                raise RuntimeError("Build (make) exited with exit code " + str(return_code))

    # Run compile.out using some sane arguments.
    def run_compile(self):
        with open(os.path.join(self.testcase_path, "log", "compile_output.txt"), "w") as log:
            return_code = subprocess.call([os.path.join(self.testcase_path, "bin", "compile.out"),
                                           "testassignment", "testuser", "1", "0"],
                                          cwd=os.path.join(self.testcase_path, "data"), stdout=log,
                                          stderr=log)
            if return_code != 0:
                raise RuntimeError("Compile exited with exit code " + str(return_code))

    # Run run.out using some sane arguments.
    def run_run(self):
        with open(os.path.join(self.testcase_path, "log", "run_output.txt"), "w") as log:
            return_code = subprocess.call([os.path.join(self.testcase_path, "bin", "run.out"),
                                           "testassignment", "testuser", "1", "0"],
                                          cwd=os.path.join(self.testcase_path, "data"),
                                          stdout=log, stderr=log)
            if return_code != 0:
                raise RuntimeError("run.out exited with exit code " + str(return_code))

    # Run the validator using some sane arguments. Likely wants to be made much more
    # customizable (different submission numbers, multiple users, etc.)
    # TODO: Read "main" for other executables, determine what files they expect and
    # the locations in which they expect them given different inputs.
    def run_validator(self):
        with open(os.path.join(self.testcase_path, "log", "validate_output.txt"), "w") as log:
            return_code = subprocess.call([os.path.join(self.testcase_path, "bin", "validate.out"),
                                           "testassignment", "testuser", "1", "0"],
                                          cwd=os.path.join(self.testcase_path, "data"), stdout=log,
                                          stderr=log)
            if return_code != 0:
                raise RuntimeError("Validator exited with exit code " + str(return_code))

    # Run the UNIX diff command given a filename. The files are compared between the
    # data folder and the validation folder within the test package. For example,
    # running test.diff("foo.txt") within the test package "test_foo", the files
    # /var/local/autograde_tests/tests/test_foo/data/foo.txt and
    # /var/local/autograde_tests/tests/test_foo/validation/foo.txt will be compared.
    def diff(self, file1, file2=""):
        # if only 1 filename provided...
        if not file2:
            file2 = file1
        # if no directory provided...
        if not os.path.dirname(file1):
            file1 = os.path.join("data", file1)
        if not os.path.dirname(file2):
            file2 = os.path.join("validation", file2)

        filename1 = os.path.join(self.testcase_path, file1)
        filename2 = os.path.join(self.testcase_path, file2)

        if not os.path.isfile(filename1):
            raise RuntimeError("File " + filename1 + " does not exist")
        if not os.path.isfile(filename2):
            raise RuntimeError("File " + filename2 + " does not exist")

        # return_code = subprocess.call(["diff", "-b", filename1, filename2]) #ignores changes in
        # white space
        process = subprocess.Popen(["diff", filename1, filename2], stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        out, _ = process.communicate()
        if process.returncode == 1:
            raise RuntimeError("Difference between " + filename1 + " and " + filename2 + " exited "
                               "with exit code " + str(process.returncode) + '\n\nDiff:\n' +
                               out.decode())

    # Helper function for json_diff.  Sorts each nested list.  Allows comparison.
    # Credit: Zero Piraeus.
    # http://stackoverflow.com/questions/25851183/how-to-compare-two-json-objects-with-the-same-
    # elements-in-a-different-order-equa
    def json_ordered(self, obj):
        if isinstance(obj, dict):
            return sorted((k, self.json_ordered(v)) for k, v in obj.items())
        if isinstance(obj, list):
            return sorted(self.json_ordered(x) for x in obj)
        else:
            return obj

    # Compares two json files allowing differences in file whitespace
    # (indentation, newlines, etc) and also alternate ordering of data
    # inside dictionary/key-value pairs
    def json_diff(self, filename1, filename2=""):
        # if only 1 filename provided...
        if not filename2:
            filename2 = filename1
        # if no directory provided...
        if not os.path.dirname(filename1):
            filename1 = os.path.join("data", filename1)
        if not os.path.dirname(filename2):
            filename2 = os.path.join("validation", filename2)

        filename1 = os.path.join(self.testcase_path, filename1)
        filename2 = os.path.join(self.testcase_path, filename2)

        if not os.path.isfile(filename1):
            raise RuntimeError("File " + filename1 + " does not exist")
        if not os.path.isfile(filename2):
            raise RuntimeError("File " + filename2 + " does not exist")

        with open(filename1) as file1:
            contents1 = json.load(file1)
        with open(filename2) as file2:
            contents2 = json.load(file2)
        if self.json_ordered(contents1) != self.json_ordered(contents2):
            raise RuntimeError("JSON files " + filename1 + " and " + filename2 + " are different")

    def empty_file(self, filename):
        # if no directory provided...
        if not os.path.dirname(filename):
            filename = os.path.join("data", filename)
        filename = os.path.join(self.testcase_path, filename)
        if not os.path.isfile(filename):
            raise RuntimeError("File " + filename + " should exist")
        if os.stat(filename).st_size != 0:
            raise RuntimeError("File " + filename + " should be empty")

    def empty_json_diff(self, filename):
        # if no directory provided...
        if not os.path.dirname(filename):
            filename = os.path.join("data", filename)
        filename1 = os.path.join(self.testcase_path, filename)
        filename2 = os.path.join(SUBMITTY_INSTALL_DIR,
                                 "test_suite/integrationTests/data/empty_json_diff_file.json")
        return self.json_diff(filename1, filename2)


def prebuild(func):
    mod = inspect.getmodule(inspect.stack()[1][0])
    path = os.path.dirname(mod.__file__)
    modname = mod.__name__
    test_wrapper = TestcaseWrapper(path)

    def wrapper():
        print("* Starting prebuild for " + modname + "... ", end="")
        func(test_wrapper)
        print("Done")
    # pylint: disable=global-variable-not-assigned
    global TO_RUN
    TO_RUN[modname].wrapper = test_wrapper
    TO_RUN[modname].prebuild = wrapper
    return wrapper


# Decorator function using some inspection trickery to determine paths
def testcase(func):
    # inspect.stack() gets the current program stack. Index 1 is one
    # level up from the current stack frame, which in this case will
    # be the frame of the function calling this decorator. The first
    # element of that tuple is a frame object, which can be passed to
    # inspect.getmodule to fetch the module associated with that frame.
    # From there, we can get the path of that module, and infer the rest
    # of the required information.
    mod = inspect.getmodule(inspect.stack()[1][0])
    path = os.path.dirname(mod.__file__)
    modname = mod.__name__
    test_wrapper = TestcaseWrapper(path)

    def wrapper():
        print("* Starting testcase " + modname + "." + func.__name__ + "... ", end="")
        try:
            func(test_wrapper)
            with BOLD + GREEN:
                print("PASSED")
        except Exception:
            with BOLD + RED:
                print("FAILED")
            # blank raise raises the last exception as is
            raise

    # pylint: disable=global-variable-not-assigned
    global TO_RUN
    TO_RUN[modname].wrapper = test_wrapper
    TO_RUN[modname].testcases.append(wrapper)
    return wrapper