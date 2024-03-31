[![Build Status Circle](https://circleci.com/gh/CounterpartyXCP/counterparty-core.svg?&style=shield)](https://circleci.com/gh/CounterpartyXCP/counterparty-core)


# Description
Counterparty Core is the reference implementation of the [Counterparty Protocol](https://counterparty.io).


# Getting Started

The simplest way to get your Counterparty node up and running is to use Docker Compose.

```
sudo apt install docker-compose
```

Then run node services in background with:

```bash
git clone git@github.com:CounterpartyXCP/counterparty-core.git
cd counterparty-core
mkdir ~/counterparty-docker-data
docker-compose up -d
```

**To run a node you must have at least 1.5TB free.** By default all data is stored in the `~/counterparty-docker-data` folder. You can modify this folder with the environment variable `$COUNTERPARTY_DOCKER_DATA`. For example:

```bash
COUNTERPARTY_DOCKER_DATA=/var/data docker-compose up -d
```

Use `docker-compose logs` to view output from services. For example:

```bash
docker-compose logs --tail=10 -f bitcoind
docker-compose logs --tail=10 -f addrindexrs
docker-compose logs --tail=10 -f counterparty-core
```

You can use the environment variable `BITCOIN_CHAIN` to run a `testnet` node:

```
BITCOIN_CHAIN=test docker-compose up -d
```

NOTES:
- By default, this Docker Compose script makes use of the `bootstrap` functionality, because Docker makes it hard to use `kickstart`. (See below.)
- When working with a low-memory system, you can tell `addrindexrs` to use JSON-RPC to communicate with `bitcoind` using the environment variable `ADDRINDEXRS_JSONRPC_IMPORT`: `ADDRINDEXRS_JSONRPC_IMPORT=true docker-compose up -d`


# Manual Installation

Counterparty Core can be installed on most platforms but, for now, manual installation is being tested and is only officially supported on Ubuntu 22.04 and MacOS.

Dependencies:

- Bitcoin Core
- AddrIndexRS
- Python >= 3.10
- Rust
- Maturin
- LevelDB

## Install dependencies

### Install Bitcoin Core

Download the latest [Bitcoin Core](https://github.com/bitcoin/bitcoin/releases) and create
a `bitcoin.conf` file (by default located in `~.bitcoin/`) with the following options:

```
rpcuser=rpc
rpcpassword=rpc
server=1
addresstype=legacy
txindex=1
prune=0
mempoolfullrbf=1
rpcworkqueue=100
```

Adding the following lines, and opening up port `8333` to incoming traffic, may improve your sync speed:

```
listen=1
dbcache=4000
```

### Install Rust

The recommended way to install Rust is to use `rustup`:

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source "$HOME/.cargo/env"
```

See https://www.rust-lang.org/tools/install for more information.


### Install Addrindexrs

Download and install the latest [AddrIndexRS](https://github.com/CounterpartyXCP/addrindexrs):

```bash
git clone https://github.com/CounterpartyXCP/addrindexrs.git
cd addrindexrs
cargo install --path=.
```

Start `addrindexrs` with:

```bash
addrindexrs --cookie=rpc:rpc -vvv
```

When working with a remote full node or low-memory system, you can tell `addrindexrs` to use JSON-RPC to communicate with `bitcoind` using the flag `--jsonrpc-import`.
You can also limit the resources available for `addrindexrs` with:

```bash
ulimit -n 8192
```

Use `addrindexrs -h` for more options.

### Install Python >= 3.10 and Maturin

On Ubuntu 22.04 and similar:

```bash
apt-get install -y python3 python3-dev python3-pip
pip3 install maturin
```

On MacOS:

```bash
brew install python
pip3 install maturin
```

See https://brew.sh/ to install Homewrew.


### Install LevelDB

On Ubuntu 22.04 and similar:

```bash
apt-get install -y libleveldb-dev
```

On MacOS:

```bash
brew install leveldb
```

## Install Counterparty Core

Download the latest version `counterparty-core`:

```bash
git clone https://github.com/CounterpartyXCP/counterparty-core.git
```

Install the `counterparty-rs` library:

```bash
cd counterparty-core/counterparty-rs
pip3 install .
```

Install the `counterparty-lib` library:

```bash
cd counterparty-core/counterparty-lib
pip3 install .
```

Install the `counterparty-cli` library:

```bash
cd counterparty-core/counterparty-cli
pip3 install .
```

*Note for MacOS users*

Use this command if you get an error while installing one of the packages:

```bash
CFLAGS="-I/opt/homebrew/include -L/opt/homebrew/lib"
```

# Usage

## Configuration

Manual configuration is not necessary for most use cases, but example configuration files may be found in the `docker/` directory.

By default, the **configuration files** are named `server.conf` and `client.conf` and are located in the following directories:

* Linux: `~/.config/counterparty/`
* Windows: `%APPDATA%\Counterparty\`

Client and server log files are named `counterparty.client.[testnet.]log` and `counterparty.server.[testnet.]log` and are located in the following directories:

* Linux: `~/.cache/counterparty/log/`
* Windows: `%APPDATA%\Local\Counterparty\counterparty\Logs`

Counterparty API activity is logged to `server.[testnet.]api.log` and `client.[testnet.]api.log`.

Counterparty database files are by default named `counterparty.[testnet.]db` and are located in the following directories:

* Linux: `~/.local/share/counterparty`
* Windows: `%APPDATA%\Roaming\Counterparty\counterparty`

All configurable parameters in the configuration file can also be passed as arguments to the `counterpart-server` command. Use `counterparty-server --help` to see the list of these options.

## Quickly Catch Up with the Network

You will not be able to run `counterparty-server` until `addrindexrs` has caught up (and its RPC server is running), which in turn requires `bitcoind` have caught up as well. The command to start the Counterparty server process is simply `counterparty-server start`. However, simply running this command requires a long time to catch up with the network, and Counterparty must have parsed all published blocks before being operational.

There are two ways to speed up the process of catching up with the network:

1. `counterparty-server bootstrap` downloads a recent snapshot of a Counterparty database from a centralized server maintained by the Counterparty Core development team. Because this method does not involve verifying the history of Counterparty transactions yourself, **the `bootstrap` command should not be used for mission-critical, commercial or public-facing nodes.**

```bash
counterparty-server bootstrap
```

1. `counterparty-server kickstart` will perform a complete catchup in around 8 to 24 hours. However, this method requires first stopping Bitcoin Core (while leaving `addrindexrs` running, so that Counterparty Core can read the Bitcoin block files directly from `bitcoind`'s database.

```bash
counterparty-server kickstart
```


## Start the Server

Once the Counterparty server has caught up with the network, you may start the server simply with `counterparty start`:

```bash
counterparty-server start
```

# Further Reading

* [Official Project Documentation](http://counterparty.io/docs/)
