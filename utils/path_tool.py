"""为整个工程提供统一的路径处理工具，避免路径处理错误"""
import os

def get_project_root() -> str:
    """
    获取项目根目录
    """
    #当前文件的绝对路径
    current_file = os.path.abspath(__file__)
    #当前文件所在目录
    current_dir = os.path.dirname(current_file)
    #再向上一级= 项目根目录
    project_root = os.path.dirname(current_dir)

    return project_root

def get_abs_path(relative_path: str) -> str:
    """传入相对路径，返回基于项目根的绝对路径"""
    project_root = get_project_root()
    return os.path.join(project_root, relative_path)


if __name__ == '__main__':
    print(get_abs_path('config/config.txt'))

