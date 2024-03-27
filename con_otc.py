I = importlib
fee = Variable()
data = Hash()
owners = Variable()
owner_perc = Hash()
payout = Hash(default_value=0)

@export
def make_offer(offer_token: str, offer_amount: float, take_token: str, take_amount: float):
    validate_positive_amount(offer_amount, "offer_amount")
    validate_positive_amount(take_amount, "take_amount")

    offer_id = generate_unique_offer_id()
    maker_fee = calculate_fee(offer_amount)
    
    I.import_module(offer_token).transfer_from(amount=offer_amount + maker_fee, to=ctx.this, main_account=ctx.caller)
    
    data[offer_id] = {'maker': ctx.caller, 'taker': None, 'offer_token': offer_token, 'offer_amount': offer_amount,
                      'take_token': take_token, 'take_amount': take_amount, 'fee': fee.get(), 'state': 'OPEN'}
    return offer_id

@export
def take_offer(offer_id: str):
    offer = get_offer(offer_id, 'OPEN')
    
    maker_fee = calculate_fee(offer['offer_amount'])
    taker_fee = calculate_fee(offer['take_amount'])
    
    execute_trades(offer, maker_fee, taker_fee)
    finalize_offer(offer_id, offer, ctx.caller, maker_fee, taker_fee)

@export
def cancel_offer(offer_id: str):
    offer = get_offer(offer_id, 'OPEN')
    assert offer['maker'] == ctx.caller, 'Only maker can cancel offer'
    
    refund_maker(offer)

@export
def adjust_fee(trading_fee: float):
    assert_owner()
    assert 0 <= trading_fee <= 10, 'Wrong fee value'
    fee.set(decimal(trading_fee))

# Revisar esta funcion no esta funcinando
@export
def payout_owners(token_list: list):
    assert_owner()
    distribute_payouts(token_list)

# Funciones Auxiliares

def validate_positive_amount(amount: float, field_name: str):
    assert amount > 0, f'Negative {field_name} not allowed'

def generate_unique_offer_id() -> str:
    offer_id = hashlib.sha256(str(now) + str(random.randrange(99))).hexdigest()
    assert not data[offer_id], 'Generated ID not unique. Try again'
    return offer_id

def calculate_fee(amount: float) -> float:
    return amount / 100 * fee.get()

def get_offer(offer_id: str, expected_state: str):
    assert data[offer_id], 'Offer ID does not exist'
    offer = data[offer_id]
    assert offer['state'] == expected_state, f'Offer not available or not in {expected_state} state'
    return offer

def execute_trades(offer, maker_fee, taker_fee):
    I.import_module(offer['take_token']).transfer_from(amount=offer['take_amount'] + taker_fee, to=ctx.this, main_account=ctx.caller)
    I.import_module(offer['take_token']).transfer(amount=offer['take_amount'], to=offer['maker'])
    I.import_module(offer['offer_token']).transfer(amount=offer['offer_amount'], to=ctx.caller)

def finalize_offer(offer_id, offer, taker, maker_fee, taker_fee):
    payout[offer['offer_token']] += maker_fee
    payout[offer['take_token']] += taker_fee
    offer.update({'state': 'EXECUTED', 'taker': taker})
    data[offer_id] = offer

def refund_maker(offer):
    maker_fee = calculate_fee(offer['offer_amount'])
    I.import_module(offer['offer_token']).transfer(amount=offer['offer_amount'] + maker_fee, to=offer['maker'])
    offer['state'] = 'CANCELED'
    data[offer['offer_id']] = offer

def assert_owner():
    assert ctx.caller in owners.get(), 'Only owner can call this method!'

# Revisar esta funcion no esta funcinando
def distribute_payouts(token_list):
    for token in token_list:
        if payout[token] > 0:
            total_payout = payout[token]
            token_balances = ForeignHash(foreign_contract=token, foreign_name='balances')
            otc_balance_before_payout = token_balances[ctx.this]
            
            for owner in owners.get():
                payout_amount = owner_perc[owner] * total_payout
                if payout_amount > 0:
                    I.import_module(token).transfer(amount=payout_amount, to=owner)
            
            otc_balance_after_payout = token_balances[ctx.this]
            actual_payout = otc_balance_before_payout - otc_balance_after_payout
            
            # Asegura que el monto pagado no exceda el saldo disponible, ajustando el saldo de payout según sea necesario.
            payout[token] -= actual_payout

