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
POLL_FREQUENCY = 60  # 检查间隔（秒）- 改为10秒，更及时的进度反馈
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
    # 保存主窗口句柄
    main_window = driver.current_window_handle
    
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
        try:
            # 安全地关闭当前标签页并切换回主窗口
            current_window = driver.current_window_handle
            if len(driver.window_handles) > 1:
                driver.close()
                # 切换回主窗口
                if main_window in driver.window_handles:
                    driver.switch_to.window(main_window)
                else:
                    # 如果主窗口句柄不存在，切换到第一个可用窗口
                    driver.switch_to.window(driver.window_handles[0])
            time.sleep(1)  # 防止快速切换导致崩溃
        except Exception as e:
            print(f"窗口切换时出错：{str(e)}")
            # 如果出错，尝试重新创建一个主窗口
            try:
                if len(driver.window_handles) == 0:
                    driver.execute_script("window.open('about:blank');")
                    driver.switch_to.window(driver.window_handles[0])
            except:
                pass


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
        # 打开主页面并检查登录状态
        print("正在检查登录状态...")
        if not check_login_status(driver):
            print("请先登录网站，然后重新运行脚本！")
            return
        
        print("登录状态正常，开始处理视频...")
        video_urls = get_video_urls()
        print(f"总共需要处理 {len(video_urls)} 个视频")
        
        for i, url in enumerate(video_urls, 1):
            print(f"正在处理第 {i}/{len(video_urls)} 个视频")
            watch_video(driver, url)
            time.sleep(2)
            
        print("所有视频处理完成！")
    except Exception as e:
        print(f"主程序出错：{str(e)}")
    finally:
        driver.quit()


if __name__ == "__main__":
    main()