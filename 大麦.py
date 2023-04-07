# -*- coding: utf-8 -*-
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
import time
import datetime
import traceback


def choose_date(driver, date):
    div = WebDriverWait(driver, 2, 0.001).until(EC.visibility_of_element_located((By.XPATH, f'//div[@class="sku-pop-wrapper"]//div[contains(text(), "{date}")]')))
    driver.execute_script("arguments[0].click();", div)
    
def choose_price(driver, prices: list):
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

def choose_num(driver, num):
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
        
def page_1(driver):
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
            choose_date(driver, date)

            # 选择价格
            flag = choose_price(driver, prices.split('|'))
            if flag == 'refresh':
                print(f'{prices}价位暂时缺货，刷新页面')
                js_code = "var target = document.elementFromPoint(10, 100); target.click();"
                driver.execute_script(js_code)
                continue
            # 选择数量
            choose_num(driver, num)

            # 确定
            buybtn = driver.find_element(By.XPATH, '//div[@class="sku-footer-bottom"]/div[text()="确定"]')
            driver.execute_script("arguments[0].click();", buybtn)
            break

def choose_viewer(driver, viewer: list[str]):
    for i in viewer:
        try:
            checkbox = driver.find_element(By.XPATH, f'//div[@class="viewer"]//div[text()="{i}"]//following-sibling::div[2]/i')
        except NoSuchElementException:
            pass
        else:
            if 'icondanxuan-weixuan_' in checkbox.get_attribute('class'):
                # checkbox.click()
                driver.execute_script("arguments[0].click();", checkbox)

def handle_div_confirm(driver):
    """处理库存不足/同一时间下单人数太多提示：点击取消按钮"""
    div_confirm = driver.find_element(By.ID, 'confirm')
    if div_confirm.find_elements(By.XPATH, './/div[contains(text(), "取消")]'):
        cancel = driver.find_element(By.XPATH, '//div[@id="confirm"]//div[contains(text(), "取消")]')
        cancel.click()
        print('点击了取消按钮')

def handle_slider_captcha(driver):
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

def handle_iframe(driver, mode):
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
            if driver.find_elements(By.ID, 'nc_1_n1z'): # 滑块验证
                handle_slider_captcha(driver)
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

def page_2(driver):
    """提交订单页面，主要是选择观演人,
    https://m.damai.cn/app/dmfe/h5-ultron-buy/index.html?buyParam=..."""
    global is_direct_page_2
    if is_direct_page_2 == 1:
        # 计算当前时间和开票时间之间的时间差
        while True:
            now_time = datetime.datetime.now()
            delta = ticket_time - now_time
            print(delta, end='\r')
            if delta.total_seconds() <= interval_time:
                print('刷新')
                driver.refresh()
                is_direct_page_2 = 0 # 只运行一次
                break

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

    handle_div_confirm(driver)

    if handle_iframe(driver, mode) in ('refresh', 'back'): # 如果返回refresh 或 back，代表刷新了页面
        return 'continue'

    choose_viewer(driver, viewer.split('|'))

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

def priority_purchase_qualification_redemption_page(driver):
    """优先购资格兑换页
    https://m.taopiaopiao.com/tickets/vip/pages/rewards-detail/index.html..."""
    while True:
        WebDriverWait(driver, 2, 0.001).until(EC.visibility_of_element_located((By.XPATH, '//div[@class="bui-card"]')))
        btn = driver.find_element(By.XPATH, '//div[@class="bt"]//div[contains(@class, "bt-left")]')
        print(btn.text)
        if 'disable' in btn.get_attribute('class'):
            driver.refresh()
        else:
            driver.execute_script("arguments[0].click();", btn)
            break

    btn_2 = WebDriverWait(driver, 2, 0.001).until(EC.element_to_be_clickable((By.XPATH, '//div[@class="btn js-exchange-bt"]')))
    driver.execute_script("arguments[0].click();", btn_2)


def main():
    url = ""
    last_url = ""
    global page_1_url
    while True:
        time.sleep(0.1)
        url = driver.current_url
        if url != last_url:
            print('goto: ' + url)
        last_url = url
        try:
            if 'm.damai.cn/damai/detail/item.html?itemId=' in url:
                page_1_url = url
                page_1(driver)
            elif 'm.damai.cn/app/dmfe/h5-ultron-buy/index.html?buyParam=' in url:
                if page_2(driver) == 'continue':
                    continue
            elif 'mclient.alipay.com' in url:
                print('恭喜你！抢到票了')
                break
            elif 'm.taopiaopiao.com/tickets/vip/pages/rewards-detail/index.html' in url:
                priority_purchase_qualification_redemption_page(driver)
        except Exception:
            print('出错了', traceback.format_exc())
            continue


if __name__ == '__main__':
    viewer = input('观演人(多个观演人用|分隔，和票的数量一致)：') # 观演人

    is_direct_page_2 = int(input('是否直接进入订单提交页面(是：1，否：0)：'))
    if is_direct_page_2 == 1: # 直接选好价格数量进入page_2
        mode = 0

        ticket_time_str = input('请输入开票时间(格式为 yyyy-mm-dd HH:MM:SS 如2023-04-07 19:25:00)：')
        # ticket_time_str = '2023-04-07 19:25:00'
        ticket_time = datetime.datetime.strptime(ticket_time_str, '%Y-%m-%d %H:%M:%S')
        
        interval_time = int(input('提前几秒刷新？(输入阿拉伯数字)：'))
    else: # 从page_1开始选
        date = input('日期(yyyy-mm-dd)：')
        prices = input('价格(多个价格用|分隔，越靠前表示优先级越高)：')
        num = input('数量（须和观演人的数量一致）：')

        mode = int(input('网络拥堵策略 刷新则输入0 返回到上一页面则输入1：'))
        # mode = 0

    page_1_url = ''

    options = webdriver.ChromeOptions()

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

    options.add_experimental_option('detach', True)
    options.page_load_strategy = 'eager'

    driver = webdriver.Chrome(options=options)

    driver.get('https://m.damai.cn') # 必须是m.damai.cn (移动端界面)

    main()
