random.seed()
I = importlib
fee = Variable()
data = Hash()
supported_tokens = Variable()
owners = Variable()
owner_perc = Hash()
payout = Hash(default_value=0)


@construct
def init():
    owners.set(["endo", "marvin"])
    owner_perc['endo'] = decimal('0.5')
    owner_perc['marvin'] = decimal('0.5')
    supported_tokens.set([
        'currency','con_rswp_lst001',
        'con_weth_lst001', 'con_lusd_lst001',
        'con_reflecttau_v2', 'con_marmite100_contract'
    ])
    fee.set(decimal('0.7'))
    
    # For testing purpose. Should be removed when deployed to mainnet/testnet
    payout["currency"] = 1000
    payout["con_rswp_lst001"] = 20_000
    payout["con_marmite100_contract"] = 5_000_000
    
    
@export
def make_offer(offer_token: str, offer_amount: float, take_token: str,
    take_amount: float):
    assert offer_token in supported_tokens.get(), 'Token not supported!'
    assert take_token in supported_tokens.get(), 'Token not supported!'
    assert offer_amount > 0, 'Negative offer_amount not allowed'
    assert take_amount > 0, 'Negative take_amount not allowed'
    offer_id = hashlib.sha256(str(now) + str(random.randrange(99)))
    assert not data[offer_id], 'Generated ID not unique. Try again'
    maker_fee = offer_amount / 100 * fee.get()
    I.import_module(offer_token).transfer_from(amount=offer_amount +
        maker_fee, to=ctx.this, main_account=ctx.caller)
    data[offer_id] = {'maker': ctx.caller, 'taker': None, 'offer_token':
        offer_token, 'offer_amount': offer_amount, 'take_token': take_token,
        'take_amount': take_amount, 'fee': fee.get(), 'state': 'OPEN'}
    return offer_id
    
@export
def take_offer(offer_id: str):
    assert data[offer_id], 'Offer ID does not exist'
    offer = data[offer_id]
    assert offer['state'] == 'OPEN', 'Offer not available'
    maker_fee = offer['offer_amount'] / 100 * offer['fee']
    taker_fee = offer['take_amount'] / 100 * offer['fee']
    #transfer take_token amount + taker_fee to this contract from taker
    I.import_module(offer['take_token']).transfer_from(amount=offer[
        'take_amount'] + taker_fee, to=ctx.this, main_account=ctx.caller)
    #transfer take_token amount to maker
    I.import_module(offer['take_token']).transfer(amount=offer[
        'take_amount'], to=offer['maker'])
    #transfer offer_token amount to taker
    I.import_module(offer['offer_token']).transfer(amount=offer[
        'offer_amount'], to=ctx.caller)
    payout[offer['offer_token']] += maker_fee
    payout[offer['take_token']] += taker_fee
    offer['state'] = 'EXECUTED'
    offer['taker'] = ctx.caller
    data[offer_id] = offer
    
@export
def cancel_offer(offer_id: str):
    assert data[offer_id], 'Offer ID does not exist'
    offer = data[offer_id]
    assert offer['state'] == 'OPEN', 'Offer can not be canceled'
    assert offer['maker'] == ctx.caller, 'Only maker can cancel offer'
    maker_fee = offer['offer_amount'] / 100 * offer['fee']
    I.import_module(offer['offer_token']).transfer(amount=offer[
        'offer_amount'] + maker_fee, to=ctx.caller)
    offer['state'] = 'CANCELED'
    data[offer_id] = offer
    
@export
def adjust_fee(trading_fee: str):
    assert ctx.caller in owners.get(), 'Only owner can adjust fee'
    assert trading_fee >= 0 and trading_fee <= 10, 'Wrong fee value'
    fee.set(trading_fee)

@export
def support_token(contract: str):
    assert ctx.caller in owners.get(), 'Only owner can adjust fee'
    token_list = supported_tokens.get()
    assert contract not in token_list, 'Token is already supported'
    supported_tokens.set(token_list + [contract])
    return supported_tokens.get()
    
@export
def remove_token_support(contract: str):
    assert ctx.caller in owners.get(), 'Only owner can adjust fee'
    token_list = supported_tokens.get()
    assert contract in token_list, 'Unsupported token cannot be removed'
    supported_tokens.set([token for token in token_list if token != contract])
    return supported_tokens.get()
    
@export
def payout_owners(token_list: list):
	assert ctx.caller in owners.get(), 'Payout only available for owner'

	if token_list == None: token_list = supported_tokens.get()
	
	for token in token_list:
		if payout[token] > 0: #what if we encounter a __fixed__ here? ContractingDecimal?
			for owner in owners.get():
				payout_amount = owner_perc[owner] * payout[token]  
				I.import_module(token).transfer(amount=payout_amount, to=owner)
			payout[token] = 0
