#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
浙江继续教育视频自动播放工具 v2.0

新增功能：
1. 📋 已完成视频记录 - 自动记录并跳过已看完的视频
2. ⚠️  失败视频记录 - 记录播放失败的视频，自动跳过避免重复尝试
3. 🎮 智能进度检测 - 自动检测视频卡住并处理
4. 📊 详细统计信息 - 显示完成、失败、待处理视频数量
5. 💾 自动保存进度 - 程序意外退出时保存已完成记录

文件说明：
- zlstudy.txt: 视频链接列表
- cookies.json: 登录状态保存
- completed_videos.json: 已完成视频记录
- failed_videos.json: 失败视频记录（含失败原因和时间）

使用方法：
1. 将视频链接放入 zlstudy.txt 文件
2. 运行程序，首次需要手动登录
3. 程序会自动处理视频，跳过已完成和失败的视频
4. 失败的视频会被自动记录并跳过，避免重复尝试

作者：AI Assistant
版本：2.0
"""

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
COMPLETED_VIDEOS_PATH = './completed_videos.json'  # 已完成视频记录路径
FAILED_VIDEOS_PATH = './failed_videos.json'  # 失败视频记录路径
WAIT_TIMEOUT = 30
POLL_FREQUENCY = 10  # 检查间隔（秒）- 改为10秒，更及时的进度反馈
COMPLETION_THRESHOLD = 1  # 剩余1秒视为完成
VIDEO_SELECTOR = "video.dplayer-video-current"  # 根据页面结构调整
LOGIN_URL = "https://www.zjce.gov.cn/login"
BASE_URL = "https://www.zjce.gov.cn"
STUCK_DETECTION_INTERVAL = 5  # 检测进度卡住的间隔（秒）
MAX_STUCK_COUNT = 3  # 最大允许进度卡住的次数

def save_completed_videos(completed_videos):
    """保存已完成视频列表到文件"""
    try:
        with open(COMPLETED_VIDEOS_PATH, 'w', encoding='utf-8') as f:
            json.dump(list(completed_videos), f, ensure_ascii=False, indent=2)
        print(f"✅ 已完成视频记录已保存到 {COMPLETED_VIDEOS_PATH}")
        return True
    except Exception as e:
        print(f"❌ 保存已完成视频记录失败: {str(e)}")
        return False

def load_completed_videos():
    """从文件加载已完成视频列表"""
    try:
        if not os.path.exists(COMPLETED_VIDEOS_PATH):
            print("📝 未找到已完成视频记录文件，将创建新记录")
            return set()
        
        with open(COMPLETED_VIDEOS_PATH, 'r', encoding='utf-8') as f:
            completed_list = json.load(f)
        
        completed_videos = set(completed_list)
        print(f"📋 已加载 {len(completed_videos)} 个已完成视频记录")
        
        # 显示最近完成的几个视频（可选）
        if len(completed_videos) > 0:
            print("📝 最近完成的视频:")
            recent_videos = list(completed_videos)[-3:]  # 显示最后3个
            for i, video in enumerate(recent_videos, 1):
                short_url = video if len(video) <= 50 else video[:47] + "..."
                print(f"   {i}. {short_url}")
            if len(completed_videos) > 3:
                print(f"   ... (还有 {len(completed_videos) - 3} 个)")
        
        return completed_videos
    except Exception as e:
        print(f"❌ 加载已完成视频记录失败: {str(e)}")
        return set()

def add_completed_video(completed_videos, video_url):
    """添加已完成视频到记录中"""
    completed_videos.add(video_url)
    save_completed_videos(completed_videos)
    print(f"✅ 已记录完成视频: {video_url}")

def save_failed_videos(failed_videos):
    """保存失败视频列表到文件"""
    try:
        with open(FAILED_VIDEOS_PATH, 'w', encoding='utf-8') as f:
            # 如果是旧格式(只有URL的列表)，转换为新格式
            if failed_videos and isinstance(next(iter(failed_videos)), str):
                failed_dict = {}
                for url in failed_videos:
                    failed_dict[url] = {
                        "reason": "未知原因",
                        "timestamp": "未知时间"
                    }
                json.dump(failed_dict, f, ensure_ascii=False, indent=2)
            else:
                json.dump(failed_videos, f, ensure_ascii=False, indent=2)
        print(f"⚠️  失败视频记录已保存到 {FAILED_VIDEOS_PATH}")
        return True
    except Exception as e:
        print(f"❌ 保存失败视频记录失败: {str(e)}")
        return False

def load_failed_videos():
    """从文件加载失败视频列表"""
    try:
        if not os.path.exists(FAILED_VIDEOS_PATH):
            print("📝 未找到失败视频记录文件，将创建新记录")
            return {}
        
        with open(FAILED_VIDEOS_PATH, 'r', encoding='utf-8') as f:
            failed_data = json.load(f)
        
        # 兼容旧格式(列表)和新格式(字典)
        if isinstance(failed_data, list):
            # 旧格式：转换为新格式
            failed_videos = {}
            for url in failed_data:
                failed_videos[url] = {
                    "reason": "未知原因",
                    "timestamp": "未知时间"
                }
        else:
            # 新格式：直接使用
            failed_videos = failed_data
        
        print(f"⚠️  已加载 {len(failed_videos)} 个失败视频记录")
        
        # 显示最近失败的几个视频（可选）
        if len(failed_videos) > 0:
            print("⚠️  最近失败的视频:")
            recent_failed = list(failed_videos.keys())[-3:]  # 显示最后3个
            for i, url in enumerate(recent_failed, 1):
                short_url = url if len(url) <= 40 else url[:37] + "..."
                reason = failed_videos[url].get("reason", "未知")
                timestamp = failed_videos[url].get("timestamp", "未知")
                print(f"   {i}. {short_url} [{reason}] ({timestamp})")
            if len(failed_videos) > 3:
                print(f"   ... (还有 {len(failed_videos) - 3} 个)")
        
        return failed_videos
    except Exception as e:
        print(f"❌ 加载失败视频记录失败: {str(e)}")
        return {}

def add_failed_video(failed_videos, video_url, reason=""):
    """添加失败视频到记录中"""
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    failed_videos[video_url] = {
        "reason": reason or "未知原因",
        "timestamp": timestamp
    }
    save_failed_videos(failed_videos)
    print(f"⚠️  已记录失败视频: {reason} - {video_url}")

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
    """
    观看视频，支持进度卡住检测
    返回: (是否成功, 失败原因)
    """
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
        stuck_count = 0
        last_time = 0
        stuck_detection_counter = 0
        
        while True:
            duration = driver.execute_script("return arguments[0].duration", video)
            current_time = driver.execute_script("return arguments[0].currentTime", video)

            if duration is None or current_time is None:
                retry_count += 1
                if retry_count > 3:
                    print("❌ 无法获取视频时长，跳过此视频")
                    return False, "无法获取视频时长"
                time.sleep(3)
                continue

            print(f"进度: {current_time:.1f}/{duration:.1f}s")

            # 检查视频是否完成
            if current_time >= duration - COMPLETION_THRESHOLD:
                print(f"✅ 视频播放完成：{url}")
                return True, "播放完成"

            # 进度卡住检测 - 每隔几次检查进度是否有变化
            stuck_detection_counter += 1
            if stuck_detection_counter >= (STUCK_DETECTION_INTERVAL / POLL_FREQUENCY):
                if abs(current_time - last_time) < 0.1:  # 进度几乎没有变化
                    stuck_count += 1
                    print(f"⚠️  检测到进度可能卡住 ({stuck_count}/{MAX_STUCK_COUNT})")
                    
                    if stuck_count >= MAX_STUCK_COUNT:
                        print(f"❌ 视频进度卡住超过{MAX_STUCK_COUNT}次，跳过此视频：{url}")
                        return False, "进度卡住"
                    
                    # 尝试重新激活视频播放
                    try:
                        video.click()
                        driver.execute_script("arguments[0].play();", video)
                        print("🔄 尝试重新激活视频播放")
                    except Exception as e:
                        print(f"⚠️  重新激活播放失败: {str(e)}")
                        
                else:
                    stuck_count = 0  # 重置卡住计数
                
                last_time = current_time
                stuck_detection_counter = 0

            time.sleep(POLL_FREQUENCY)

    except Exception as e:
        print(f"❌ 处理视频时出错：{str(e)}")
        return False, f"处理异常: {str(e)}"
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
            print(f"❌ 窗口切换时出错：{str(e)}")
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
        print("📝 功能说明:")
        print("   ✅ 自动跳过已完成的视频")
        print("   ⚠️  自动跳过失败的视频")
        print("   🎮 智能检测视频卡住并自动处理")
        print("   💾 自动保存学习进度")
        print("   📊 显示详细进度统计")
        print("=" * 50)
        
        # 加载已完成视频列表
        completed_videos = load_completed_videos()
        
        # 加载失败视频列表
        failed_videos = load_failed_videos()
        
        # 使用新的自动登录流程
        if not auto_login(driver):
            print("❌ 登录失败，程序退出")
            return
        
        print("\n🎬 开始处理视频列表...")
        video_urls = get_video_urls()
        total_videos = len(video_urls)
        
        # 过滤掉已完成和失败的视频
        remaining_videos = [url for url in video_urls if url not in completed_videos and url not in failed_videos]
        completed_count = len([url for url in video_urls if url in completed_videos])
        failed_count = len([url for url in video_urls if url in failed_videos])
        
        print(f"📊 视频进度统计:")
        print(f"   📋 总视频数: {total_videos}")
        if total_videos > 0:
            print(f"   ✅ 已完成: {completed_count} ({completed_count/total_videos*100:.1f}%)")
            print(f"   ❌ 已失败: {failed_count} ({failed_count/total_videos*100:.1f}%)")
            print(f"   ⏳ 待处理: {len(remaining_videos)} ({len(remaining_videos)/total_videos*100:.1f}%)")
        else:
            print(f"   ✅ 已完成: {completed_count}")
            print(f"   ❌ 已失败: {failed_count}")
            print(f"   ⏳ 待处理: {len(remaining_videos)}")
        
        if completed_count > 0 or failed_count > 0:
            print(f"   ⏭️  本次跳过: {completed_count + failed_count} 个视频 (已完成: {completed_count}, 已失败: {failed_count})")
        
        if len(remaining_videos) == 0:
            if total_videos == 0:
                print("❌ 未找到任何视频链接，请检查 zlstudy.txt 文件")
            else:
                print("🎉 所有视频都已处理完成！")
            return
        
        # 在开始处理视频前，再次保存一下cookies（确保是最新的）
        save_cookies(driver)
        
        successful_count = 0
        failed_count = 0
        
        for i, url in enumerate(remaining_videos, 1):
            print(f"\n🎥 正在处理第 {i}/{len(remaining_videos)} 个视频")
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
            
            # 观看视频
            video_completed, reason = watch_video(driver, url)
            
            if video_completed:
                # 视频成功完成，记录到已完成列表
                add_completed_video(completed_videos, url)
                successful_count += 1
                print(f"✅ 成功完成视频 {i}/{len(remaining_videos)}")
                
                # 如果这个视频之前在失败列表中，移除它
                if url in failed_videos:
                    del failed_videos[url]
                    save_failed_videos(failed_videos)
                    print(f"🔄 已从失败列表中移除该视频")
            else:
                # 视频失败或卡住，记录到失败列表
                add_failed_video(failed_videos, url, reason)
                failed_count += 1
                print(f"❌ 视频失败，已记录到失败列表 {i}/{len(remaining_videos)}")
            
            time.sleep(2)
            
        print(f"\n🎉 视频处理完成！")
        print(f"📊 统计结果：")
        print(f"   ✅ 成功完成: {successful_count} 个")
        print(f"   ❌ 失败跳过: {failed_count} 个")
        print(f"   📋 总已完成: {len(completed_videos)} 个")
        print(f"   ⚠️  总失败记录: {len(failed_videos)} 个")
        
        # 如果本次有失败的视频，显示详细信息
        if failed_count > 0:
            print(f"\n⚠️  本次失败的视频:")
            current_failed = [url for url in remaining_videos if url in failed_videos]
            for i, url in enumerate(current_failed, 1):
                short_url = url if len(url) <= 50 else url[:47] + "..."
                reason = failed_videos[url].get("reason", "未知")
                print(f"   {i}. {short_url} [{reason}]")
            
            print(f"\n💡 提示：")
            print(f"   - 失败的视频已记录到 {FAILED_VIDEOS_PATH}")
            print(f"   - 这些视频在下次运行时会被自动跳过")
            print(f"   - 如需重新尝试，请手动删除失败记录文件")
        
        print("💾 最终保存登录状态...")
        save_cookies(driver)
        
    except KeyboardInterrupt:
        print("\n⏹️  用户手动停止程序")
        print("💾 保存当前登录状态...")
        save_cookies(driver)
        # 确保已完成视频记录被保存
        if 'completed_videos' in locals():
            save_completed_videos(completed_videos)
        # 确保失败视频记录被保存
        if 'failed_videos' in locals():
            save_failed_videos(failed_videos)
    except Exception as e:
        print(f"❌ 主程序出错：{str(e)}")
        print("💾 尝试保存登录状态...")
        save_cookies(driver)
        # 确保已完成视频记录被保存
        if 'completed_videos' in locals():
            save_completed_videos(completed_videos)
        # 确保失败视频记录被保存
        if 'failed_videos' in locals():
            save_failed_videos(failed_videos)
    finally:
        driver.quit()
        print("🏁 程序结束")


if __name__ == "__main__":
    main()