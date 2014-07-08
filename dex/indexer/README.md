## Multiprocess indexing module for Algthm.

This module is comprised of a queue and several worker instances. Each of these workers 
run in their own process and pull tasks off the shared queue. A task is simply a repository 
url that is to be indexed. The worker passes this off to the indexer and carries out 
various operations on the repository after checking it out to the local file system.

Output includes commit activity, code base metrics, score generation and contributor 
analysis. This output is then updated in the system.

