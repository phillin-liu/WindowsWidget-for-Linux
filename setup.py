from setuptools import setup, find_packages

setup(
    name="widget-panel",
    version="1.0.0",
    description="Linux 版 Windows11 小组件面板（MSN 资讯/实时天气/日期/设置）",
    packages=find_packages(exclude=("debian",)),
    python_requires=">=3.8",
    install_requires=[
        "PyQt5>=5.15",
        "requests>=2.28",
        "Pillow>=9.0",
    ],
    entry_points={
        "console_scripts": [
            "widget-panel=widget_panel.main:main",
        ],
    },
    include_package_data=True,
    package_data={"widget_panel": ["img.png"]},
)
