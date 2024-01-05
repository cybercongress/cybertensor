# CYBERTENSOR
<p>
    <img alt="GitHub" src="https://img.shields.io/github/license/cybercongress/cybertensor">
    <img alt="Python" src="https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11-blue">
</p>

## Install

1. From source:
```bash
git clone https://github.com/cybercongress/cybertensor.git
python3 -m pip install -e cybertensor/
```
2. To test your installation, type:
```bash
ctcli --help
```
or using python
```python
import cybertensor
```

## Space Pussy setup

1. Clone:
```bash
git clone https://github.com/cybercongress/cybertensor.git
cd cybertensor
git checkout add-space-pussy-network
```
2. [Optional] Create and activate a virtual environment:
```bash
python3 -m venv venv
. venv/bin/activate
```
3. Install from the source
```bash
python3 -m pip install -e .
```

4. To test your installation, type:
```bash
ctcli --help
```
or using python
```python
import cybertensor
```

## Dev setup
1. Use localbostrom:
```bash
git clone https://github.com/cybercongress/localbostrom
cd localbostrom
./hard_restart.sh
```
2. Add mnemonics from localbostrom's README to local keystore:
```bash
cyber keys add validator --recover --home ./home
```
3. Deploy code and instantiate contract:
```bash
cyber tx wasm store cybernet.wasm --from validator --home ./home --chain-id localbostrom --gas 7000000 --broadcast-mode block -y --keyring-backend test
cyber tx wasm instantiate 1 "{}" --from validator --home ./home --chain-id localbostrom --gas 5000000 --label cybernet1 --admin bostrom1phaxpevm5wecex2jyaqty2a4v02qj7qm5n94ug --broadcast-mode block -y --keyring-backend test
```
4. Send tokens to contract and activate (with dmn):
```bash
cyber tx bank send validator bostrom14hj2tavq8fpesdwxxcu44rty3hh90vhujrvcmstl4zr3txmfvw9sww4mxt 1000000000000boot --home ./home --chain-id localbostrom --gas 500000 --broadcast-mode block -y --keyring-backend test
cyber tx wasm execute bostrom14hj2tavq8fpesdwxxcu44rty3hh90vhujrvcmstl4zr3txmfvw9sww4mxt '{"activate":{}}' --from validator --home ./home --chain-id localbostrom --gas 5000000 --broadcast-mode block -y --keyring-backend test
```
5. Add mnemonics from localbostrom's README to ctcli keystore:
```bash
ctcli w regen_hotkey
ctcli w regen_coldkey
```
6. Add contract and schemas to .cybertensor/contract dir:
```bash
tree ~/.cybertensor/contract 
```
```
/Users/cyberhead/.cybertensor/contract
├── cybernet.wasm
└── schema
    ├── execute.json
    ├── instantiate.json
    ├── query.json
    └── schema.json
````
7. Register network:
```bash
ctcli s create
```
