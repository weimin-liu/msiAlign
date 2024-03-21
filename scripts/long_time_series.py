import pandas as pd
import os
import numpy as np
import matplotlib.pyplot as plt


dfs = []
for i in os.listdir('/Users/weimin/Projects/sbb_triggercore'):
    if 'PAH' in i:
        df = pd.read_csv(f'/Users/weimin/Projects/sbb_triggercore/{i}/1d.csv')
        age_model = pd.read_csv(f'/Users/weimin/Projects/sbb_triggercore/{i}/age.csv',index_col=0)
        age_model = age_model.reset_index()
        age_model.columns = ['year', 'index', 'd']
        age_model = age_model.astype(float)
        age_model = age_model.drop(columns='index')
        df['age'] = np.interp(df['d'], age_model['d']/10, age_model['year'])
        df = df.dropna()
        df = df.sort_values(by='age')
        dfs.append(df)

dfs = pd.concat(dfs)
dfs = dfs.sort_values(by='age')
plt.plot(dfs['age'], dfs['ratio'])
plt.show()
