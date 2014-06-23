Multiprocess module for repository discovery and indexing.

This is a core component in the Algthm architecture, optimized for commodity hardware
in a cloud environment. The discovery module is responsible for finding/crawling repositories
that reside on the github network. It is broken up into 2 modules.

1. Crawler 
2. Indexer

---

### Crawler
The Crawler polls github api with essentially what is an empty search. Results are by 
default paginated by 100 items. This process is lengthy as github is comprised of roughly
10M public repositories. Api fixed responses to 1 response per second per key. 
Once the end is reached, we simply stop and fire this module off again at a later time. 
Most likely once every hour. This keeps the platform up-to-date with github as close as possible.

### Indexer
The Indexer module is fed repository URLs by the Worker, which are then downloaded and checked 
out to the local file system. Once this process completes, various indexing processes are 
carried out on the repository source. 

Indexers execute in their own process, this is possible due to its highly parallel nature. 
The number of workers that spawn is fixed and dependant on the hardware it's running on. 
Typically, 2 workers per core. Anymore than this is results in an non-optimal performing system.


