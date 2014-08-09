"""
Indexer exceptions to be here.
"""

class IndexerBootFailure(Exception):
    """
    Occurs on start up. Denotes a system start up failure.
    """
    pass

class IndexerDependencyFailure(Exception):
    """
    IndexerDependencyFailure should result in a halt of the Indexer module. This exception denotes a lib dependency of
    the Indexer module is not available.
    """
    pass

class RepositoryCloneFailure(Exception):
    """
    IndexerCloneFailure is a result of a failed git clone operation. This repository should be reported if this occurs
    regularly. On catching this exception, you should inform the repository reporting module.
    """
    pass

class StatisticsUnavailable(Exception):
    """
    NoStatisticsAvailable is thrown when no statistics were generated for a code base. This means the codebase contains
    no code at all.
    """
    pass

class ExternalSystemException(Exception):
    """
    This exception is thrown when an external dependency/system is unreachable. For example, submitting results
    to elasticsearch failed. The exception message is logged to an error database and the worker is shutdown. This is
    to prevent the system from stalling and quietly idling instead sysadmins are informed of the issue.
    """
    pass