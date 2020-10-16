# coding:utf-8
#
# The MIT License (MIT)
#
# Copyright (c) 2018-2020 azai/Rgveda/GolemQuant
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
import datetime
import time
import numpy as np
import pandas as pd
import pymongo

try:
    import QUANTAXIS as QA
except:
    print('PLEASE run "pip install QUANTAXIS" before call GolemQ.GQFetch.StockCN_realtime modules')
    pass

try:
    from GolemQ.GQUtil.parameter import (
        AKA, 
        INDICATOR_FIELD as FLD, 
        TREND_STATUS as ST
    )
except:
    class AKA():
        """
        常量，专有名称指标，定义成常量可以避免直接打字符串造成的拼写错误。
        """

        # 蜡烛线指标
        CODE = 'code'
        NAME = 'name'
        OPEN = 'open'
        HIGH = 'high'
        LOW = 'low'
        CLOSE = 'close'
        VOLUME = 'volume'
        VOL = 'vol'
        DATETIME = 'datetime'
        LAST_CLOSE = 'last_close'
        PRE_CLOSE = 'pre_close'

        def __setattr__(self, name, value):
            raise Exception(u'Const Class can\'t allow to change property\' value.')
            return super().__setattr__(name, value)

from QUANTAXIS.QAUtil import (
    DATABASE,
    )


def GQ_fetch_stock_realtime_adv(
    code=None,
    num=1,
    collections=DATABASE.get_collection(
        'realtime_{}'.format(datetime.date.today())
    ),
    verbose=True,
):
    '''
    返回当日的上下五档, code可以是股票可以是list, num是每个股票获取的数量
    :param code:
    :param num:
    :param collections:  realtime_XXXX-XX-XX 每天实时时间
    :return: DataFrame
    '''
    if code is not None:
        # code 必须转换成list 去查询数据库
        if isinstance(code, str):
            code = [code]
        elif isinstance(code, list):
            pass
        else:
            print(
                "QA Error QA_fetch_stock_realtime_adv parameter code is not List type or String type"
            )

        items_from_collections = [
            item for item in collections.find(
                {'code': {
                    '$in': code
                }},
                limit=num * len(code),
                sort=[('datetime',
                       pymongo.DESCENDING)]
            )
        ]
        if (items_from_collections is None) or \
            (len(items_from_collections) == 0):
            if verbose:
                print(
                    "QA Error QA_fetch_stock_realtime_adv find parameter code={} num={} collection={} return NOne"
                    .format(code,
                            num,
                            collections)
                )
            return

        data = pd.DataFrame(items_from_collections)
        data_set_index = data.set_index(['datetime',
                                         'code'],
                                        drop=False).drop(['_id'],
                                                            axis=1)

        return data_set_index
    else:
        print("QA Error QA_fetch_stock_realtime_adv parameter code is None")


def GQ_fetch_stock_day_realtime_adv(codelist, 
                                    data_day, 
                                    verbose=True):
    """
    查询日线实盘数据，支持多股查询
    """
    if codelist is not None:
        # codelist 必须转换成list 去查询数据库
        if isinstance(codelist, str):
            codelist = [codelist]
        elif isinstance(codelist, list):
            pass
        else:
            print("QA Error GQ_fetch_stock_day_realtime_adv parameter codelist is not List type or String type")

    if ((datetime.datetime.combine(datetime.date.today(), 
                                   datetime.datetime.min.time()) - data_day.data.index.get_level_values(level=0)[-1].to_pydatetime()) > datetime.timedelta(hours=10)):
        if (verbose == True):
            print('时间戳差距超过：', datetime.datetime.combine(datetime.date.today(), 
                                                             datetime.datetime.min.time()) - data_day.data.index.get_level_values(level=0)[-1].to_pydatetime(),
                  '尝试查找实盘数据....', codelist)
        #print(codelist, verbose)
        try:
            data_realtime = QA.QA_fetch_stock_realtime_adv(codelist, num=5000, verbose=verbose)
        except: 
            data_realtime = GQ_fetch_stock_realtime_adv(codelist, num=5000, verbose=verbose)
        if (data_realtime is not None) and \
            (len(data_realtime) > 0):
            # 合并实盘实时数据
            data_realtime = data_realtime.drop_duplicates((["datetime",
                        'code'])).set_index(["datetime",
                        'code'],
                            drop=False)
            data_realtime = data_realtime.reset_index(level=[1], drop=True)
            data_realtime['date'] = pd.to_datetime(data_realtime['datetime']).dt.strftime('%Y-%m-%d')
            data_realtime['datetime'] = pd.to_datetime(data_realtime['datetime'])
            for code in codelist:
                # 顺便检查股票行情长度，发现低于30天直接砍掉。
                if (len(data_day.select_code(code)) < 30):
                    print(u'{} 行情只有{}天数据，新股或者数据不足，不进行择时分析。'.format(code, 
                                                                   len(data_day.select_code(code))))
                    data_day.data.drop(data_day.select_code(code), inplace=True)
                    continue

                # *** 注意，QA_data_tick_resample_1min 函数不支持多标的 *** 需要循环处理
                data_realtime_code = data_realtime[data_realtime['code'].eq(code)]
                if (len(data_realtime_code) > 0):
                    data_realtime_code = data_realtime_code.set_index(['datetime']).sort_index()
                    if ('volume' in data_realtime_code.columns) and \
                        ('vol' not in data_realtime_code.columns):
                        # 我也不知道为什么要这样转来转去，但是各家(新浪，pytdx)l1数据就是那么不统一
                        data_realtime_code.rename(columns={"volume": "vol"}, 
                                                    inplace = True)
                    elif ('volume' in data_realtime_code.columns):
                        data_realtime_code['vol'] = np.where(np.isnan(data_realtime_code['vol']), 
                                                             data_realtime_code['volume'], 
                                                             data_realtime_code['vol'])

                    # 一分钟数据转出来了
                    #data_realtime_1min =
                    #QA.QA_data_tick_resample_1min(data_realtime_code,
                    #                                                   type_='1min')
                    try:
                        data_realtime_1min = QA.QA_data_tick_resample_1min(data_realtime_code, 
                                                                           type_='1min')
                    except:
                        print('fooo1', code)
                        print(data_realtime_code)
                        raise('foooo1{}'.format(code))
                    data_realtime_1day = QA.QA_data_min_to_day(data_realtime_1min)
                    if (len(data_realtime_1day) > 0):
                        # 转成日线数据
                        data_realtime_1day.rename(columns={"vol": "volume"}, 
                                                    inplace = True)

                        # 假装复了权，我建议复权那几天直接量化处理，复权几天内对策略买卖点影响很大
                        data_realtime_1day['adj'] = 1.0 
                        data_realtime_1day['datetime'] = pd.to_datetime(data_realtime_1day.index)
                        data_realtime_1day = data_realtime_1day.set_index(['datetime', 'code'], 
                                                                        drop=True).sort_index()

                        # issue:成交量计算不正确，成交量计算差距较大，这里尝试处理方法，但是貌似不对
                        data_realtime_1day[AKA.VOLUME] = data_realtime_1min[AKA.VOLUME][-1] / data_realtime_1min[AKA.CLOSE][-1]

                        if (verbose == True):
                            print(u'追加实时实盘数据，股票代码：{} 时间：{} 价格：{}'.format(data_realtime_1day.index[0][1],
                                                                                     data_realtime_1day.index[0][0],
                                                                                     data_realtime_1day[AKA.CLOSE][-1]))
                        data_day.data = data_day.data.append(data_realtime_1day, 
                                                             sort=True)

    return data_day


def GQ_fetch_stock_min_realtime_adv(codelist,
                                    data_min,
                                    frequency, 
                                    verbose=True):
    """
    查询A股的指定小时/分钟线线实盘数据
    """
    if codelist is not None:
        # codelist 必须转换成list 去查询数据库
        if isinstance(codelist, str):
            codelist = [codelist]
        elif isinstance(codelist, list):
            pass
        else:
            print("QA Error GQ_fetch_stock_min_realtime_adv parameter codelist is not List type or String type")

    if data_min is None:
        print(u'代码：{} 今天停牌或者已经退市'.format(codelist))  
        return None

    try:
        foo = (datetime.datetime.now() - data_min.data.index.get_level_values(level=0)[-1].to_pydatetime())
    except:
        print(u'代码：{} 今天停牌或者已经退市'.format(codelist))                    
        return None

    if ((datetime.datetime.now() - data_min.data.index.get_level_values(level=0)[-1].to_pydatetime()) > datetime.timedelta(hours=10)):
        if (verbose == True):
            print('时间戳差距超过：', datetime.datetime.now() - data_min.data.index.get_level_values(level=0)[-1].to_pydatetime(),
                  '尝试查找实盘数据....', codelist)
        #print(codelist, verbose)
        try:
            data_realtime = QA.QA_fetch_stock_realtime_adv(codelist, num=5000, verbose=verbose)
        except: 
            data_realtime = GQ_fetch_stock_realtime_adv(codelist, num=5000, verbose=verbose)
        if (data_realtime is not None) and \
            (len(data_realtime) > 0):
            # 合并实盘实时数据
            data_realtime = data_realtime.drop_duplicates((["datetime",
                        'code'])).set_index(["datetime",
                        'code'],
                            drop=False)

            data_realtime = data_realtime.reset_index(level=[1], drop=True)
            data_realtime['date'] = pd.to_datetime(data_realtime['datetime']).dt.strftime('%Y-%m-%d')
            data_realtime['datetime'] = pd.to_datetime(data_realtime['datetime'])
            for code in codelist:
                # 顺便检查股票行情长度，发现低于30天直接砍掉。
                try:
                    if (len(data_min.select_code(code)) < 30):
                        print(u'{} 行情只有{}天数据，新股或者数据不足，不进行择时分析。新股买不买卖不卖，建议掷骰子。'.format(code, 
                                                                       len(data_min.select_code(code))))
                        data_min.data.drop(data_min.select_code(code), inplace=True)
                        continue
                except:
                    print(u'代码：{} 今天停牌或者已经退市'.format(code))                    
                    continue

                # *** 注意，QA_data_tick_resample_1min 函数不支持多标的 *** 需要循环处理
                data_realtime_code = data_realtime[data_realtime['code'].eq(code)]
                if (len(data_realtime_code) > 0):
                    data_realtime_code = data_realtime_code.set_index(['datetime']).sort_index()
                    if ('volume' in data_realtime_code.columns) and \
                        ('vol' not in data_realtime_code.columns):
                        # 我也不知道为什么要这样转来转去，但是各家(新浪，pytdx)l1数据就是那么不统一
                        data_realtime_code.rename(columns={"volume": "vol"}, 
                                                  inplace = True)
                    elif ('volume' in data_realtime_code.columns):
                        data_realtime_code['vol'] = np.where(np.isnan(data_realtime_code['vol']), 
                                                             data_realtime_code['volume'], 
                                                             data_realtime_code['vol'])

                    # 将l1 Tick数据重采样为1分钟
                    try:
                        data_realtime_1min = QA.QA_data_tick_resample_1min(data_realtime_code, 
                                                                           type_='1min')
                    except:
                        print('fooo1', code)
                        print(data_realtime_code)
                        pass
                        #raise('foooo1{}'.format(code))

                    if (len(data_realtime_1min) == 0):
                        # 没有数据或者数据缺失，尝试获取腾讯财经的1分钟数据
                        import easyquotation
                        quotation = easyquotation.use("timekline")
                        data = quotation.real(codelist, prefix=False)
                        print(data)
                        pass
                        return data_min

                    # 一分钟数据转出来了，重采样为指定小时/分钟线数据
                    data_realtime_1min = data_realtime_1min.reset_index([1], drop=False)
                    data_realtime_mins = QA.QA_data_min_resample(data_realtime_1min, 
                                                                      type_=frequency)

                    if (len(data_realtime_mins) > 0):
                        # 转成指定分钟线数据
                        data_realtime_mins.rename(columns={"vol": "volume"}, 
                                                    inplace = True)


                        # 假装复了权，我建议复权那几天直接量化处理，复权几天内对策略买卖点影响很大
                        data_realtime_mins['adj'] = 1.0 
                        #data_realtime_mins['datetime'] =
                        #pd.to_datetime(data_realtime_mins.index)
                        #data_realtime_mins =
                        #data_realtime_mins.set_index(['datetime', 'code'],
                        #                                                drop=True).sort_index()
                        if (verbose == True):
                            print(u'追加实时实盘数据，股票代码：{} 时间：{} 价格：{}'.format(data_realtime_mins.index[0][1],
                                                                                     data_realtime_mins.index[0][0],
                                                                                     data_realtime_mins[AKA.CLOSE][-1]))
                        data_min.data = data_min.data.append(data_realtime_mins, 
                                                             sort=True)
                        # Amount, Volume 计算不对
    else:
        if (verbose == True):
            print(u'没有时间差', datetime.datetime.now() - data_min.data.index.get_level_values(level=0)[-1].to_pydatetime())

    return data_min

    #
    #data_realtime_1min = data_realtime_1min.reset_index(level=[1], drop=False)

    #data_realtime_5min = QA.QA_data_min_resample(data_realtime_1min,
    #                                             type_='5min')
    #print(data_realtime_5min)

    #data_realtime_15min = QA.QA_data_min_resample(data_realtime_1min,
    #                                              type_='15min')
    #print(data_realtime_15min)

    #data_realtime_30min = QA.QA_data_min_resample(data_realtime_1min,
    #                                              type_='30min')
    #print(data_realtime_30min)
    #data_realtime_1hour = QA.QA_data_min_resample(data_realtime_1min,
    #                                             type_='60min')
    #print(data_realtime_1hour)
    #return data_min
def GQ_fetch_index_min_realtime_adv(codelist,
                                    data_min,
                                    frequency, 
                                    verbose=True):
    """
    查询指数和ETF的分钟线实盘数据
    """
    # 将l1 Tick数据重采样为1分钟
    data_realtime_1min = data_realtime_1min.reset_index(level=[1], drop=False)

    # 检查 1min数据是否完整，如果不完整，需要从腾讯财经获取1min K线
    #if ():


    data_realtime_5min = QA.QA_data_min_resample(data_realtime_1min, 
                                                 type_='5min')
    print(data_realtime_5min)

    data_realtime_15min = QA.QA_data_min_resample(data_realtime_1min, 
                                                  type_='15min')
    print(data_realtime_15min)

    data_realtime_30min = QA.QA_data_min_resample(data_realtime_1min, 
                                                  type_='30min')
    print(data_realtime_30min)
    data_realtime_1hour = QA.QA_data_min_resample(data_realtime_1min,
                                                 type_='60min')
    print(data_realtime_1hour)
    return data_min


if __name__ == '__main__':
    """
    用法示范
    """
    codelist = ['600157', '300263']
    data_min = QA.QA_fetch_stock_day_adv(codelist,
                                        '2008-01-01',
                                        '{}'.format(datetime.date.today(),)).to_qfq()

    data_min = GQ_fetch_stock_day_realtime_adv(codelist, data_min)