# -*- coding: utf-8 -*-
import os
import dash
import dash_core_components as dcc
import dash_html_components as html
import dash_bootstrap_components as dbc
import pandas as pd
from numpy import nan
from datetime import datetime as dt
from datetime import timedelta

from .models import Stinfo, o2013Obs, o2014Obs, o2015Obs, o2016Obs, o2017Obs, o2018Obs, o2019Obs
from django.forms.models import model_to_dict

from django.db.models import Q

from dash.dependencies import Input, Output
from django_plotly_dash import DjangoDash

from plotly.offline import plot
import plotly.graph_objs as go


app = DjangoDash('dashApp1', add_bootstrap_links=True)

DBname = 'epaobs'

####取得測站資訊、區域測站、縣市測站
stlists = Stinfo.objects.using(DBname).all().filter(
    ~Q(type='FPG')).order_by("-county")
stDict = {i.pop("ch_name"): i for i in stlists.values()}
areaDict, stTypeDict = {}, {}
for key,value in stDict.items():
    try:
        areaDict.update({ value['county'] : areaDict[value['county']] + [key]})
    except KeyError:
        areaDict.update({ value['county'] : [key]})

    try:
        if len(value['type'].split(',')) > 1:
            for tt in value['type'].split(','):
                stTypeDict.update({ tt : stTypeDict[tt] + [key]})
        else:
            stTypeDict.update({ value['type'] : stTypeDict[value['type']] + [key]})
    except KeyError:
        stTypeDict.update({ value['type'] : [key]})
# print(stDict)
# print(areaDict)
# print(stTypeDict)

#取得觀測數據
def getepaobs(stlist,spclist,date1,date2):
    for year in range(date1.year,date2.year+1):
        # print('ccc0',date1.strftime("%Y-%m-%d"),(date2+timedelta(days=1)).strftime("%Y-%m-%d"))
        c_stlist =  '( '+' | '.join(['Q(stid="'+str(id)+'")' for id in stlist ])+' )'
        cmd = 'o'+str(year)+'Obs.objects.using(DBname).filter('+c_stlist + \
                ' & Q(time__range=["'+date1.strftime("%Y-%m-%d")+'","'+(date2+timedelta(days=1)).strftime("%Y-%m-%d")+'"]))'
        # print(cmd)
        obs = eval(cmd)
        df = pd.DataFrame(list(obs.values()))
    return(df)

#整理觀測數據
def changeColname(pdOld,flag):
    pdOld = pdOld.set_index(pdOld['time'])
    pdOld = pdOld.drop(['time'], axis=1).drop(['id'], axis=1)
    allSTList = list(pdOld['stid'].unique())
    pdNew = pd.DataFrame()
    for st in allSTList:
        dataTmp = pdOld[pdOld['stid'] == st] #.drop(['stid'], axis=1)
        if flag=='cwb':
            ST_cname = Stinfo.objects.using(DBname).filter(stid=st)
            ST_cname = [i.ch_name for i in ST_cname][0]
            coltuples = [(ST_cname, self.cwbVarInfo[i.upper()]) for i in list(dataTmp.columns)]
        elif flag=='epa':
            ST_cname = Stinfo.objects.using(DBname).filter(stid=st)
            ST_cname = [i.ch_name for i in ST_cname][0]
            coltuples = [(ST_cname, i) for i in list(dataTmp.columns)]
        dataTmp.columns = pd.MultiIndex.from_tuples(coltuples, names=['st', 'spc'])
        pdNew = pd.concat([pdNew, dataTmp], axis=1)
    return pdNew

###### 網頁框架呈現開始
app.layout = html.Div([
    dbc.Row([
        dbc.Col([
            dbc.Row(
                dcc.DatePickerRange(
                    id='my-date-picker-range',
                    display_format='YYYY-MM-DD',
                    min_date_allowed=dt(2015, 1, 1),
                    max_date_allowed=dt(2019, 12, 31),
                    initial_visible_month=dt(2016, 1, 15),
                    start_date=dt(2016, 1, 1).date(),
                    end_date=dt(2016, 1, 31).date(),
                    style=dict(
                        width='100%',
                    ),
                ),align='center',style={'padding':'10px 20px'}),
            dbc.Row(
                dbc.Select( id='plotType', 
                    value='mapPlot',
                    options=[{'label': i, 'value': j} for j, i in [('lineChart', '折線圖'), ('mapPlot','全台測站日均值(MAP)')]],
                    ),
                style={'padding':'10px 20px'}
            ),
            dbc.Row(
                id='specSelectDiv', style={'padding':'10px 20px'}),
            dbc.Row(
                id='select1Div',align='center',style={'padding':'10px 20px'}),
            dbc.Row(
                dbc.RadioItems( id='select2',inline=True, ),
                style={'padding':'10px 20px'}
            ),
            dbc.Row(
                dbc.Checklist( id='select3',inline=True, ),
                style={'padding':'10px 20px'}
            ),
        ],width=3,style={'board':'1px'}),
        dbc.Col(id='plotArea', width=9,),
    ]),
])

@app.callback(
    [Output('specSelectDiv', 'children'),
     Output('select1Div', 'children')
    ],
    [Input('plotType', 'value')])
def set_specSelect_option(plotTypeVal):
    option = [{'label':i,'value':i} for i in ['no','no2','nox','o3','pm10','pm25','so2','thc','nmhc']]
    if plotTypeVal == 'lineChart':
        return [[dbc.Checklist(options=option, id='specSelect', inline=True,)],
        [dbc.Select(id='select1',
        options=[{'label': i, 'value': j} for j, i in [('areaDict', '縣市分類'), ('stTypeDict', '形態分類')]],
        value='areaDict', style=dict(width='100%'))]]
    else:
        return [[dbc.RadioItems(options=option, id='specSelect', inline=True)],[]]

@app.callback(
    Output('select2', 'options'),
    [Input('select1', 'value'),
     Input('plotType', 'value')])
def set_select2_options(select1Val,plotTypeVal):
    if plotTypeVal == 'lineChart':
        return [{'label': i, 'value': i} for i in eval(select1Val)]
    else:
        return []

@app.callback(
    Output('select3', 'options'),
    [Input('select1', 'value'),
     Input('select2', 'value'),
     Input('plotType', 'value')])
def set_select3_options(select1Val, select2Val,plotTypeVal):
    # print('bbb',select1Val,select2Val)
    if select2Val and plotTypeVal == 'lineChart':
        stNameList = eval(select1Val)[select2Val]
        # print('bbb', stNameList)
        return [{'label': i, 'value': stDict[i]['stid']} for i in stNameList]
    else:
        return []

@app.callback(
    # [Output("plotLineOut", "style"), Output("plotLineOut", "figure"),],
    Output("plotArea", "children"),
    [Input("select3", "value"),
    Input("specSelect", "value"),
    Input("my-date-picker-range", "start_date"),
    Input("my-date-picker-range", "end_date"),
    Input("plotType", "value"),
    ])
def plotChart(st_list,spec_list,date1,date2,plotType):
    #####折線圖#################
    if spec_list and len(spec_list)>0:
        date1 = dt.strptime(date1,'%Y-%m-%d')
        date2 = dt.strptime(date2,'%Y-%m-%d')
        dccGraph = []

        if plotType=='lineChart':
            df = getepaobs(st_list,spec_list,date1,date2)
            df = changeColname(df,'epa')
            cst_list = df.columns.levels[0]
            for spec in spec_list:
                cmd = []
                for st in cst_list:
                    y_data = df[st,spec]
                    y_data[y_data<0] = None   #去除-999
                    cmd.append(go.Scatter(x=df.index, y=y_data, mode='lines', name=st, opacity=0.8)) 

                layout = go.Layout(
                            title= spec,font=dict(family='<b>Courier New</b>', size=20, color='black'),
                            xaxis=dict(tickfont=dict(family='<b>Courier New</b>', size=15),color='black',gridcolor='#9d9d9d',
                                    showline=True,linewidth=3,mirror='ticks',tickformat='%d %B (%a)<br>%Y'),
                            yaxis=dict(rangemode='tozero',
                                    titlefont=dict(family='<b>Courier New</b>',color='black'),
                                    tickfont=dict(family='<b>Courier New</b>', size=15,color='black'),
                                    gridcolor='#9d9d9d',showline=True,linewidth=3,mirror='ticks'),
                            # showlegend=True,
                            legend=dict(font={'size':12}, bordercolor="Black",borderwidth=2,traceorder="normal",),
                        )
                dccGraph.append(dcc.Graph(figure={'data':cmd,'layout':layout},animate=False))
            return dccGraph

        #####地圖呈現 時間內平均值#################
        elif plotType=='mapPlot':
            cmd = 'o'+str(date1.year)+'Obs.objects.using(DBname).filter( Q(time__range=["'+date1.strftime("%Y-%m-%d")+'","'+(date2+timedelta(days=1)).strftime("%Y-%m-%d")+'"]))'
            df = pd.DataFrame(list(eval(cmd).values()))
            df = changeColname(df,'epa')

            ###取得觀測值測站代碼
            stid = df.iloc[:, df.columns.get_level_values(1)=='stid'].iloc[0]
            stid_index = list(stid.index.droplevel(1))
            stid_value = [int(i) for i in list(stid[:])]
            stid = pd.DataFrame(data={'stname':stid_index},index=stid_value)

            ###取得測站詳細資訊(lat lon)
            stInfo = pd.DataFrame(list((Stinfo.objects.using(DBname)).values()))
            stInfo.index = stInfo.stid
            ###合併兩者，得到本資料得詳細測站資料順序      
            stInfo = pd.merge(stid,stInfo ,left_index=True, right_index=True, how='inner')

            ###選出物種
            df = df.iloc[:, df.columns.get_level_values(1)==spec_list]
            df.columns = df.columns.droplevel(1)
            df[df<0] = nan #去除-999
            dataseris = df.mean(axis=0).round(2)

            stInfo['text'] = [x +' '+spec_list.upper()+ ' : '+str(y) for x, y in zip(stInfo['ch_name'], dataseris)]
            
            cmd = [go.Scattermapbox(
                    lon = stInfo['lon'],
                    lat = stInfo['lat'],
                    text = stInfo['ch_name'],
                    mode = 'markers',
                    hovertext = stInfo['text'],
                    hoverinfo = 'text',

                    hoverlabel=dict(
                        bgcolor="white", 
                        font_size=16, 
                        font_family="Rockwell"
                    ),
                    marker_color=dataseris,
                    marker = go.scattermapbox.Marker(size=14),  
                    )]
            mapbox_access_token = os.environ['mapbox_access_token']

            layout = go.Layout(
                title = spec_list.upper()+'於'+date1.strftime('%Y/%m/%d')+'的日均值',
                font=dict(family='Courier New, monospace', size=18, color='rgb(0,0,0)'),
                autosize=False,
                hovermode='closest',
                showlegend=False,
                width=1200,
                height=1000,
                mapbox=dict(
                    accesstoken=mapbox_access_token,
                    bearing=0,
                    center=dict(
                        lat=23.5,
                        lon=121),
                    pitch=0,
                    zoom=7,
                    style = 'dark'
                    ),
                )
            dccGraph.append(dcc.Graph(figure={'data':cmd,'layout':layout},animate=False))
            return dccGraph

    else:
        return []

