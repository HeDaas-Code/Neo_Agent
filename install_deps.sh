#!/bin/bash
cd /home/hedass/桌面/Lien_os
source venv/bin/activate

echo "开始安装依赖..."
pip install langchain langchain-core langchain-openai 2>&1 | tee install.log
pip install -e git+https://github.com/HeDaas-Code/pyvdisk.git@1ca863f4373fbb1ec72748922365a733139cf0ff#egg=pyvdisk 2>&1 | tee -a install.log
echo "安装完成！"
