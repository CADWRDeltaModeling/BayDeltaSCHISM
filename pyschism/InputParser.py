# Simple input parser based on ConfigParser
# Only additions are echoing.
# ConfigParser follows format of common INI files with substitutions.

import configparser

class InputParser(configparser.SafeConfigParser):
    def __init__(self):
#         super(InputParser, self).__init__(self)
        configparser.SafeConfigParser.__init__(self)
        self._param = dict()

        
    def read(self, fname):
        """ Read an input file
        """
        configparser.SafeConfigParser.read(self, [fname])
        for section in self.sections():
            if section != "env":
                for key, value in self.items("env"):
                    if not self.has_option(section, key):
                        self.set(section, key, value)
            for key, value in self.items(section):
                self._param[key] = value
        return self._param
    
        
    def write(self, fname):
        """ Write a file after substitution
        """
        # Create a new ConfigParser with substitution
        config_out = configparser.ConfigParser()
        for section in self.sections():
            config_out.add_section(section)
            for name, value in self.items(section):
                config_out.set(section, name, value)
        with open(fname, 'w') as f:
            config_out.write(f)

