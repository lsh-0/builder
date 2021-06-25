"""a collection of predicates that return either True or False

these should compliment not replicate any project configuration validation."""

from . import core, project
from .project import repo

class AccessProblem(RuntimeError):
    pass

class StackAlreadyExistsProblem(RuntimeError):
    def __init__(self, message, stackname):
        RuntimeError.__init__(self, message)
        self.stackname = stackname

def can_access_builder_private(pname):
    "`True` if current user can access the private-repo for given project"
    pdata = project.project_data(pname)
    return repo.access(pdata['private-repo'])

def ensure_can_access_builder_private(pname):
    if not can_access_builder_private(pname):
        pdata = project.project_data(pname)
        raise AccessProblem("failed to access your organisation's 'builder-private' repository: %s . You'll need access to this repository to add a deploy key later" % pdata['private-repo'])

def ensure_stack_does_not_exist(stackname):
    if core.stack_is_active(stackname):
        raise StackAlreadyExistsProblem("%s is an active stack" % stackname, stackname)
