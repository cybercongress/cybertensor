## Basic flow
Here is the basic flow to explore and play with Cybernet deployed in Space-Pussy network and Cybertensor tooling.
- Deployed [contract](https://deploy-preview-1081--rebyc.netlify.app/contracts/pussy1ddwq8rxgdsm27pvpxqdy2ep9enuen6t2yhrqujvj9qwl4dtukx0s8hpka9)
- Your [account](https://deploy-preview-1081--rebyc.netlify.app/robot)
- Yuma [Consensus](https://github.com/opentensor/subtensor/blob/f0a3da50fd7e949ca0d5284200cb80fdd25a79e3/docs/consensus.md)

### Setup keys
First create keys, while wallet creation you will be asked to enter a password to encrypt keys inside the inner keys storage. Two mnemonics will be created and two keys will be derived from them - hotkey and coldkey. Save mnemonics in a safe place. 
- The coldkey is encrypted on your device. It is used to store funds securely and perform high-risk operations such as transfers and staking.
- The hotkey is by default unencrypted. However, you can encrypt the hotkey. The hotkey is used for less secure operations such as signing messages into the network, running subnet miners, and validating the network. 
```bash
ctcli wallet create
```

You can list all the local wallets stored directly with:
```bash
ctcli wallet list
```

Get a detailed report of your wallet pairs (coldkey, hotkey). This report includes balance and staking information for both the coldkey and hotkey associated with the wallet.
```bash
ctcli wallet inspect
```
### Root network register
Make registration to the root network. Validators on the root network cast weights to subnets, voting to tokens distribution across subnets in the network. Total consensus weighted distribution to subnets calculated based on validators' stake and their assigned weights to subnets. The network continuously distributes tokens to subnets and these tokens are distributed to subnets operators and validators. All operators and validators of root network and subnets should continuously cast weights. Both root network and subnets have operators and validators. Validators are given a subset of the operators of the root network and subnets with a top-k stake. Only weights of validators are used for consensus algorithm calculation. Join the root network to participate in token distribution across subnets.

Register to the root network to participate in the distribution process of tokens across subnets:
```bash
- ctcli root register
```

### Subnet network register
Now you can join the given subnet. Subnets are incentivized groups of operators that produce work coordinated by a consensus algorithm based on subjective assessment of other work inside the group using weight votes and stake distribution.

List all subnets and choose which to join:
```bash
ctcli subnets list
```

Join a subnet using a solution of PoW task, you will be asked which subnet to join. Each subnet has a different current PoW difficulty based on its parameters and the current demand of participation.
```bash
ctcli subnets pow_register
```

Join a subnet paying some amount of tokens, you will be asked which subnet to join. Each subnet has a different current registration fee based on its parameters and the current demand for participation.
```bash
ctcli subnets register
```

### Staking
Stake and weights are used to compute consensus algorithms applied to the root network and subnets. The stake is global. That means that your stake will be applied to calculate token distribution across root network and subnets as you participate with multiple ones.

Add stake to your account:
```bash
ctcli stake add
```

Remove stake from your account:
```bash
ctcli stake remove
```

Show stake of your account:
```bash
ctcli stake show
```

### Set root weights

Let's set weights on the root network for subnets. This weights represents your subjective measured value of each of the subnets and their work, along with the view of desired token distribution to them.

Get the list of subnets and weights assigned to each subnet by every operator within the root network. This command provides visibility into how network responsibilities and rewards are distributed among various subnets.
```bash
ctcli root get_weights
```

Set weights for different subnets within the root network:
```bash
ctcli root weights --netuids 1,2 --weights 0.75,0.25
```

### Set subnet weights
Let's set the weight on the subnet network. This weight represents your subjective assessment of other operators' work inside the subnet. Your weight will be used to compute consensus and token distribution across the subnet to each operator. You should continuously make weights and send them to the network. You can put different weight values, weights will be normalized if needed.

Get a list of operators and weights assigned to each operator within the root network to each other:
```bash
ctcli subnet weights
```

Set weights to different operators within the subnet:
```bash
- ctcli subnet weights --uids 0,1,2,3 --weights 0.25,0.25,0.25,0.25
```

### Delegate stake
You can delegate stakes to different operators and earn rewards. You can stake to other operators if you are not an operator and if you are. Operators will take a commission from your rewards. Your stake is global and will be applied to all networks (root and subnets) where the chosen operator is participating.

Get the list of all delegates and choose which to stake:
```bash
ctcli root list_delegates
```

Delegate to the chosen operator:
```bash
ctcli root delegate
```

Undelegate to the chosen operator:
```bash
ctcli root undelegate
```

Get a list of your delegates:
```bash
ctcli root my_delegates
```

### Explore
Get the entire metagraph for a specified network. This metagraph contains detailed information about all the operators participating in the network, including their stakes, trust scores, and more.
```bash
ctcli subnet metagraph
```

Get subnet hyperparameters:
```bash
ctcli subnet hyperparameters
```

Get the list of all operators on the root network with their total stake:
```
ctcli root list
```

If you are an operator on a subnet or a couple of subnets and would like to allow another stakers and operators stake to you, then you need to nominate. This command will signal that you are ready to receive stake. If you joined the root network then you are nominated automatically. That means if you join the root network then everybody can stake in you from this moment, if not then you need to make the nomination. You will take fees from your staker' stake rewards.
```bash
ctcli root nominate
```

### Create subnet
You can create a subnet paying the subnet's creation fee to the network. The subnet will be initialized using default parameters, subnet calculation will happen every 360 blocks. As subnet creator and administrator you have permission to change the parameters of the subnet.

Get the subnet creation fee:
```bash
ctcli lock_cost create
```

Create subnet:
```bash
ctcli subnets create
```

Get subnet hyperparameters and choose which to change:
```bash
ctcli sudo get
```

Set subnet new hyperparameter value:
```bash
ctcli sudo set --netuid 1 --param immunity_period --value 5000
```
