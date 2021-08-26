# TODO.md

This is just a scratchpad for keeping track of ideas, nice-to-haves, etc.

## done

## todo

## todo (bucket)

* add a changelog and versioning and releases
* revisit tests
    - they take *forever*
* switch to threadbare
    - remove fabric
    - remove python2 support
* switch *away* from threadbare and fabric to something sane
    - with fewer dependencies
* revisit project configuration
    - config merging is painfully slow
    - 'aws' sections don't make a lot of sense now that resources across terraform and cloudformation are mixed
    - where to store unique per-instance non-templated configuration?
        - is this even the right place?
    - how to model new-instance vs existing-instance changes?
        - for example, new instances should get a ssd, old instances should continue using whatever
    - can project configuration be split from the code altogether?
        - we want to update project config and have it run through tests fast!
    - default resource blocks
        - so an ec2 instance is only present if an ec2 block is included
    - project config speccing
    - rip out caching
        - parsing/merging/validating little yaml/json files should be *quick*