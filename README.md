        .'   .;.    _
   .-..'  .-.   `.,' '      
  :   ; .;.-'   ,'`.        DEX indexing module 0.0.4. Copyright 2014 Algthm.
  `:::'`.`:::'-'    `._.    

Multiprocess module for repository discovery and indexing.

This is a core component in the Algthm architecture, optimized for commodity hardware in cloud environments. The
indexer has the obvious job of indexing repositories existing in the repository database.

---

### Indexer
The Indexer module is fed repository URLs by the Worker, which are then downloaded and checked 
out to the local file system. Once this process completes, various indexing processes are 
carried out on the repository source. 

Indexers execute in their own process, this is possible due to its highly parallel nature. 
The number of workers that spawn is fixed and dependant on the hardware it's running on. 
Typically, 2 workers per core. Anymore than this is results in an non-optimal performing system.


