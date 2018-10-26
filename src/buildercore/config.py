"""Configuration file for `buildercore`.

`buildercore.config` is a place to record assumptions really.
Settings that the users are encouraged to tweak should go into the
`settings.yml` file at the root of the project and incorporated here.

buildercore was originally part of the builder, then separated out
into it's own project 'builder-core' but has now been re-integrated.
This transition meant that `src/buildercore/` is still neatly separated
from the interface logic in the fabfile.

"""
import os
from os.path import join
from fabric.api import env
from buildercore import utils
from buildercore.utils import lmap, lfilter
from kids.cache import cache
import logging


# no un-catchable errors from Fabric

class FabricException(Exception):
    pass

env.abort_exception = FabricException

class ConfigurationError(Exception):
    pass

# dirs are relative
# paths are absolute
# a file is an absolute path to a file
# filenames are names of files without any other context


# these users should probably be specified in the project/org config file
# as 'defaults'. deploy user especially
ROOT_USER = 'root'
BOOTSTRAP_USER = 'ubuntu'
DEPLOY_USER = 'elife'

PROJECT_PATH = os.getcwd() # ll: /path/to/elife-builder/
SRC_PATH = join(PROJECT_PATH, 'src') # ll: /path/to/elife-builder/src/

TEMP_PATH = "/tmp/"

CFN = ".cfn"

STACK_DIR = join(CFN, "stacks") # ll: ./.cfn/stacks
CONTEXT_DIR = join(CFN, "contexts") # ll: ./.cfn/stacks
SCRIPTS_DIR = "scripts"
PRIVATE_DIR = "private"
KEYPAIR_DIR = join(CFN, "keypairs") # ll: ./.cfn/keypairs
# the .cfn dir was for cloudformation stuff, but we keep keypairs in there too, so this can't hurt
# perhaps a namechange from .cfn to .state or something later
TERRAFORM_DIR = join(CFN, "terraform")

STACK_PATH = join(PROJECT_PATH, STACK_DIR) # "/.../.cfn/stacks/"
CONTEXT_PATH = join(PROJECT_PATH, CONTEXT_DIR) # "/.../.cfn/contexts/"
KEYPAIR_PATH = join(PROJECT_PATH, KEYPAIR_DIR) # "/.../.cfn/keypairs/"
SCRIPTS_PATH = join(PROJECT_PATH, SCRIPTS_DIR) # "/.../scripts/"

# create all necessary paths and ensure they are writable
lmap(utils.mkdir_p, [TEMP_PATH, STACK_PATH, CONTEXT_PATH, SCRIPTS_PATH, KEYPAIR_PATH])

# logging

LOG_DIR = "logs"
LOG_PATH = join(PROJECT_PATH, LOG_DIR) # /.../logs/
LOG_FILE = join(LOG_PATH, "app.log") # /.../logs/app.log
utils.mkdir_p(LOG_PATH)

FORMAT = logging.Formatter("%(asctime)s - %(levelname)s - %(processName)s - %(name)s - %(message)s")
CONSOLE_FORMAT = logging.Formatter("%(levelname)s - %(name)s - %(message)s")

# http://docs.python.org/2/howto/logging-cookbook.html
ROOTLOG = logging.getLogger() # important! this is the *root LOG*
# all other LOGs are derived from this one
ROOTLOG.setLevel(logging.DEBUG) # *default* output level for all LOGs

# StreamHandler sends to stderr by default
CONSOLE_HANDLER = logging.StreamHandler()
CONSOLE_HANDLER.setLevel(logging.INFO) # output level for *this handler*
CONSOLE_HANDLER.setFormatter(CONSOLE_FORMAT)


# FileHandler sends to a named file
FILE_HANDLER = logging.FileHandler(LOG_FILE)
_log_level = os.environ.get('LOG_LEVEL_FILE', 'INFO')
FILE_HANDLER.setLevel(getattr(logging, _log_level))
FILE_HANDLER.setFormatter(FORMAT)

ROOTLOG.addHandler(CONSOLE_HANDLER)
ROOTLOG.addHandler(FILE_HANDLER)

LOG = logging.getLogger(__name__)
logging.getLogger('paramiko.transport').setLevel(logging.ERROR)
# TODO: leave on for FILE_HANDLER but not for CONSOLE_HANDLER
# logging.getLogger('botocore.vendored').setLevel(logging.ERROR)

def get_logger(name):
    "ensures logging is setup before handing out a Logger object to use"
    return logging.getLogger(name)

#
# remote
#

# where the builder can write stuff that should persist across installations/users
# like ec2 instance keypairs
BUILDER_BUCKET = 'elife-builder'
BUILDER_REGION = 'us-east-1'
BUILDER_NON_INTERACTIVE = 'BUILDER_NON_INTERACTIVE' in os.environ and os.environ['BUILDER_NON_INTERACTIVE']
KEYPAIR_PREFIX = 'keypairs/'
CONTEXT_PREFIX = 'contexts/'

PACKER_BOX_PREFIX = "elifesciences" # the 'elifesciences' in 'elifesciences/basebox'
PACKER_BOX_BUCKET = "builder-boxes"
PACKER_BOX_KEY = "boxes"
# ll: s3://elife-builder/boxes
PACKER_BOX_S3_PATH = "s3://%s" % join(PACKER_BOX_BUCKET, PACKER_BOX_KEY)
PACKER_BOX_S3_HTTP_PATH = join("https://s3.amazonaws.com", PACKER_BOX_BUCKET, PACKER_BOX_KEY)

# these sections *shouldn't* be merged if they *don't* exist in the project
AWS_EXCLUDING = ['rds', 'ext', 'elb', 'cloudfront', 'elasticache', 'fastly']

#
# settings
# believe it or not but buildercore.config is NOT the place for user config
#

SETTINGS_FILE = join(PROJECT_PATH, 'settings.yml')
SETTINGS_FILE = os.environ.get('SETTINGS_FILE', SETTINGS_FILE)

USER_PRIVATE_KEY = os.environ.get('CUSTOM_SSH_KEY', '~/.ssh/id_rsa')
#
# testing
#

# 'Test With Instance', see integration_tests.test_with_instance
TWI_REUSE_STACK = os.environ.get('BLDR_TWI_REUSE_STACK', '0') == '1' # use existing test stack if exists
TWI_CLEANUP = os.environ.get('BLDR_TWI_CLEANUP', '1') == '1' # tear down test stack after testing

#
# logic
#

def load(settings_yaml_file):
    "read the settings.yml file in from yaml"
    return utils.ordered_load(open(settings_yaml_file, 'r'))

def _parse_loc(loc):
    "turn a project-location path into a triple of (protocol, hostname, path)"
    bits = loc.split('://', 1)
    if len(bits) == 2:
        host, path = bits[1].split('/', 1)
        # ll: (http, example.org, '/path/to/org/file/')
        return (bits[0], host, '/' + path)
    # ll: (file, None, '/path/to/org/file/')
    path = os.path.abspath(os.path.expanduser(loc))
    return 'file' if os.path.isfile(path) else 'dir', None, path

def parse_loc_list(loc_list):
    "wrangle the list of paths the user gave us. expand if they specify a directory, etc"
    # give the convenient user-form some structure
    p_loc_list = lmap(_parse_loc, loc_list)
    # do some post processing

    def expand_dirs(triple):
        protocol, host, path = triple
        if protocol in ['dir', 'file'] and not os.path.exists(path):
            LOG.warn("could not resolve %r, skipping", path)
            return [None]
        if protocol == 'dir':
            yaml_files = utils.listfiles(path, ['.yaml'])
            return [('file', host, ppath) for ppath in yaml_files]
        return [triple]
    # we don't want dirs, we want files
    p_loc_list = utils.shallow_flatten(map(expand_dirs, p_loc_list))

    # remove any bogus values
    p_loc_list = lfilter(None, p_loc_list)

    # remove any duplicates. can happen when we expand dir => files
    p_loc_list = utils.unique(p_loc_list)

    return p_loc_list

def parse(settings_data):
    "iterate through the settings file and do any data coercion necessary"
    processors = {
        'project-locations': parse_loc_list,
    }
    for key, processor in processors.items():
        settings_data[key] = processor(settings_data[key])
    return settings_data

@cache
def app(settings_path=None):
    # set default here so tests can change the value of SETTINGS_FILE
    settings_path = settings_path or SETTINGS_FILE
    LOG.debug("using settings path %r", settings_path)
    return parse(load(settings_path))

def feature_enabled(feature):
    return app().get(feature, False)
