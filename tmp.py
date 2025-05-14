import pandas as pd
from lecoo_tool.lecoo_pkidreader import PKIDReader
import numpy as np


def merge(df: pd.DataFrame, data: list):
    for item in data:
        df.loc[df['装箱条码'] == item['sn'], 'pkid'] = item['pkid']
        print(f"{item['sn']}\t{item['pkid']}")


pkid_reader = PKIDReader()
pkids = pkid_reader.read_pkid()
print(pkids)
df = pd.read_excel("C:/Users/SHEN/Documents/testpkid.xlsx")
merge(df, pkids)
print(df)
df.to_excel('F:/临时文档/tmp/tmp.xlsx', index=False)
