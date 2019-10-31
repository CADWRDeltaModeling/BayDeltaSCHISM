""" A customized version of YAML parser for SCHISM
    It stores document in an ordered dict and supports variable substitution.
"""

import yaml
from yaml.reader import *
from yaml.scanner import *
from yaml.parser import *
from yaml.composer import *
from yaml.constructor import *
from yaml.resolver import *
from yaml.nodes import *
from yaml.dumper import *
from yaml.loader import *
from yaml.tokens import *
import collections
import string
import re
import os
import argparse
import sys

__all__ = ["load", "dump", "YamlAction", "ArgumentParserYaml"]
include_keywords = ["include",]
substitute_keywords = ["config", "env",]
yaml_extensions = [".yaml",]

def check_env(env):
    """ Check the integrity of environment variables
    """
    msg = ""
    n_errors = 0
    for k, v in env.items():
        if '$' in k:
            msg += "A Name of environment variable cannot be a variable: " \
                   "%s\n" % k
            n_errors += 1
        if not isinstance(v, str):
            msg += "Environment variables do not accept non-scalar " \
                   "variables: %s\n" % k
            n_errors += 1
    if n_errors > 0:
        raise ValueError(msg)


def substitute_env(env):
    """ Substitute environmental variables
    """
    if env is None:
        return
    check_env(env)
    while True:
        count_substitutions = 0
        for k, v in env.items():
            template = string.Template(v)
            substituted = template.safe_substitute(**env)
            if v != substituted:
                env[k] = substituted
                count_substitutions += 1
        if count_substitutions == 0:
            break


class SubstituteComposer(Composer):
    """ Composer with substitution
    """
    def __init__(self, env=None):
        self.env = env
        super(SubstituteComposer, self).__init__()

    def compose_scalar_node(self, anchor):
        if self.env is None:
            return super(SubstituteComposer, self).compose_scalar_node(anchor)
        event = self.get_event()
        tag = event.tag
        if tag is None or tag == '!':
            tag = self.resolve(ScalarNode, event.value, event.implicit)
        template = string.Template(event.value)
        value = template.safe_substitute(**self.env)
        if '$' in value:
            raise ComposerError("Expected a substitution",
                                event.start_mark,
                                "No corresponding config variable")
        node = ScalarNode(tag, value,
                event.start_mark, event.end_mark, style=event.style)
        if anchor is not None:
            self.anchors[anchor] = node
        return node


class SubstituteConstructor(SafeConstructor):
    """ Customized constructor for including.
        If a key value is one of include_keywords, a following YAML file
        will be included.
    """
    def __init__(self, env=None):
        self.env = env
        super(SubstituteConstructor, self).__init__()
        # super(SubstituteConstructor, self).add_constructor('!include',
                                              # SubstituteConstructor.include)

    def construct_pairs(self, node, deep=False):
        """ Overridden construct_pairs function with substitution
        """
        if not isinstance(node, MappingNode):
            raise ConstructorError(None, None,
                    "expected a mapping node, but found %s" % node.id,
                    node.start_mark)
        pairs = []
        for key_node, value_node in node.value:
            if key_node.value in include_keywords:
                included = self.include(value_node)
                if isinstance(included, dict):
                    pairs.extend(iter(included.items()))
                else:
                    raise ValueError("Included YAML must be a dictionary")
            else:
                key = self.construct_object(key_node, deep=deep)
                value = self.construct_object(value_node, deep=deep)
                pairs.append((key, value))
        return pairs

    def include(self, node):
        """ Process a node with !include tag.
            This code is copied from Stackoverflow.
        """
        if isinstance(node, yaml.ScalarNode):
            return self.extractFile(self.construct_scalar(node))
        elif isinstance(node, yaml.SequenceNode):
            result = []
            for filename in self.construct_sequence(node):
                result += self.extractFile(filename)
            return result
        elif isinstance(node, yaml.MappingNode):
            result = {}
            for k, v in self.construct_mapping(node).items():
                result[k] = self.extractFile(v)
            return result
        else:
            print("Error: unrecognized node type in the include constructor")
            raise ConstructorError

    def extractFile(self, filename):
        """ Load an yaml file to include
        """
        filepath = os.path.join(self.root, filename)
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                loader = SubstituteLoader(f, self.env)
                return loader.get_single_data()
        else:
            print("Error: cannot find the file:" + filename)
            raise ValueError('Cannot find included file: {}'.format(filename))


SubstituteConstructor.add_constructor('!include',
                                      SubstituteConstructor.include)


class SubstituteLoader(Reader, Scanner, Parser,
                       SubstituteComposer, SubstituteConstructor,
                       Resolver):
    """ Raw Loader with substitute.
    """
    def __init__(self, stream, env):
        """ Constructor
        """
        self.root = os.path.split(stream.name)[0]
        Reader.__init__(self, stream)
        Scanner.__init__(self)
        Parser.__init__(self)
        SubstituteComposer.__init__(self, env)
        SubstituteConstructor.__init__(self, env)
        Resolver.__init__(self)


class SubstituteRawLoader(Reader, Scanner, Parser,
                          SubstituteComposer, SubstituteConstructor,
                          BaseResolver):
    """ Raw Loader with substitute.
    """
    def __init__(self, stream, env):
        """ Constructor
        """
        self.root = os.path.split(stream.name)[0]
        Reader.__init__(self, stream)
        Scanner.__init__(self)
        Parser.__init__(self)
        SubstituteComposer.__init__(self, env)
        SubstituteConstructor.__init__(self, env)
        BaseResolver.__init__(self)


class RawLoader(Reader, Scanner, Parser,
                Composer, SubstituteConstructor,
                BaseResolver):
    """ Raw Loader, No automatic resolving.
    """
    def __init__(self, stream):
        self.root = os.path.split(stream.name)[0]
        Reader.__init__(self, stream)
        Scanner.__init__(self)
        Parser.__init__(self)
        Composer.__init__(self)
        SubstituteConstructor.__init__(self)
        BaseResolver.__init__(self)


def dict_constructor(loader, node):
    """ Constructor with OrderedDict
    """
    return collections.OrderedDict(loader.construct_pairs(node))


def dict_representer(dumper, data):
    """ Dumper with OrderedDict
    """
    return dumper.represent_mapping(BaseResolver.DEFAULT_MAPPING_TAG,
                                    iter(data.items()))


# Add constructor and representer
yaml.add_representer(collections.OrderedDict, dict_representer,
                     Dumper=SafeDumper)
yaml.add_constructor(BaseResolver.DEFAULT_MAPPING_TAG,
                     dict_constructor, Loader=SubstituteLoader)
yaml.add_constructor(BaseResolver.DEFAULT_MAPPING_TAG,
                     dict_constructor, Loader=RawLoader)


def load(stream):
    """ Load a schism YAML
    """
    # First round to get environmental variables
    loader = RawLoader(stream)
    try:
        data = loader.get_single_data()
    finally:
        loader.dispose()
    stream.seek(0)

    # Second round with substitution
    env = {}
    for key in substitute_keywords:
        if key in data:
            env.update(data[key])
    substitute_env(env)
    loader = SubstituteLoader(stream, env)
    try:
        data = loader.get_single_data()
        return data
    finally:
        loader.dispose()


def load_raw(stream):
    """ Load a schism YAML
    """
    # First round to get environmental variables
    loader = RawLoader(stream)
    try:
        data = loader.get_single_data()
    finally:
        loader.dispose()
    stream.seek(0)

    # Second round with substitution
    env = {}
    for key in substitute_keywords:
        if key in data:
            env.update(data[key])
    substitute_env(env)
    loader = SubstituteRawLoader(stream, env)
    try:
        data = loader.get_single_data()
        return data
    finally:
        loader.dispose()


def dump(data, stream=None, Dumper=Dumper, **kwds):
    """
    Serialize a Python object into a YAML stream.
    If stream is None, return the produced string instead.
    """
    return yaml.dump(data, stream, Dumper=Dumper, **kwds)


def safe_dump(data, stream=None, **kwds):
    """
    Serialize a Python object into a YAML stream.
    If stream is None, return the produced string instead.
    """
    return yaml.safe_dump(data, stream, **kwds)


class YamlAction(argparse.Action):
    """ Custom action to parse YAML files for argparse.
        This action reads in simple pairs of data from a YAML file, and
        feeds them to the parser. A YAML file must be a list of pairs
        without multiple levels of tree.
        Example:
        parser.add_argument("--yaml", action=YamlAction)
    """
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        super(YamlAction, self).__init__(option_strings, dest,
                                         nargs=nargs, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        if not isinstance(values, list):
            values = [values]
        args_string = []
        for value in values:
            with open(value) as f:
                loader = RawLoader(f)
                try:
                    data = loader.get_single_data()
                finally:
                    loader.dispose()
                for k, v in data.items():
                    if re.search(r"[\s]", k):
                        raise ValueError("No whitespace is allowed in the key.")
                    if not isinstance(v, str):
                        raise ValueError("Only plain string is allowed in the value.")
                    arg = "--%s %s" % (k, v)
                    args_string.extend(arg.split())
        args, argv = parser.parse_known_args(args_string, namespace)


class ArgumentParserYaml(argparse.ArgumentParser):
    """ Extended parser to handle YAML file as file input for ArgumentParser.
        If a file input given with 'fromfile_prefix_chars' has a YAML extension,
        '.yaml', it will be handled as optional pairs for ArgumentParser.
        For example, 'script.py' can use a YAML file for an input file of 
        ArgumentParser as follow:
        parser = schism_yaml.ArgumentParserYaml(fromfile_prefix_chars='@')
        parser.parse_arg()

        $script.py @args.yaml

        And when 'args.yaml' contains:
        input1: 1
        input2: 2 3

        it has the same effect as
        $script.py --input1 1 --input2 2 3
    """
    def __init__(self,
                 prog=None,
                 usage=None,
                 description=None,
                 epilog=None,
                 version=None,
                 parents=[],
                 formatter_class=argparse.HelpFormatter,
                 prefix_chars='-',
                 fromfile_prefix_chars=None,
                 argument_default=None,
                 conflict_handler='error',
                 add_help=True):
        if sys.version_info[0] == 2:
            super(ArgumentParserYaml, self).__init__(prog, usage,
                                                    description, epilog,
                                                    version, parents,
                                                    formatter_class,
                                                    prefix_chars,
                                                    fromfile_prefix_chars,
                                                    argument_default,
                                                    conflict_handler,
                                                    add_help)
        elif sys.version_info[0] == 3:
            super(ArgumentParserYaml, self).__init__(prog, usage,
                                                    description, epilog,
                                                    parents,
                                                    formatter_class,
                                                    prefix_chars,
                                                    fromfile_prefix_chars,
                                                    argument_default,
                                                    conflict_handler,
                                                    add_help)
        else:
            raise NotImplementedError("Not supported Python version")

    def _read_args_from_files(self, arg_strings):
        """ Override this function to handle YAML files
        """
        # expand arguments referencing files
        new_arg_strings = []
        for arg_string in arg_strings:
            # for regular arguments, just add them back into the list
            if not arg_string or arg_string[0] not in self.fromfile_prefix_chars:
                new_arg_strings.append(arg_string)

            # replace arguments referencing files with the file content
            else:
                _, ext = os.path.splitext(arg_string[1:])
                if ext in yaml_extensions:
                    try:
                        with open(arg_string[1:]) as args_file:
                            loader = RawLoader(args_file)
                            try:
                                data = loader.get_single_data()
                            finally:
                                loader.dispose()
                            for k, v in data.items():
                                if re.search(r"[\s]", k):
                                    raise ValueError("No whitespace is allowed in the key.")
                                if not isinstance(v, str):
                                    raise ValueError("Only plain string is allowed in the value.")
                                arg = "--%s %s" % (k, v)
                                arg = arg.split()
                                # No recursive call
                                new_arg_strings.extend(arg)
                    except IOError:
                        err = sys.exc_info()[1]
                        self.error(str(err))
                else:
                    try:
                        args_file = open(arg_string[1:])
                        try:
                            arg_strings = []
                            for arg_line in args_file.read().splitlines():
                                for arg in self.convert_arg_line_to_args(arg_line):
                                    arg_strings.append(arg)
                            arg_strings = self._read_args_from_files(arg_strings)
                            new_arg_strings.extend(arg_strings)
                        finally:
                            args_file.close()
                    except IOError:
                        err = sys.exc_info()[1]
                        self.error(str(err))

        # return the modified argument list
        return new_arg_strings


def create_arg_parser():
    """ Create a command line argument parser
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('filename', type=str, help="A YAML file that follows SCHSIM YAML.")
    return parser


if __name__ == "__main__":
    parser_ = create_arg_parser()
    args_ = parser_.parse_args()
    fname_ = args_.filename
    with open(fname_, 'r') as f:
        data_ = load(f)
        print(yaml.safe_dump(data_))
