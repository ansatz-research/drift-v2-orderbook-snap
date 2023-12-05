import requests
import os
import pandas as pd
import numpy as np

x = requests.get('https://dlob.drift.trade/orders/json').json()

market_to_oracle_map = pd.DataFrame(x['oracles']).set_index('marketIndex').to_dict()['price']

df = pd.DataFrame([order['order'] for order in x['orders']])
user = pd.DataFrame([order['user'] for order in x['orders']], columns=['user'])
df = pd.concat([df, user],axis=1)
df['oraclePrice'] = None
df.loc[df.marketType=='perp', 'oraclePrice'] = df.loc[df.marketType=='perp', 'marketIndex'].apply(lambda x: market_to_oracle_map.get(x, 0))

#todo, invariant may change w/ future spot markets
df.loc[df.marketType=='spot', 'oraclePrice'] = df.loc[df.marketType=='spot', 'marketIndex'].apply(lambda x: market_to_oracle_map.get(int(x)-1, 0))

df1 = df[(df.orderType=='limit')]
df1.loc[((df1['price'].astype(int)==0) & (df1['oraclePrice'].astype(int)!=0)), 'price'] = df1['oraclePrice'].astype(int) + df1['oraclePriceOffset'].astype(int)

for col in ['price', 'oraclePrice', 'oraclePriceOffset']:
    df1[col] = df1[col].astype(int)
    df1[col] /= 1e6
    
for col in ['quoteAssetAmountFilled']:
    df1[col] = df1[col].astype(int)
    df1[col] /= 1e6 

for col in ['baseAssetAmount', 'baseAssetAmountFilled']:
    df1[col] = df1[col].astype(int)
    df1[col] /= 1e9
    

market_types = sorted(df.marketType.unique())
market_indexes = sorted(df.marketIndex.unique())
for t in market_types:
    for i in market_indexes:
        mdf = df1[((df1.marketType==t) & (df1.marketIndex==i))]
        if len(mdf)==0:
            continue

        mdf = mdf[['price', 'baseAssetAmount', 'direction', 'user', 'status', 'orderType', 'marketType', 'slot', 'orderId', 'userOrderId',
       'marketIndex',  'baseAssetAmountFilled',
       'quoteAssetAmountFilled',  'reduceOnly', 'triggerPrice',
       'triggerCondition', 'existingPositionDirection', 'postOnly',
       'immediateOrCancel', 'oraclePriceOffset', 'auctionDuration',
       'auctionStartPrice', 'auctionEndPrice', 'maxTs', 'oraclePrice']]
        mdf = mdf.sort_values('price').reset_index(drop=True)
        dir_ff = 'data/'+str(t)+str(i)
        out_ff = dir_ff+'/orderbook_slot_'+str(x['slot'])+'.csv.gz'
        os.makedirs(dir_ff, exist_ok=True)
        mdf.to_csv(out_ff, index=False, compression='gzip')
