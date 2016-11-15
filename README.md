# generic-rest
Simple generic REST API server.

If you want simply to set up a test API rest server you can use the prebuilt docker image: 

    $ docker run -t -p 5000:5000 sverrirab/generic-rest
    
You can then test locally using your favorite tool.  Such as `curl`

Upload one text record and view all data:

    $ curl http://localhost:5000/api -d "text=hello" -X POST
    
    $ curl http://localhost:5000/api

If you want to persist the data (saved as a .json file) and configure the endpoint you can do something like:

    $ docker run -d -v $PWD/data:/data -p 5000:5000 --name bookmark sverrirab/generic-rest \
      --file /data/bookmark.json --api '/bookmark' url description
    

Instant bookmark API server!  Now to add some data and view it:

    $ curl http://localhost:5000/bookmark -d "url=http://reddit.com&description=Reddit" -X POST
    "Ugt3Tl"
    
    $ curl http://localhost:5000/bookmark
    {"Ugt3Tl": {"url": "http://reddit.com", "description": "Reddit"}}
        
    $ curl http://localhost:5000/bookmark/Ugt3Tl
    {"url": "http://reddit.com", "description": "Reddit"}
    
    $ http://localhost:5000/bookmark/Ugt3Tl/description
    "Reddit"

For detailed instructions run with `--help` argument.
 

