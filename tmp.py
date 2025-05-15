import pandas as pd
from lecoo_tool.lecoo_pkidreader import PKIDReader
import numpy as np

pkid_reader = PKIDReader()
show_popup = pkid_reader.show_popup
exit_program = pkid_reader.exit_program

def merge(df: pd.DataFrame, data: list):
    for item in data:
        df.loc[df['装箱条码'] == item['sn'], 'pkid'] = item['pkid']


def check_data_consistency(df: pd.DataFrame, pkids_list: list):
    item_count = df.shape[0]
    pkids_len = len(pkids_list)
    item_list = df['装箱条码'].tolist()
    pkids_sn = [item['sn'] for item in pkids_list]
    loss_data = []

    if item_count == pkids_len:
        return
    else:
        if item_count > pkids_len:
            for item in item_list:
                if item not in pkids_sn:
                    loss_data.append(item)
            show_popup(f"读取所有的pkid文件，发现缺少以下SN码对应的pkid，SN：{loss_data}，请检查pkid文件是否缺少", exit_program)
        else:
            for item in pkids_sn:
                if item not in item_list:
                    loss_data.append(item)
            show_popup(f"读取表格文件，发现缺少以下SN码对应的，SN：{loss_data}，请检查表格数据是否完整", exit_program)


pkids = pkid_reader.read_pkid()
df = pd.read_excel("C:/Users/SHEN/Documents/testpkid.xlsx")
merge(df, pkids)
print(df)
check_data_consistency(df, pkids)
