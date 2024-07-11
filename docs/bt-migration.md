```
# change imported library (all files)
- import bittensor as bt
+ import cybertensor as ct

# change imported library alias usage (all usages)
# (bt. -> ct.)
- bt.logging.warning("Ending miner...")
+ ct.logging.warning("Ending miner...")

# change subtensor to cwtensor
# (self.subtensor -> self.cwtensor)
- self.metagraph.sync(subtensor=self.subtensor)
+ self.metagraph.sync(cwtensor=self.cwtensor)

# refactor base neuron fields 
- subtensor: "bt.subtensor"
- wallet: "bt.wallet"
- metagraph: "bt.metagraph"
+ cwtensor: "ct.cwtensor"
+ wallet: "ct.Wallet"
+ metagraph: "ct.metagraph"

# and here
- self.wallet = bt.wallet(config=self.config)
- self.subtensor = bt.subtensor(config=self.config)
- self.metagraph = self.subtensor.metagraph(self.config.netuid)
+ self.wallet = ct.Wallet(config=self.config)
+ self.cwtensor = ct.cwtensor(config=self.config)
+ self.metagraph = self.cwtensor.metagraph(self.config.netuid)

# refactor hotkey and address namings
# (ss58_address->address)
# (hotkey_ss58->hotkey)
- self.uid = self.metagraph.hotkeys.index(self.wallet.hotkey.ss58_address)
+ self.uid = self.metagraph.hotkeys.index(self.wallet.hotkey.address)

- hotkey_ss58=self.wallet.hotkey.ss58_address
+ hotkey=self.wallet.hotkey.address

# refactor chain info
(self.config.subtensor.chain_endpoint->self.config.cwtensor.network)
- bt.logging.info(
-	f"Running validator {self.axon} on network: {self.config.subtensor.chain_endpoint} with netuid: {self.config.netuid}"
+ ct.logging.info(
+	f"Running validator {self.axon} on network: {self.config.cwtensor.network} with netuid: {self.config.netuid}"

# extra
- class MockSubtensor(bt.MockSubtensor):
+ class MockCwtensor(ct.MockCwtensor):

- vpermit_tao_limit: int,
+ vpermit_limit: int,
```
