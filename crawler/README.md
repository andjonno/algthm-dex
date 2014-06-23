## Crawler module

The crawler module is quite simply an api poller.

The github api is fixed to 100 items/response/key. So unfortunately, to obtain all of the Github
public repositories, we must poll from the beginning at 100 items per call per second. Two factors 
limit this operation from being executed in parallel.
1. the repositories aren't evenly distributed between a range of IDs.
2. the api limits us to 1 call per second.

Fortunately, this process only needs to be ran once from the beginning. Once we reach the end, 
we store the state and this is then our point to resume after a small timeout period. Because 
github is so active, there are new public repositories being created every minute so we essentially 
have a moving target. This process will be ran on an interval, cron every hour or so. This will 
keep us as close as possible to a relevant state to Github.

-- 

### Other repository providers. 

Only Github is supported at this time, other providers will be added later.
Google Code and Bitbucket are next in line for support.

