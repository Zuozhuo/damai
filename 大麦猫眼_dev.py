# -*- coding: utf-8 -*-
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from undetected_chromedriver import Chrome, ChromeOptions
import time
import datetime
import traceback
import pickle
import os
import sys
import json
import playsound
import openpyxl


def get_app_root():
    # 讀取檔案裡的參數值
    basis = ""
    if hasattr(sys, 'frozen'):
        basis = sys.executable
    else:
        basis = sys.argv[0]
    app_root = os.path.dirname(basis)
    return app_root

def play_sound():
    global app_root
    file_path = os.path.join(app_root, 'ding-dong.wav')
    playsound(file_path)

def load_config(config_file):
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    return config

def excel_to_list_dict(file_path, selected_cols):
    workbook = openpyxl.load_workbook(file_path)
    sheet = workbook.active
    headers = [cell.value for i, cell in enumerate(sheet[1]) if i+1 in selected_cols]  # 读取选中的列
    rows = []
    for row in sheet.iter_rows(min_row=2, max_col=max(selected_cols), values_only=True):
        row_values = [row[i-1] for i in selected_cols]
        rows.append({headers[i]: row_values[i] for i in range(len(headers))})
    return rows

def damai_login(account, pwd):
    try:
        iframe = driver.find_element(By.ID, 'alibaba-login-box')
    except:
        pass
    else:
        driver.switch_to.frame(iframe)
        try:
            driver.find_element(By.XPATH, '//a[text()="账号密码登录"]').click()
            time.sleep(0.5)
            input_account = driver.find_element(By.ID, "fm-login-id")
            input_pwd = driver.find_element(By.ID, 'fm-login-password')
            btn = driver.find_element(By.XPATH, '//button[text()="登录"]')

            input_account.send_keys(account)
            time.sleep(1)
            input_pwd.send_keys(pwd)
            time.sleep(1)
            btn.click()
            time.sleep(1)
        except:
            pass
        
    try:
        iframe = driver.find_element(By.ID, 'baxia-dialog-content')
    except:
        print('没有验证码')
        pass
    else:
        print('有验证码')
        driver.switch_to.frame(iframe)
        if driver.find_elements(By.ID, 'nc_1_n1z') : # 滑块验证
            damai_handle_slider_captcha(driver)
        elif driver.find_elements(By.ID, '`nc_1_refresh1`'): # 验证失败，请点击框体重试/请刷新页面
            click_or_refresh_div = driver.find_element(By.ID, '`nc_1_refresh1`')
            print(click_or_refresh_div.text)
            if '刷新' in click_or_refresh_div.text:
                driver.refresh()
            elif '点击' in click_or_refresh_div.text:
                click_or_refresh_div.click()
        print(0)
        # damai_handle_slider_captcha(driver)
    finally:
        driver.switch_to.default_content()

def get_cookies(account):
    filename = os.path.join(app_root, account + "_cookies.pkl")
    pickle.dump(driver.get_cookies(), open(filename, "wb")) 
    print(f"###{account} Cookie保存成功###", end='\r')
    
def set_cookies(account):
    try:
        filename = os.path.join(app_root, account + "_cookies.pkl")
        cookies = pickle.load(open(filename, "rb"))#载入cookie
        print(cookies)
        for cookie in cookies:
            cookie_dict = {
                'domain':'.damai.cn',#必须有，不然就是假登录
                'name': cookie.get('name'),
                'value': cookie.get('value'),
                "expires": "",
                'path': '/',
                'httpOnly': False,
                'HostOnly': False,
                'secure': False}
            driver.add_cookie(cookie_dict)
        print(f'###载入{account} Cookie###')
    except Exception as e:
        print(e)

def refresh_until_time(driver, ticket_time, interval_time):
    global is_need_refresh
    while True:
        now_time = datetime.datetime.now()
        delta = ticket_time - now_time
        print(delta, end='\r')
        if delta.total_seconds() <= interval_time:
            print('刷新')
            driver.refresh()
            is_need_refresh = 0
            break

def damai_choose_date(driver, dates: list):
    div = WebDriverWait(driver, 2, 0.001).until(EC.visibility_of_element_located((By.XPATH, f'//div[@class="sku-pop-wrapper"]//div[contains(text(), "{dates[0]}")]')))
    btns = []
    for date in dates:
        btn = driver.find_element(By.XPATH, '//div[@class="sku-pop-wrapper"]//div[contains(text(), "{}")]/../..'.format(date))
        btns.append(btn)
    
    count = 0 # 记录缺货登记的票价数量
    for btn_date in btns:
        try:
            btn_date.find_element(By.XPATH, './/div[contains(text(),"无票")]')    
        except NoSuchElementException: # 该日期没有“无票”标志，表示可选
            # 方法一
            driver.execute_script("arguments[0].click();", btn_date)

            # 方法二，但是在开启设备模拟仿真时会造成代码堵塞
            # actions = ActionChains(driver)
            # actions.move_to_element(btn_date).click().perform()
            return
        else: # 该价位有“缺货登记”标志，表示不可选
            count += 1
    if count == len(btns):
        return 'refresh'

def damai_choose_price(driver, prices: list):
    WebDriverWait(driver, 2, 0.001).until(
        EC.visibility_of_any_elements_located((By.XPATH, '//div[contains(@class, "sku-tickets-card")]//div[@class="sku-content"]/div'))
    ) # 所有的价格按钮

    btns = []
    for price in prices:
        btn = driver.find_element(By.XPATH, '//div[@class="sku-content"]//div[contains(text(), "{}")]/..'.format(price))
        btns.append(btn)

    count = 0 # 记录缺货登记的票价数量
    for btn_price in btns:
        try:
            btn_price.find_element(By.XPATH, './/div[contains(text(),"缺货登记")]')    
        except NoSuchElementException: # 该价位没有“缺货登记”标志，表示可选
            # 方法一，有些场次的有些价位会自动取消选定
            # driver.execute_script("arguments[0].click();", btn_price)

            # 方法二，但是在开启设备模拟仿真时会造成代码堵塞
            actions = ActionChains(driver)
            actions.move_to_element(btn_price).click().perform()
            return
        else: # 该价位有“缺货登记”标志，表示不可选
            count += 1
    if count == len(btns):
        return 'refresh'

def damai_choose_num(driver, num):
    plus = WebDriverWait(driver, 2, 0.001).until(EC.element_to_be_clickable((By.XPATH, '//div[@class="number-edit"]//div[@class="number-edit-bg"][2]')))
    try:
        value = driver.find_element(By.XPATH, '//div[@class="number-edit"]//div[@class="total"]')

        minus = driver.find_element(By.XPATH, '//div[@class="number-edit"]//div[@class="number-edit-bg"][1]')
        plus = driver.find_element(By.XPATH, '//div[@class="number-edit"]//div[@class="number-edit-bg"][2]')

        # while value.text[0] != '1':
        #     minus.click()
        for i in range(int(num)-1):
            driver.execute_script("arguments[0].click();", plus)
        try:
            assert value.text[0] == num
        except AssertionError:
            print('实际选择数量不等于{num}')
    except NoSuchElementException:
        print("页面不可选择数量")
        
def damai_page_1(driver):
    """选票页面，在选票页面选择日期，票价，数量
    https://m.damai.cn/damai/detail/item.html?itemId=..."""
    while True:
        try:
            driver.find_element(By.XPATH, '//div[@class="bui-modal sku-pop"]')
        except NoSuchElementException: # 没有弹出窗口
            while True:
                WebDriverWait(driver, 10, 0.001).until(EC.text_to_be_present_in_element_attribute((By.XPATH, '//div[@class="detail-button"]/div'), 'class', 'button button-primary'))        
                buy_btn = driver.find_element(By.XPATH, '//p[@class="buy__button__text"]')
                print(buy_btn.text, end='\r')
                if '立即' in buy_btn.text:
                    break
                elif '即将' in buy_btn.text or '缺货登记' in buy_btn.text:
                    driver.refresh()
            # buy_btn = WebDriverWait(driver, 10*60, 0.001).until(EC.text_to_be_present_in_element((By.XPATH, '//p[@class="buy__button__text"]'), '立即预订'))
            
            book = WebDriverWait(driver, 2, 0.001).until(EC.element_to_be_clickable((By.XPATH, '//div[@class="buy"]')))
            driver.execute_script("arguments[0].click();", book)
        finally: # 弹出窗口，开始选票
            # 选择日期
            flag = damai_choose_date(driver, dates.split('|'))
            if flag == 'refresh':
                print(f'{dates}都无票，刷新页面')
                js_code = "var target = document.elementFromPoint(10, 100); target.click();"
                driver.execute_script(js_code)
                continue
            # 选择价格
            flag = damai_choose_price(driver, prices.split('|'))
            if flag == 'refresh':
                print(f'{prices}价位暂时缺货，刷新页面')
                js_code = "var target = document.elementFromPoint(10, 100); target.click();"
                driver.execute_script(js_code)
                continue
            # 选择数量
            damai_choose_num(driver, num)

            # 确定
            buybtn = driver.find_element(By.XPATH, '//div[@class="sku-footer-bottom"]/div[text()="确定"]')
            driver.execute_script("arguments[0].click();", buybtn)
            break

def damai_choose_viewer(driver, viewer: list[str]):
    for i in viewer:
        try:
            checkbox = driver.find_element(By.XPATH, f'//div[@class="viewer"]//div[text()="{i}"]//following-sibling::div[2]/i')
        except NoSuchElementException:
            pass
        else:
            if 'icondanxuan-weixuan_' in checkbox.get_attribute('class'):
                # checkbox.click()
                driver.execute_script("arguments[0].click();", checkbox)

def damai_handle_div_confirm(driver):
    """处理库存不足/同一时间下单人数太多提示：点击取消按钮"""
    div_confirm = driver.find_element(By.ID, 'confirm')
    if div_confirm.find_elements(By.XPATH, './/div[contains(text(), "取消")]'):
        cancel = driver.find_element(By.XPATH, '//div[@id="confirm"]//div[contains(text(), "取消")]')
        cancel.click()
        print('点击了取消按钮')

def damai_handle_slider_captcha(driver):
    """滑块验证"""
    # 获取滑块和滑动轨道的元素
    slider = driver.find_element(By.ID, "nc_1_n1z")
    slider_scale = driver.find_element(By.ID, "nc_1__scale_text")

    # 获取滑和滑动轨道的宽度
    slider_width = slider.size["width"]
    slider_scale_width = slider_scale.size["width"]
    # print(slider_width)

    # 创建动作链
    action_chains = ActionChains(driver)

    # 点击并按住滑块
    action_chains.click_and_hold(slider).perform()

    # 拖动滑块到滑动轨道的右侧
    action_chains.drag_and_drop_by_offset(slider, slider_scale_width - slider_width, 0).perform()

    # 释放滑块
    action_chains.release().perform()

def damai_handle_iframe(driver, mode):
    """处理网络拥堵/滑动验证"""
    try:
        div_baxia_dialog_auto = driver.find_element(By.XPATH, '//div[contains(@class, "baxia-dialog auto")]')
    except NoSuchElementException:
        pass
    else:
        print('iframe可见' if div_baxia_dialog_auto.is_displayed() else 'iframe不可见')
        if div_baxia_dialog_auto.is_displayed():
            iframe = div_baxia_dialog_auto.find_element(By.TAG_NAME, 'iframe')
            driver.switch_to.frame(iframe)
            if driver.find_elements(By.ID, 'nc_1_n1z') : # 滑块验证
                damai_handle_slider_captcha(driver)
            elif driver.find_elements(By.ID, '`nc_1_refresh1`'): # 验证失败，请点击框体重试/请刷新页面
                click_or_refresh_div = driver.find_element(By.ID, '`nc_1_refresh1`')
                driver.refresh() # 刷新
                # if '刷新' in click_or_refresh_div.text:
                #     driver.refresh()
                # elif '点击' in click_or_refresh_div.text:
                #     click_or_refresh_div.click()
            elif driver.find_elements(By.XPATH, '//div[contains(text(), "网络拥堵")]'): # 网络拥堵，刷新
                driver.switch_to.default_content()
                # cancel = driver.find_element(By.XPATH, '//div[@class="baxia-dialog-close" and text()="X"]')
                # cancel.click()
                # print('点击了×按钮')
                if mode == 0:
                    print('网络拥堵，刷新网页')
                    driver.refresh()
                    return 'refresh'
                elif mode == 1:
                    print('网络拥堵，返回到选票页面')
                    driver.get(page_1_url)
                    return 'back'
            else:
                print('其他？')
            driver.switch_to.default_content()

def damai_page_2(driver):
    """提交订单页面，主要是选择观演人,
    https://m.damai.cn/app/dmfe/h5-ultron-buy/index.html?buyParam=..."""
    global is_need_refresh
    if is_need_refresh == 1:
        # 计算当前时间和开票时间之间的时间差，小于interval_time则开始刷新页面
        refresh_until_time(driver, ticket_time, interval_time)

    app = WebDriverWait(driver, 2, 0.001).until(EC.presence_of_element_located((By.ID, 'app')))
    try:
        div_refresh = driver.find_element(By.XPATH, '//div[@id="app"]//div[text()="刷新"]')
    except NoSuchElementException:
        pass
    else:
        if div_refresh.is_enabled():
            div_refresh.click()
        else:
            driver.execute_script("arguments[0].click();", div_refresh)

    damai_handle_div_confirm(driver)

    if damai_handle_iframe(driver, mode) in ('refresh', 'back'): # 如果返回refresh 或 back，代表刷新了页面
        return 'continue'

    damai_choose_viewer(driver, viewer.split('|'))

    try:
        btn = driver.find_element(By.XPATH, '//span[text()="提交订单"]/..')
    except NoSuchElementException: # 没有提交订单按钮
        return 'continue' # 返回给主函数，continue
    else:
        if btn.is_enabled():
            btn.click()
        else:
            # driver.execute_script("arguments[0].click();", btn)
            actions = ActionChains(driver)
            actions.move_to_element(btn).click().perform()

def damai_priority_purchase_qualification_redemption_page(driver):
    """优先购资格兑换页(要开设备仿真才能点击btn_2)
    https://m.taopiaopiao.com/tickets/vip/pages/rewards-detail/index.html..."""
    global is_need_refresh
    while True:
        if is_need_refresh == 1:
            # 计算当前时间和开票时间之间的时间差，小于interval_time则开始刷新页面
            refresh_until_time(driver, ticket_time, interval_time)

        WebDriverWait(driver, 2, 0.001).until(EC.visibility_of_element_located((By.XPATH, '//div[@class="bui-card"]')))
        btn = driver.find_element(By.XPATH, '//div[@class="bt"]//div[contains(@class, "bt-left")]')
        print(btn.text)
        if 'disable' in btn.get_attribute('class'):
            driver.refresh()
        else:
            driver.execute_script("arguments[0].click();", btn)
            break

    btn_2 = WebDriverWait(driver, 2, 0.001).until(EC.element_to_be_clickable((By.XPATH, '//div[@class="btn js-exchange-bt"]')))
    btn_2.click() # 不能js点击，不能动作链

def damai_main(url):
    global page_1_url
    if 'm.damai.cn/damai/minilogin/index.html' in url:
        damai_login(account, pwd)
    if 'm.damai.cn/damai/mine/my/index.html' in url:
        get_cookies(account)
    if 'm.damai.cn/damai/detail/item.html?itemId=' in url:
        page_1_url = url
        damai_page_1(driver)
    elif 'm.damai.cn/app/dmfe/h5-ultron-buy/index.html?buyParam=' in url:
        if damai_page_2(driver) == 'continue':
            return 'continue'
    elif 'mclient.alipay.com' in url:
        print('恭喜你！抢到票了')
        return 'break'

def maoyan_choose_price(driver, prices: list):
    WebDriverWait(driver, 2, 0.001).until(
        EC.visibility_of_any_elements_located((By.XPATH, '//div[@id="ticket-list-wrap"]/div'))
    ) # 所有的价格按钮

    btns = []
    for price in prices:
        btn = driver.find_element(By.XPATH, '//span[@class="price" and contains(text(), "{}")]/../..'.format(price))
        btns.append(btn)

    count = 0 # 记录缺货登记的票价数量
    for btn_price in btns:
        try:
            btn_price.find_element(By.XPATH, './/span[contains(text(),"缺货登记")]')    
        except NoSuchElementException: # 该价位没有“缺货登记”标志，表示可选
            # 方法一，有些场次的有些价位会自动取消选定
            driver.execute_script("arguments[0].click();", btn_price)
            print('click了一下')
            # 方法二，但是在开启设备模拟仿真时会造成代码堵塞
            # actions = ActionChains(driver)
            # actions.move_to_element(btn_price).click().perform()
            return
        else: # 该价位有“缺货登记”标志，表示不可选
            count += 1
    if count == len(btns):
        return 'refresh'

def maoyan_choose_num(driver, num):
    try:
        plus = WebDriverWait(driver, 2, 0.001).until(EC.element_to_be_clickable((By.XPATH, '//div[contains(@class, "ticket-number-select-add")]')))
        value = driver.find_element(By.XPATH, '//div[contains(@class, "ticket-number-select-amount")]')

        # while value.text[0] != '1':
        #     minus.click()
        for i in range(int(num)-1):
            driver.execute_script("arguments[0].click();", plus)
        try:
            assert value.text[0] == num
        except AssertionError:
            print('实际选择数量不等于{num}')
    except NoSuchElementException:
        print("页面不可选择数量")

def maoyan_choose_viewer(driver, viewer: list[str]):
    for i in viewer:
        try:
            checkbox = driver.find_element(By.XPATH, f'//div[@class="wrapper__list"]//*[text()="{i}"]/../../..')
        except NoSuchElementException:
            pass
        else:
            if 'selected' not in checkbox.get_attribute('class'):
                driver.execute_script("arguments[0].click();", checkbox)

def maoyan_page_1(driver):
    """https://show.maoyan.com/qqw#/detail/..."""
    global is_need_refresh
    if is_need_refresh == 1:
        # 计算当前时间和开票时间之间的时间差，小于interval_time则开始刷新页面
        refresh_until_time(driver, ticket_time, interval_time)

    btn = WebDriverWait(driver, 2, 0.001).until(EC.element_to_be_clickable((By.XPATH, '//div[@class="bottom-button"]/div')))
    print(btn.text, end='\r')
    if '立即' in btn.text:
        driver.execute_script("arguments[0].click();", btn)
    else:
        driver.refresh()

def maoyan_page_2(driver):
    """https://show.maoyan.com/qqw#/ticket-level?id=..."""
    # 选择日期
    try:
        date_btn= driver.find_element(By.XPATH, f'//span[contains(text(), "{dates}")]/../..')
        if 'selected' not in date_btn.get_attribute('class'):
            driver.execute_script("arguments[0].click();", date_btn)
    except NoSuchElementException:
        return 'continue'
    
    WebDriverWait(driver, 2, 0.001).until(EC.invisibility_of_element_located((By.XPATH, "//div[@class='lx-load-mark']"))) # 很关键，不然会自动取消已选择的票档
    time.sleep(0.05) # 关键
    # 选择价格
    maoyan_choose_price(driver, prices.split('|'))

    # 选择数量
    maoyan_choose_num(driver, num)
    
    # 确认按钮
    btn = driver.find_element(By.XPATH, '//div[@class="button" and text()="确认"]')
    driver.execute_script("arguments[0].click();", btn)
    
    WebDriverWait(driver, 2, 0.001).until(EC.invisibility_of_element_located((By.XPATH, "//div[@class='lx-load-mark']"))) # 很关键
    # break

def maoyan_page_3(driver):
    try:
        resume_btn = driver.find_element(By.XPATH, '//div[@class="mask"]//div[@class="refresh__button"]')
        print(resume_btn.get_attribute('class'))
        if 'disabled' in resume_btn.get_attribute('class'):
            return 'continue'
        else:
            driver.execute_script("arguments[0].click();", resume_btn)    
    except:
        pass
            
    try:
        WebDriverWait(driver, 2, 0.001).until(EC.presence_of_all_elements_located((By.XPATH, '//div[@class="wrapper__list"]/*')))
        driver.find_element(By.ID, 'yodaBox')
    except NoSuchElementException:
        print('没有滑块？')
        maoyan_choose_viewer(driver, viewer.split('|'))

        # template_script = 'document.querySelector("#loading > div.body-wrap > div.main > div.wrapper > div.wrapper__list > div:nth-child({})").click();'
        # for i in range(1, int(num) + 1):
        #     script_i = template_script.format(i)
        #     driver.execute_script(script_i)

        script2 = 'document.querySelector("#loading > div.body-wrap > div.submit-b.w-block.focus-hidden.flex-sb.mb-outline-t > button").click();'
        time.sleep(maoyan_page_3_interval)     
        driver.execute_script(script2)

        WebDriverWait(driver, 2, 0.001).until(EC.invisibility_of_element_located((By.XPATH, "//div[@class='lx-load-mark']"))) # 很关键
    else:
        print('请进行滑块验证')
        # maoyan_handle_captcha(driver)
        WebDriverWait(driver, 5, 0.001).until(EC.invisibility_of_element_located((By.ID, 'yodaBox')))  

def maoyan_main(url):
    if 'show.maoyan.com/qqw#/detail/' in url:
        maoyan_page_1(driver)
    if 'show.maoyan.com/qqw#/ticket-level?id=' in url:
        maoyan_page_2(driver)
    if 'show.maoyan.com/qqw/confirm?' in url:
        maoyan_page_3(driver)

def main():
    url = ""
    last_url = ""

    while True:
        url = driver.current_url
        if url != last_url:
            print('goto: ' + url)
        last_url = url
        try:
            if 'damai' in url or 'mclient.alipay.com' in url:
                flag = damai_main(url)
                if flag == 'continue':
                    continue
                if flag == 'break':
                    break
            if 'taopiaopiao' in url: # 大麦优先购（淘票票）
                if 'm.taopiaopiao.com/tickets/vip/pages/rewards-detail/index.html' in url:
                    damai_priority_purchase_qualification_redemption_page(driver)
            if 'maoyan' in url:
                maoyan_main(url)
        except Exception as exc:
            error_message = str(exc)
            left_part = None
            if "Stacktrace:" in error_message:
                left_part = error_message.split("Stacktrace:")[0]
                print(left_part)
            else:
                print(traceback.format_exc())


if __name__ == '__main__':
    print('INFO: 大麦可以选多个日期，猫眼只能选一个')
    app_root = get_app_root()
    filename = os.path.join(app_root, '大麦猫眼config.xlsx')
    selected_cols = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
    config = excel_to_list_dict(file_path=filename, selected_cols=selected_cols)
    print(f'###读取配置文件{filename}###')
    i = int(input('ID：'))

    try:
        maoyan_or_damai = str(config[i]['maoyan_or_damai'])
        account = str(config[i]['account'])
        pwd = str(config[i]['pwd'])
        is_direct_page_2 = int(config[i]['is_direct_page_2'])
        mode = int(config[i]['mode'])
        ticket_time_str = str(config[i]['ticket_time_str'])
        interval_time = int(config[i]['interval_time'])
        dates = str(config[i]['dates'])
        prices = str(config[i]['prices'])
        num = str(config[i]['num'])
        viewer = str(config[i]['viewer'])
        maoyan_page_3_interval = float(config[i]['maoyan_page_3_interval'])

        ticket_time = datetime.datetime.strptime(ticket_time_str, '%Y-%m-%d %H:%M:%S')
    except Exception as e:
        print('###出错了，请检查excel的信息是否格式正确###')
        print(e)
        input('按任意键退出程序')
        exit()

    if maoyan_or_damai == '大麦':
        options = webdriver.ChromeOptions()
        if is_direct_page_2 == 1: # # 直接选好价格数量进入page_2
            mode = 0
            is_need_refresh == 1
        else: # 从page_1开始选
            print(0)
    elif maoyan_or_damai == '猫眼':
        is_need_refresh = 1
        options = ChromeOptions()

    page_1_url = ''

    # 隐藏 webdriver 属性
    options.add_argument("--disable-blink-features")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument('--disable-blink-features=AutomationControlledForSecurityByPolicy')

    options.add_argument('--disable-features=TranslateUI')
    options.add_argument('--disable-translate')
    options.add_argument('--disable-web-security')
    options.add_argument("--no-sandbox")

    # 禁止图片、js、css加载
    prefs = {"profile.managed_default_content_settings.images": 2,
                "profile.managed_default_content_settings.javascript": 1,
                'permissions.default.stylesheet': 2}
    options.add_experimental_option("prefs", prefs)

    options.page_load_strategy = 'eager'

    if maoyan_or_damai == '大麦':
        options.add_experimental_option('detach', True)
        options.add_experimental_option('excludeSwitches', ['enable-logging'])

        driver = webdriver.Chrome(options=options)

        driver.get('https://m.damai.cn') # 必须是m.damai.cn (移动端界面)
        if not os.path.exists(account + '_cookies.pkl'):#如果不存在cookie.pkl,就获取一下
            get_cookies(account)
        else:
            set_cookies(account)
            get_cookies(account)
        time.sleep(0.5)
        driver.find_element(By.XPATH, '//div[@class="home-top"]/i').click()
        time.sleep(2)
    elif maoyan_or_damai == '猫眼':
        driver = Chrome(options=options)

    main()
