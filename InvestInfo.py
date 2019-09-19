#當日大盤每日盤後資訊
import pandas as pd,sys,json,requests as rq
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib

#是否為假日 schedule:DataFrame sToday:西元 yyyy/mm/dd 不補0
def isHoliday(schedule,date):
    getDate = schedule[schedule['date']==date]
    if getDate.size > 0 and getDate.iloc[0,1] == '是':
        return True
    else:
        return False

#取得大盤資訊;13:35公布 sToday:西元 yyyymmdd 補0
def getXTAI(sToday):
    #大盤成交資訊
    sUrl = "https://www.twse.com.tw/exchangeReport/FMTQIK?response=html&date=" + sToday

    try:
        df = pd.read_html(sUrl)
        df = df[0]
    except:
        raise Exception("查無大盤資料")

    #調整欄位名稱
    df.columns = [ "日期", "成交股數","成交金額", "成交筆數","發行量加權股價指數","漲跌點數" ]
    df = df.tail(1)

    sFormat = "<div style='text-align:center'><h2>加權指數{0}點，收盤{1:,}點，成交量{2:,}億</h2></div><br><br>"
    #成交金額
    sAmt = round(df.iloc[0,2]/(10**8),2)
    #交易日
    sDate = df.iloc[0,0]
    #漲跌
    if df.iloc[0,5] < 0 :
        sUpDown = "下跌" + str(df.iloc[0,5]*(-1))
    else:
        sUpDown = "上漲" + str(df.iloc[0,5])

    #Format : 加權指數下跌xxx.xx點，收盤xx,xxx.xx點，成交量xx,xxx.xx億
    return sFormat.format(sUpDown,df.iloc[0,4],sAmt)

#單位轉換:億 買賣超
def billion(numb):
    if numb < 0 :
        sBySl = "賣超{0:,.2f}億元".format(numb*(-1)/(10**8))
    else:
        sBySl = "買超{0:,.2f}億元".format(numb/(10**8))
    return sBySl

#單位轉換:百萬
def million(numb):
    numb = int(numb)
    return "{0:,.2f}".format(numb/(10**6))

#每日三大法人買賣資訊;14:45公布 sToday:西元 yyyymmdd 補0
def get3People(sToday):
    sUrl = "https://www.twse.com.tw/fund/BFI82U?response=html&type=day&dayDate=" + sToday

    try:
        df = pd.read_html(sUrl)
        df = df[0]
    except:
        raise Exception("查無法人資料")

    #調整欄位名稱
    df.columns = [ "單位名稱", "買進金額","賣出金額", "買賣差額"]
    #自營商(自行買賣)
    s0,s1 = "自營商",billion(df.iloc[0,3])
    #投信
    s2,s3 = df.iloc[2,0],billion(df.iloc[2,3])
    #外資
    s4,s5 = "外資",billion(df.iloc[3,3])
    #買賣超合計
    s6,s7 = df.iloc[5,0],billion(df.iloc[5,3])

    #輸出格式
    sFormat = f'''
    <table style='border:1px solid black;margin-left:auto;margin-right:auto;padding:5px;' width='100%'
    rules="all" cellpadding='5'>
        <tr><td colspan='2' style='text-align:center;font-weight: bold;'>集中市場三大法人買賣超</td></tr>
        <tr><td width='50%'>{s0}</td><td>{s1}</td></tr>
        <tr><td>{s2}</td><td>{s3}</td></tr>
        <tr><td>{s4}</td><td>{s5}</td></tr>
        <tr><td>{s6}</td><td>{s7}</td></tr>    
    </table>
    '''

    return sFormat

#台指期貨外資留單狀況;15:00公布 sToday:西元 yyyy/mm/dd 補0
def getFuture(sToday):
    sUrl = "https://www.taifex.com.tw/cht/3/futContractsDate"
    formdata = {"queryType":"1", "goDay":"", "doQuery":"1", "dateaddcnt":"","commodityId":"TXF",
                "queryDate":sToday}

    try:
        html = rq.post(sUrl, data=formdata)
        df = pd.read_html(html.content)[2].iloc[4:8,0:17].iloc[1:,[2,9,10,11,12,13,14]]
    except:
        raise Exception("查無期市資料")

    df.reset_index(drop=True, inplace=True)
    df.columns = ['身份別','多方口數','多方淨額','空方口數','空方淨額','多空口數','多空淨額']

    #格式化
    for i in range(0,3):
        for j in range(1,7):
            if (j % 2) == 1 :
                #index 1,3,5是買賣口數
                df.iloc[i,j] = "{0:,}".format(int(df.iloc[i,j]))
            else:
                #index 2,4,6是買賣金額
                df.iloc[i,j] = million(df.iloc[i,j])

    #自營商
    s0,s1,s2,s3,s4,s5 = tuple(df.iloc[0,1:])
    #投信
    s6,s7,s8,s9,s10,s11 = tuple(df.iloc[1,1:])
    #外資
    s12,s13,s14,s15,s16,s17 = tuple(df.iloc[2,1:])

    #輸出格式
    sOut = f'''<br>
        <table style="border:1px solid black;margin-left:auto;margin-right:auto;padding:5px;text-align:right"
        rules="all" cellpadding="5" width="100%">
         <tr><td colspan="7" style="text-align:center;font-weight: bold;">台指期未平倉餘額</td></tr>
         <tr style="text-align:center">
          <td>&nbsp;</td>
          <td colspan="2">多方</td><td colspan="2">空方</td><td colspan="2">多空淨額</td>
         </tr>
         <tr style="text-align:center">
          <td>身份別</td>          
          <td>口數</td>
          <td>契約<br>金額</td>
          <td>口數</td>
          <td>契約<br>金額</td>
          <td>口數</td>
          <td>契約<br>金額</td>
         </tr>
         <tr>
          <td style="text-align:center">自營商</td><td>{s0}</td><td>{s1}</td><td>{s2}</td><td>{s3}</td><td>{s4}</td><td>{s5}</td>
         </tr>
         <tr>
          <td style="text-align:center">投信</td><td>{s6}</td><td>{s7}</td><td>{s8}</td><td>{s9}</td><td>{s10}</td><td>{s11}</td>
         </tr>
         <tr>
          <td style="text-align:center">外資</td><td>{s12}</td><td>{s13}</td><td>{s14}</td><td>{s15}</td><td>{s16}</td><td>{s17}</td>
         </tr>
        </table>契約金額單位:百萬元
    '''
    return sOut

if __name__ == '__main__':
    #工作日
    dToday = datetime.now()
    #dToday = datetime(2019,7,31,15,11)

    #取得內政部行事曆
    schd = pd.read_json('https://data.ntpc.gov.tw/api/v1/rest/datastore/382000000A-000077-002')
    schd = pd.DataFrame(schd.iloc[2,1]).iloc[:,[0,3]].tail(200).reset_index(drop=True)

    if isHoliday(schd,dToday.strftime('%Y/%#m/%#d')):
        print('股期休市')
    elif dToday.hour < 15 or (dToday.hour == 15 and dToday.minute < 10):
        #最後公布的是台指期15:00，怕會delay，所以設15:10
        print('資訊尚未完整公布，請下午3點10分過後執行')
    else:
        #大盤
        sBody = getXTAI(dToday.strftime('%Y%m%d'))
        #三大法人
        sBody += get3People(dToday.strftime('%Y%m%d'))
        #台指期外資未平倉淨額
        sBody += getFuture(dToday.strftime('%Y/%m/%d'))

    #email html格式
    try:
        # 設定檔
        with open(r'json\cfg.json', encoding='utf-8') as json_data: cfgData = json.load(json_data)[0]
        # 信箱SMTP url
        urlSMTP = cfgData['urlSMTP']
        # 信箱登入密碼
        passwd = cfgData['passwd']
        # 寄件人信箱
        mail_from = cfgData['mail_from']
        # 收件人信箱
        receivers = cfgData['receivers']
        #合併多收件人
        mail_to = [elem.strip().split(',') for elem in receivers]

        #郵件基本設定
        msg = MIMEMultipart()
        msg['Subject'] = dToday.strftime('%m/%d') + "台股盤後彙整"
        msg['From'] = mail_from
        msg['To'] = ','.join(receivers)
        msg.preamble = 'Multipart massage.\n'

        #加入郵件本文
        part = MIMEText(sBody, 'html', 'utf-8')
        msg.attach(part)

        #連線smtp server
        smtp = smtplib.SMTP(urlSMTP)
        smtp.ehlo()
        smtp.starttls()
        smtp.login(mail_from, passwd)
        #寄信
        smtp.sendmail(msg['From'], mail_to , msg.as_string())

        print(msg['To'],"信件已寄出")
    except:
        print('{}:{}:{}'.format(sys.exc_info()[0],sys.exc_info()[1],sys.exc_info()[2]))