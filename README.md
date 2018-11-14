![logo](src/renderer/onion.png)

# PyTor Browser [![Codacy Badge](https://api.codacy.com/project/badge/Grade/41fa263f875e4d50b5d290a15f5c3d6c)](https://www.codacy.com/app/limyaojie93/pytor-browser?utm_source=github.com&utm_medium=referral&utm_content=causztic/pytor-browser&utm_campaign=Badge_Grade)

A simple demonstration of onion-routing done in Python and Electron/NodeJS.

## Pre-Requisites
-   Linux/MacOS

-   Yarn

-   Any Node LTS (I built it with v11)

-   Python 3.6.5 (preferably with pyenv) and corresponding Pip

-   Respective system libraries if you are building cross platform,
    see electron-builder's [documentation](https://www.electron.build/multi-platform-build).

## Setup

```sh
yarn install    # optional if you want to run without the GUI
python -m pip install cryptography requests
chmod +x test_spawns.sh
```

## Running with GUI

```sh
./test_spawns.sh
yarn dev
```

## Running with CLI

See their respective files for more parameters.

```sh
cd src/common/mini_pytor
python directory.py
python relay.py a
python relay.py b
python relay.py c
python client.py
curl localhost:27182?url=http://www.example.com
```



## Details

Python files are located in `src/common/mini_pytor`.

`test_spawns.sh` will spawn 1 **Directory** at `localhost:50000` and 5 **Relays** at `localhost:45000-45004`.

After setting up and running `yarn dev`, a simple web browser will appear. It starts **Client**, which is essentially a proxy server which will process the requests in place of the normal HTTP servers. 

If you want to add more relays into the network, point them to the Directory with `python relay.py [relay port] (directory ip) (directory port)`

**Client** starts with the default URL of `localhost:27182`. Currently our implementation will only resolve `text/html` URLs. Other formats will be unparsed and returned as gibberish.

Behind the scenes, this is what happens:

1.  User goes to a particular website, say example.com.

2.  Client prepares a n-layer encrypted HTTP request (n being a number from 3 to 5) and sends it to the first
    relay.

3.  First relay will decrypt the first layer with their private key, ie. peeling the encryption layer off and pass the result along to the second relay.

4.  The intermmediate relays will do the same thing until it reaches the nth relay.

5.  The last relay will peel off the last layer and pass the raw HTTP request to
    the HTTP server of example.com.

6.  The nth relay receives the HTTP response, encrypts it, ie. adding an
    encryption layer and pass it to the next relay.

7.  This happens to all the relays in between, so the client will receive a
    n-layer encrypted HTTP response.

8.  The client decrypts it to get the raw HTTP response, and processes it for the Browser to render.

## Browser Features
-   History Navigation
-   Viewing of Directory Status
-   Status textbox to show current status of Network
-   Relative link resolution
