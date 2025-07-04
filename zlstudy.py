import os
os.environ["SE_SELENIUM_MANAGER"] = "0"  # 禁用自动驱动管理

from selenium.webdriver.chrome.service import Service  # 修改为Chrome
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options as ChromeOptions  # 修改为Chrome
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager  # 添加webdriver管理器
import time

# 配置参数
TXT_PATH = './zlstudy.txt'  # 修改为相对路径
WAIT_TIMEOUT = 30
POLL_FREQUENCY = 60  # 检查间隔（秒）
COMPLETION_THRESHOLD = 1  # 剩余1秒视为完成
VIDEO_SELECTOR = "video.dplayer-video-current"  # 根据页面结构调整

def get_video_urls():
    with open(TXT_PATH, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]

def check_login_status(driver):
    driver.get("https://www.zjce.gov.cn/videos")
    if "login" in driver.current_url:
        print("Cookie已失效，需要更新！")
        return False
    return True

def watch_video(driver, url):
    # 新标签页打开
    driver.execute_script("window.open('');")
    driver.switch_to.window(driver.window_handles[-1])
    driver.get(url)

    try:
        # 等待视频加载
        video = WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, VIDEO_SELECTOR)))

        # 点击视频区域激活播放（重要！）
        video.click()
        print("已激活视频交互")

        # 强制通过JavaScript播放（应对点击失效）
        driver.execute_script("arguments[0].play();", video)


        # 监控播放进度
        retry_count = 0
        while True:
            duration = driver.execute_script("return arguments[0].duration", video)
            current_time = driver.execute_script("return arguments[0].currentTime", video)

            if duration is None or current_time is None:
                retry_count += 1
                if retry_count > 3:
                    print("无法获取视频时长，强制结束")
                    break
                time.sleep(3)
                continue

            print(f"进度: {current_time:.1f}/{duration:.1f}s")

            if current_time >= duration - COMPLETION_THRESHOLD:
                print(f"视频播放完成：{url}")
                break

            time.sleep(POLL_FREQUENCY)

    except Exception as e:
        print(f"处理视频时出错：{str(e)}")
    finally:
        # 关闭标签页
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        time.sleep(1)  # 防止快速切换导致崩溃


def main():
    options = ChromeOptions()  # 修改为Chrome选项
    options.add_argument("--mute-audio")
    options.add_argument("--disable-infobars")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_argument("--autoplay-policy=no-user-gesture-required")
    # macOS上添加无头模式选项（可选）
    # options.add_argument("--headless")

    # 使用webdriver-manager自动管理Chrome驱动程序
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    try:
        for url in get_video_urls():
            watch_video(driver, url)
            time.sleep(2)
    finally:
        driver.quit()


if __name__ == "__main__":
    main()