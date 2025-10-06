#!/bin/bash

# ChromeDriver安装脚本 for macOS
echo "=== ChromeDriver安装脚本 ==="

# 检查是否安装了Homebrew
if ! command -v brew &> /dev/null; then
    echo "❌ 未检测到Homebrew，请先安装Homebrew："
    echo "   /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
    exit 1
fi

echo "✅ 检测到Homebrew"

# 检查Chrome是否已安装
if ! ls /Applications/Google\ Chrome.app &> /dev/null; then
    echo "❌ 未检测到Google Chrome浏览器，请先安装Chrome"
    echo "   下载地址: https://www.google.com/chrome/"
    exit 1
fi

echo "✅ 检测到Google Chrome"

# 安装ChromeDriver
echo "📦 正在安装ChromeDriver..."
if brew install chromedriver; then
    echo "✅ ChromeDriver安装成功！"
    
    # 验证安装
    if command -v chromedriver &> /dev/null; then
        echo "✅ ChromeDriver验证成功"
        echo "📍 安装路径: $(which chromedriver)"
        echo "📋 版本信息: $(chromedriver --version)"
    else
        echo "❌ ChromeDriver验证失败"
        exit 1
    fi
else
    echo "❌ ChromeDriver安装失败"
    exit 1
fi

echo ""
echo "🎉 安装完成！现在可以运行爬虫程序了："
echo "   python3 main.py status"