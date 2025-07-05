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
import json
import os
from pathlib import Path

# 配置参数
TXT_PATH = './zlstudy.txt'  # 修改为相对路径
COOKIES_PATH = './cookies.json'  # Cookie存储路径
WAIT_TIMEOUT = 30
POLL_FREQUENCY = 60  # 检查间隔（秒）- 改为10秒，更及时的进度反馈
COMPLETION_THRESHOLD = 1  # 剩余1秒视为完成
VIDEO_SELECTOR = "video.dplayer-video-current"  # 根据页面结构调整
LOGIN_URL = "https://www.zjce.gov.cn/login"
BASE_URL = "https://www.zjce.gov.cn"

def save_cookies(driver):
    """保存当前浏览器的cookies到文件"""
    try:
        cookies = driver.get_cookies()
        with open(COOKIES_PATH, 'w', encoding='utf-8') as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)
        print(f"✅ Cookies已保存到 {COOKIES_PATH}")
        return True
    except Exception as e:
        print(f"❌ 保存cookies失败: {str(e)}")
        return False

def load_cookies(driver):
    """从文件加载cookies到浏览器"""
    try:
        if not os.path.exists(COOKIES_PATH):
            print("📝 未找到cookies文件，需要重新登录")
            return False
        
        with open(COOKIES_PATH, 'r', encoding='utf-8') as f:
            cookies = json.load(f)
        
        # 先访问主站以建立域名上下文
        driver.get(BASE_URL)
        time.sleep(2)
        
        # 加载cookies
        for cookie in cookies:
            try:
                # 清理可能导致问题的字段
                cookie_to_add = {
                    'name': cookie['name'],
                    'value': cookie['value'],
                    'domain': cookie.get('domain', '.zjce.gov.cn')
                }
                
                # 添加可选字段
                if 'path' in cookie:
                    cookie_to_add['path'] = cookie['path']
                if 'secure' in cookie:
                    cookie_to_add['secure'] = cookie['secure']
                if 'httpOnly' in cookie:
                    cookie_to_add['httpOnly'] = cookie['httpOnly']
                    
                driver.add_cookie(cookie_to_add)
            except Exception as e:
                print(f"⚠️  加载cookie失败 {cookie.get('name', 'unknown')}: {str(e)}")
                continue
        
        print("✅ Cookies加载完成")
        return True
    except Exception as e:
        print(f"❌ 加载cookies失败: {str(e)}")
        return False

def check_login_status(driver):
    """检查登录状态"""
    try:
        print("🔍 正在检查登录状态...")
        driver.get("https://www.zjce.gov.cn/videos")
        time.sleep(3)
        
        # 检查是否跳转到登录页面
        if "login" in driver.current_url.lower():
            print("❌ 未登录状态")
            return False
        
        # 检查页面是否包含登录用户信息的元素
        try:
            # 尝试查找用户信息相关的元素（你可能需要根据实际页面调整选择器）
            user_elements = driver.find_elements(By.CSS_SELECTOR, 
                ".user-info, .username, .user-name, [class*='user'], [class*='User']")
            
            # 检查是否有退出登录的按钮
            logout_elements = driver.find_elements(By.CSS_SELECTOR, 
                "[href*='logout'], [onclick*='logout'], .logout, [class*='logout']")
            
            if user_elements or logout_elements:
                print("✅ 已登录状态")
                return True
                
        except Exception as e:
            print(f"⚠️  检查用户元素时出错: {str(e)}")
        
        # 如果没有明显的登录标识，尝试访问一个需要登录的页面
        print("🔍 尝试访问受保护页面验证登录状态...")
        current_url = driver.current_url
        
        # 如果当前在视频列表页且没有跳转到登录页，可能已登录
        if "videos" in current_url and "login" not in current_url:
            print("✅ 疑似已登录状态（基于页面URL判断）")
            return True
            
        print("❌ 登录状态检查失败")
        return False
        
    except Exception as e:
        print(f"❌ 检查登录状态时出错: {str(e)}")
        return False

def interactive_login(driver):
    """交互式登录流程"""
    print("\n" + "="*50)
    print("🔐 需要进行登录操作")
    print("="*50)
    
    try:
        # 打开登录页面
        print("📱 正在打开登录页面...")
        driver.get(LOGIN_URL)
        time.sleep(3)
        
        print("\n请按照以下步骤操作：")
        print("1. 👀 在浏览器中完成登录操作")
        print("2. ✅ 登录成功后，请在此终端按 Enter 键继续...")
        print("3. 💾 系统将自动保存您的登录状态")
        
        input("\n⏸️  登录完成后按 Enter 键继续...")
        
        # 验证登录是否成功
        if check_login_status(driver):
            print("✅ 登录验证成功！")
            save_cookies(driver)
            return True
        else:
            print("❌ 登录验证失败，请重试")
            return False
            
    except Exception as e:
        print(f"❌ 登录过程中出错: {str(e)}")
        return False

def auto_login(driver):
    """自动登录流程：尝试加载cookies，失败则进行交互式登录"""
    print("🚀 开始自动登录流程...")
    
    # 1. 尝试加载已保存的cookies
    if load_cookies(driver):
        # 2. 检查cookies是否有效
        if check_login_status(driver):
            print("🎉 使用已保存的cookies登录成功！")
            return True
        else:
            print("⚠️  已保存的cookies无效，需要重新登录")
    
    # 3. Cookies无效或不存在，进行交互式登录
    print("🔄 开始交互式登录流程...")
    return interactive_login(driver)

def get_video_urls():
    with open(TXT_PATH, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]

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
        print("🎯 浙江继续教育视频自动播放工具")
        print("=" * 50)
        
        # 使用新的自动登录流程
        if not auto_login(driver):
            print("❌ 登录失败，程序退出")
            return
        
        print("\n🎬 开始处理视频列表...")
        video_urls = get_video_urls()
        print(f"📋 总共需要处理 {len(video_urls)} 个视频")
        
        # 在开始处理视频前，再次保存一下cookies（确保是最新的）
        save_cookies(driver)
        
        for i, url in enumerate(video_urls, 1):
            print(f"\n🎥 正在处理第 {i}/{len(video_urls)} 个视频")
            print(f"🔗 URL: {url}")
            
            # 每隔一段时间检查一下登录状态并更新cookies
            if i % 10 == 0:  # 每处理10个视频检查一次
                print("🔄 检查登录状态并更新cookies...")
                if check_login_status(driver):
                    save_cookies(driver)
                else:
                    print("⚠️  登录状态异常，尝试重新登录...")
                    if not auto_login(driver):
                        print("❌ 重新登录失败，程序退出")
                        return
            
            watch_video(driver, url)
            time.sleep(2)
            
        print("\n🎉 所有视频处理完成！")
        print("💾 最终保存登录状态...")
        save_cookies(driver)
        
    except KeyboardInterrupt:
        print("\n⏹️  用户手动停止程序")
        print("💾 保存当前登录状态...")
        save_cookies(driver)
    except Exception as e:
        print(f"❌ 主程序出错：{str(e)}")
        print("💾 尝试保存登录状态...")
        save_cookies(driver)
    finally:
        driver.quit()
        print("🏁 程序结束")


if __name__ == "__main__":
    main()