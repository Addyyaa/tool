import sys

import matplotlib
matplotlib.use('TkAgg')  # 设置后端
import matplotlib.pyplot as plt
plt.style.use('default')
plt.rcParams['figure.figsize'] = (10, 6)
plt.rcParams['figure.dpi'] = 100
from fastai.imports import *
import seaborn as sns
from numpy import random
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.tree import DecisionTreeClassifier, export_graphviz
import os
import graphviz
from sklearn.metrics import mean_absolute_error


np.set_printoptions(linewidth=200)

df = pd.read_csv("F:/aileanning/data/train.csv")
tst_df = pd.read_csv("F:/aileanning/data/test.csv")
modes = df.mode().iloc[0]


def proc_data(df):
    df['Fare'] = df.Fare.fillna(0)
    df.fillna(modes, inplace=True)
    df['LogFare'] = np.log1p(df['Fare'])
    df['Embarked'] = pd.Categorical(df.Embarked)
    df['Sex'] = pd.Categorical(df.Sex)


proc_data(df)
proc_data(tst_df)
cats=["Sex","Embarked"]
conts=['Age', 'SibSp', 'Parch', 'LogFare',"Pclass"]
dep="Survived"
fig,axs = plt.subplots(1,2, figsize=(11,5))
sns.barplot(data=df, y=dep, x="Sex", ax=axs[0]).set(title="Survival rate")
sns.countplot(data=df, x="Sex", ax=axs[1]).set(title="Histogram")
plt.show()
random.seed(42)
trn_df,val_df = train_test_split(df, test_size=0.25)
trn_df[cats] = trn_df[cats].apply(lambda x: x.cat.codes)
val_df[cats] = val_df[cats].apply(lambda x: x.cat.codes)
def xs_y(df):
    xs = df[cats+conts].copy()
    return xs,df[dep] if dep in df else None

trn_xs,trn_y = xs_y(trn_df)
val_xs,val_y = xs_y(val_df)
preds = val_xs.Sex==0  # 这里的意思是所有女性幸存
abs_mean = mean_absolute_error(val_y, preds)
print(abs_mean)
df_fare = trn_df[trn_df.LogFare>0]
fig,axs = plt.subplots(1,2, figsize=(11,5))
sns.boxenplot(data=df_fare, x=dep, y="LogFare", ax=axs[0])
sns.kdeplot(data=df_fare, x="LogFare", ax=axs[1])
plt.show()
preds = val_xs.LogFare>2.7
abs_mean = mean_absolute_error(val_y, preds)
print(abs_mean)

def _side_score(side, y):
    """
    计算子集的得分（标准差x权重，乘以权重是因为子集大小可能不一样，乘以权重可以平衡）
    side: a boolean series
    y: y是因变量，完整的
    y[side]: 从完整的因变量挑出子集side对应的因变量子集
    """
    tot = side.sum()
    if tot<=1: return 0
    return y[side].std()*tot

def score(col, y, split):
    """
    计算不纯度，两个子集的得分之和除以总的行数
    其中col是特征列、y是因变量，split是分割点即分割阈值
    """
    lhs = col<=split
    return (_side_score(lhs,y) + _side_score(~lhs,y))/len(y)
score1 = score(trn_xs["Sex"], trn_y, 0.5)
print(score1)
score2 = score(trn_xs["LogFare"], trn_y, 2.7)
print(score2)
nm = "Age"
col = trn_xs[nm]
unq = col.unique()
unq.sort()
scores = np.array([score(col, trn_y, o) for o in unq if not np.isnan(o)])
def min_col(df, nm):
    # df 是二元分割的子集
    col,y = df[nm],df[dep]
    unq = col.dropna().unique()
    scores = np.array([score(col, y, o) for o in unq if not np.isnan(o)])
    idx = scores.argmin()
    return unq[idx],scores[idx]

idx, score3 = min_col(trn_df, "Age")
print(idx, score3)
cols = cats+conts
d = {o:min_col(trn_df, o) for o in cols}
print(d)
cols = cats+conts
d1 = {o:min_col(trn_df, o) for o in cols}
print(d1)

cols.remove("Sex")
print(cols)

ismale = trn_df.Sex==1
males, females = trn_df[ismale], trn_df[~ismale]

score_dict = {o: min_col(males, o) for o in cols}
print(f"males====>\n{score_dict}")
score_dict = {o: min_col(females, o) for o in cols}
print(f"females====>\n{score_dict}")


# 使用sklearn封装的分类器来构造优化的决策树

m = DecisionTreeClassifier(max_leaf_nodes=4).fit(trn_xs, trn_y)
print(m,m.score(trn_xs, trn_y),m.score(val_xs, val_y))

def draw_tree(t, df, size=10, ratio=0.6, precision=2, **kwargs):
    s=export_graphviz(t, out_file=None, feature_names=df.columns, filled=True, rounded=True,
                      special_characters=True, rotate=False, precision=precision, **kwargs)
    return graphviz.Source(re.sub('Tree {', f'Tree {{ size={size}; ratio={ratio}', s))

dot = draw_tree(m, trn_xs, size=10)
dot.render("tree", view=True)

def gini(cond):
    act = df.loc[cond, dep]
    return 1 - act.mean()**2 - (1-act).mean()**2

gini(df.Sex=='female'), gini(df.Sex=='male')

mean_absolute_error(val_y, m.predict(val_xs))

m = DecisionTreeClassifier(min_samples_leaf=50)
m.fit(trn_xs, trn_y)
draw_tree(m, trn_xs, size=12)

sc = mean_absolute_error(val_y, m.predict(val_xs))
print(f"sc+++>{sc}")
pd.DataFrame(dict(cols=trn_xs.columns, imp=m.feature_importances_)).plot(kind='barh',
                                                                         x='cols',
                                                                         y='imp',
                                                                         figsize=(10, 6))
plt.title('Feature Importances')
plt.xlabel('Importance')
plt.ylabel('Features')
plt.tight_layout()
plt.show()

# 使用网格搜索优化决策树

m = DecisionTreeClassifier()
param_grid = {'min_samples_leaf': [i + 4 for i in range(61)],
              'max_leaf_nodes': [i + 4 for i in range(61)],
              'max_depth': [i + 4 for i in range(61)]
              }
grid_search = GridSearchCV(m, param_grid, cv=5, scoring='neg_mean_absolute_error')

# 训练网格搜索模型
grid_search.fit(trn_xs, trn_y)

# 获取最佳参数
best_min_samples = grid_search.best_params_['min_samples_leaf']
# best_max_leaf_nodes = grid_search.best_params_['max_leaf_nodes']
best_max_depth = grid_search.best_params_['max_depth']
print(f"Best parameters: min_samples_leaf={best_min_samples}, max_depth={best_max_depth}")
# # 使用最佳参数重新训练模型
# m = DecisionTreeClassifier(
#     min_samples_leaf=int(best_min_samples),
#     max_leaf_nodes=best_max_leaf_nodes,
#     max_depth=best_max_depth,
#     random_state=42
# )
# m.fit(trn_xs, trn_y)
#
# sc = mean_absolute_error(val_y, m.predict(val_xs))
# print(f"使用网格搜索优化后的决策树得分：{sc}")
# print(m.score(trn_xs, trn_y), m.score(val_xs, val_y))  # 优化后
